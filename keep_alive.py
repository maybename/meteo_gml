from time import ticks_ms

class WDT:
    def __init__(self, timeout: int = 5000):
        self.timeout = timeout
        self.timer = 0

    def reset(self):
        self.timer = 0
        
    def feed(self):
        self.timer = ticks_ms()
        #print(self, " feeded")

    def is_alive(self):
        #print(self.timer, self.timeout, ticks_ms())
        if self.timer == 0:
            #print("WDT is alive")
            return True
        return self.timer + self.timeout > ticks_ms()