from abc import ABC, abstractmethod

class Stresser(ABC):
    
    @abstractmethod
    def run(self):
        pass
    
    @abstractmethod
    def monitor(self):
        pass
