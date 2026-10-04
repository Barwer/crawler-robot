import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import tkinter as tk
from crawler_controller import CrawlerController
from crawler_ui import CrawlerUI
from read_maker import ArucoTracker


def marker_test_frame():
    """Generate fixtures in memory; no image assets needed after cloning."""
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    tiles = []
    for marker_id in (1, 2):
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 400)
        tiles.append(cv2.copyMakeBorder(marker, 50, 50, 50, 50,
                                       cv2.BORDER_CONSTANT, value=255))
    return cv2.cvtColor(cv2.hconcat(tiles), cv2.COLOR_GRAY2BGR)


class RefactorTests(unittest.TestCase):
    def setUp(self):
        self.ui = Mock()
        self.tracker = Mock(target_ids=[1, 2])
        self.tracker.get_distance.return_value = {2: -2.0, 1: 3.0}
        self.client = Mock()
        self.client.is_complete.return_value = False
        self.controller = CrawlerController(self.ui, self.tracker, self.client)

    def test_training_waits_and_maps_reward_by_id(self):
        c = self.controller
        c.setPauseRun()
        c.appRun()
        self.assertIsNotNone(c.pending_step)
        self.assertEqual(self.client.order.call_count, 1)
        self.assertEqual(len(c.learner.qValues), 0)
        c.appRun()
        self.assertEqual(self.client.order.call_count, 1)
        self.client.is_complete.return_value = True
        c.appRun()
        self.assertIsNone(c.pending_step)
        self.assertEqual(list(c.ws.values)[-1], (1, 3.0, -2.0))
        self.assertTrue(c.learner.qValues)
        self.assertEqual(self.tracker.update_frame.call_args_list[0].kwargs, {'measure': False})

    def test_greedy_never_updates(self):
        c = self.controller
        c.setTest()
        with patch.object(c.learner, 'getAction', side_effect=AssertionError('exploration used')):
            c.appRun()
            self.client.is_complete.return_value = True
            c.appRun()
        self.assertEqual(len(c.learner.qValues), 0)
        self.assertEqual(c.ws.max_row, 1)

    def test_timeout_pause_close_and_single_start(self):
        c = self.controller
        self.ui.after.return_value = 'job1'
        c.start()
        c.start()
        self.assertEqual(self.ui.after.call_count, 1)
        c.step()
        c.pending_step = c.pending_step[:-1] + (time.monotonic()-10,)
        c._poll_step()
        self.assertTrue(c.pause)
        self.ui.warning.assert_called_once()
        c.close()
        c.close()
        self.tracker.close.assert_called_once()
        self.client.close.assert_called_once()
        self.ui.cancel.assert_called_once_with('job1')

    def test_save_load_and_reset(self):
        c = self.controller
        with tempfile.TemporaryDirectory() as tmp:
            self.ui.get_filename.return_value = str(Path(tmp)/'q.log')
            key = ((2,2), 'arm-up')
            c.learner.qValues[key] = 12.5
            c.dumpQvalues()
            c.resetQvalues()
            self.assertEqual(c.learner.getQValue(*key), 0)
            c.loadQvalues()
            self.assertEqual(c.learner.getQValue(*key), 12.5)

    def test_tracker_detects_without_tk(self):
        frame = marker_test_frame()
        capture = Mock()
        capture.read.return_value = (True, frame.copy())
        tracker = ArucoTracker(capture=capture)
        rgb = tracker.update_frame(measure=False)
        self.assertEqual(set(tracker.detected_ids), {1,2})
        self.assertEqual(rgb.shape, frame.shape)
        self.assertEqual(tracker.positions, {1: [], 2: []})
        tracker.get_start_world()
        tracker.update_frame()
        self.assertEqual(set(tracker.get_distance()), {1,2})
        tracker.close()
        capture.release.assert_called_once()

    def test_real_widgets_bind_render_and_camera_reuse(self):
        original_tk = tk.Tk
        def hidden_root():
            root = original_tk()
            root.withdraw()
            return root
        with patch('crawler_ui.tk.Tk', side_effect=hidden_root):
            ui = CrawlerUI()
        try:
            c = CrawlerController(ui, self.tracker, self.client)
            ui.run_button.invoke()
            self.assertFalse(c.pause)
            ui.test_button.invoke()
            self.assertTrue(c.pause and c.testStete)
            frame = marker_test_frame()
            ui.show_frame(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            ui.show_frame(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.assertEqual(len(ui.camera.find_all()), 1)
            self.assertGreater(len(ui.analysis.find_all()), 0)
            ui.root.update_idletasks()
            c.close()
        except Exception:
            ui.close()
            raise


if __name__ == '__main__':
    unittest.main(verbosity=2)

