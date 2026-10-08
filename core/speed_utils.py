# -*- coding: utf-8 -*-
"""
网络速度计算与格式化工具函数库 (speed_utils)
- 统一管理速度档位到每秒比特数 (bps) 的转换
- 提供自适应单位的可视化格式化 (B/s, KB/s, MB/s, GB/s)
- 统一策略限速摘要生成逻辑
"""


def speed_str_to_bps(speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
    """
    将选择的速度档位转换为每秒比特数 (bps)
    - "block": -1 (完全断开连接/防火墙阻断)
    - "1kb": 8,192 bps (1 KB/s)
    - "100kb": 819,200 bps (100 KB/s)
    - "1000kb": 8,192,000 bps (1000 KB/s, ~1 MB/s)
    - "custom": 根据 custom_val 与 unit 动态换算
    - "none" 或其它: 0 (不限制)
    """
    if speed_type == "block":
        return -1
    elif speed_type == "1kb":
        return 8192
    elif speed_type == "100kb":
        return 819200
    elif speed_type == "1000kb":
        return 8192000
    elif speed_type == "custom":
        u = (unit or "KB/s").strip().upper()
        if u == "GB/S":
            multiplier = 1024 * 1024 * 1024 * 8
        elif u == "MB/S":
            multiplier = 1024 * 1024 * 8
        else:  # 默认 KB/s
            multiplier = 1024 * 8
        bps = int(custom_val * multiplier)
        return max(1000, bps)  # 最低 1000 bps 防止极端非法数值
    return 0


def format_speed_display(bps: int) -> str:
    """将 bps 转换为直观的人类可读速度字符串 (B/s, KB/s, MB/s, GB/s)"""
    if bps <= 0:
        return "不限"
    bytes_sec = bps / 8.0
    if bytes_sec >= 1024 * 1024 * 1024:
        val = bytes_sec / (1024 * 1024 * 1024)
        return f"{val:.1f} GB/s" if val % 1 != 0 else f"{int(val)} GB/s"
    elif bytes_sec >= 1024 * 1024:
        val = bytes_sec / (1024 * 1024)
        return f"{val:.1f} MB/s" if val % 1 != 0 else f"{int(val)} MB/s"
    elif bytes_sec >= 1024:
        val = bytes_sec / 1024
        return f"{val:.1f} KB/s" if val % 1 != 0 else f"{int(val)} KB/s"
    else:
        return f"{int(bytes_sec)} B/s"


def format_policy_summary(is_blocked: bool, up_bps: int = 0, dl_bps: int = 0, block_tag: str = "⛔ 完全断网") -> str:
    """生成统一的限速策略摘要描述文本"""
    if is_blocked:
        return block_tag
    parts = []
    if up_bps > 0:
        parts.append(f"上: {format_speed_display(up_bps)}")
    if dl_bps > 0:
        parts.append(f"下: {format_speed_display(dl_bps)}")
    return " | ".join(parts) if parts else "正常"
