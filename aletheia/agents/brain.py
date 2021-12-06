class Thing:
    def __init__(self, name) -> None:
        self.name = name

        
class Agent(Thing):
    is_a = [Thing]
    def __init__(self, name) -> None:
        super().__init__(name)


class World(dict):

    def dotGet (self, attr):
        return dict.__getitem__(self, attr)

    def dotSet (self, attr, value):
        return dict.__setitem__(self, attr, value)

    def allowDotting (self, state=True):
        if state:
            self.__getattr__ = self.dotGet
            self.__setattr__ = self.dotSet
        else:
            del self.__setattr__
            del self.__getattr__

            