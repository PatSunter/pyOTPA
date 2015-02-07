
from datetime import time

class OD_Based_TripGenerator:
    def __init__(self, random_time_gen, od_counts,
            origin_loc_generator, dest_loc_generator, n_trips):
        self._random_time_gen = random_time_gen
        self._od_counts = od_counts
        self.n_trips = n_trips
        self._od_counts_total = sum(od_counts.itervalues())
        self._ordered_ods = sorted(od_counts.iterkeys())
        self._curr_trip_i = 0
        self._curr_od_i = 0
        self._init_ctrs_for_od(self._curr_od_i)
        self._origin_loc_generator = origin_loc_generator
        self._dest_loc_generator = dest_loc_generator

    def _init_ctrs_for_od(self, od_i):
        self._curr_od = self._ordered_ods[od_i]
        print "Updating to generate trips between ODs '%s' and '%s'" \
            % (self._curr_od[0], self._curr_od[1])
        self._trip_i_in_od = 0    
        self._scaled_trips_in_curr_od = self._calc_scaled_trips_in_od(
            self._curr_od)

    def gen_next(self):
        while self._trip_i_in_od >= self._scaled_trips_in_curr_od:
            if self._curr_od_i < (len(self._ordered_ods)-1):
                self._curr_od_i += 1
                self._init_ctrs_for_od(self._curr_od_i)
            else:
                return None

        origin_loc = self._origin_loc_generator.gen_loc_within_zone(
            self._curr_od[0])
        dest_loc = self._dest_loc_generator.gen_loc_within_zone(
            self._curr_od[1])
        # TODO:- need to link up start times with O-Ds properly later.
        T_START = time(06,00)
        T_END = time(11,00)
        start_time = self._random_time_gen.gen_time_in_range(T_START, T_END)
        trip = (origin_loc, dest_loc, start_time, self._curr_od[0], \
            self._curr_od[1])
        self._trip_i_in_od += 1
        self._curr_trip_i += 1
        return trip

    def _calc_scaled_trips_in_od(self, od_pair):
        base_trip_cnt = self._od_counts[od_pair]
        scaled_trip_cnt = int(round(base_trip_cnt * self.n_trips / \
            float(self._od_counts_total)))
        return scaled_trip_cnt


