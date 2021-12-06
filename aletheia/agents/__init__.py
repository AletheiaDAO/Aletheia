"""
general agent framework
"""
from datamodel import  AgentModel

class Agent:
    def __init__(self, unique_id: int, system) -> None:
        self.unique_id = unique_id
        self.system = system
        self.state = {} # the agent
        self.state_history = []
        self.agentModel = AgentModel(unique_id=unique_id, step = system.step, state=self.state)
        pass

    def step(self) -> None:
        pass

    def save(self) -> None:
        # id, timestamp, step, state
        self.agentModel.step = self.system.step
        self.agentModel.state = self.state
        self.agentModel.save()

    @property
    def model(self):
        return self.agentModel