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
import heapq
import socket
import threading
import logging
import re
import psutil
from dataclasses import dataclass
from core.limiter_engine import PolicyStatus, LimitRequest, ASSOCIATED_PROCESSES, SYSTEM_PROTECTED_EXES
from core.speed_utils import speed_str_to_bps as util_speed_str_to_bps, format_policy_summary
from core.traffic_monitor import TrafficMonitor

logger = logging.getLogger("WinDivertEngine")


class TokenBucket:
    """高精度字节级令牌桶算法（赤字欠账式平滑调度与硬封顶架构）"""
    def __init__(self, rate_bytes_per_sec: float, capacity: float = 0, is_blocked: bool = False, max_pacing_delay: float = 0.05):
        self.rate_bytes_per_sec = float(rate_bytes_per_sec)
        # 桶容量设置为较小突发（例如 0.5 秒或最低 2048 字节），防止初始突发过高穿透限速
        self.capacity = float(capacity) if capacity > 0 else max(2048.0, self.rate_bytes_per_sec * 0.5)
        self.tokens = self.capacity
        self.last_refill = time.perf_counter()
        self.is_blocked = is_blocked
        self.max_pacing_delay = float(max_pacing_delay)
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
        尝试扣减令牌（欠账赤字式调度）：
        返回 (is_allowed, wait_time)
        - 如果完全阻断：返回 (False, -1.0)
        - 如果不设限制：返回 (True, 0.0)
        - 如果令牌充足：扣减并返回 (True, 0.0)
        - 如果令牌不足但处于可整形窗口 (wait <= max_pacing_delay)：
          将赤字计入负令牌（欠账），允许进入 Pacer 队列，返回 (False, wait_time)
        - 如果严重超额 (wait > max_pacing_delay)：
          不计入赤字（直接丢弃），返回 (False, wait_time)
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
                # 只有在可平滑延迟窗口内，才计入负债以备 Pacer 延时重注入
                # 这样进入延迟队列的数据包也严格消耗带宽，彻底杜绝 2 倍超速漏洞
                if wait_time <= self.max_pacing_delay:
                    self.tokens -= num_bytes
                return False, wait_time


@dataclass
class ProcessRule:
    app_name: str
    app_path: str
    up_bucket: TokenBucket
    dl_bucket: TokenBucket
    is_up_blocked: bool = False
    is_dl_blocked: bool = False
    up_rate_bps: int = 0
    dl_rate_bps: int = 0
    summary: str = "未限制"

    @property
    def is_blocked(self) -> bool:
        """向后兼容属性：任意方向被阻断时为 True"""
        return self.is_up_blocked or self.is_dl_blocked


class WinDivertEngine:
    """
    WinDivert 内核流量整形引擎 (管理线程、端口追踪、非阻塞队列与数据包分发)
    """
    def __init__(self):
        self.rules: dict[str, ProcessRule] = {}  # key: lower app name, e.g. "steam.exe"
        self.port_to_rules: dict[object, ProcessRule] = {}  # key: (proto, port) or port (原子替换，免锁读取)
        self.port_to_app: dict[object, str] = {}  # key: (proto, port) or port -> app_name
        self.traffic_monitor = TrafficMonitor()
        self._lock = threading.RLock()
        self._running = False
        self._stop_event = threading.Event()
        self._divert_handle = None
        self._divert_thread = None
        self._tracker_thread = None
        self._pacer_thread = None
        self._pacer_cond = threading.Condition(threading.Lock())
        self._pacer_heap: list[tuple[float, int, object]] = []
        self._pacer_seq = 0
        self._pacing_queue = queue.Queue(maxsize=300)
        self._driver_last_error = ""
        self.driver_diag_code = 0
        self.driver_diag_advice = ""
        self._pydivert_available = self._check_pydivert_available()

    @staticmethod
    def parse_driver_error(exc: Exception) -> tuple[int, str, str]:
        """
        深度解析 WinDivert / Windows 底层驱动 Win32 异常
        返回: (win_error_code, error_name, user_friendly_advice)
        """
        winerror = getattr(exc, 'winerror', None)
        msg = str(exc)

        # 尝试从错误文本中正则匹配 [WinError 123]
        if winerror is None:
            m = re.search(r'\[WinError\s+(\d+)\]', msg, re.IGNORECASE)
            if m:
                winerror = int(m.group(1))

        if winerror == 5:
            return 5, "ERROR_ACCESS_DENIED", "权限受限或被杀毒软件 (360/火绒/Defender) 拦截驱动加载，建议添加信任"
        elif winerror == 1275:
            return 1275, "ERROR_DRIVER_BLOCKED", "驱动被系统安全策略或内核隔离 (HVCI) 阻止加载"
        elif winerror == 577:
            return 577, "ERROR_INVALID_IMAGE_HASH", "驱动数字签名无法被系统验证"
        elif winerror in (2, 3):
            return winerror or 2, "ERROR_FILE_NOT_FOUND", "未找到 WinDivert 驱动文件，可能已被杀软查杀隔离"
        elif winerror == 1058:
            return 1058, "ERROR_SERVICE_DISABLED", "WinDivert 系统服务已被禁用"
        elif winerror == 1753:
            return 1753, "ERROR_ENDPOINT_NOT_AVAILABLE", "网络过滤服务终端不可用"

        return winerror or -1, "DRIVER_INITIALIZATION_ERROR", f"驱动初始化失败 ({msg})"

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
            self.driver_diag_code = -1
            self.driver_diag_advice = "未安装 pydivert 驱动依赖库"
            return False
        try:
            import pydivert
            # 以匹配 false 快速测试打开与关闭，不捕获任何实际数据包
            with pydivert.WinDivert("false"):
                pass
            self.driver_diag_code = 0
            self.driver_diag_advice = ""
            return True
        except Exception as e:
            code, name, advice = self.parse_driver_error(e)
            self.driver_diag_code = code
            self.driver_diag_advice = advice
            self._driver_last_error = f"{name}: {advice}"
            logger.debug(f"WinDivert 驱动功能探测失败: {e} -> {advice}")
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
        return util_speed_str_to_bps(speed_type, custom_val, unit)

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

                is_up_blocked = (req.upload_speed_type == "block")
                is_dl_blocked = (req.download_speed_type == "block")
                is_blocked = (is_up_blocked and is_dl_blocked)

                # 计算每秒字节数
                up_bytes_sec = (up_bps // 8) if up_bps > 0 else 0
                dl_bytes_sec = (dl_bps // 8) if dl_bps > 0 else 0

                # 构造摘要文字 (单向阻断精细化显示)
                if is_up_blocked and is_dl_blocked:
                    summary = "⛔ 完全断网 (内核硬阻断)"
                elif is_up_blocked:
                    summary = format_policy_summary(
                        is_blocked=False,
                        up_bps=0,
                        dl_bps=dl_bps,
                        block_tag="⛔ 上传断开"
                    ) + " (上行阻断)"
                elif is_dl_blocked:
                    summary = format_policy_summary(
                        is_blocked=False,
                        up_bps=up_bps,
                        dl_bps=0,
                        block_tag="⛔ 下载断开"
                    ) + " (下行阻断)"
                else:
                    summary = format_policy_summary(
                        is_blocked=False,
                        up_bps=up_bps,
                        dl_bps=dl_bps,
                        block_tag="⛔ 完全断网 (内核硬阻断)"
                    )

                up_bucket = TokenBucket(rate_bytes_per_sec=up_bytes_sec, is_blocked=is_up_blocked)
                dl_bucket = TokenBucket(rate_bytes_per_sec=dl_bytes_sec, is_blocked=is_dl_blocked)

                rule = ProcessRule(
                    app_name=clean_name,
                    app_path=req.app_path,
                    up_bucket=up_bucket,
                    dl_bucket=dl_bucket,
                    is_up_blocked=is_up_blocked,
                    is_dl_blocked=is_dl_blocked,
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

        # 清空并唤醒 Pacer 调度堆
        with self._pacer_cond:
            self._pacer_heap.clear()
            self._pacer_cond.notify_all()

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

        # 清空兼容队列
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
        """扫描活动连接并在锁外构建端口映射表，实现极速原子赋值与协议区分"""
        try:
            with self._lock:
                target_names = set(self.rules.keys())

            new_port_map: dict[object, ProcessRule] = {}
            new_port_to_app: dict[object, str] = {}
            pids_to_name: dict[int, str] = {}
            pids_to_rules: dict[int, ProcessRule] = {}

            for p in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if pname:
                        pids_to_name[p.info['pid']] = pname
                        if pname in target_names:
                            with self._lock:
                                rule = self.rules.get(pname)
                            if rule:
                                pids_to_rules[p.info['pid']] = rule
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            for c in psutil.net_connections(kind='all'):
                if c.pid and c.laddr and hasattr(c.laddr, 'port') and c.laddr.port > 0:
                    port = c.laddr.port
                    proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                    key_proto = (proto, port)

                    if c.pid in pids_to_rules:
                        rule = pids_to_rules[c.pid]
                        new_port_map[key_proto] = rule
                        new_port_map[port] = rule  # 兼容单整数端口回退
                    if c.pid in pids_to_name:
                        name = pids_to_name[c.pid]
                        new_port_to_app[key_proto] = name
                        new_port_to_app[port] = name

            # 原子指针替换，工作收包线程读取时绝对免锁！
            self.port_to_rules = new_port_map
            self.port_to_app = new_port_to_app
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
        专用处理被限速数据包的微秒级平滑延迟放行，使用小顶堆最小延迟调度避免队头阻塞
        """
        while self._running and not self._stop_event.is_set():
            packet_to_send = None
            with self._pacer_cond:
                while not self._pacer_heap and self._running and not self._stop_event.is_set():
                    self._pacer_cond.wait(timeout=0.02)

                if not self._running or self._stop_event.is_set():
                    break

                if self._pacer_heap:
                    now = time.perf_counter()
                    send_at, _, pkt = self._pacer_heap[0]
                    wait_left = send_at - now
                    if wait_left > 0:
                        self._pacer_cond.wait(timeout=min(wait_left, 0.05))
                    else:
                        heapq.heappop(self._pacer_heap)
                        packet_to_send = pkt

            if packet_to_send is not None:
                handle = self._divert_handle
                if handle is not None and self._running:
                    try:
                        handle.send(packet_to_send)
                    except Exception:
                        pass

    def _divert_loop(self, ready_event: threading.Event, start_error: list):
        """
        WinDivert 核心数据包拦截与高速分发循环：
        - 严禁任何 sleep 阻塞！
        - 非受限数据包直接 0 延迟放行，保证全系统其他程序网络毫秒级畅通
        - 受限数据包根据令牌桶状态直接放行或提交延迟优先队列
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
            code, name, advice = self.parse_driver_error(e)
            err_msg = f"{name}: {advice}"
            start_error.append(err_msg)
            self._driver_last_error = err_msg
            logger.error(f"WinDivert 打开句柄异常: {e} ({advice})")
            ready_event.set()
            return

        try:
            while self._running and not self._stop_event.is_set():
                try:
                    packet = divert.recv()
                    if packet is None:
                        continue

                    # 局域网服务发现与多播/广播安全放行保护 (SSDP/mDNS/LLMNR)
                    if hasattr(packet, 'dst_addr') and packet.dst_addr:
                        dst_ip = str(packet.dst_addr)
                        if dst_ip.startswith("224.") or dst_ip.startswith("239.") or dst_ip == "255.255.255.255":
                            divert.send(packet)
                            continue

                    # 极速哈希匹配端口与协议 (读取原子字典，零锁争用)
                    is_outbound = packet.is_outbound
                    port_to_check = packet.src_port if is_outbound else packet.dst_port
                    proto_str = "TCP" if (hasattr(packet, 'tcp') and packet.tcp) else "UDP"
                    proto_key = (proto_str, port_to_check)

                    rule = self.port_to_rules.get(proto_key) or self.port_to_rules.get(port_to_check)
                    app_name = rule.app_name if rule else (self.port_to_app.get(proto_key) or self.port_to_app.get(port_to_check))
                    pkt_len = len(packet.raw) if hasattr(packet, 'raw') and packet.raw else 1500

                    # 记录实时流量统计
                    if app_name:
                        self.traffic_monitor.record_packet(app_name, is_outbound, pkt_len)

                    # 若非受限进程数据包：立即 0 延迟重注入放行！
                    if not rule:
                        divert.send(packet)
                        continue

                    # 若规则判定当前方向为独立阻断：直接丢弃 (不 send)
                    is_blocked = rule.is_up_blocked if is_outbound else rule.is_dl_blocked
                    if is_blocked:
                        continue

                    # 令牌桶消耗判定
                    bucket = rule.up_bucket if is_outbound else rule.dl_bucket
                    allowed, wait_sec = bucket.consume(pkt_len)
                    if allowed:
                        divert.send(packet)
                    else:
                        if wait_sec > 0 and wait_sec <= 0.05:
                            # 将延迟数据包异步推送到 Pacer 优先队列，收包线程绝不等待！
                            with self._pacer_cond:
                                if len(self._pacer_heap) < 300:
                                    self._pacer_seq += 1
                                    heapq.heappush(self._pacer_heap, (time.perf_counter() + wait_sec, self._pacer_seq, packet))
                                    self._pacer_cond.notify()
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
