import _thread, json, time
from collections import deque

# Shared buffer for messages
BUFFER_LIMIT = 20   # max number of entries
buffer = deque([], BUFFER_LIMIT)
buffer_lock = _thread.allocate_lock()

# Core0: producer
def log_measurement(data):
    line = json.dumps(data)
    with buffer_lock:
        buffer.append(line)

# Core1: consumer
def get_entry():
        with buffer_lock:
            if len(buffer) > 0:
                line = buffer.popleft()
            else:
                line = None
        return line