# qlearningAgents.py
# ------------------
# To following the instruction of not publishing the solutions, the core
# functions in class QLearningAgent are left incomplete.

# ------------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).



import random
import collections
from collections import defaultdict
import numpy as np

class QLearningAgent:
    """
      Q-Learning Agent

      Functions you should fill in:
        - computeValueFromQValues
        - computeActionFromQValues
        - getQValue
        - getAction
        - update

      Instance variables you have access to
        - self.epsilon (exploration prob)
        - self.alpha (learning rate)
        - self.discount (discount rate)

      Functions you should use
        - self.getLegalActions(state)
          which returns legal actions for a state
    """

    def __init__(self, actionFn=None, epsilon=0.5, alpha=0.5, gamma=1):
        """
        actionFn: Function which takes a state and returns the list of legal actions

        alpha    - learning rate
        epsilon  - exploration rate
        gamma    - discount factor
         """
        if actionFn == None:
            actionFn = lambda state: state.getLegalActions()
        self.actionFn = actionFn
        # print(self.actionFn((4,7)))

        self.epsilon = float(epsilon)
        self.alpha = float(alpha)
        self.discount = float(gamma)
        
        self.min_epsilon = 0.01
        self.decay_rate = 0.9995

        self.qvalues = collections.Counter()
        self.visited = collections.Counter()
        self.qValues = defaultdict(float)


    def getQValue(self, state, action):
        """
          Returns Q(state,action)
          Should return 0.0 if we have never seen a state
          or the Q node value otherwise
        """

        # raise Exception('Incomplete Function!')
        return self.qValues.get((state, action), 0.0)


    def computeValueFromQValues(self, state):
      """
        Returns max_action Q(state,action)
        where the max is over legal actions.  Note that if
        there are no legal actions, which is the case at the
        terminal state, you should return a value of 0.0.
      """
      legalActions = self.getLegalActions(state)
      
      if not legalActions:  # Terminal state
          return 0.0

      # หา Q-value สูงสุดจากทุก action ที่ทำได้ในสถานะนี้
      maxQ = max(self.getQValue(state, action) for action in legalActions)
      return maxQ


    def computeActionFromQValues(self, state):
      """
      Compute the best action to take in a state. If there are no legal actions,
      which is the case at the terminal state, return None.
      """
      legalActions = self.getLegalActions(state)
      
      if not legalActions:
          return None  # terminal state

      # หา action ที่ให้ Q-value สูงสุด
      maxQ = float('-inf')
      bestActions = []

      for action in legalActions:
          qValue = self.getQValue(state, action)
          if qValue > maxQ:
              maxQ = qValue
              bestActions = [action]
          elif qValue == maxQ:
              bestActions.append(action)

      # กรณีมีหลาย action ที่ดีที่สุด ให้สุ่มเลือกหนึ่งอัน
      return random.choice(bestActions)


    def getAction(self, state):
        """
          Compute the action to take in the current state.  With
          probability self.epsilon, we should take a random action and
          take the best policy action otherwise.  Note that if there are
          no legal actions, which is the case at the terminal state, you
          should choose None as the action.

          HINT: You might want to use util.flipCoin(prob)
          HINT: To pick randomly from a list, use random.choice(list)
        """
        legalActions = self.getLegalActions(state)
        if not legalActions:
            return None
        if random.random() < self.epsilon:
            self.epsilon = max(self.min_epsilon, self.epsilon * self.decay_rate)
            return random.choice(legalActions)   # Exploration
        else:
            return self.computeActionFromQValues(state)
        
    def getTestAction(self, state):
        """
          Compute the action to take in the current state.  With
          probability self.epsilon, we should take a random action and
          take the best policy action otherwise.  Note that if there are
          no legal actions, which is the case at the terminal state, you
          should choose None as the action.

          HINT: You might want to use util.flipCoin(prob)
        """
        legalActions = self.getLegalActions(state)
        if not legalActions:
            return None
        return self.computeActionFromQValues(state)


    def update(self, state, action, nextState, reward):
      """
      Q-learning update:
      Q(s,a) ← (1 - alpha) * Q(s,a) + alpha * (reward + gamma * max Q(s', a'))
      """
      # เพิ่มจำนวนครั้งที่เยี่ยมชม state-action นี้ (หากใช้งาน self.visited)
      self.visited[(state, action)] += 1

      # ค่าปัจจุบันของ Q(state, action)
      currentQ = self.getQValue(state, action)

      # ค่าที่ดีที่สุดในสถานะถัดไป (future reward)
      nextMaxQ = self.computeValueFromQValues(nextState)

      # คำนวณ Q-value ใหม่
      updatedQ = (1 - self.alpha) * currentQ + self.alpha * (reward + self.discount * nextMaxQ)

      # บันทึกค่าใหม่
      self.qValues[(state, action)] = updatedQ
      
      self.qvalues[(state, action)] = self.qValues[(state, action)]

    def getPolicy(self, state):
        return self.computeActionFromQValues(state)

    def getValue(self, state):
        return self.computeValueFromQValues(state)

    def setEpsilon(self, epsilon):
        self.epsilon = epsilon

    def setLearningRate(self, alpha):
        self.alpha = alpha

    def setDiscount(self, discount):
        self.discount = discount

    def getLegalActions(self, state):
        """
          Get the actions available for a given
          state. This is what you should use to
          obtain legal actions for a state
        """
        # print(self.actionFn(state))
        return self.actionFn(state)

    def observeTransition(self, state, action, nextState, deltaReward):
        """
            Called by environment to inform agent that a transition has
            been observed. This will result in a call to self.update
            on the same arguments

            NOTE: Do *not* override or call this function
        """
        self.update(state, action, nextState, deltaReward)

