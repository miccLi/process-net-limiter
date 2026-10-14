# -*- coding: utf-8 -*-
from unittest.mock import patch, MagicMock
import unittest
import time
from core.windivert_engine import TokenBucket, WinDivertEngine
from core.engine_manager import EngineManager
from core.limiter_engine import LimitRequest


class TestWinDivertEngine(unittest.TestCase):
    def test_token_bucket_unlimited(self):
        b = TokenBucket(0)
        allowed, wait = b.consume(1500)
        self.assertTrue(allowed)
        self.assertEqual(wait, 0.0)

    def test_token_bucket_blocked(self):
        b = TokenBucket(1024, is_blocked=True)
        allowed, wait = b.consume(100)
        self.assertFalse(allowed)
        self.assertEqual(wait, -1.0)

    def test_token_bucket_rate_pacing(self):
        # 1024 字节/秒 = 1 KB/s, 容量 1024
        b = TokenBucket(1024, capacity=1024)
        t0 = 1000.0
        b.last_refill = t0
        b.tokens = 1024.0

        # 消耗 800 字节 -> 应该立即放行，剩余 224 字节
        allowed, wait = b.consume(800, now=t0)
        self.assertTrue(allowed)
        self.assertAlmostEqual(b.tokens, 224.0, places=2)

        # 紧接着尝试消耗 500 字节 -> 令牌不足 (缺 276 字节)
        allowed, wait = b.consume(500, now=t0)
        self.assertFalse(allowed)
        self.assertAlmostEqual(wait, 276.0 / 1024.0, places=3)

    @patch.object(WinDivertEngine, "_ensure_workers_running", return_value=(True, ""))
    def test_windivert_engine_batch_rules(self, mock_workers):
        engine = WinDivertEngine()
        self.assertTrue(engine.is_driver_available())

        req = [
            LimitRequest(
                app_name="game.exe",
                app_path="C:\\Games\\game.exe",
                upload_speed_type="1kb",
                download_speed_type="1kb"
            )
        ]
        ok, msg, policies = engine.apply_limits_batch(req)
        self.assertTrue(ok)
        self.assertIn("game.exe", policies)
        status = policies["game.exe"]
        self.assertEqual(status.upload_bps, 8192)
        self.assertEqual(status.download_bps, 8192)
        self.assertIn("1 KB/s", status.summary)

        # 移除
        ok2, msg2, policies2 = engine.remove_limits_batch(["game.exe"])
        self.assertTrue(ok2)
        self.assertNotIn("game.exe", policies2)

    def test_token_bucket_deficit_accounting(self):
        """测试：赤字欠账式平滑调度，延迟包预扣减负令牌，杜绝超发"""
        # 1024 字节/秒，容量 1024，允许缓冲 0.5s 的轻微超额
        b = TokenBucket(1024, capacity=1024, max_pacing_delay=0.5)
        t0 = 1000.0
        b.last_refill = t0
        b.tokens = 500.0

        # 消耗 800 字节，不足 300 字节，等待 300/1024 ~ 0.29s <= 0.5s
        allowed, wait = b.consume(800, now=t0)
        self.assertFalse(allowed)
        self.assertGreater(wait, 0)
        # 验证令牌已进入欠账赤字状态 (-300)
        self.assertAlmostEqual(b.tokens, -300.0, places=2)

        # 超额严重超出 max_pacing_delay (例如请求 10000 字节，需等待近 10 秒)
        allowed2, wait2 = b.consume(10000, now=t0)
        self.assertFalse(allowed2)
        self.assertGreater(wait2, b.max_pacing_delay)
        # 丢弃的包绝不累积赤字
        self.assertAlmostEqual(b.tokens, -300.0, places=2)

    def test_stop_lifecycle_cleanup(self):
        """测试：停止引擎时能够干净重置运行标志并清空小顶堆与队列"""
        engine = WinDivertEngine()
        engine._running = True
        engine._pacing_queue.put((time.perf_counter(), "mock_packet"))
        with engine._pacer_cond:
            engine._pacer_heap.append((time.perf_counter(), 0, "mock_packet"))
        
        engine.stop()
        
        self.assertFalse(engine._running)
        self.assertTrue(engine._stop_event.is_set())
        self.assertTrue(engine._pacing_queue.empty())
        self.assertEqual(len(engine._pacer_heap), 0)

    def test_engine_manager_facade(self):
        mgr = EngineManager()
        self.assertIn(mgr.active_engine_name, ["WINDIVERT", "NATIVE"])
        self.assertTrue(len(mgr.active_engine_display) > 0)


if __name__ == "__main__":
    unittest.main()
