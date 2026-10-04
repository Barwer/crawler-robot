"""Robot/training orchestration. UI is injected; no Tkinter dependency."""
import collections
import pickle
import time
from pathlib import Path
from openpyxl import Workbook
import env
import agen
import servo
import read_maker


class CrawlerController:
    def __init__(self, ui, tracker=None, servo_client=None):
        self.ui = ui
        self.pause = True
        self.testStete = False
        self.pending_step = None
        self.mqtt_timeout = 5.0
        self.massege_id = 0
        self._closed = False
        self._job = None
        self.mark = tracker if tracker is not None else read_maker.ArucoTracker()
        self.servo1 = None
        try:
            self.servo1 = servo_client if servo_client is not None else servo.controlServo()
        except Exception:
            self.mark.close()
            raise
        self.robot = env.CrawlingRobot()
        self.robot2 = env.CrawlingRobot()
        self.robotEnvironment = env.CrawlingRobotEnvironment(self.robot)
        self.robotEnvironment2 = env.CrawlingRobotEnvironment(self.robot2)
        self.learner = agen.QLearningAgent(actionFn=self.robotEnvironment.getPossibleActions)
        self.learner.setEpsilon(0.28299795565300107)
        self.learner.setLearningRate(0.8)
        self.learner.setDiscount(0.8)
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.append(["Index", "Distance_1", "Distance_2"])
        self.ui.bind(self)
        self.appDraw()

    def setPauseRun(self):
        self.pause = not self.pause
        if not self.pause:
            self.testStete = False
        self.ui.set_mode(self.pause, self.testStete)

    def setTest(self):
        self.testStete = not self.testStete
        if self.testStete:
            self.pause = True
        self.ui.set_mode(self.pause, self.testStete)

    def dumpQvalues(self):
        try:
            filename = self.ui.get_filename()
            if filename:
                with open(filename, 'wb') as handle:
                    pickle.dump(self.learner.qValues, handle)
        except Exception as error:
            self.ui.error("Save error", str(error))

    def loadQvalues(self):
        if self.pending_step is not None or not self.pause or self.testStete:
            self.ui.warning("Load QValues", "Pause and wait for the current action before loading.")
            return
        try:
            filename = self.ui.get_filename()
            if filename:
                with open(filename, 'rb') as handle:
                    values = pickle.load(handle)
                self.learner.qValues = values
                self.learner.qvalues = values
                self.learner.visited = collections.Counter()
                self.appDraw()
        except Exception as error:
            self.ui.error("Load error", str(error))

    def resetQvalues(self):
        self.learner.qValues.clear()
        self.learner.qvalues.clear()
        self.learner.visited.clear()
        self.appDraw()

    def appDraw(self):
        actions = ('hand-down', 'hand-up', 'arm-down', 'arm-up')
        cells = []
        for i in range(self.robotEnvironment.nArmStates):
            for j in range(self.robotEnvironment.nHandStates):
                state = (i, j)
                cells.append({'state': state,
                              'value': self.learner.getValue(state),
                              'q': {a: self.learner.getQValue(state, a) for a in actions}})
        self.ui.render_analysis({'cells': cells, 'step': self.massege_id,
                                 'epsilon': self.learner.epsilon,
                                 'state': self.robotEnvironment.getCurrentState(),
                                 'action': self.robot.nextAction})

    def step(self):
        self._begin_step(training=True)

    def stepTest(self):
        self._begin_step(training=False)

    def _begin_step(self, training):
        self.massege_id += 1
        state1 = self.robotEnvironment.getCurrentState()
        state2 = self.robotEnvironment2.getCurrentState()
        choose = self.learner.getAction if training else self.learner.getTestAction
        action1, action2 = choose(state1), choose(state2)
        if action1 is None or action2 is None:
            raise RuntimeError("No legal action available")
        self.robotEnvironment.lastState = state1
        self.robotEnvironment2.lastState = state2
        self.mark.get_start_world()
        angle1, next1 = self.robotEnvironment.doAction(action1, self.massege_id)
        angle2, next2 = self.robotEnvironment2.doAction(action2, self.massege_id)
        self.servo1.order(angle1, angle2)
        self.pending_step = (training, state1, action1, next1,
                             state2, action2, next2, time.monotonic())
        print("Waiting for both robots, command", self.massege_id)

    def _poll_step(self):
        training, state1, action1, next1, state2, action2, next2, started = self.pending_step
        if self.servo1.is_complete(self.massege_id):
            self.pending_step = None
            if training:
                self.mark.update_frame()
                distance = self.mark.get_distance()
                # Bind rewards to marker IDs, never dictionary insertion order.
                rewards = [distance.get(marker_id, 0.0) for marker_id in self.mark.target_ids]
                rewards = [0.0 if abs(value) < 0.5 else value for value in rewards]
                reward1, reward2 = rewards
                self.ws.append([self.massege_id, reward1, reward2])
                self.learner.observeTransition(state1, action1, next1, reward1)
                self.learner.observeTransition(state2, action2, next2, reward2)
                if self.massege_id % 100 == 0:
                    from pathlib import Path
                    output = Path(__file__).resolve().parent / "Output"
                    output.mkdir(exist_ok=True)
                    self.wb.save(output / "output_3.xlsx")
            choose = self.learner.getAction if training else self.learner.getTestAction
            self.robot.nextAction = choose(next1)
            self.robot2.nextAction = choose(next2)
            self.appDraw()
        elif time.monotonic() - started >= self.mqtt_timeout:
            self.pending_step = None
            self.pause = True
            self.testStete = False
            self.ui.set_mode(self.pause, self.testStete)
            # Physical positions are uncertain; stop rather than issuing more actions.
            self.ui.warning("MQTT timeout",
                "Both robots did not acknowledge command " + str(self.massege_id) +
                ". Check power, topics and command IDs; reset robot poses before continuing.")

    def appRun(self):
        if self._closed:
            return
        try:
            self.ui.show_frame(self.mark.update_frame(measure=False))
            if self.pending_step is not None:
                self._poll_step()
            elif self.testStete:
                self.stepTest()
            elif not self.pause:
                self.step()
        except Exception as error:
            self.pause = True
            self.testStete = False
            self.pending_step = None
            self.ui.set_mode(self.pause, self.testStete)
            import traceback
            traceback.print_exc()
            self.ui.error("Crawler error", str(error))
        finally:
            if not self._closed:
                self._job = self.ui.after(50, self.appRun)

    def start(self):
        if self._job is None and not self._closed:
            self._job = self.ui.after(50, self.appRun)

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._job is not None:
            self.ui.cancel(self._job)
            self._job = None
        try:
            self.mark.close()
        finally:
            try:
                self.servo1.close()
            finally:
                self.ui.close()
