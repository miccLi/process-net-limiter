# -*- coding: utf-8 -*-
"""
进程扫描与智能归类引擎
- 扫描系统当前运行进程
- 识别常见 游戏、网盘、下载器、浏览器
- 排序规则：被限速/断网的程序排在最前；其次是下载器、网盘、游戏；再次为活跃联网程序
- 彻底修复 NoneType 比较导致进程异常消失的问题
"""
import os
import psutil
from dataclasses import dataclass
from enum import Enum
from core.limiter_engine import PolicyStatus

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

# 常见下载器特征
DOWNLOADER_EXES = {
    "thunder.exe", "downloadsdkserver.exe", "idman.exe", "fdm.exe", "aria2c.exe",
    "qbittorrent.exe", "bittorrent.exe", "utorrent.exe", "motrix.exe", "deluge.exe",
    "transmission-qt.exe", "xdm.exe", "eagleget.exe", "bitcomet.exe", "folx.exe",
    "p2psearcher.exe", "baidudl.exe"
}

# 常见网盘特征
CLOUD_DRIVE_EXES = {
    "onedrive.exe", "baidunetdisk.exe", "baidunetdiskhost.exe", "aliyunpan.exe",
    "123pan.exe", "quark.exe", "quarkbrowser.exe", "googledrivefs.exe", "dropbox.exe",
    "nutstore.exe", "jianguoyun.exe", "icloud.exe", "icloudservices.exe", "lanzou.exe",
    "pikpak.exe", "weiyun.exe", "ctfile.exe", "terabox.exe", "mega.exe", "megasync.exe"
}

# 常见游戏平台与游戏特征
GAME_EXES = {
    "steam.exe", "steamservice.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "riotclientservices.exe", "wegame.exe", "yuanshen.exe", "genshinimpact.exe",
    "starrail.exe", "honkaistarrail.exe", "cs2.exe", "csgo.exe", "dota2.exe",
    "pubg.exe", "valorant.exe", "leagueclient.exe", "minecraft.exe", "javaw.exe",
    "battle.net.exe", "origin.exe", "ea.exe", "eadesktop.exe", "uplay.exe", "upc.exe",
    "blackmythwukong.exe", "naraka.exe", "overwatch.exe", "apex.exe", "r5apex.exe",
    "crossfire.exe", "dnf.exe", "tora.exe", "cyberpunk2077.exe", "gta5.exe", "witcher3.exe"
}

# 常见浏览器与即时通讯
BROWSER_SOCIAL_EXES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe",
    "wechat.exe", "wechatappex.exe", "qq.exe", "dingtalk.exe", "feishu.exe",
    "discord.exe", "telegram.exe", "slack.exe", "skype.exe", "thunderbird.exe"
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
    selected: bool = False

def classify_process(name: str, exe_path: str) -> ProcessCategory:
    """保留程序原本的自然分类"""
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

def scan_processes(active_policies: dict[str, PolicyStatus]) -> list[ProcessItem]:
    """
    扫描系统中所有进程，与限速策略结合后进行归类和多级置顶排序。
    """
    connections_by_pid: dict[int, int] = {}
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.pid:
                connections_by_pid[c.pid] = connections_by_pid.get(c.pid, 0) + 1
    except Exception:
        pass

    items: list[ProcessItem] = []
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

            # 严格类型安全检测限速策略，防 None 异常
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

            # 排序权重计算：
            # Priority -1: 已限速程序 (始终置于最顶部，方便查看与取消)
            # Priority 1: 下载器
            # Priority 2: 网盘
            # Priority 3: 游戏
            # Priority 4: 浏览器/通讯
            # Priority 5: 具有活跃网络连接的其他程序
            # Priority 6: 无活跃网络连接的普通程序
            if is_limited:
                sort_p = -1
            elif category == ProcessCategory.DOWNLOADER:
                sort_p = 1
            elif category == ProcessCategory.CLOUD_DRIVE:
                sort_p = 2
            elif category == ProcessCategory.GAME:
                sort_p = 3
            elif category == ProcessCategory.BROWSER_SOCIAL:
                sort_p = 4
            elif conn_count > 0:
                sort_p = 5
            else:
                sort_p = 6

            items.append(ProcessItem(
                pid=pid,
                name=name,
                exe_path=exe_path,
                category=category,
                connections_count=conn_count,
                is_limited=is_limited,
                limit_summary=limit_summary,
                sort_priority=sort_p
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            print(f"扫描单进程跳过异常: {e}")
            continue

    # 多级排序：第一优先级 sort_priority 升序；第二优先级活跃网络连接数降序；第三优先级程序名升序
    items.sort(key=lambda x: (x.sort_priority, -x.connections_count, x.name.lower()))
    return items
