from abc import abstractmethod


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseDriverHelper(metaclass=Singleton):

    __slots__ = ['name']

    @abstractmethod
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def cleanup(self):
        ...