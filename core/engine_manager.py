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

logger = logging.getLogger("EngineManager")


class EngineManager:
    """统一限速引擎路由管理器"""
    def __init__(self):
        self.native_engine = LimiterEngine()
        self.windivert_engine = WinDivertEngine()

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

    def apply_limits_batch(self, requests: list[LimitRequest]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量应用策略 (支持驱动失败时自动平滑降级至原生引擎)"""
        if self.use_windivert:
            # 1. 在 WinDivert 内存引擎中下发毫秒级规则
            ok, msg, wd_policies = self.windivert_engine.apply_limits_batch(requests)

            # 若 WinDivert 初始化失败，自动平滑降级至 Native 引擎
            if not ok:
                logger.warning(f"WinDivert 下发失败，自动平滑降级至原生引擎: {msg}")
                self.use_windivert = False
                return self.native_engine.apply_limits_batch(requests)

            # 2. 对其中“完全断开连接”的请求，同步下发 Windows 防火墙物理阻断，实现双重硬防
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
        """批量解除策略 (同时清理 WinDivert 和 Native，确保不留死角)"""
        ok1, msg1, p1 = self.windivert_engine.remove_limits_batch(app_names)
        ok2, msg2, p2 = self.native_engine.remove_limits_batch(app_names)
        return (ok1 and ok2), f"已成功解除 {len(app_names)} 个程序的网络限制", self.get_active_policies()

    def remove_limit(self, app_name: str) -> tuple[bool, str]:
        ok, msg, _ = self.remove_limits_batch([app_name])
        return ok, msg

    def remove_all_limits(self) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """一键清除全部策略 (彻底清除内核与原生系统所有规则)"""
        ok1, msg1, _ = self.windivert_engine.remove_all_limits()
        ok2, msg2, _ = self.native_engine.remove_all_limits()
        return (ok1 and ok2), "已一键清除所有网络限速与阻断规则", {}

    def speed_str_to_bps(self, speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
        return self.native_engine.speed_str_to_bps(speed_type, custom_val, unit)

    def stop(self):
        """安全停止并释放底层引擎资源与驱动线程"""
        try:
            if self.windivert_engine:
                self.windivert_engine.stop()
        except Exception as e:
            logger.warning(f"停止 WinDivert 引擎时发生异常: {e}")

