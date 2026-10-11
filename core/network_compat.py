# -*- coding: utf-8 -*-
"""
网络兼容性防护与冲突避让模块 (core/network_compat.py)
- 检测与诊断 VPN、TUN/TAP 虚拟网卡与第三方游戏加速器环境
- 识别 198.18.x.x 等透明代理虚拟网段
- 优化数据包捕获过滤规则，避免与回环、基础局域网广播产生冲突
- 提供结构化诊断报告与平滑共存建议
"""
import re
import ipaddress
import logging
import psutil
from dataclasses import dataclass, field

logger = logging.getLogger("NetworkCompat")

# 常见虚拟网卡与加速器特征关键字 (忽略大小写)
VIRTUAL_ADAPTER_KEYWORDS = [
    "tap", "tun", "wintun", "wireguard", "openvpn",
    "tailscale", "zerotier", "clash", "sing-box",
    "uu", "uugame", "leigod", "qiyou", "xunyou", "biubiu"
]

# 常见游戏加速器与透明代理进程列表 (进程名小写)
ACCELERATOR_PROCESS_NAMES = {
    "uu.exe": "UU加速器",
    "uugamebooster.exe": "UU加速器",
    "leigod.exe": "雷神加速器",
    "leigodgui.exe": "雷神加速器",
    "qiyou.exe": "奇游加速器",
    "xunyou.exe": "迅游加速器",
    "biubiu.exe": "biubiu加速器",
    "nn.exe": "NN加速器",
    "clash.exe": "Clash内核",
    "clash-verge.exe": "Clash Verge",
    "sing-box.exe": "sing-box内核",
    "v2ray.exe": "V2Ray",
    "xray.exe": "Xray"
}


@dataclass
class NetworkDiagnostic:
    """系统网络环境兼容性诊断报告"""
    has_virtual_adapter: bool = False
    virtual_adapters: list[str] = field(default_factory=list)
    has_tun_ip: bool = False
    tun_ips: list[str] = field(default_factory=list)
    active_accelerators: list[str] = field(default_factory=list)
    is_accelerator_environment: bool = False
    recommended_filter: str = "!loopback and (tcp or udp)"
    summary: str = "标准物理网络环境"


class NetworkCompatManager:
    """网络兼容性分析与冲突避让管理器"""

    def __init__(self):
        self._cached_diagnostic: NetworkDiagnostic = None

    def diagnose(self, force_refresh: bool = False) -> NetworkDiagnostic:
        """
        全面诊断当前操作系统的网络环境
        检测内容：
        1. 是否存在 TUN/TAP、Wintun、WireGuard 等虚拟网络接口
        2. 是否存在 198.18.0.0/15 等典型 TUN 虚拟网段 IP
        3. 是否正在运行游戏加速器或代理客户端
        """
        if self._cached_diagnostic is not None and not force_refresh:
            return self._cached_diagnostic

        diag = NetworkDiagnostic()

        # 1. 检测网卡适配器名称与 IP 地址
        try:
            if_addrs = psutil.net_if_addrs()
            tun_network = ipaddress.ip_network("198.18.0.0/15")

            for if_name, snic_list in if_addrs.items():
                lower_name = if_name.lower()
                is_virt = any(kw in lower_name for kw in VIRTUAL_ADAPTER_KEYWORDS)
                if is_virt:
                    diag.has_virtual_adapter = True
                    diag.virtual_adapters.append(if_name)

                for snic in snic_list:
                    # 仅检测 IPv4
                    if snic.family.name in ("AF_INET", "2"):
                        ip_str = snic.address
                        try:
                            ip_obj = ipaddress.ip_address(ip_str)
                            if ip_obj in tun_network:
                                diag.has_tun_ip = True
                                diag.tun_ips.append(f"{if_name} ({ip_str})")
                        except ValueError:
                            pass
        except Exception as e:
            logger.debug(f"诊断网络适配器异常: {e}")

        # 2. 检测正在运行的加速器/代理进程
        try:
            detected_acc = set()
            for p in psutil.process_iter(['name']):
                try:
                    pname = (p.info['name'] or '').lower()
                    if pname in ACCELERATOR_PROCESS_NAMES:
                        detected_acc.add(ACCELERATOR_PROCESS_NAMES[pname])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            diag.active_accelerators = sorted(list(detected_acc))
        except Exception as e:
            logger.debug(f"诊断加速器进程异常: {e}")

        # 3. 综合判定与生成摘要
        diag.is_accelerator_environment = bool(
            diag.has_virtual_adapter or diag.has_tun_ip or diag.active_accelerators
        )

        if diag.is_accelerator_environment:
            parts = []
            if diag.active_accelerators:
                parts.append(f"加速器/代理: {', '.join(diag.active_accelerators)}")
            if diag.virtual_adapters:
                parts.append(f"虚拟网卡: {len(diag.virtual_adapters)} 个")
            if diag.has_tun_ip:
                parts.append("TUN网段(198.18.x.x)")
            diag.summary = f"检测到加速器/虚拟网络环境 ({' | '.join(parts)})"
        else:
            diag.summary = "标准物理网络环境 (未检测到虚拟网卡冲突)"

        # 4. 构建最优过滤表达式 (显式避开 loopback，保证 TCP/UDP 精准截流)
        diag.recommended_filter = "!loopback and (tcp or udp)"

        self._cached_diagnostic = diag
        return diag

    @staticmethod
    def is_multicast_or_broadcast(ip_str: str) -> bool:
        """
        判断 IP 是否为组播 (224.0.0.0/4) 或有限广播 (255.255.255.255)，
        此类数据包用于局域网服务发现 (SSDP, mDNS, LLMNR)，绝不可予以硬阻断
        """
        if not ip_str:
            return False
        try:
            ip = ipaddress.ip_address(ip_str)
            return ip.is_multicast or ip_str == "255.255.255.255"
        except ValueError:
            return False
