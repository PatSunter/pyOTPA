
import random
from datetime import time

class RandomTimeGenerator:
    def __init__(self, seed):
        self._random_seed = seed
        self._randomiser = random.Random(seed)

    def gen_time_in_range(self, time_start, time_end):
        assert time_end > time_start
        ts_min = time_start.hour * 60 + time_start.minute
        te_min = time_end.hour * 60 + time_end.minute
        gt_min = self._randomiser.randrange(ts_min, te_min)
        gen_time = time(gt_min / 60, gt_min % 60)
        return gen_time


