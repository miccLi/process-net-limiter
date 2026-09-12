# -*- coding: utf-8 -*-
"""
网络限速与阻断核心引擎
基于 Windows 原生 QoS 策略 (NetQosPolicy) 与 高级防火墙规则 (NetFirewallRule) 实现：
- 速度限制 (1KB/s, 100KB/s, 1000KB/s, 自定义速度)
- 完全断开连接 (阻断出站与入站网络)
- 上传与下载独立或联动控制
- 一键扫描、应用、解除所有策略
"""
import re
import json
from dataclasses import dataclass
from core.uac_manager import run_powershell_script, is_admin

QOS_PREFIX = "NetLimit_QoS_"
FW_PREFIX = "NetLimit_Block_"

@dataclass
class PolicyStatus:
    app_name: str
    is_blocked: bool = False
    upload_bps: int = 0
    download_bps: int = 0
    summary: str = "未限制"

class LimiterEngine:
    def __init__(self):
        pass

    @staticmethod
    def speed_str_to_bps(speed_type: str, custom_val: float = 0, unit: str = "KB/s") -> int:
        """将选择的速度档位转换为每秒比特数 (bits per second)"""
        if speed_type == "block":
            return -1  # 特殊标记：完全阻断
        elif speed_type == "1kb":
            return 8192      # 1 KB/s = 8192 bps
        elif speed_type == "100kb":
            return 819200    # 100 KB/s = 819,200 bps
        elif speed_type == "1000kb":
            return 8192000   # 1000 KB/s (~1MB/s) = 8,192,000 bps
        elif speed_type == "custom":
            multiplier = 1024 * 8
            if unit.upper() == "MB/S":
                multiplier = 1024 * 1024 * 8
            elif unit.upper() == "GB/S":
                multiplier = 1024 * 1024 * 1024 * 8
            bps = int(custom_val * multiplier)
            return max(1000, bps)  # 最低 1000 bps
        return 0  # 0 代表无限制

    def get_active_policies(self) -> dict[str, PolicyStatus]:
        """
        查询系统中所有由本程序建立的活动 QoS 策略与防火墙阻断规则。
        返回字典: { "app_name.exe": PolicyStatus }
        """
        results: dict[str, PolicyStatus] = {}
        
        # 1. 检索 QoS 策略
        ps_script = f"""
        $qos = Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like '{QOS_PREFIX}*' }}
        $gpoQos = Get-NetQosPolicy -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like '{QOS_PREFIX}*' }}
        $allQos = @($qos) + @($gpoQos) | Select-Object -Unique Name, AppPathNameMatchCondition, ThrottleRateActionBitsPerSecond
        
        $fw = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like '{FW_PREFIX}*' }} | Select-Object DisplayName, Direction, Action
        
        [PSCustomObject]@{{
            QoS = $allQos
            Firewall = $fw
        }} | ConvertTo-Json -Depth 3 -Compress
        """
        ok, output = run_powershell_script(ps_script)
        if not ok or not output:
            return results

        try:
            # 尝试提取 JSON 内容
            json_str = output[output.find('{'):output.rfind('}')+1]
            data = json.loads(json_str)
            
            # 解析 QoS
            qos_list = data.get("QoS", [])
            if isinstance(qos_list, dict):
                qos_list = [qos_list]
            elif not isinstance(qos_list, list):
                qos_list = []

            for item in qos_list:
                name = item.get("Name", "")
                app_path = item.get("AppPathNameMatchCondition", "")
                rate = item.get("ThrottleRateActionBitsPerSecond", 0)
                
                # 从 name 中提取 app 标识
                # 命名规范: NetLimit_QoS_UP_{app_name} 或 NetLimit_QoS_DL_{app_name} 或 NetLimit_QoS_ALL_{app_name}
                app_name = ""
                direction = "ALL"
                if name.startswith(f"{QOS_PREFIX}UP_"):
                    direction = "UP"
                    app_name = name[len(f"{QOS_PREFIX}UP_"):]
                elif name.startswith(f"{QOS_PREFIX}DL_"):
                    direction = "DL"
                    app_name = name[len(f"{QOS_PREFIX}DL_"):]
                elif name.startswith(f"{QOS_PREFIX}ALL_"):
                    direction = "ALL"
                    app_name = name[len(f"{QOS_PREFIX}ALL_"):]
                elif name.startswith(QOS_PREFIX):
                    app_name = name[len(QOS_PREFIX):]

                if not app_name and app_path:
                    app_name = app_path.split("\\")[-1]

                app_name_lower = app_name.lower()
                if app_name_lower not in results:
                    results[app_name_lower] = PolicyStatus(app_name=app_name)
                
                status = results[app_name_lower]
                if direction in ("UP", "ALL"):
                    status.upload_bps = rate
                if direction in ("DL", "ALL"):
                    status.download_bps = rate

            # 解析防火墙阻断
            fw_list = data.get("Firewall", [])
            if isinstance(fw_list, dict):
                fw_list = [fw_list]
            elif not isinstance(fw_list, list):
                fw_list = []

            for item in fw_list:
                dname = item.get("DisplayName", "")
                if dname.startswith(FW_PREFIX):
                    app_name = dname[len(FW_PREFIX):]
                    app_name_lower = app_name.lower()
                    if app_name_lower not in results:
                        results[app_name_lower] = PolicyStatus(app_name=app_name)
                    results[app_name_lower].is_blocked = True

            # 格式化汇总摘要
            for status in results.values():
                if status.is_blocked:
                    status.summary = "⛔ 完全断网 (阻断连接)"
                else:
                    parts = []
                    if status.upload_bps > 0:
                        parts.append(f"上: {status.upload_bps // 8192} KB/s")
                    if status.download_bps > 0:
                        parts.append(f"下: {status.download_bps // 8192} KB/s")
                    status.summary = " | ".join(parts) if parts else "已限速"

        except Exception as e:
            print(f"解析活动策略失败: {e}")

        return results

    def apply_limit(
        self,
        app_name: str,
        app_path: str = "",
        upload_speed_type: str = "none",
        download_speed_type: str = "none",
        custom_upload_val: float = 0,
        custom_upload_unit: str = "KB/s",
        custom_download_val: float = 0,
        custom_download_unit: str = "KB/s"
    ) -> tuple[bool, str]:
        """
        对指定程序应用速度限制或完全阻断连接。
        """
        clean_app = app_name.strip()
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean_app)
        
        up_bps = self.speed_str_to_bps(upload_speed_type, custom_upload_val, custom_upload_unit)
        dl_bps = self.speed_str_to_bps(download_speed_type, custom_download_val, custom_download_unit)
        
        # 先清理旧策略
        cleanup_ps = f"""
        Remove-NetQosPolicy -Name '{QOS_PREFIX}*_{safe_name}' -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetQosPolicy -Name '{QOS_PREFIX}*_{safe_name}' -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetQosPolicy -Name '{QOS_PREFIX}{safe_name}' -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetFirewallRule -DisplayName '{FW_PREFIX}{safe_name}*' -ErrorAction SilentlyContinue
        """

        commands = [cleanup_ps]

        # 检查是否为“完全断开连接”
        if upload_speed_type == "block" or download_speed_type == "block":
            prog_arg = f"-Program '{app_path}'" if (app_path and os.path.exists(app_path)) else ""
            # 新建阻断防火墙出入站规则
            block_ps = f"""
            New-NetFirewallRule -DisplayName '{FW_PREFIX}{safe_name}_Out' -Direction Outbound -Action Block {prog_arg} -Description 'ProcessNetLimiter 阻断规则' -ErrorAction SilentlyContinue
            New-NetFirewallRule -DisplayName '{FW_PREFIX}{safe_name}_In' -Direction Inbound -Action Block {prog_arg} -Description 'ProcessNetLimiter 阻断规则' -ErrorAction SilentlyContinue
            """
            commands.append(block_ps)
        else:
            # QoS 速度限制
            # 1. 上传限制
            if up_bps > 0 and (up_bps == dl_bps):
                # 上下行速率一致，创建统一策略
                qos_cmd = f"New-NetQosPolicy -Name '{QOS_PREFIX}ALL_{safe_name}' -AppPathNameMatchCondition '{clean_app}' -ThrottleRateActionBitsPerSecond {up_bps} -PolicyStore ActiveStore -ErrorAction SilentlyContinue"
                commands.append(qos_cmd)
            else:
                if up_bps > 0:
                    qos_up = f"New-NetQosPolicy -Name '{QOS_PREFIX}UP_{safe_name}' -AppPathNameMatchCondition '{clean_app}' -ThrottleRateActionBitsPerSecond {up_bps} -PolicyStore ActiveStore -ErrorAction SilentlyContinue"
                    commands.append(qos_up)
                if dl_bps > 0:
                    # Windows QoS 主要针对出站速率整形。通过限制该进程出站速率（包括 TCP ACK 反馈速率），
                    # TCP 流量受滑动窗口与拥塞控制限制，会平滑限制下行下载速率。
                    qos_dl = f"New-NetQosPolicy -Name '{QOS_PREFIX}DL_{safe_name}' -AppPathNameMatchCondition '{clean_app}' -ThrottleRateActionBitsPerSecond {dl_bps} -PolicyStore ActiveStore -ErrorAction SilentlyContinue"
                    commands.append(qos_dl)

        full_script = "\n".join(commands)
        ok, msg = run_powershell_script(full_script)
        if ok:
            return True, f"已成功为 {clean_app} 配置网络限制规则"
        return False, f"配置失败: {msg}"

    def remove_limit(self, app_name: str) -> tuple[bool, str]:
        """解除指定程序的限速与阻断"""
        clean_app = app_name.strip()
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean_app)
        
        script = f"""
        Remove-NetQosPolicy -Name '{QOS_PREFIX}*_{safe_name}' -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetQosPolicy -Name '{QOS_PREFIX}*_{safe_name}' -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetQosPolicy -Name '{QOS_PREFIX}{safe_name}' -Confirm:$false -ErrorAction SilentlyContinue
        Remove-NetFirewallRule -DisplayName '{FW_PREFIX}{safe_name}*' -ErrorAction SilentlyContinue
        """
        ok, msg = run_powershell_script(script)
        if ok:
            return True, f"已成功解除 {clean_app} 的所有限制"
        return False, f"解除失败: {msg}"

    def remove_all_limits(self) -> tuple[bool, str, int]:
        """一键解除所有由本程序创建的限速与防火墙规则"""
        script = f"""
        $q1 = Get-NetQosPolicy -PolicyStore ActiveStore -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like '{QOS_PREFIX}*' }}
        $q2 = Get-NetQosPolicy -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like '{QOS_PREFIX}*' }}
        $fw = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like '{FW_PREFIX}*' }}
        
        $count = ($q1.Count + $q2.Count + $fw.Count)
        
        $q1 | Remove-NetQosPolicy -PolicyStore ActiveStore -Confirm:$false -ErrorAction SilentlyContinue
        $q2 | Remove-NetQosPolicy -Confirm:$false -ErrorAction SilentlyContinue
        $fw | Remove-NetFirewallRule -ErrorAction SilentlyContinue
        
        Write-Output $count
        """
        ok, msg = run_powershell_script(script)
        count = 0
        try:
            for line in msg.splitlines():
                if line.strip().isdigit():
                    count = int(line.strip())
                    break
        except Exception:
            pass
        if ok:
            return True, "已成功一键清除所有网络限制与断网规则", count
        return False, f"一键清除失败: {msg}", 0
