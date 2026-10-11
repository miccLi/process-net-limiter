# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from collections import namedtuple
from core.network_compat import NetworkCompatManager, NetworkDiagnostic


Snic = namedtuple('Snic', ['family', 'address', 'netmask', 'broadcast', 'ptp'])
Family = namedtuple('Family', ['name'])


class TestNetworkCompat(unittest.TestCase):
    def setUp(self):
        self.mgr = NetworkCompatManager()

    def test_multicast_and_broadcast_detection(self):
        """测试局域网组播与广播 IP 判定"""
        # 组播地址
        self.assertTrue(self.mgr.is_multicast_or_broadcast("224.0.0.1"))
        self.assertTrue(self.mgr.is_multicast_or_broadcast("239.255.255.250"))
        # 广播地址
        self.assertTrue(self.mgr.is_multicast_or_broadcast("255.255.255.255"))
        # 普通单播地址
        self.assertFalse(self.mgr.is_multicast_or_broadcast("192.168.1.1"))
        self.assertFalse(self.mgr.is_multicast_or_broadcast("1.1.1.1"))
        self.assertFalse(self.mgr.is_multicast_or_broadcast("127.0.0.1"))
        self.assertFalse(self.mgr.is_multicast_or_broadcast(""))
        self.assertFalse(self.mgr.is_multicast_or_broadcast("invalid_ip"))

    @patch("psutil.net_if_addrs")
    @patch("psutil.process_iter")
    def test_diagnose_standard_physical_network(self, mock_procs, mock_if):
        """测试标准物理网卡环境诊断"""
        # 模拟物理网卡以太网
        mock_if.return_value = {
            "Ethernet 1": [
                Snic(family=Family(name="AF_INET"), address="192.168.31.50", netmask="255.255.255.0", broadcast=None, ptp=None)
            ]
        }
        # 无加速器进程
        p1 = MagicMock()
        p1.info = {'name': 'notepad.exe'}
        mock_procs.return_value = [p1]

        diag = self.mgr.diagnose(force_refresh=True)
        self.assertFalse(diag.has_virtual_adapter)
        self.assertFalse(diag.has_tun_ip)
        self.assertFalse(diag.is_accelerator_environment)
        self.assertEqual(len(diag.active_accelerators), 0)
        self.assertIn("标准物理网络", diag.summary)

    @patch("psutil.net_if_addrs")
    @patch("psutil.process_iter")
    def test_diagnose_tun_and_accelerator_environment(self, mock_procs, mock_if):
        """测试包含 TUN 网卡与加速器进程的环境诊断"""
        # 模拟包含 Wintun 网卡与 198.18.0.1 网段
        mock_if.return_value = {
            "Wintun Userspace Tunnel": [
                Snic(family=Family(name="AF_INET"), address="198.18.0.1", netmask="255.255.0.0", broadcast=None, ptp=None)
            ]
        }
        # 模拟存在 UU 加速器
        p1 = MagicMock()
        p1.info = {'name': 'uu.exe'}
        mock_procs.return_value = [p1]

        diag = self.mgr.diagnose(force_refresh=True)
        self.assertTrue(diag.has_virtual_adapter)
        self.assertTrue(diag.has_tun_ip)
        self.assertTrue(diag.is_accelerator_environment)
        self.assertIn("UU加速器", diag.active_accelerators)
        self.assertIn("检测到加速器/虚拟网络环境", diag.summary)


if __name__ == "__main__":
    unittest.main()
