
import random
import operator
from datetime import time, date, datetime, timedelta

class TimeGenerator:
    def initialise(self):
        return

    def update_zones(self, od_pair, trip_cnt_to_gen_from_zone):
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

class RandomTimeGenerator(TimeGenerator):
    def __init__(self, seed, min_time, max_time):
        self._random_seed = seed
        self._randomiser = None
        self._min_time = min_time
        self._max_time = max_time

    def initialise(self):
        self._randomiser = random.Random(self._random_seed)
        
    def gen_time(self):
        gen_time = gen_random_time_in_range_minute(self._randomiser,
            self._min_time, self._max_time)
        return gen_time

class ZoneBlockBasedTimeGenerator(TimeGenerator):
    def __init__(self, seed, od_counts_by_time):
        self._random_seed = seed
        self._randomiser = None
        self._od_counts_by_time = od_counts_by_time

    def initialise(self):
        self._randomiser = random.Random(self._random_seed)
        
    def update_zones(self, od_pair, trip_cnt_to_gen_from_zone):
        self._trip_cnt_to_gen_from_curr_zone = trip_cnt_to_gen_from_zone
        self._curr_zone_trip_cnts = {}
        time_start_vals = []
        trip_cnts_in_zone = self._od_counts_by_time[od_pair]
        total_trip_cnt_in_zone = sum(trip_cnts_in_zone.itervalues())
        # Make a dict of scaled trips to generate per time-zone.
        self._curr_od_trip_scaled_trip_cnts = {}
        # Because of allocating out a fractional count, need to 
        # do a 2-stage process here.
        scaled_trip_cnt_floats_map = {}
        for t_str, trip_cnt in self._od_counts_by_time[od_pair].iteritems():
            t_val = (datetime.strptime(t_str, "%H:%M")).time()
            time_start_vals.append(t_val)
            if total_trip_cnt_in_zone:
                scaled_trip_cnt_float = trip_cnt * trip_cnt_to_gen_from_zone \
                        / float(total_trip_cnt_in_zone)
            else:
                scaled_trip_cnt_float = 0
            scaled_trip_cnt_floats_map[t_val] = scaled_trip_cnt_float
        
        trips_allocated = 0
        for t_val in time_start_vals:
            self._curr_od_trip_scaled_trip_cnts[t_val] = 0
        while trips_allocated < trip_cnt_to_gen_from_zone:
            max_cnt_pair = max(scaled_trip_cnt_floats_map.iteritems(),
                key=operator.itemgetter(1))
            self._curr_od_trip_scaled_trip_cnts[max_cnt_pair[0]] += 1
            scaled_trip_cnt_floats_map[max_cnt_pair[0]] = max_cnt_pair[1] - 1
            trips_allocated += 1
        assert sum(self._curr_od_trip_scaled_trip_cnts.itervalues()) \
            == trip_cnt_to_gen_from_zone
        self._sorted_curr_od_blocks = sorted(time_start_vals)
        self._ctr_within_zone = 0
        self._next_time_block_trip_i_in_zone = 0
        self._update_time_block(0)
        return

    def _update_time_block(self, block_i):
        self._curr_block_i = block_i
        self._curr_block = self._sorted_curr_od_blocks[block_i]
        self._curr_block_end = (datetime.combine(date.today(),
            self._curr_block) + timedelta(hours=1)).time()
        self._next_time_block_trip_i_in_zone += \
            self._curr_od_trip_scaled_trip_cnts[self._curr_block]
        print "Updating gen_times to create %d trips b/w %s and %s" % \
            (self._curr_od_trip_scaled_trip_cnts[self._curr_block], \
             self._curr_block, self._curr_block_end)

    def gen_time(self):
        assert sum(self._curr_od_trip_scaled_trip_cnts.itervalues()) > 0
        while self._ctr_within_zone >= self._next_time_block_trip_i_in_zone:
            next_block_i = self._curr_block_i+1
            self._update_time_block(self._curr_block_i+1)
        gen_time = gen_random_time_in_range_minute(self._randomiser,
            self._curr_block, self._curr_block_end)
        self._ctr_within_zone += 1
        return gen_time


