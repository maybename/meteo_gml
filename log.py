import time

class log:
    def __init__(self, file:str) -> None:        
        self.file = file
        try:
            with open(self.file, "r") as f: #opens the file
                f.close()
            
        except: #creates the file
            with open(self.file, "w") as f: #opens the file
                f.close()
        
    def write(self, *args, end = "\n", timestamp:bool | str = True):
        args = [str(arg) for arg in args]
        text = ' '.join(args)
        if type(timestamp) == bool:
            if timestamp:
                timestamp = '[' + str(time.time()) + ']\t'
            else:
                timestamp = ''
                
        with open(self.file, "a") as f:
            f.write(timestamp + text + end)
            f.close()