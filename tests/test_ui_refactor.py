import sys
import time
import threading
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
from servo import controlServo


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
        self.ui.get_robot_count.return_value = 2
        self.ui.get_single_robot_id.return_value = 1
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

    def test_single_robot_does_not_move_or_train_robot_two(self):
        c = self.controller
        self.ui.get_robot_count.return_value = 1
        initial = c.robotEnvironment2.getCurrentState()
        c.step()
        self.assertIsNone(self.client.order.call_args.args[1])
        self.assertEqual(c.robotEnvironment2.getCurrentState(), initial)
        self.client.is_complete.return_value = True
        with patch.object(c.learner, 'observeTransition', wraps=c.learner.observeTransition) as update:
            c._poll_step()
            self.assertEqual(update.call_count, 1)
        self.assertEqual(list(c.ws.values)[-1], (1, 3.0, 0.0))

    def test_mqtt_single_and_dual_acknowledgements(self):
        client = controlServo.__new__(controlServo)
        client.client = Mock()
        client.client.is_connected.return_value = True
        client.client.publish.return_value = Mock(rc=0, mid=1)
        client.responses = {}
        client.response_lock = threading.Lock()
        client.topic, client.topic2 = 'servo/angles', 'servo2/angles'
        client.resp_topic = 'servo/crawler1_status'
        client.resp_topic2 = 'servo2/crawler2_status'
        client.order([(45, 'x', 2)])
        self.assertEqual(client.client.publish.call_count, 1)
        client.responses[client.resp_topic] = 'finish, 2'
        self.assertTrue(client.is_complete(2))
        self.assertNotIn('Robot 2', client.acknowledgement_details(2))
        client.order(None, [('x', 45, 2)])
        self.assertEqual(client.client.publish.call_args.args[0], 'servo2/angles')
        client.responses[client.resp_topic2] = 'finish,2'
        self.assertTrue(client.is_complete(2))
        self.assertNotIn('Robot 1', client.acknowledgement_details(2))
        client.order([(45, 'x', 3)], [('x', 45, 3)])
        client.responses[client.resp_topic] = 'finish,3'
        client.responses[client.resp_topic2] = 'finish,2'
        self.assertFalse(client.is_complete(3))
        self.assertIn('WRONG ID', client.acknowledgement_details(3))
        client.responses[client.resp_topic2] = 'finish,3'
        self.assertTrue(client.is_complete(3))
        client.client.is_connected.return_value = False
        count = client.client.publish.call_count
        with self.assertRaisesRegex(RuntimeError, 'not connected'):
            client.order([(45, 'x', 4)])
        self.assertEqual(client.client.publish.call_count, count)
        client.client.is_connected.return_value = True
        client.client.publish.return_value = Mock(rc=4, mid=2)
        with self.assertRaisesRegex(RuntimeError, 'publish failed'):
            client.order([(45, 'x', 4)])

    def test_robot_two_only_uses_marker_two_and_state_two(self):
        c = self.controller
        self.ui.get_robot_count.return_value = 1
        self.ui.get_single_robot_id.return_value = 2
        initial1 = c.robotEnvironment.getCurrentState()
        c.step()
        self.assertIsNone(self.client.order.call_args.args[0])
        self.assertIsNotNone(self.client.order.call_args.args[1])
        self.assertEqual(c.robotEnvironment.getCurrentState(), initial1)
        expected = c.pending_step[4:7]
        self.client.is_complete.return_value = True
        with patch.object(c.learner, 'observeTransition') as update:
            c._poll_step()
            update.assert_called_once_with(*expected, -2.0)
        self.assertEqual(list(c.ws.values)[-1], (1, 0.0, -2.0))
        self.assertEqual(self.ui.render_analysis.call_args.args[0]['state'], c.robotEnvironment2.getCurrentState())
    def test_connection_status_and_retained_messages(self):
        client = controlServo.__new__(controlServo)
        client.response_lock = threading.Lock()
        client.broker_connected = True
        client.last_seen, client.last_payloads, client.responses = {}, {}, {}
        client.pending_command = None
        client.active_response_topics = ()
        client.timed_out_topics = set()
        client.resp_topic, client.resp_topic2 = 'r1/status', 'r2/status'
        self.assertEqual([r['state'] for r in client.connection_snapshot()['robots']], ['unknown', 'unknown'])
        message = Mock(topic='r1/status', payload=b'finish,2', retain=True)
        client.on_message(None, None, message)
        self.assertFalse(client.last_seen)
        message.retain = False
        client.on_message(None, None, message)
        self.assertEqual(client.connection_snapshot()['robots'][0]['state'], 'recent')
        client.active_response_topics = ('r1/status', 'r2/status')
        client.pending_command = 2
        self.assertEqual(client.connection_snapshot()['robots'][1]['state'], 'waiting')
        client.mark_timeout(2)
        states = [r['state'] for r in client.connection_snapshot()['robots']]
        self.assertEqual(states, ['recent', 'timeout'])
        client.last_seen['r1/status'] = time.monotonic()-40
        self.assertEqual(client.connection_snapshot()['robots'][0]['state'], 'stale')
        client.on_disconnect(None, None, None, 0)
        self.assertTrue(all(r['state']=='broker_offline' for r in client.connection_snapshot()['robots']))

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
            ui.render_connections({'broker_connected': True, 'robots': [
                {'id': 1, 'state': 'recent', 'age': 2, 'payload': 'finish,2'},
                {'id': 2, 'state': 'unknown', 'age': None, 'payload': None}]})
            self.assertIn('finish,2', ui.robot_labels[1].cget('text'))
            self.assertIn('ยังไม่พบ', ui.robot_labels[2].cget('text'))
            ui.root.update_idletasks()
            self.assertLessEqual(ui.root.winfo_reqwidth(), 1024)
            self.assertLessEqual(ui.root.winfo_reqheight(), 720)
            with patch.object(ui.camera, 'winfo_width', return_value=400), patch.object(ui.camera, 'winfo_height', return_value=200):
                ui._resize_camera()
                self.assertLessEqual(ui.photo.width(), 400)
                self.assertLessEqual(ui.photo.height(), 200)
                self.assertAlmostEqual(ui.photo.width()/ui.photo.height(), frame.shape[1]/frame.shape[0], places=1)
            c.close()
        except Exception:
            ui.close()
            raise


if __name__ == '__main__':
    unittest.main(verbosity=2)

