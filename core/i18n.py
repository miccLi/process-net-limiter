# -*- coding: utf-8 -*-
"""
国际化多语言管理模块 (i18n)
支持简体中文 (zh_CN) 与英文 (en_US) 动态切换与偏好持久化。
"""
import os
import json
import locale

CONFIG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ProcessNetLimiter")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

TRANSLATIONS = {
    "zh_CN": {
        # 通用与标题
        "app_title": "进程网络限制器",
        "app_window_title": "进程网络限制器 (ProcessNetLimiter) - 专业版",
        "app_subtitle": "支持多进程家族折叠、精确上下行分离限速与物理断网",
        "admin_granted": "🛡️ 已获管理员权限",
        "admin_needed": "⚠️ 未获取管理员权限 (点击提权)",
        "refresh_btn": "🔄 刷新进程",
        "auto_refresh": "自动刷新 (5s)",
        "search_placeholder": "🔍 搜索程序名称、PID、可执行文件路径...",
        
        # 过滤器芯片
        "filter_all": "全部程序",
        "filter_limited": "⛔ 仅看已限制",
        "filter_downloader": "⚡ 下载器优先",
        "filter_cloud_drive": "☁️ 网盘优先",
        "filter_game": "🎮 游戏优先",
        "filter_browser_social": "🌐 浏览器与社交",

        # 快捷选择
        "select_all": "全选",
        "invert_sel": "反选",
        "clear_sel": "全不选",

        # 进程树列头
        "col_name": "程序名称 / 进程家族",
        "col_status": "当前限制状态",
        "col_up_speed": "↑ 上传",
        "col_down_speed": "↓ 下载",
        "col_pid": "PID",
        "col_category": "类别",
        "col_conns": "网络连接",
        "col_path": "执行文件路径",
        "global_traffic_label": "实时总吞吐: ↑ {up}  ↓ {down}",
        "tray_tooltip_traffic": "进程网络限制器\n↑ {up} | ↓ {down}",

        # 分类名称
        "cat_DOWNLOADER": "下载器",
        "cat_CLOUD_DRIVE": "网盘",
        "cat_GAME": "游戏",
        "cat_BROWSER_SOCIAL": "浏览器/通讯",
        "cat_OTHER": "系统/其它",

        # 家族树节点文本
        "processes_count": " ({count} 个进程)",
        "total_count": "共 {count}",
        "conn_units": "{count} 个",
        "protected_tooltip": "系统核心保护进程，已锁定禁止限制网络",

        # 控制栏
        "selected_summary": "已选择 {count} 个程序/家族",
        "separate_checkbox": "⚙️ 分别设置上传和下载速度 (独立配置)",
        "speed_limit_label": "速度限制 (上传与下载):",
        "upload_limit_label": "上传限制:",
        "download_limit_label": "下载限制:",
        
        # 预设档位
        "preset_block": "完全断开连接 (0 KB/s - 阻断连接)",
        "preset_1kb": "1 KB/s (极限限速)",
        "preset_100kb": "100 KB/s (低速限制)",
        "preset_1000kb": "1000 KB/s (中速限制 / ~1MB/s)",
        "preset_custom": "自定义速度限制...",
        "preset_none_up": "不进行限制",
        "preset_none_dl": "不限制下载",

        # 操作按钮
        "btn_apply": "🚀 应用限速",
        "btn_apply_busy": "⏳ {action}...",
        "btn_remove_selected": "❌ 取消选中限制",
        "btn_reset_all": "⚡ 一键解除全部限制",

        # 状态栏与提示
        "ready_tip": "就绪。提示：支持直接勾选进程家族批量限速，或展开家族仅限制某一特定进程。",
        "scanning_status": "正在获取活动策略并扫描进程家族...",
        "scan_done_status": "已就绪 | 进程家族: {fams} | 总进程数: {procs} | 联网家族: {conns} | 已限制: {limited}",
        "scan_failed": "刷新失败",
        "busy_applying": "⏳ 正在{action}，后台处理中，界面保持流畅响应...",
        "action_apply": "下发策略",
        "action_remove": "解除限制",
        "action_reset": "一键清除策略",
        "op_finished": "✅ {msg} | 当前受限进程家族数: {count}",
        "auto_refresh_on": "已开启自动刷新 (每 5 秒)",
        "auto_refresh_off": "已关闭自动刷新",

        # 弹窗提示
        "no_selection_warning": "请先在列表中勾选想要限制的程序或家族！",
        "no_selection_remove_warning": "请先在列表中勾选想要解除限制的程序或家族！",
        "reset_confirm_title": "确认重置",
        "reset_confirm_text": "确定要一键清除系统中所有由本程序设置的 QoS 速度限制与防火墙阻断规则吗？\n此操作将确保所有网络程序恢复原始无限制状态。",
        "elevation_title": "提权提示",
        "elevation_failed": "未能获取管理员权限。请右键选择“以管理员身份运行”。",
        "op_error": "操作异常",
        "notice": "提示",

        # 引擎提示文案
        "engine_tip_windivert": "💡 提示：当前已启用 WinDivert 内核级流量整形引擎 (NetLimiter 同级技术，秒级生效且支持游戏 UDP/TCP 严格卡死 1KB/s)。“完全断开连接”同时执行内核与防火墙双重物理阻断。",
        "engine_tip_native": "💡 提示：当前处于 Windows 原生系统策略引擎模式 (基于系统组策略 QoS 出站整形与高级安全防火墙)。出站限速内核级平稳生效，入站限速由 TCP 窗口协商节流，“完全断开连接”通过防火墙双向毫秒级物理阻断。",
        "engine_tip_downgraded": "⚠️ 提示：由于内核驱动加载受阻 ({reason})，已自动平滑降级至 Windows 原生 QoS 与防火墙引擎。限速与断网功能持续稳定生效。",
        "network_compat_accelerator_detected": "🌐 环境提示：检测到系统正在运行网络加速器/VPN 虚拟网卡，已启用局域网与广播兼容透传保护。",

        # 摘要显示
        "policy_blocked": "⛔ 完全断网",
        "policy_normal": "正常",
        "policy_up_prefix": "上: ",
        "policy_down_prefix": "下: ",
        "speed_unlimited": "不限",
        "lang_switch_label": "🌐 语言 / Language",

        # 托盘与开机自启
        "tray_show": "显示主界面",
        "tray_hide": "最小化到托盘",
        "tray_emergency_restore": "⚡ 紧急恢复网络",
        "tray_autostart": "开机静默启动",
        "tray_exit": "退出程序",
        "tray_minimized_title": "ProcessNetLimiter 已转入后台",
        "tray_minimized_msg": "程序已最小化至系统托盘，限速与断网策略持续在后台生效。",
        "tray_restore_title": "网络已紧急恢复",
        "tray_restore_done": "已清除所有限速与阻断策略，所有程序网络恢复正常。",
        "autostart_enabled_msg": "已开启开机静默启动 (通过系统计划任务)",
        "autostart_disabled_msg": "已关闭开机静默启动"
    },
    "en_US": {
        # App & Header
        "app_title": "Process Net Limiter",
        "app_window_title": "ProcessNetLimiter - Professional Edition",
        "app_subtitle": "Process Family Grouping, Dual-Direction Rate Throttling & Network Severing",
        "admin_granted": "🛡️ Administrator Active",
        "admin_needed": "⚠️ Standard User (Click to Elevate)",
        "refresh_btn": "🔄 Refresh",
        "auto_refresh": "Auto-refresh (5s)",
        "search_placeholder": "🔍 Search process name, PID, or executable path...",

        # Filter Chips
        "filter_all": "All Processes",
        "filter_limited": "⛔ Limited Only",
        "filter_downloader": "⚡ Downloaders",
        "filter_cloud_drive": "☁️ Cloud Storage",
        "filter_game": "🎮 Games",
        "filter_browser_social": "🌐 Browsers & Social",

        # Quick Selection
        "select_all": "Select All",
        "invert_sel": "Invert",
        "clear_sel": "Clear",

        # Tree Headers
        "col_name": "Application / Process Family",
        "col_status": "Limit Status",
        "col_up_speed": "↑ Upload",
        "col_down_speed": "↓ Download",
        "col_pid": "PID",
        "col_category": "Category",
        "col_conns": "Connections",
        "col_path": "Executable Path",
        "global_traffic_label": "Total Throughput: ↑ {up}  ↓ {down}",
        "tray_tooltip_traffic": "ProcessNetLimiter\n↑ {up} | ↓ {down}",

        # Categories
        "cat_DOWNLOADER": "Downloader",
        "cat_CLOUD_DRIVE": "Cloud Storage",
        "cat_GAME": "Game",
        "cat_BROWSER_SOCIAL": "Browser/Chat",
        "cat_OTHER": "System/Other",

        # Tree Item Formats
        "processes_count": " ({count} processes)",
        "total_count": "Total {count}",
        "conn_units": "{count} active",
        "protected_tooltip": "Core Windows protected process, locked to prevent system instability",

        # Controls
        "selected_summary": "Selected {count} program(s) / family(ies)",
        "separate_checkbox": "⚙️ Separate Upload & Download Rates (Dual Config)",
        "speed_limit_label": "Rate Limit (Upload & Download):",
        "upload_limit_label": "Upload Limit:",
        "download_limit_label": "Download Limit:",

        # Presets
        "preset_block": "Sever Connection (0 KB/s - Block Traffic)",
        "preset_1kb": "1 KB/s (Extreme Throttle)",
        "preset_100kb": "100 KB/s (Low Speed)",
        "preset_1000kb": "1000 KB/s (Medium Speed / ~1MB/s)",
        "preset_custom": "Custom Rate...",
        "preset_none_up": "No Limit (Unlimited)",
        "preset_none_dl": "No Download Limit",

        # Buttons
        "btn_apply": "🚀 Apply Limits",
        "btn_apply_busy": "⏳ {action}...",
        "btn_remove_selected": "❌ Remove Selected",
        "btn_reset_all": "⚡ Reset All Limits",

        # Status & Notifications
        "ready_tip": "Ready. Tip: Check a process family to throttle all instances, or expand to limit individual processes.",
        "scanning_status": "Scanning active policies and grouping process families...",
        "scan_done_status": "Ready | Families: {fams} | Total Processes: {procs} | Network Active: {conns} | Limited: {limited}",
        "scan_failed": "Scan failed",
        "busy_applying": "⏳ Performing {action}, processing in background...",
        "action_apply": "applying limits",
        "action_remove": "removing limits",
        "action_reset": "resetting all limits",
        "op_finished": "✅ {msg} | Currently limited families: {count}",
        "auto_refresh_on": "Auto-refresh enabled (every 5 seconds)",
        "auto_refresh_off": "Auto-refresh disabled",

        # Dialogs
        "no_selection_warning": "Please select the programs or families you want to limit first!",
        "no_selection_remove_warning": "Please select the programs or families to remove limits first!",
        "reset_confirm_title": "Confirm Reset",
        "reset_confirm_text": "Are you sure you want to clear all QoS policies and firewall block rules created by this app?\nAll applications will be restored to their normal unrestricted network state.",
        "elevation_title": "Elevation Required",
        "elevation_failed": "Failed to acquire Administrator privileges. Please right-click and 'Run as administrator'.",
        "op_error": "Operation Error",
        "notice": "Notice",

        # Engine Tips
        "engine_tip_windivert": "💡 Tip: WinDivert kernel-level traffic shaping engine active (NetLimiter-grade packet inspection, microsecond pacing, supports strict 1 KB/s throttling for both TCP and game UDP). 'Sever Connection' enforces bi-directional physical block.",
        "engine_tip_native": "💡 Tip: Windows Native QoS & Firewall mode active. Egress traffic is shaped smoothly via OS kernel QoS; ingress is throttled via TCP window scaling; 'Sever Connection' executes bi-directional hardware-level firewall block.",
        "engine_tip_downgraded": "⚠️ Tip: Kernel driver blocked ({reason}). Smoothly downgraded to Windows Native QoS & Firewall engine. Rate limiting and blocking remain fully functional.",
        "network_compat_accelerator_detected": "🌐 Network Notice: Accelerator/VPN virtual adapter detected. LAN and multicast compatibility bypass active.",

        # Summary Display
        "policy_blocked": "⛔ Blocked",
        "policy_normal": "Normal",
        "policy_up_prefix": "Up: ",
        "policy_down_prefix": "Down: ",
        "speed_unlimited": "Unlimited",
        "lang_switch_label": "🌐 Language",

        # Tray and Autostart
        "tray_show": "Show Window",
        "tray_hide": "Minimize to Tray",
        "tray_emergency_restore": "⚡ Emergency Restore All",
        "tray_autostart": "Start with Windows",
        "tray_exit": "Exit",
        "tray_minimized_title": "ProcessNetLimiter Active in Background",
        "tray_minimized_msg": "Application minimized to system tray. Rate limiting and blocking rules remain active.",
        "tray_restore_title": "Network Restored",
        "tray_restore_done": "All rate limits and blocks have been cleared. Normal traffic restored.",
        "autostart_enabled_msg": "Auto-start on logon enabled (via Task Scheduler)",
        "autostart_disabled_msg": "Auto-start on logon disabled"
    }
}


class I18nManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18nManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._current_lang = self._load_persisted_lang() or self._detect_system_lang()

    def _detect_system_lang(self) -> str:
        try:
            sys_lang, _ = locale.getdefaultlocale()
            if sys_lang and sys_lang.lower().startswith("zh"):
                return "zh_CN"
        except Exception:
            pass
        return "zh_CN"  # 默认使用中文以保持原有基线，可随时在 UI 切换为 en_US

    def _load_persisted_lang(self) -> str:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang = data.get("language")
                    if lang in TRANSLATIONS:
                        return lang
            except Exception:
                pass
        return None

    def save_persisted_lang(self, lang: str):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            cfg = {}
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg["language"] = lang
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @property
    def current_lang(self) -> str:
        return self._current_lang

    def set_language(self, lang: str):
        if lang in TRANSLATIONS and lang != self._current_lang:
            self._current_lang = lang
            self.save_persisted_lang(lang)

    def t(self, key: str, **kwargs) -> str:
        table = TRANSLATIONS.get(self._current_lang, TRANSLATIONS["zh_CN"])
        text = table.get(key)
        if text is None:
            # 降级尝试中文
            text = TRANSLATIONS["zh_CN"].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text


# 全局单例辅助函数
i18n = I18nManager()

def t(key: str, **kwargs) -> str:
    return i18n.t(key, **kwargs)
