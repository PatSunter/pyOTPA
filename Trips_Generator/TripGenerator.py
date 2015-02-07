
class OD_Based_TripGenerator:
    def __init__(self, time_generator, od_counts,
            origin_loc_generator, dest_loc_generator, n_trips):
        self._time_generator = time_generator
        self._od_counts = od_counts
        self.n_trips = n_trips
        self._od_counts_total = sum(od_counts.itervalues())
        self._ordered_ods = sorted(od_counts.iterkeys())
        self._origin_loc_generator = origin_loc_generator
        self._dest_loc_generator = dest_loc_generator

    def initialise(self):    
        self._origin_loc_generator.initialise()
        self._dest_loc_generator.initialise()
        self._time_generator.initialise()
        self._curr_trip_i = 0
        self._curr_od_i = 0
        self.update_zones(self._ordered_ods[0])

    def update_zones(self, od_pair):
        self._curr_od = od_pair
        self._init_ctrs_for_curr_od()
        self._origin_loc_generator.update_zone(self._curr_od[0])
        self._dest_loc_generator.update_zone(self._curr_od[1])
        self._time_generator.update_zones(self._curr_od,
            self._scaled_trips_in_curr_od)

    def _init_ctrs_for_curr_od(self):
        print "Updating to generate trips between ODs '%s' and '%s'" \
            % (self._curr_od[0], self._curr_od[1])
        self._trip_i_in_od = 0
        self._scaled_trips_in_curr_od = self._calc_scaled_trips_in_od(
            self._curr_od)

    def gen_next(self):
        while self._trip_i_in_od >= self._scaled_trips_in_curr_od:
            if self._curr_od_i < (len(self._ordered_ods)-1):
                self._curr_od_i += 1
                self.update_zones(self._ordered_ods[self._curr_od_i])
            else:
                return None

        origin_loc = self._origin_loc_generator.gen_loc_within_curr_zone()
        dest_loc = self._dest_loc_generator.gen_loc_within_curr_zone()
        start_time = self._time_generator.gen_time()
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

    def cleanup(self):
        self._origin_loc_generator.cleanup()
        self._dest_loc_generator.cleanup()
        self._time_generator.cleanup()
        return

