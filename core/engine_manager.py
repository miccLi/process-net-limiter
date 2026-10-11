# -*- coding: utf-8 -*-
"""
双引擎路由门面 (EngineManager)
- 默认优先：WinDivert 内核级流量整形引擎 (毫秒生效、严格限速 1KB/s、通杀 UDP/TCP)
- 备选兼容：Windows 原生 QoS 组策略与防火墙引擎 (纯绿色、免安装、优雅降级)
- 启动时自动预热并同步系统持久化防火墙策略，消除重启后状态孤岛
- 运行时支持驱动故障自动平滑降级
"""
import logging
from core.limiter_engine import LimiterEngine, LimitRequest, PolicyStatus
from core.windivert_engine import WinDivertEngine
from core.uac_manager import is_admin
from core.rules_store import RulesStore

logger = logging.getLogger("EngineManager")


class EngineManager:
    """统一限速引擎路由管理器"""
    def __init__(self, rules_store: RulesStore = None):
        self.native_engine = LimiterEngine()
        self.windivert_engine = WinDivertEngine()
        self.rules_store = rules_store if rules_store is not None else RulesStore()
        self.traffic_monitor = self.windivert_engine.traffic_monitor

        # 严格校验：以管理员运行 且 驱动能够正常打开时才启用 WinDivert 内核引擎
        self.use_windivert = is_admin() and self.windivert_engine.is_driver_functional()

        # 启动时预热查询系统持久化规则 (防止遗留防火墙阻断无法在界面识别)
        try:
            self.native_engine.get_active_policies()
        except Exception:
            pass


    @property
    def active_engine_name(self) -> str:
        return "WINDIVERT" if self.use_windivert else "NATIVE"

    @property
    def active_engine_display(self) -> str:
        if self.use_windivert:
            return "🚀 内核驱动整形 (WinDivert 硬件级精准)"
        return "🛡️ 原生组策略引擎 (Windows QoS 出站整形 + 防火墙)"

    def get_active_policies(self) -> dict[str, PolicyStatus]:
        """获取当前生效的所有策略 (融合 WinDivert 内存策略与系统持久化防火墙策略)"""
        # 1. 始终查询系统级持久化策略 (QoS 与 防火墙)
        policies = dict(self.native_engine.get_active_policies())

        # 2. 如果 WinDivert 处于激活状态，叠加其内存限速规则
        if self.use_windivert:
            wd_p = self.windivert_engine.get_active_policies()
            for app, status in wd_p.items():
                policies[app] = status

        return policies

    def apply_limits_batch(self, requests: list[LimitRequest], persist: bool = True) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量应用策略 (支持持久化存储与驱动失败时自动平滑降级至原生引擎)"""
        # 1. 持久化存储规则到本地磁盘
        if persist and self.rules_store:
            try:
                self.rules_store.save_requests_batch(requests)
            except Exception as e:
                logger.warning(f"持久化存储规则失败: {e}")

        if self.use_windivert:
            # 2. 在 WinDivert 内存引擎中下发毫秒级规则
            ok, msg, wd_policies = self.windivert_engine.apply_limits_batch(requests)

            # 若 WinDivert 初始化失败，自动平滑降级至 Native 引擎
            if not ok:
                logger.warning(f"WinDivert 下发失败，自动平滑降级至原生引擎: {msg}")
                self.use_windivert = False
                return self.native_engine.apply_limits_batch(requests)

            # 3. 对其中“完全断开连接”的请求，同步下发 Windows 防火墙物理阻断，实现双重硬防
            block_reqs = [r for r in requests if (r.upload_speed_type == "block" or r.download_speed_type == "block")]
            if block_reqs:
                try:
                    self.native_engine.apply_limits_batch(block_reqs)
                except Exception:
                    pass

            return ok, msg, self.get_active_policies()
        else:
            return self.native_engine.apply_limits_batch(requests)

    def remove_limits_batch(self, app_names: list[str]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量解除策略 (同时清理 WinDivert、Native 与本地持久化存储，确保不留死角)"""
        if self.rules_store:
            try:
                self.rules_store.remove_rules_batch(app_names)
            except Exception as e:
                logger.warning(f"删除持久化规则失败: {e}")

        ok1, msg1, p1 = self.windivert_engine.remove_limits_batch(app_names)
        ok2, msg2, p2 = self.native_engine.remove_limits_batch(app_names)
        return (ok1 and ok2), f"已成功解除 {len(app_names)} 个程序的网络限制", self.get_active_policies()

    def remove_limit(self, app_name: str) -> tuple[bool, str]:
        ok, msg, _ = self.remove_limits_batch([app_name])
        return ok, msg

    def remove_all_limits(self) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """一键清除全部策略 (彻底清除内核、原生系统所有规则与本地持久化存储)"""
        if self.rules_store:
            try:
                self.rules_store.clear()
            except Exception as e:
                logger.warning(f"清空持久化规则失败: {e}")

        ok1, msg1, _ = self.windivert_engine.remove_all_limits()
        ok2, msg2, _ = self.native_engine.remove_all_limits()
        return (ok1 and ok2), "已一键清除所有网络限速与阻断规则", {}

    def auto_rebind_persistent_rules(self, running_apps: dict[str, str]) -> tuple[int, int]:
        """
        开机或扫描时，自动对存活的进程恢复持久化规则，并自愈路径漂移。
        返回：(成功下发恢复的规则数, 路径自愈校准数)
        """
        if not self.rules_store:
            return 0, 0

        requests, healed_count = self.rules_store.reconcile_and_heal(running_apps)
        if not requests:
            return 0, healed_count

        # 下发恢复规则，设置 persist=False 避免重复写入磁盘
        self.apply_limits_batch(requests, persist=False)
        return len(requests), healed_count


    def speed_str_to_bps(self, speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
        return self.native_engine.speed_str_to_bps(speed_type, custom_val, unit)

    def stop(self):
        """安全停止并释放底层引擎资源与驱动线程"""
        try:
            if self.windivert_engine:
                self.windivert_engine.stop()
        except Exception as e:
            logger.warning(f"停止 WinDivert 引擎时发生异常: {e}")

    def tick_traffic_monitor(self) -> tuple[float, float]:
        """推进流量监控器时间步并返回系统全局吞吐 (global_up_bytes_sec, global_down_bytes_sec)"""
        return self.traffic_monitor.tick()

    def get_global_rates(self) -> tuple[float, float]:
        """获取当前系统全局上传与下载实时速率 (bytes/sec)"""
        return self.traffic_monitor.get_global_rates()

    def get_process_rates(self) -> dict[str, tuple[float, float]]:
        """获取各应用程序的实时上传与下载速率映射 (bytes/sec)"""
        return self.traffic_monitor.get_all_app_rates()

