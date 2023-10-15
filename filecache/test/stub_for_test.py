
import time
from filecache import filecache

@filecache(30)
def the_time() -> float:
    return time.time()
