# -*- coding: utf-8 -*-
"""
WinDivert 内核级流量整形引擎
- 基于微软数字签名的 WinDivert (WFP Callout) 内核驱动
- 实现高精度微秒级令牌桶算法 (Token Bucket)
- 支持毫秒级极速生效、入站/出站双向精确控速与游戏 UDP/TCP 全协议硬件级截流
"""
import time
import threading
import logging
import psutil
from dataclasses import dataclass
from core.limiter_engine import PolicyStatus, LimitRequest, ASSOCIATED_PROCESSES

logger = logging.getLogger("WinDivertEngine")

class TokenBucket:
    """高精度字节级令牌桶算法"""
    def __init__(self, rate_bytes_per_sec: float, capacity: float = 0, is_blocked: bool = False):
        self.rate_bytes_per_sec = float(rate_bytes_per_sec)
        # 桶容量设置为较小突发（例如 0.5 秒或最低 2048 字节），防止初始突发过高穿透限速
        self.capacity = float(capacity) if capacity > 0 else max(2048.0, self.rate_bytes_per_sec * 0.5)
        self.tokens = self.capacity
        self.last_refill = time.perf_counter()
        self.is_blocked = is_blocked
        self._lock = threading.Lock()

    def update_rate(self, rate_bytes_per_sec: float, is_blocked: bool = False):
        with self._lock:
            self.rate_bytes_per_sec = float(rate_bytes_per_sec)
            self.is_blocked = is_blocked
            self.capacity = max(2048.0, self.rate_bytes_per_sec * 0.5) if self.rate_bytes_per_sec > 0 else 0
            self.tokens = min(self.tokens, self.capacity)
            self.last_refill = time.perf_counter()

    def refill(self, now: float = None):
        if now is None:
            now = time.perf_counter()
        dt = now - self.last_refill
        if dt > 0 and self.rate_bytes_per_sec > 0:
            self.tokens = min(self.capacity, self.tokens + dt * self.rate_bytes_per_sec)
            self.last_refill = now

    def consume(self, num_bytes: int, now: float = None) -> tuple[bool, float]:
        """
        尝试扣减令牌。
        返回 (is_allowed, wait_time)
        - 如果完全阻断：返回 (False, -1.0)
        - 如果不设限制：返回 (True, 0.0)
        - 如果令牌充足：扣减并返回 (True, 0.0)
        - 如果令牌不足：返回 (False, 需要等待的时间秒数)
        """
        with self._lock:
            if self.is_blocked:
                return False, -1.0
            if self.rate_bytes_per_sec <= 0:
                return True, 0.0

            if now is None:
                now = time.perf_counter()
            self.refill(now)

            if self.tokens >= num_bytes:
                self.tokens -= num_bytes
                return True, 0.0
            else:
                deficit = num_bytes - self.tokens
                wait_time = deficit / self.rate_bytes_per_sec
                return False, wait_time


@dataclass
class ProcessRule:
    app_name: str
    app_path: str
    up_bucket: TokenBucket
    dl_bucket: TokenBucket
    is_blocked: bool
    up_rate_bps: int
    dl_rate_bps: int
    summary: str


class WinDivertEngine:
    """
    WinDivert 内核流量整形引擎 (管理线程、端口追踪与数据包分发)
    """
    def __init__(self):
        self.rules: dict[str, ProcessRule] = {}  # key: lower app name, e.g. "steam.exe"
        self.port_to_rules: dict[int, ProcessRule] = {}  # key: local port
        self._lock = threading.RLock()
        self._running = False
        self._divert_thread = None
        self._tracker_thread = None
        self._pydivert_available = self._check_pydivert_available()

    @staticmethod
    def _check_pydivert_available() -> bool:
        try:
            import pydivert
            return True
        except ImportError:
            return False

    def is_driver_available(self) -> bool:
        """检查 WinDivert 驱动模块与环境是否就绪"""
        return self._pydivert_available

    def get_active_policies(self) -> dict[str, PolicyStatus]:
        """获取当前正在生效的活动限速策略 (微秒级内存回读)"""
        with self._lock:
            results: dict[str, PolicyStatus] = {}
            for app_name, rule in self.rules.items():
                results[app_name] = PolicyStatus(
                    app_name=rule.app_name,
                    is_blocked=rule.is_blocked,
                    upload_bps=rule.up_rate_bps,
                    download_bps=rule.dl_rate_bps,
                    summary=rule.summary
                )
            return results

    def speed_str_to_bps(self, speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
        if speed_type == "block":
            return -1
        elif speed_type == "1kb":
            return 8192
        elif speed_type == "100kb":
            return 819200
        elif speed_type == "1000kb":
            return 8192000
        elif speed_type == "custom":
            multiplier = 1024 * 8
            if unit.upper() == "MB/S":
                multiplier = 1024 * 1024 * 8
            elif unit.upper() == "GB/S":
                multiplier = 1024 * 1024 * 1024 * 8
            bps = int(custom_val * multiplier)
            return max(1000, bps)
        return 0

    def apply_limits_batch(self, requests: list[LimitRequest]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量下发限速与阻断策略 (毫秒级内存生效并启动内核抓包线程)"""
        if not requests:
            return True, "未指定待配置的程序", self.get_active_policies()

        with self._lock:
            for req in requests:
                clean_name = req.app_name.strip()
                clean_lower = clean_name.lower()

                up_bps = self.speed_str_to_bps(req.upload_speed_type, req.custom_upload_val, req.custom_upload_unit)
                dl_bps = self.speed_str_to_bps(req.download_speed_type, req.custom_download_val, req.custom_download_unit)

                is_blocked = (req.upload_speed_type == "block" or req.download_speed_type == "block")

                # 计算每秒字节数
                up_bytes_sec = (up_bps // 8) if up_bps > 0 else 0
                dl_bytes_sec = (dl_bps // 8) if dl_bps > 0 else 0

                # 构造摘要文字
                if is_blocked:
                    summary = "⛔ 完全断网 (内核硬阻断)"
                else:
                    parts = []
                    if up_bps > 0:
                        parts.append(f"上: {up_bps // 8192} KB/s")
                    if dl_bps > 0:
                        parts.append(f"下: {dl_bps // 8192} KB/s")
                    summary = " | ".join(parts) if parts else "已限速"

                up_bucket = TokenBucket(rate_bytes_per_sec=up_bytes_sec, is_blocked=is_blocked)
                dl_bucket = TokenBucket(rate_bytes_per_sec=dl_bytes_sec, is_blocked=is_blocked)

                rule = ProcessRule(
                    app_name=clean_name,
                    app_path=req.app_path,
                    up_bucket=up_bucket,
                    dl_bucket=dl_bucket,
                    is_blocked=is_blocked,
                    up_rate_bps=up_bps,
                    dl_rate_bps=dl_bps,
                    summary=summary
                )
                self.rules[clean_lower] = rule

                # 同时展开关联子进程 (例如 steam.exe -> steamwebhelper.exe)
                if clean_lower in ASSOCIATED_PROCESSES:
                    for sub_app in ASSOCIATED_PROCESSES[clean_lower]:
                        sub_lower = sub_app.strip().lower()
                        self.rules[sub_lower] = rule

            # 更新端口映射
            self._update_port_mapping_locked()

            # 确保抓包与跟踪线程处于运行状态
            self._ensure_workers_running()

        return True, f"已通过 WinDivert 内核引擎成功为 {len(requests)} 个程序下发精准限速规则", self.get_active_policies()

    def remove_limits_batch(self, app_names: list[str]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量移除限速规则"""
        with self._lock:
            for name in app_names:
                clean_lower = name.strip().lower()
                self.rules.pop(clean_lower, None)
                if clean_lower in ASSOCIATED_PROCESSES:
                    for sub_app in ASSOCIATED_PROCESSES[clean_lower]:
                        self.rules.pop(sub_app.strip().lower(), None)

            self._update_port_mapping_locked()
            if not self.rules:
                self.stop()

        return True, f"已成功移除 {len(app_names)} 个程序的限速规则", self.get_active_policies()

    def remove_all_limits(self) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """一键清除全部限速规则"""
        with self._lock:
            self.rules.clear()
            self.port_to_rules.clear()
            self.stop()

        return True, "已一键清除所有内核限速策略", {}

    def stop(self):
        """停止后台抓包与端口监控线程"""
        self._running = False

    def _ensure_workers_running(self):
        if not self._running:
            self._running = True
            self._tracker_thread = threading.Thread(target=self._tracker_loop, daemon=True, name="FlowTracker")
            self._tracker_thread.start()
            self._divert_thread = threading.Thread(target=self._divert_loop, daemon=True, name="WinDivertWorker")
            self._divert_thread.start()

    def _update_port_mapping_locked(self):
        """扫描活动连接并更新 本地端口 -> ProcessRule 的极速哈希映射表"""
        new_port_map: dict[int, ProcessRule] = {}
        try:
            # 建立 pid -> rule 索引
            target_names = set(self.rules.keys())
            if not target_names:
                self.port_to_rules = {}
                return

            pids_to_rules = {}
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if pname in self.rules:
                        pids_to_rules[p.info['pid']] = self.rules[pname]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # 遍历所有网络连接 (耗时约 2ms)
            for c in psutil.net_connections(kind='all'):
                if c.pid and c.pid in pids_to_rules:
                    if c.laddr and hasattr(c.laddr, 'port') and c.laddr.port > 0:
                        new_port_map[c.laddr.port] = pids_to_rules[c.pid]

            self.port_to_rules = new_port_map
        except Exception as e:
            logger.debug(f"更新端口映射异常: {e}")

    def _tracker_loop(self):
        """后台轮询线程：周期性扫描新建立的动态端口，确保多线程并发连接无缝纳入管控"""
        while self._running:
            try:
                with self._lock:
                    if not self.rules:
                        break
                    self._update_port_mapping_locked()
            except Exception:
                pass
            time.sleep(0.3)  # 每 300ms 刷新一次端口表

    def _divert_loop(self):
        """WinDivert 核心数据包拦截与令牌桶整形循环"""
        try:
            import pydivert
        except ImportError:
            return

        filter_str = "!loopback and (tcp or udp)"
        try:
            with pydivert.WinDivert(filter_str) as divert:
                while self._running:
                    try:
                        packet = divert.recv()
                        if packet is None:
                            continue

                        # 匹配数据包端口
                        rule = None
                        is_outbound = packet.is_outbound
                        port_to_check = packet.src_port if is_outbound else packet.dst_port

                        with self._lock:
                            rule = self.port_to_rules.get(port_to_check)

                        # 若非受限进程的数据包，立即 0 延迟重注入放行
                        if not rule:
                            divert.send(packet)
                            continue

                        # 检查完全阻断
                        if rule.is_blocked:
                            # 丢弃数据包 (直接不调用 divert.send)
                            continue

                        # 令牌桶整形判定
                        bucket = rule.up_bucket if is_outbound else rule.dl_bucket
                        pkt_len = len(packet.raw) if hasattr(packet, 'raw') and packet.raw else 1500

                        allowed, wait_sec = bucket.consume(pkt_len)
                        if allowed:
                            divert.send(packet)
                        else:
                            if wait_sec > 0 and wait_sec <= 0.05:
                                # 极小延迟：微秒级休眠后放行，形成极其平滑的物理流量波形
                                time.sleep(wait_sec)
                                divert.send(packet)
                            else:
                                # 超出延迟上限：直接丢弃以迫使远端滑动窗口紧缩并维持 1KB/s 硬上限
                                continue

                    except Exception as e:
                        # 避免单包异常打断整个循环
                        if not self._running:
                            break
                        continue
        except Exception as e:
            logger.error(f"WinDivert 运行时异常: {e}")
        finally:
            self._running = False
