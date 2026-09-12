# -*- coding: utf-8 -*-
"""
实时网速监控引擎
通过差量采样 Windows 进程 I/O 字节流 (Read/Write Delta)，
计算每个进程及进程家族的实时下载速率 (Down) 与实时上传速率 (Up)。
"""
import time
import psutil
from dataclasses import dataclass

@dataclass
class ProcessSpeed:
    download_bytes_per_sec: float = 0.0
    upload_bytes_per_sec: float = 0.0

class SpeedMonitor:
    def __init__(self):
        # 记录上一时间戳与读写字节数: {pid: (timestamp, read_bytes, write_bytes)}
        self._prev_stats: dict[int, tuple[float, int, int]] = {}

    def update_and_get_speeds(self) -> dict[int, ProcessSpeed]:
        """
        采样当前进程 I/O 状态，计算各 PID 自上次采样以来的瞬时网速 (B/s)。
        """
        now = time.time()
        results: dict[int, ProcessSpeed] = {}
        current_pids = set()

        for proc in psutil.process_iter(["pid"]):
            pid = proc.info.get("pid")
            if pid is None or pid == 0:
                continue
            current_pids.add(pid)

            try:
                io = proc.io_counters()
                r_bytes = io.read_bytes
                w_bytes = io.write_bytes
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                continue

            prev = self._prev_stats.get(pid)
            if prev is not None:
                prev_time, prev_r, prev_w = prev
                dt = now - prev_time
                if dt >= 0.2:
                    dl_speed = max(0.0, (r_bytes - prev_r) / dt)
                    up_speed = max(0.0, (w_bytes - prev_w) / dt)
                    results[pid] = ProcessSpeed(
                        download_bytes_per_sec=dl_speed,
                        upload_bytes_per_sec=up_speed
                    )

            self._prev_stats[pid] = (now, r_bytes, w_bytes)

        # 清除终止的 PID
        dead_pids = set(self._prev_stats.keys()) - current_pids
        for dpid in dead_pids:
            self._prev_stats.pop(dpid, None)

        return results

    @staticmethod
    def format_speed(bytes_per_sec: float) -> str:
        """格式化网速为易读文本"""
        if bytes_per_sec < 1024:
            if bytes_per_sec >= 10:
                return f"{bytes_per_sec:.0f} B/s"
            return "—"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024.0:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024.0 * 1024.0):.2f} MB/s"
        else:
            return f"{bytes_per_sec / (1024.0 * 1024.0 * 1024.0):.2f} GB/s"
