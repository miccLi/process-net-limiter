# -*- coding: utf-8 -*-
import unittest
import time
import threading
from unittest.mock import patch, MagicMock
from core.traffic_monitor import TrafficMonitor


class TestTrafficMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = TrafficMonitor(ema_alpha=1.0)  # 使用 alpha=1.0 使得 instant_rate 等于输出，便于精准数值断言

    def test_record_packet_and_tick(self):
        """测试单进程数据包记录与速率计算"""
        # 初始时全为 0
        up, dl = self.monitor.get_global_rates()
        self.assertEqual(up, 0.0)
        self.assertEqual(dl, 0.0)
        self.assertEqual(self.monitor.get_app_rate("test.exe"), (0.0, 0.0))

        # 模拟记录 100 KB 出站，200 KB 入站
        t0 = 1000.0
        self.monitor._last_tick_time = t0
        self.monitor.record_packet("test.exe", is_outbound=True, length=102400)
        self.monitor.record_packet("test.exe", is_outbound=False, length=204800)

        # 1 秒后 tick
        t1 = 1001.0
        self.monitor.tick(now=t1)

        app_up, app_dl = self.monitor.get_app_rate("test.exe")
        self.assertAlmostEqual(app_up, 102400.0, delta=10.0)
        self.assertAlmostEqual(app_dl, 204800.0, delta=10.0)

        # 不区分大小写查询
        app_up2, app_dl2 = self.monitor.get_app_rate("TEST.EXE")
        self.assertEqual(app_up, app_up2)
        self.assertEqual(app_dl, app_dl2)

    def test_zero_traffic_decay(self):
        """测试流量停止后的衰减与最终清理"""
        t0 = 1000.0
        self.monitor._last_tick_time = t0
        self.monitor.record_packet("streamer.exe", is_outbound=True, length=50000)
        self.monitor.tick(now=1001.0)
        self.assertGreater(self.monitor.get_app_rate("streamer.exe")[0], 0)

        # 接下来几个周期没有流量
        t = 1001.0
        for _ in range(6):
            t += 1.0
            self.monitor.tick(now=t)

        # 连续无流量后归零
        up, dl = self.monitor.get_app_rate("streamer.exe")
        self.assertEqual(up, 0.0)
        self.assertEqual(dl, 0.0)

    @patch("psutil.net_io_counters")
    def test_global_system_traffic_calculation(self, mock_counters):
        """测试基于 psutil 的系统总网速计算"""
        # 第一次采样初始化
        mock_c1 = MagicMock()
        mock_c1.bytes_sent = 1000000
        mock_c1.bytes_recv = 2000000
        mock_counters.return_value = mock_c1

        self.monitor._last_tick_time = 100.0
        self.monitor.tick(now=100.0)

        # 第二次采样 (1秒后，sent增加50000，recv增加150000)
        mock_c2 = MagicMock()
        mock_c2.bytes_sent = 1050000
        mock_c2.bytes_recv = 2150000
        mock_counters.return_value = mock_c2

        up, dl = self.monitor.tick(now=101.0)
        self.assertAlmostEqual(up, 50000.0, delta=100.0)
        self.assertAlmostEqual(dl, 150000.0, delta=100.0)

    def test_concurrent_recording(self):
        """测试多线程高并发记录下的线程安全性"""
        threads = []
        for i in range(10):
            def _worker():
                for _ in range(500):
                    self.monitor.record_packet("worker.exe", True, 100)
                    self.monitor.record_packet("worker.exe", False, 200)
            t = threading.Thread(target=_worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.monitor._last_tick_time = 10.0
        self.monitor.tick(now=11.0)
        up, dl = self.monitor.get_app_rate("worker.exe")
        # 10 线程 * 500 次 * 100 字节 = 500,000 字节/秒
        self.assertEqual(up, 500000.0)
        self.assertEqual(dl, 1000000.0)


if __name__ == '__main__':
    unittest.main()
