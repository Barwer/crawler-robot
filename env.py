import math
from math import pi as PI

class CrawlingRobotEnvironment:

    def __init__(self, crawlingRobot):

        self.crawlingRobot = crawlingRobot

        # The state is of the form (armAngle, handAngle)
        # where the angles are bucket numbers, not actual
        # degree measurements
        self.state = None
        self.lastState = None

        self.nArmStates = 5
        self.nHandStates = 5

        # create a list of arm buckets and hand buckets to
        # discretize the state space
        minArmAngle, maxArmAngle = self.crawlingRobot.getMinAndMaxArmAngles()
        minHandAngle, maxHandAngle = self.crawlingRobot.getMinAndMaxHandAngles()
        armIncrement = (maxArmAngle - minArmAngle) / (self.nArmStates - 1)
        handIncrement = (maxHandAngle - minHandAngle) / (self.nHandStates - 1)
        self.armBuckets = [int(minArmAngle + (armIncrement * i)) for i in range(self.nArmStates)]
        self.handBuckets = [int(minHandAngle + (handIncrement * i)) for i in range(self.nHandStates)]
        
        # print(minArmAngle, maxArmAngle)
        # print(minHandAngle, maxHandAngle)
        # print(self.armBuckets)
        # print(self.handBuckets)

        # Reset
        self.distanceOld = 0
        self.distanceNew = 0
        self.reset()

    def getCurrentState(self):
        """
          Return the current state
          of the crawling robot
        """
        return self.state

    def getPossibleActions(self, state):
        """
          Returns possible actions
          for the states in the
          current state
        """
        actions = list()

        currArmBucket, currHandBucket = state
        if currArmBucket > 0: actions.append('arm-down')
        if currArmBucket < self.nArmStates - 1: actions.append('arm-up')
        if currHandBucket > 0: actions.append('hand-down')
        if currHandBucket < self.nHandStates - 1: actions.append('hand-up')

        return actions

    def doAction(self, action, massege_id):
        """
          Perform the action and update
          the current state of the Environment
          and return the reward for the
          current state, the next state
          and the taken action.

          Returns:
            nextState, reward
        """
        nextState = None
        
        # print(action)
        # print(self.state)

        armBucket, handBucket = self.state
        angle = []
        if action == 'arm-up':
            newArmAngle = self.armBuckets[armBucket + 1]
            nextState = (armBucket + 1, handBucket)
            angle = [(newArmAngle, "x", massege_id)]
        elif action == 'arm-down':
            newArmAngle = self.armBuckets[armBucket - 1]
            nextState = (armBucket - 1, handBucket)
            angle = [(newArmAngle, "x", massege_id)]
        elif action == 'hand-up':
            newHandAngle = self.handBuckets[handBucket + 1]
            nextState = (armBucket, handBucket + 1)
            angle = [("x", newHandAngle, massege_id)]
        elif action == 'hand-down':
            newHandAngle = self.handBuckets[handBucket - 1]
            nextState = (armBucket, handBucket - 1)
            angle = [("x", newHandAngle, massege_id)]
        else:
            raise Exception('invalid action..!!')

        self.state = nextState

        return angle, nextState
    
    def cal_reward(self, distanceNew):
        self.distanceNew = distanceNew
        reward = self.distanceNew - self.distanceOld

        self.distanceOld = self.distanceNew

        return reward


    def reset(self):
        """
         Resets the Environment to the initial state
        """
        armState = self.nArmStates // 2
        handState = self.nHandStates // 2
        self.setCurrentState((armState, handState))

    def setCurrentState(self, state):
        """
          Return the current state
          of the crawling robot
        """
        armState, handState = state
        self.state = state
        self.crawlingRobot.setAngles(self.armBuckets[armState], self.handBuckets[handState])
        self.lastState = state


class CrawlingRobot:

    def setAngles(self, armAngle, handAngle):
        """
            set the robot's arm and hand angles
            to the passed in values
        """
        self.armAngle = armAngle
        self.handAngle = handAngle

    def getAngles(self):
        """
            returns the pair of (armAngle, handAngle)
        """
        return self.armAngle, self.handAngle

    def getMinAndMaxArmAngles(self):
        """
            get the lower- and upper- bound
            for the arm angles returns (min,max) pair
        """
        return self.minArmAngle, self.maxArmAngle

    def getMinAndMaxHandAngles(self):
        """
            get the lower- and upper- bound
            for the hand angles returns (min,max) pair
        """
        return self.minHandAngle, self.maxHandAngle

    def __init__(self):
        self.armAngle = 0.0
        self.handAngle = 180
        self.maxArmAngle = 90
        self.minArmAngle = 0
        self.maxHandAngle = 90
        self.minHandAngle = 0
        self.nextAction = None
