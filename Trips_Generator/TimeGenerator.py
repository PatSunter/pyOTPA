
import random
from datetime import time

class TimeGenerator:
    def initialise(self):
        return

    def update_zones(self, od_pair):
        return
    
    def gen_time(self):
        raise NotImplementedError("Error, needed function not included.")

    def cleanup(self):
        return

##############

def gen_random_time_in_range_minute(randomiser, time_start, time_end):
    assert time_end > time_start
    ts_min = time_start.hour * 60 + time_start.minute
    te_min = time_end.hour * 60 + time_end.minute
    gt_min = randomiser.randrange(ts_min, te_min)
    gen_time = time(gt_min / 60, gt_min % 60)
    return gen_time

class RandomTimeGenerator:
    def __init__(self, seed, min_time, max_time):
        self._random_seed = seed
        self._randomiser = None
        self._min_time = min_time
        self._max_time = max_time

    def initialise(self):
        self._randomiser = random.Random(self._random_seed)
        
    def update_zones(self, od_pair):
        return

    def gen_time(self):
        gen_time = gen_random_time_in_range_minute(self._randomiser,
            self._min_time, self._max_time)
        return gen_time
