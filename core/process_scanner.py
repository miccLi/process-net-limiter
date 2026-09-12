# -*- coding: utf-8 -*-
"""
进程扫描与进程家族智能树状分组引擎
- 扫描系统当前运行进程与实时网速
- 进程家族 (Process Family) 聚合：类似 Windows 任务管理器的父子多级折叠菜单
- 优先级排序：被限速家族置顶 > 下载器 > 网盘 > 游戏 > 活跃网络家族 > 普通后台
"""
import os
import re
import psutil
from dataclasses import dataclass, field
from enum import Enum
from core.limiter_engine import PolicyStatus
from core.speed_monitor import ProcessSpeed

class ProcessCategory(Enum):
    DOWNLOADER = ("下载器", "⚡", "#8b5cf6", 1)
    CLOUD_DRIVE = ("网盘", "☁️", "#06b6d4", 2)
    GAME = ("游戏", "🎮", "#10b981", 3)
    BROWSER_SOCIAL = ("浏览器/通讯", "🌐", "#f59e0b", 4)
    OTHER = ("系统/其它", "⚙️", "#94a3b8", 5)

    def __init__(self, display_name: str, icon: str, color: str, priority: int):
        self.display_name = display_name
        self.icon = icon
        self.color = color
        self.priority = priority

# 常见特征库
DOWNLOADER_EXES = {
    "thunder.exe", "downloadsdkserver.exe", "idman.exe", "fdm.exe", "aria2c.exe",
    "qbittorrent.exe", "bittorrent.exe", "utorrent.exe", "motrix.exe", "deluge.exe",
    "transmission-qt.exe", "xdm.exe", "eagleget.exe", "bitcomet.exe", "folx.exe",
    "p2psearcher.exe", "baidudl.exe"
}

CLOUD_DRIVE_EXES = {
    "onedrive.exe", "baidunetdisk.exe", "baidunetdiskhost.exe", "aliyunpan.exe",
    "123pan.exe", "quark.exe", "quarkbrowser.exe", "googledrivefs.exe", "dropbox.exe",
    "nutstore.exe", "jianguoyun.exe", "icloud.exe", "icloudservices.exe", "lanzou.exe",
    "pikpak.exe", "weiyun.exe", "ctfile.exe", "terabox.exe", "mega.exe", "megasync.exe"
}

GAME_EXES = {
    "steam.exe", "steamservice.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "riotclientservices.exe", "wegame.exe", "yuanshen.exe", "genshinimpact.exe",
    "starrail.exe", "honkaistarrail.exe", "cs2.exe", "csgo.exe", "dota2.exe",
    "pubg.exe", "valorant.exe", "leagueclient.exe", "minecraft.exe", "javaw.exe",
    "battle.net.exe", "origin.exe", "ea.exe", "eadesktop.exe", "uplay.exe", "upc.exe",
    "blackmythwukong.exe", "naraka.exe", "overwatch.exe", "apex.exe", "r5apex.exe",
    "crossfire.exe", "dnf.exe", "tora.exe", "cyberpunk2077.exe", "gta5.exe", "witcher3.exe"
}

BROWSER_SOCIAL_EXES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe",
    "wechat.exe", "wechatappex.exe", "qq.exe", "dingtalk.exe", "feishu.exe",
    "discord.exe", "telegram.exe", "slack.exe", "skype.exe", "thunderbird.exe"
}

# 预设家族映射 (应用族标识, 友好名称)
KNOWN_FAMILIES = {
    "steam.exe": ("Steam", "Steam 客户端"),
    "steamwebhelper.exe": ("Steam", "Steam 客户端"),
    "steamservice.exe": ("Steam", "Steam 客户端"),
    "onedrive.exe": ("OneDrive", "Microsoft OneDrive"),
    "filesyncconfig.exe": ("OneDrive", "Microsoft OneDrive"),
    "filesynchelper.exe": ("OneDrive", "Microsoft OneDrive"),
    "filecoauth.exe": ("OneDrive", "Microsoft OneDrive"),
    "baidunetdisk.exe": ("BaiduNetdisk", "百度网盘"),
    "baidunetdiskhost.exe": ("BaiduNetdisk", "百度网盘"),
    "thunder.exe": ("Thunder", "迅雷下载"),
    "downloadsdkserver.exe": ("Thunder", "迅雷下载"),
    "xunlei.exe": ("Thunder", "迅雷下载"),
    "epicgameslauncher.exe": ("EpicGames", "Epic Games 启动器"),
    "epicwebhelper.exe": ("EpicGames", "Epic Games 启动器"),
    "chrome.exe": ("Chrome", "Google Chrome 浏览器"),
    "msedge.exe": ("Edge", "Microsoft Edge 浏览器"),
    "firefox.exe": ("Firefox", "Mozilla Firefox 浏览器"),
    "wechat.exe": ("WeChat", "微信 WeChat"),
    "wechatappex.exe": ("WeChat", "微信 WeChat"),
    "qq.exe": ("QQ", "腾讯 QQ"),
    "qqprotect.exe": ("QQ", "腾讯 QQ"),
    "dingtalk.exe": ("DingTalk", "钉钉 DingTalk"),
    "feishu.exe": ("Feishu", "飞书 Feishu"),
    "aliyunpan.exe": ("AliyunPan", "阿里云盘"),
    "123pan.exe": ("123Pan", "123 云盘"),
    "qbittorrent.exe": ("qBittorrent", "qBittorrent"),
    "idman.exe": ("IDM", "Internet Download Manager"),
}

@dataclass
class ProcessItem:
    pid: int
    name: str
    exe_path: str
    category: ProcessCategory
    connections_count: int
    is_limited: bool
    limit_summary: str
    sort_priority: int
    download_speed: float = 0.0
    upload_speed: float = 0.0
    selected: bool = False

@dataclass
class ProcessFamily:
    family_id: str
    display_name: str
    category: ProcessCategory
    children: list[ProcessItem] = field(default_factory=list)
    is_limited: bool = False
    limit_summary: str = "正常"
    total_connections: int = 0
    total_download_speed: float = 0.0
    total_upload_speed: float = 0.0
    sort_priority: int = 6
    selected: bool = False

def classify_process(name: str, exe_path: str) -> ProcessCategory:
    name_lower = name.lower()
    path_lower = exe_path.lower() if exe_path else ""

    if name_lower in DOWNLOADER_EXES or any(k in path_lower for k in ["thunder", "xunlei", "idm", "qbittorrent", "bittorrent", "aria2", "motrix"]):
        return ProcessCategory.DOWNLOADER
    if name_lower in CLOUD_DRIVE_EXES or any(k in path_lower for k in ["onedrive", "baidunetdisk", "aliyunpan", "123pan", "nutstore", "jianguoyun", "dropbox", "googledrive"]):
        return ProcessCategory.CLOUD_DRIVE
    if name_lower in GAME_EXES or any(k in path_lower for k in ["steam", "epic games", "riot games", "wegame", "genshin", "starrail", "games", "game"]):
        return ProcessCategory.GAME
    if name_lower in BROWSER_SOCIAL_EXES or any(k in path_lower for k in ["chrome", "edge", "firefox", "wechat", "tencent"]):
        return ProcessCategory.BROWSER_SOCIAL
    return ProcessCategory.OTHER

def scan_and_group_processes(
    active_policies: dict[str, PolicyStatus],
    speeds: dict[int, ProcessSpeed] = None
) -> list[ProcessFamily]:
    """
    扫描当前系统中所有运行的进程，聚合其实时网速与网络连接，并分组为任务管理器式进程家族树。
    """
    if speeds is None:
        speeds = {}

    connections_by_pid: dict[int, int] = {}
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.pid:
                connections_by_pid[c.pid] = connections_by_pid.get(c.pid, 0) + 1
    except Exception:
        pass

    # 1. 扫描所有单进程
    flat_items: list[ProcessItem] = []
    seen_pids = set()

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid = proc.info.get("pid")
            if pid is None or pid == 0 or pid in seen_pids:
                continue
            seen_pids.add(pid)

            name = proc.info.get("name") or f"Process_{pid}"
            exe_path = proc.info.get("exe") or ""
            conn_count = connections_by_pid.get(pid, 0)

            # 提取实时网速
            pspeed = speeds.get(pid)
            dl_speed = pspeed.download_bytes_per_sec if pspeed else 0.0
            up_speed = pspeed.upload_bytes_per_sec if pspeed else 0.0

            # 限速策略查询 (安全防 None)
            name_lower = name.lower()
            policy = active_policies.get(name_lower)
            is_limited = False
            limit_summary = "正常"

            if policy:
                up_bps = int(policy.upload_bps or 0)
                dl_bps = int(policy.download_bps or 0)
                is_limited = bool(policy.is_blocked or up_bps > 0 or dl_bps > 0)
                if is_limited:
                    limit_summary = policy.summary or "已限速"

            category = classify_process(name, exe_path)

            flat_items.append(ProcessItem(
                pid=pid,
                name=name,
                exe_path=exe_path,
                category=category,
                connections_count=conn_count,
                is_limited=is_limited,
                limit_summary=limit_summary,
                sort_priority=category.priority,
                download_speed=dl_speed,
                upload_speed=up_speed
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            continue

    # 2. 聚合到进程家族 (Process Families)
    families_dict: dict[str, ProcessFamily] = {}

    for item in flat_items:
        name_lower = item.name.lower()
        if name_lower in KNOWN_FAMILIES:
            fam_id, fam_name = KNOWN_FAMILIES[name_lower]
        else:
            # 通用聚类：去掉 .exe 作为家族名
            base_name = re.sub(r'\.exe$', '', item.name, flags=re.IGNORECASE)
            fam_id = base_name.lower()
            fam_name = base_name

        if fam_id not in families_dict:
            families_dict[fam_id] = ProcessFamily(
                family_id=fam_id,
                display_name=fam_name,
                category=item.category,
                children=[]
            )

        fam = families_dict[fam_id]
        fam.children.append(item)

        # 只要家族中某一个子进程是关键分类，家族自动提档至更重要的类别
        if item.category.priority < fam.category.priority:
            fam.category = item.category

    # 3. 统计家族聚合指标与排序权重
    family_list: list[ProcessFamily] = []
    for fam in families_dict.values():
        fam.total_connections = sum(c.connections_count for c in fam.children)
        fam.total_download_speed = sum(c.download_speed for c in fam.children)
        fam.total_upload_speed = sum(c.upload_speed for c in fam.children)
        
        # 家族限速判定
        limited_children = [c for c in fam.children if c.is_limited]
        fam.is_limited = bool(limited_children)
        if limited_children:
            fam.limit_summary = limited_children[0].limit_summary
        else:
            fam.limit_summary = "正常"

        # 排序优先级
        if fam.is_limited:
            fam.sort_priority = -1  # 已限速家族绝对置顶
        elif fam.category == ProcessCategory.DOWNLOADER:
            fam.sort_priority = 1
        elif fam.category == ProcessCategory.CLOUD_DRIVE:
            fam.sort_priority = 2
        elif fam.category == ProcessCategory.GAME:
            fam.sort_priority = 3
        elif fam.category == ProcessCategory.BROWSER_SOCIAL:
            fam.sort_priority = 4
        elif fam.total_connections > 0 or fam.total_download_speed > 100 or fam.total_upload_speed > 100:
            fam.sort_priority = 5
        else:
            fam.sort_priority = 6

        # 子进程内部排序 (按连接数降序、PID升序)
        fam.children.sort(key=lambda c: (-c.connections_count, -c.download_speed, c.pid))
        family_list.append(fam)

    # 家族列表排序：优先级升序 -> 总网速降序 -> 总连接数降序 -> 名称
    family_list.sort(key=lambda f: (
        f.sort_priority,
        -(f.total_download_speed + f.total_upload_speed),
        -f.total_connections,
        f.display_name.lower()
    ))

    return family_list
