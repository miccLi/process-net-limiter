# -*- coding: utf-8 -*-
"""
双引擎路由门面 (EngineManager)
- 默认优先：WinDivert 内核级流量整形引擎 (毫秒生效、严格限速 1KB/s、通杀 UDP/TCP)
- 备选兼容：Windows 原生 QoS 组策略与防火墙引擎 (纯绿色、免安装、优雅降级)
- 对外提供完全统一的策略下发、查询与清除接口
"""
from core.limiter_engine import LimiterEngine, LimitRequest, PolicyStatus
from core.windivert_engine import WinDivertEngine
from core.uac_manager import is_admin


class EngineManager:
    """统一限速引擎路由管理器"""
    def __init__(self):
        self.native_engine = LimiterEngine()
        self.windivert_engine = WinDivertEngine()

        # 判定是否启用 WinDivert 内核引擎
        self.use_windivert = self.windivert_engine.is_driver_available() and is_admin()

    @property
    def active_engine_name(self) -> str:
        return "WINDIVERT" if self.use_windivert else "NATIVE"

    @property
    def active_engine_display(self) -> str:
        if self.use_windivert:
            return "🚀 内核驱动整形 (WinDivert 硬件级精准)"
        return "🛡️ 原生组策略引擎 (Windows QoS)"

    def get_active_policies(self) -> dict[str, PolicyStatus]:
        """获取当前生效的所有策略"""
        if self.use_windivert:
            policies = self.windivert_engine.get_active_policies()
            # 若 WinDivert 规则为空，尝试检查是否有原生的遗留策略
            if not policies:
                native_p = self.native_engine.cached_policies
                if native_p:
                    return native_p
            return policies
        return self.native_engine.get_active_policies()

    def apply_limits_batch(self, requests: list[LimitRequest]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量应用策略"""
        if self.use_windivert:
            # 1. 在 WinDivert 内存引擎中下发毫秒级规则
            ok, msg, policies = self.windivert_engine.apply_limits_batch(requests)

            # 2. 对其中“完全断开连接”的请求，同步下发 Windows 防火墙物理阻断，实现内核+防火墙双重硬防
            block_reqs = [r for r in requests if (r.upload_speed_type == "block" or r.download_speed_type == "block")]
            if block_reqs:
                try:
                    self.native_engine.apply_limits_batch(block_reqs)
                except Exception:
                    pass

            return ok, msg, policies
        else:
            return self.native_engine.apply_limits_batch(requests)

    def remove_limits_batch(self, app_names: list[str]) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """批量解除策略 (同时清理 WinDivert 和 Native，确保不留死角)"""
        ok1, msg1, p1 = self.windivert_engine.remove_limits_batch(app_names)
        ok2, msg2, p2 = self.native_engine.remove_limits_batch(app_names)
        policies = p1 if self.use_windivert else p2
        return (ok1 and ok2), f"已成功解除 {len(app_names)} 个程序的网络限制", policies

    def remove_limit(self, app_name: str) -> tuple[bool, str]:
        ok, msg, _ = self.remove_limits_batch([app_name])
        return ok, msg

    def remove_all_limits(self) -> tuple[bool, str, dict[str, PolicyStatus]]:
        """一键清除全部策略"""
        ok1, msg1, _ = self.windivert_engine.remove_all_limits()
        ok2, msg2, _ = self.native_engine.remove_all_limits()
        return (ok1 and ok2), "已一键清除所有网络限速与阻断规则", {}

    def speed_str_to_bps(self, speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
        return self.native_engine.speed_str_to_bps(speed_type, custom_val, unit)
