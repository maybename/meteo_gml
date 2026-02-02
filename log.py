import time, _thread

class log:
    def __init__(self, file:str, remember_writes = 5) -> None:
        self.lock = _thread.allocate_lock()
        self.file = file
        self.tail = [' '*100 for i in range(remember_writes)]
        try:
            with open(self.file, "r") as f: #opens the file
                pass
            
        except: #creates the file
            with open(self.file, "w") as f: #opens the file
                pass
            
        
    def write(self, *args, end = "\n", timestamp:bool | str = True):
        args = [str(arg) for arg in args]
        text = ' '.join(args)
        if type(timestamp) == bool:
            if timestamp:
                timestamp = '[' + str(time.time()) + ']\t'
            else:
                timestamp = ''
                
        self.lock.acquire()                
        with open(self.file, "a") as f:
            f.write(timestamp + text + end)
        f.close()
        self.lock.release()
        for i in range(len(self.tail) - 1):
            self.tail[i] = self.tail[i+1]
        
        self.tail[-1] = timestamp + text + end
        
        
    def last_writes(self) -> list[str]:
        return self.tail