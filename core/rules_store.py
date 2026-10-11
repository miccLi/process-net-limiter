# -*- coding: utf-8 -*-
r"""
策略规则持久化与版本自愈重绑模块 (core/rules_store.py)
- 本地规则持久化：保存至 `%LOCALAPPDATA%\ProcessNetLimiter\rules.json`
- 跨开机与程序重启保持限速策略状态
- 进程路径漂移自愈算法：检测版本升级导致的可执行文件路径变更并自动重新校准
"""

import os
import json
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict
from core.limiter_engine import LimitRequest

logger = logging.getLogger("RulesStore")

RULES_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ProcessNetLimiter")
RULES_FILE = os.path.join(RULES_DIR, "rules.json")


@dataclass
class StoredRule:
    app_name: str
    app_path: str
    upload_speed_type: str = "none"
    download_speed_type: str = "none"
    custom_upload_val: float = 0.0
    custom_upload_unit: str = "KB/s"
    custom_download_val: float = 0.0
    custom_download_unit: str = "KB/s"
    is_blocked: bool = False
    updated_at: float = field(default_factory=time.time)

    def to_limit_request(self, current_path: Optional[str] = None) -> LimitRequest:
        return LimitRequest(
            app_name=self.app_name,
            app_path=current_path or self.app_path,
            upload_speed_type=self.upload_speed_type,
            download_speed_type=self.download_speed_type,
            custom_upload_val=self.custom_upload_val,
            custom_upload_unit=self.custom_upload_unit,
            custom_download_val=self.custom_download_val,
            custom_download_unit=self.custom_download_unit,
        )

    @classmethod
    def from_limit_request(cls, req: LimitRequest) -> "StoredRule":
        is_blocked = (req.upload_speed_type == "block" or req.download_speed_type == "block")
        return cls(
            app_name=req.app_name,
            app_path=req.app_path,
            upload_speed_type=req.upload_speed_type,
            download_speed_type=req.download_speed_type,
            custom_upload_val=req.custom_upload_val,
            custom_upload_unit=req.custom_upload_unit,
            custom_download_val=req.custom_download_val,
            custom_download_unit=req.custom_download_unit,
            is_blocked=is_blocked,
            updated_at=time.time()
        )


class RulesStore:
    def __init__(self, filepath: str = RULES_FILE):
        self.filepath = filepath
        self._rules: Dict[str, StoredRule] = {}
        self.load()

    def load(self) -> Dict[str, StoredRule]:
        """从本地磁盘加载持久化规则"""
        if not os.path.exists(self.filepath):
            self._rules = {}
            return self._rules

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            rules_dict = {}
            for item in data.get("rules", []):
                rule = StoredRule(
                    app_name=item.get("app_name", ""),
                    app_path=item.get("app_path", ""),
                    upload_speed_type=item.get("upload_speed_type", "none"),
                    download_speed_type=item.get("download_speed_type", "none"),
                    custom_upload_val=float(item.get("custom_upload_val", 0.0)),
                    custom_upload_unit=item.get("custom_upload_unit", "KB/s"),
                    custom_download_val=float(item.get("custom_download_val", 0.0)),
                    custom_download_unit=item.get("custom_download_unit", "KB/s"),
                    is_blocked=bool(item.get("is_blocked", False)),
                    updated_at=float(item.get("updated_at", time.time()))
                )
                if rule.app_name:
                    rules_dict[rule.app_name.lower()] = rule
            self._rules = rules_dict
        except Exception as e:
            logger.warning(f"读取规则文件失败，重置为空: {e}")
            self._rules = {}
        return self._rules

    def get_all_requests(self) -> list[LimitRequest]:
        """获取所有已持久化规则对应的 LimitRequest 请求对象"""
        return [rule.to_limit_request() for rule in self._rules.values()]

    def save(self) -> bool:
        """将当前规则写入本地磁盘"""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            data = {
                "version": 1,
                "rules": [asdict(r) for r in self._rules.values()]
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"写入规则文件失败: {e}")
            return False

    def save_request(self, req: LimitRequest) -> None:
        """保存单条限速请求"""
        key = req.app_name.lower()
        self._rules[key] = StoredRule.from_limit_request(req)
        self.save()

    def save_requests_batch(self, requests: list[LimitRequest]) -> None:
        """批量保存限速请求"""
        for req in requests:
            key = req.app_name.lower()
            self._rules[key] = StoredRule.from_limit_request(req)
        self.save()

    def remove_rule(self, app_name: str) -> bool:
        """删除指定程序的持久化规则"""
        key = app_name.lower()
        if key in self._rules:
            del self._rules[key]
            self.save()
            return True
        return False

    def remove_rules_batch(self, app_names: list[str]) -> int:
        """批量删除持久化规则"""
        count = 0
        for name in app_names:
            key = name.lower()
            if key in self._rules:
                del self._rules[key]
                count += 1
        if count > 0:
            self.save()
        return count

    def clear(self) -> None:
        """清空所有持久化规则"""
        self._rules.clear()
        self.save()

    def get_rule(self, app_name: str) -> Optional[StoredRule]:
        return self._rules.get(app_name.lower())

    def get_all_rules(self) -> list[StoredRule]:
        return list(self._rules.values())

    def reconcile_and_heal(self, running_apps: dict[str, str]) -> tuple[list[LimitRequest], int]:
        """
        核心自愈与对齐算法：
        比对当前正在运行的程序映射表 {app_name_lower: current_exe_path}：
        1. 针对已记录的持久化规则，如果程序正在运行：
           - 检测 exe 路径是否发生漂移（如版本号子目录升级）；
           - 若发生漂移，自动更新存储路径；
           - 转换为 LimitRequest 下发对象；
        返回：(待重新应用的 LimitRequest 列表, 路径自愈校准数量)
        """
        requests_to_apply = []
        healed_count = 0
        needs_save = False

        for key, rule in self._rules.items():
            if key in running_apps:
                current_live_path = running_apps[key]
                # 路径漂移检测
                if current_live_path and current_live_path.lower() != rule.app_path.lower():
                    logger.info(f"检测到程序路径漂移自愈: {rule.app_name} 从 '{rule.app_path}' -> '{current_live_path}'")
                    rule.app_path = current_live_path
                    rule.updated_at = time.time()
                    healed_count += 1
                    needs_save = True

                req = rule.to_limit_request(current_live_path)
                requests_to_apply.append(req)

        if needs_save:
            self.save()

        return requests_to_apply, healed_count
