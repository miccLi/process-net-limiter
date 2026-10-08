# -*- coding: utf-8 -*-
"""
WinDivert 内核级流量整形引擎 (高精度无阻塞延迟调度架构)
- 基于微软合规数字签名的 WinDivert (WFP Callout) 内核驱动
- 微秒级无锁令牌桶算法 (Token Bucket) 与独立 Pacer 延迟队列
- 彻底移除收包主循环中的同步 sleep，杜绝拖慢系统全局网络时延
- 严格受控的工作线程生命周期：显式句柄注销、无竞态启停
- 真实驱动可用性探测与多重异常降级护栏
"""
import time
import queue
import threading
import logging
import psutil
from dataclasses import dataclass
from core.limiter_engine import PolicyStatus, LimitRequest, ASSOCIATED_PROCESSES, SYSTEM_PROTECTED_EXES

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
    WinDivert 内核流量整形引擎 (管理线程、端口追踪、非阻塞队列与数据包分发)
    """
    def __init__(self):
        self.rules: dict[str, ProcessRule] = {}  # key: lower app name, e.g. "steam.exe"
        self.port_to_rules: dict[int, ProcessRule] = {}  # key: local port (原子替换，免锁读取)
        self._lock = threading.RLock()
        self._running = False
        self._stop_event = threading.Event()
        self._divert_handle = None
        self._divert_thread = None
        self._tracker_thread = None
        self._pacer_thread = None
        self._pacing_queue = queue.Queue(maxsize=300)
        self._driver_last_error = ""
        self._pydivert_available = self._check_pydivert_available()

    @staticmethod
    def _check_pydivert_available() -> bool:
        try:
            import pydivert
            return True
        except ImportError:
            return False

    def is_driver_available(self) -> bool:
        """检查 WinDivert 驱动模块与依赖库是否已成功安装"""
        return self._pydivert_available

    def is_driver_functional(self) -> bool:
        """真实测试当前权限下 WinDivert 内核驱动是否可以被打开使用"""
        if not self._pydivert_available:
            return False
        try:
            import pydivert
            # 以匹配 false 快速测试打开与关闭，不捕获任何实际数据包
            with pydivert.WinDivert("false"):
                pass
            return True
        except Exception as e:
            self._driver_last_error = str(e)
            logger.debug(f"WinDivert 驱动功能探测失败: {e}")
            return False

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
        """批量下发限速与阻断策略 (毫秒级生效并启动内核抓包与异步整形线程)"""
        if not requests:
            return True, "未指定待配置的程序", self.get_active_policies()

        with self._lock:
            for req in requests:
                clean_name = req.app_name.strip()
                clean_lower = clean_name.lower()

                if clean_lower in SYSTEM_PROTECTED_EXES:
                    logger.warning(f"安全拦截：忽略对系统核心保护进程 '{clean_name}' 的限速操作")
                    continue

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
                        if sub_lower in SYSTEM_PROTECTED_EXES:
                            continue
                        self.rules[sub_lower] = rule

            # 更新端口映射
            self._scan_and_update_ports()

            # 启动抓包、整形与端口跟踪后台工作线程
            ok, err = self._ensure_workers_running()
            if not ok:
                return False, f"WinDivert 驱动启动失败: {err}", self.get_active_policies()

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

            self._scan_and_update_ports()
            if not self.rules:
                self.stop()

        return True, f"已成功移除 {len(app_names)} 个程序的限速规则", self.get_active_policies()

    def remove_all_limits(self) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """一键清除全部限速规则"""
        with self._lock:
            self.rules.clear()
            self.port_to_rules = {}
            self.stop()

        return True, "已一键清除所有内核限速策略", {}

    def stop(self):
        """显式安全停止后台抓包、延迟队列与端口监控工作线程"""
        self._running = False
        self._stop_event.set()

        # 主动关闭底层 WinDivert 句柄，立即中断阻塞在 recv() 处的系统调用
        if self._divert_handle is not None:
            try:
                self._divert_handle.close()
            except Exception:
                pass
            self._divert_handle = None

        # 安全回收工作线程
        for th in [self._divert_thread, self._pacer_thread, self._tracker_thread]:
            if th and th.is_alive():
                try:
                    th.join(timeout=0.4)
                except Exception:
                    pass

        self._divert_thread = None
        self._pacer_thread = None
        self._tracker_thread = None

        # 清空延迟调度队列
        while not self._pacing_queue.empty():
            try:
                self._pacing_queue.get_nowait()
            except Exception:
                break

    def _ensure_workers_running(self) -> tuple[bool, str]:
        """确保工作线程平稳启动；若已在运行则保持，若未运行则初始化并校验驱动"""
        if self._running and self._divert_thread and self._divert_thread.is_alive():
            return True, ""

        # 启动前先停止任何遗留状态
        self.stop()

        self._running = True
        self._stop_event.clear()

        # 启动端口扫描跟踪线程
        self._tracker_thread = threading.Thread(target=self._tracker_loop, daemon=True, name="FlowTracker")
        self._tracker_thread.start()

        # 启动延迟发送整形队列线程 (Pacer)
        self._pacer_thread = threading.Thread(target=self._pacer_loop, daemon=True, name="WinDivertPacer")
        self._pacer_thread.start()

        # 启动核心拦截分发线程
        ready_event = threading.Event()
        start_error = []

        self._divert_thread = threading.Thread(
            target=self._divert_loop,
            args=(ready_event, start_error),
            daemon=True,
            name="WinDivertWorker"
        )
        self._divert_thread.start()

        # 等待驱动句柄初始化就绪 (最多等待 0.8s)
        ready_event.wait(timeout=0.8)
        if start_error:
            self.stop()
            return False, start_error[0]

        return True, ""

    def _scan_and_update_ports(self):
        """扫描活动连接并在锁外构建端口映射表，实现极速原子赋值"""
        try:
            with self._lock:
                target_names = set(self.rules.keys())

            if not target_names:
                self.port_to_rules = {}
                return

            pids_to_rules = {}
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if pname in target_names:
                        with self._lock:
                            rule = self.rules.get(pname)
                        if rule:
                            pids_to_rules[p.info['pid']] = rule
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            new_port_map: dict[int, ProcessRule] = {}
            for c in psutil.net_connections(kind='all'):
                if c.pid and c.pid in pids_to_rules:
                    if c.laddr and hasattr(c.laddr, 'port') and c.laddr.port > 0:
                        new_port_map[c.laddr.port] = pids_to_rules[c.pid]

            # 原子指针替换，工作收包线程读取时绝对免锁！
            self.port_to_rules = new_port_map
        except Exception as e:
            logger.debug(f"更新端口映射异常: {e}")

    def _tracker_loop(self):
        """后台轮询线程：周期性扫描新建立的动态端口，确保多线程并发连接无缝纳入管控"""
        while self._running and not self._stop_event.is_set():
            try:
                with self._lock:
                    has_rules = bool(self.rules)
                if not has_rules:
                    break
                self._scan_and_update_ports()
            except Exception:
                pass
            time.sleep(0.3)

    def _pacer_loop(self):
        """
        独立延迟发送整形线程 (Pacer)：
        专用处理被限速数据包的微秒级平滑延迟放行，彻底消除主收包线程的时延阻塞
        """
        while self._running and not self._stop_event.is_set():
            try:
                item = self._pacing_queue.get(timeout=0.02)
            except queue.Empty:
                continue
            except Exception:
                break

            send_at, packet = item
            now = time.perf_counter()
            wait_left = send_at - now
            if wait_left > 0:
                time.sleep(min(wait_left, 0.05))

            handle = self._divert_handle
            if handle is not None and self._running:
                try:
                    handle.send(packet)
                except Exception:
                    pass

    def _divert_loop(self, ready_event: threading.Event, start_error: list):
        """
        WinDivert 核心数据包拦截与高速分发循环：
        - 严禁任何 sleep 阻塞！
        - 非受限数据包直接 0 延迟放行，保证全系统其他程序网络毫秒级畅通
        - 受限数据包根据令牌桶状态直接放行或提交延迟队列
        """
        try:
            import pydivert
        except ImportError as e:
            start_error.append(str(e))
            ready_event.set()
            return

        filter_str = "!loopback and (tcp or udp)"
        divert = None
        try:
            divert = pydivert.WinDivert(filter_str)
            divert.open()
            self._divert_handle = divert
            ready_event.set()
        except Exception as e:
            start_error.append(str(e))
            self._driver_last_error = str(e)
            logger.error(f"WinDivert 打开句柄异常: {e}")
            ready_event.set()
            return

        try:
            while self._running and not self._stop_event.is_set():
                try:
                    packet = divert.recv()
                    if packet is None:
                        continue

                    # 极速哈希匹配端口 (读取原子字典，零锁争用)
                    is_outbound = packet.is_outbound
                    port_to_check = packet.src_port if is_outbound else packet.dst_port
                    rule = self.port_to_rules.get(port_to_check)

                    # 若非受限进程数据包：立即 0 延迟重注入放行！
                    if not rule:
                        divert.send(packet)
                        continue

                    # 若规则为“完全阻断”：直接丢弃 (不 send)
                    if rule.is_blocked:
                        continue

                    # 令牌桶消耗判定
                    bucket = rule.up_bucket if is_outbound else rule.dl_bucket
                    pkt_len = len(packet.raw) if hasattr(packet, 'raw') and packet.raw else 1500

                    allowed, wait_sec = bucket.consume(pkt_len)
                    if allowed:
                        divert.send(packet)
                    else:
                        if wait_sec > 0 and wait_sec <= 0.05:
                            # 将延迟数据包异步推送到 Pacer 队列，收包线程绝不等待！
                            try:
                                self._pacing_queue.put_nowait((time.perf_counter() + wait_sec, packet))
                            except queue.Full:
                                # 队列满时丢弃，有效触发 TCP 拥塞控制滑动窗口紧缩
                                continue
                        else:
                            # 超出延迟阈值丢弃，锁定硬速率上限
                            continue

                except Exception:
                    if not self._running or self._stop_event.is_set():
                        break
                    continue
        except Exception as e:
            logger.error(f"WinDivert 循环退出: {e}")
        finally:
            if divert is not None:
                try:
                    divert.close()
                except Exception:
                    pass
            self._divert_handle = None
            self._running = False
