# -*- coding: utf-8 -*-
"""
实时网络流量测速与吞吐监控模块 (TrafficMonitor)
- 提供高精度出站 (Upload) 与入站 (Download) 字节统计
- 兼顾系统全局物理网速 (基于 psutil 差分) 与单进程/单应用独立流量追踪
- 指数移动平均 (EMA) 平滑算法，消除突发抖动，平稳展示
- 线程安全无锁/轻量锁设计，确保微秒级收包循环零拖累
"""
import time
import threading
import logging
import psutil

logger = logging.getLogger("TrafficMonitor")


class TrafficMonitor:
    """
    网络吞吐与速率监控引擎
    """
    def __init__(self, ema_alpha: float = 0.7):
        self.ema_alpha = max(0.01, min(1.0, ema_alpha))
        self._lock = threading.Lock()

        # 内存累加计数器 (当前测量周期内)
        # key: app_name.lower(), value: {'up': int, 'down': int}
        self._acc_bytes: dict[str, dict[str, int]] = {}

        # 最近一次计算得到的每秒速率 (bytes/sec)
        # key: app_name.lower(), value: (up_bytes_sec, down_bytes_sec)
        self._app_rates: dict[str, tuple[float, float]] = {}

        # 连续零流量计数 (用于超时清理不活跃项)
        self._idle_counts: dict[str, int] = {}

        # 全局系统网速监控
        self._last_sys_sent = 0
        self._last_sys_recv = 0
        self._global_up_rate = 0.0
        self._global_down_rate = 0.0
        self._sys_initialized = False

        self._last_tick_time = time.perf_counter()

    def record_packet(self, app_name: str, is_outbound: bool, length: int):
        """
        记录单个数据包的大小 (供收包核心循环高频调用，极轻量)
        :param app_name: 应用程序名称 (如 "steam.exe")
        :param is_outbound: True 为上传出站，False 为下载入站
        :param length: 数据包字节大小
        """
        if not app_name or length <= 0:
            return

        clean_app = app_name.strip().lower()
        key = "up" if is_outbound else "down"

        with self._lock:
            if clean_app not in self._acc_bytes:
                self._acc_bytes[clean_app] = {"up": 0, "down": 0}
            self._acc_bytes[clean_app][key] += length

    def tick(self, now: float = None) -> tuple[float, float]:
        """
        时间步推进：计算当前采样周期的各进程速率与系统全局总速率，并重置周期计数器。
        通常由 1s 定时器驱动。
        返回：(global_up_bytes_sec, global_down_bytes_sec)
        """
        current_time = now if now is not None else time.perf_counter()
        dt = current_time - self._last_tick_time
        if dt <= 0:
            dt = 0.001
        self._last_tick_time = current_time

        # 1. 计算系统全局吞吐 (psutil 差分)
        try:
            counters = psutil.net_io_counters(pernic=False)
            sent = counters.bytes_sent
            recv = counters.bytes_recv

            if self._sys_initialized:
                d_sent = max(0, sent - self._last_sys_sent)
                d_recv = max(0, recv - self._last_sys_recv)
                instant_up = d_sent / dt
                instant_down = d_recv / dt

                # EMA 平滑
                self._global_up_rate = (self.ema_alpha * instant_up) + ((1.0 - self.ema_alpha) * self._global_up_rate)
                self._global_down_rate = (self.ema_alpha * instant_down) + ((1.0 - self.ema_alpha) * self._global_down_rate)
            else:
                self._sys_initialized = True

            self._last_sys_sent = sent
            self._last_sys_recv = recv
        except Exception as e:
            logger.debug(f"读取系统网络计数器异常: {e}")

        # 2. 计算各应用速率
        with self._lock:
            # 拷贝当前周期的累加量并清空
            current_acc = self._acc_bytes
            self._acc_bytes = {}

            all_apps = set(self._app_rates.keys()) | set(current_acc.keys())
            new_rates: dict[str, tuple[float, float]] = {}

            for app in all_apps:
                counts = current_acc.get(app, {"up": 0, "down": 0})
                up_bytes = counts.get("up", 0)
                down_bytes = counts.get("down", 0)

                instant_up = up_bytes / dt
                instant_down = down_bytes / dt

                old_up, old_down = self._app_rates.get(app, (0.0, 0.0))

                # 若本周期有流量，进行 EMA 平滑；若连续无流量，平滑归零
                smooth_up = (self.ema_alpha * instant_up) + ((1.0 - self.ema_alpha) * old_up) if (instant_up > 0 or old_up > 0) else 0.0
                smooth_down = (self.ema_alpha * instant_down) + ((1.0 - self.ema_alpha) * old_down) if (instant_down > 0 or old_down > 0) else 0.0

                # 极小值直接截断为 0
                if smooth_up < 5.0:
                    smooth_up = 0.0
                if smooth_down < 5.0:
                    smooth_down = 0.0

                if smooth_up == 0.0 and smooth_down == 0.0:
                    self._idle_counts[app] = self._idle_counts.get(app, 0) + 1
                    # 连续 5 个周期为 0 时，清理该项
                    if self._idle_counts[app] <= 5:
                        new_rates[app] = (0.0, 0.0)
                else:
                    self._idle_counts[app] = 0
                    new_rates[app] = (smooth_up, smooth_down)

            self._app_rates = new_rates

        return self._global_up_rate, self._global_down_rate

    def get_global_rates(self) -> tuple[float, float]:
        """获取当前全局上传与下载速率 (bytes/sec)"""
        return self._global_up_rate, self._global_down_rate

    def get_app_rate(self, app_name: str) -> tuple[float, float]:
        """获取特定程序的实时速率 (bytes/sec)，返回 (up, down)"""
        if not app_name:
            return 0.0, 0.0
        clean_app = app_name.strip().lower()
        with self._lock:
            return self._app_rates.get(clean_app, (0.0, 0.0))

    def get_all_app_rates(self) -> dict[str, tuple[float, float]]:
        """获取所有已记录应用程序的实时速率映射"""
        with self._lock:
            return dict(self._app_rates)

    def reset(self):
        """重置所有计数器与历史状态"""
        with self._lock:
            self._acc_bytes.clear()
            self._app_rates.clear()
            self._idle_counts.clear()
            self._global_up_rate = 0.0
            self._global_down_rate = 0.0
            self._sys_initialized = False
            self._last_tick_time = time.perf_counter()
