import operator

class TripGenerator:
    def initialise(self):    
        return

    def gen_next(self):
        raise NotImplementedError("Method needs to be implemented.")

    def cleanup(self):
        return

class OD_Based_TripGenerator(TripGenerator):
    def __init__(self, time_generator, od_counts,
            origin_loc_generator, dest_loc_generator,
            n_trips, assign_fully=True):
        self._time_generator = time_generator
        self._od_counts = od_counts
        self.n_trips = n_trips
        self._od_counts_total = sum(od_counts.itervalues())
        self._ordered_ods = sorted(od_counts.iterkeys())
        self._od_counts_scaled = None
        self._assign_fully = assign_fully
        self._origin_loc_generator = origin_loc_generator
        self._dest_loc_generator = dest_loc_generator

    def initialise(self):    
        self._origin_loc_generator.initialise()
        self._dest_loc_generator.initialise()
        self._time_generator.initialise()
        self._curr_trip_i = 0
        self._curr_od_i = 0
        self.assign_scaled_trip_counts_to_ods()
        self.update_zones(self._ordered_ods[0])

    def assign_scaled_trip_counts_to_ods(self):    
        print "Assigning the %d requested trips to the %d OD pairs:" \
            % (self.n_trips, len(self._od_counts))

        od_counts_scaled_floats = {}
        for od_pair in self._ordered_ods:
            base_trip_cnt = self._od_counts[od_pair]
            od_counts_scaled_floats[od_pair] = base_trip_cnt \
                * self.n_trips / float(self._od_counts_total)
        self._od_counts_scaled = {}
        if not self._assign_fully:
            # proportionately assign all trips as a fraction of total, rounded. 
            # Means there may be less trips generated than
            # the requested total due to rounding.
            for od_pair in self._ordered_ods:
                self._od_counts_scaled[od_pair] = int(round(
                    od_counts_scaled_floats[od_pair]))
        else:            
            # Assign the exact number of requested trips, based on maximums.
            # Means there may be some trips assigned there may be some
            # rounding up done to make sure all trips allocated.
            trips_assigned = 0
            for od_pair in self._ordered_ods:
                self._od_counts_scaled[od_pair] = 0
            while trips_assigned < self.n_trips:
                max_cnt_pair = max(od_counts_scaled_floats.iteritems(),
                    key=operator.itemgetter(1))
                self._od_counts_scaled[max_cnt_pair[0]] += 1
                od_counts_scaled_floats[max_cnt_pair[0]] = \
                    max_cnt_pair[1] - 1
                trips_assigned += 1
        print "...assigned %d trips." \
            % (sum(self._od_counts_scaled.itervalues()))
        return

    def update_zones(self, od_pair):
        self._curr_od = od_pair
        self._init_ctrs_for_curr_od()
        if self._scaled_trips_in_curr_od > 0:
            print "Updating to generate %d trips between ODs '%s' and '%s'" \
                % (self._scaled_trips_in_curr_od, od_pair[0], od_pair[1])
            self._origin_loc_generator.update_zone(self._curr_od[0])
            self._dest_loc_generator.update_zone(self._curr_od[1])
            self._time_generator.update_zones(self._curr_od,
                self._scaled_trips_in_curr_od)
        else:
            #print "No trips to generate between ODs '%s' and '%s'" \
            #    % (od_pair[0], od_pair[1])
            pass
        return

    def _init_ctrs_for_curr_od(self):
        self._trip_i_in_od = 0
        self._scaled_trips_in_curr_od = self._od_counts_scaled[self._curr_od]

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

    def cleanup(self):
        self._origin_loc_generator.cleanup()
        self._dest_loc_generator.cleanup()
        self._time_generator.cleanup()
        return

