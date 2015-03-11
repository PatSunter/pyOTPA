import sys
import operator
from datetime import date, time, datetime

import abs_zone_io

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

##------------------------------------

VISTA_TRIPS_TABLE = 'vista_t'
VISTA_PEOPLE_TABLE = 'vista_p'
VISTA_DOW_LOOKUP_TABLE = 'tbl_day'
VISTA_MODE_LOOKUP_TABLE = 'tbl_mainmode'
V_TRIP_ID_FIELD = 'TRIPID'
V_PERSON_ID_FIELD = 'PERSID'

def create_vista_day_code_name_map(connection):
    day_code_name_map = {}
    sql = "select Code, Name from %s"\
            % (VISTA_DOW_LOOKUP_TABLE)
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    for row in rows:
        day_code_name_map[int(row[0])] = row[1]
    return day_code_name_map

def get_vista_mode_codes(connection, mode_names):
    mode_codes = []
    sql = "select code, name from %s"\
            % (VISTA_MODE_LOOKUP_TABLE)
    cursor = connection.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    mode_name_dict = {}
    for row in rows:
        mode_name_dict[row[1]] = int(row[0])
    for m_name in mode_names:
        mode_codes.append(mode_name_dict[m_name])
    return mode_codes

class VISTA_DB_TripGenerator(TripGenerator):
    def __init__(self, connection,
            origin_loc_gen, dest_loc_gen, n_trips,
            trips_date_week_start,
            ccd_feats_dict,
            skipped_modes = None,
            allowed_origin_slas = None,
            allowed_dest_slas = None,
            trip_min_dist_km = None):
        self._connection = connection
        self._origin_loc_generator = origin_loc_gen
        self._dest_loc_generator = dest_loc_gen
        self.n_trips = n_trips
        self._trips_date_week_start = trips_date_week_start
        self._ccd_feats_dict = ccd_feats_dict
        self.skipped_modes = skipped_modes
        self.allowed_origin_slas = allowed_origin_slas
        self.allowed_dest_slas = allowed_dest_slas
        self.trip_min_dist_km = trip_min_dist_km
        self._trips_cursor = None
        self._skipped_mode_codes = None
        return

    def initialise(self): 
        self._origin_loc_generator.initialise()
        self._dest_loc_generator.initialise()
        self._curr_trip_i = 0
        # Initialise DOW table
        self._day_code_name_map = create_vista_day_code_name_map(
            self._connection)
        self._skipped_mode_codes = get_vista_mode_codes(self._connection,
            self.skipped_modes)
        self._trips_cursor = self._connection.cursor()
        # The "order by " clause is to save re-calculating any necessary
        # buffers etc where possible.
        sql = "select TRIPID, PERSID, STARTIME, ORIGCCD, DESTCCD, DISTMODE, "\
                "CUMDIST from %s "\
                "order by ORIGCCD, DESTCCD"\
                % (VISTA_TRIPS_TABLE)
                #"where TRIPID = 'Y07H063109P01T03' "\
        self._trips_cursor.execute(sql)
        return

    def gen_next(self):
        trip_valid = False
        while not trip_valid:
            trip_row = self._trips_cursor.fetchone()
            if trip_row == None:
                print "Warning:- Ran out of trips in your VISTA DB "\
                    "that satisfy constraints."
                return None
            trip_id = trip_row[0]
            pers_id = trip_row[1]
            trip_start_time_min = int(trip_row[2])
            origin_ccd = str(int(trip_row[3]))
            dest_ccd = str(int(trip_row[4]))
            dist_mode = int(trip_row[5])
            trip_dist_km = trip_row[6]
            origin_sla = abs_zone_io.get_sla_name_ccd_within(
                self._ccd_feats_dict, origin_ccd)
            dest_sla = abs_zone_io.get_sla_name_ccd_within(
                self._ccd_feats_dict, dest_ccd)
            # Now check the trip is 'valid' according to any constraint
            # criteria to apply.
            trip_valid = True
            if self.allowed_origin_slas \
                    and origin_sla not in self.allowed_origin_slas:
                trip_valid = False
            if self.allowed_dest_slas \
                    and dest_sla not in self.allowed_dest_slas:
                trip_valid = False
            if self._skipped_mode_codes \
                    and dist_mode in self._skipped_mode_codes:
                trip_valid = False
            if self.trip_min_dist_km \
                    and trip_dist_km < self.trip_min_dist_km:
                trip_valid = False

        sql = "select TRAVDOW from %s where %s = '%s'" \
            % (VISTA_PEOPLE_TABLE, V_PERSON_ID_FIELD, pers_id)
        # Use a separate cursor for person lookup stuff.
        cursor = self._connection.cursor()
        cursor.execute(sql)
        pers_row = cursor.fetchone()
        cursor.close()
        trip_dow_code = int(pers_row[0])
        try:
            trip_start_dt = self.gen_trip_datetime(trip_dow_code,
                trip_start_time_min)
        except ValueError as e:
            print "Error while trying to create the start time for VISTA "\
                "trip with ID %s:- %s" % (trip_id, e)
            sys.exit(1)    
        self._origin_loc_generator.update_zone(origin_ccd)
        self._dest_loc_generator.update_zone(dest_ccd)
        origin_loc = self._origin_loc_generator.gen_loc_within_curr_zone()
        dest_loc = self._dest_loc_generator.gen_loc_within_curr_zone()
        trip = (origin_loc, dest_loc, trip_start_dt, \
            origin_sla, dest_sla, trip_id)
        self._curr_trip_i += 1

        return trip

    def cleanup(self):
        if self._trips_cursor:
            self._trips_cursor.close()
        self._origin_loc_generator.cleanup()
        self._dest_loc_generator.cleanup()
        return

    def gen_trip_datetime(self, trip_dow_code, trip_start_time_min):
        days_to_add = trip_dow_code-1
        if trip_start_time_min > 28 * 60:
            raise ValueError("Trip start time in min is > 4AM the "\
                "following day: unexpected for VISTA trips.")
        if trip_start_time_min >= 24 * 60:
            # the start time is the next morning.
            trip_start_time_min -= 24 * 60
            days_to_add += 1
        # Add the # of days in day_code to start date.
        wk_start = self._trips_date_week_start
        trip_date = date(wk_start.year, wk_start.month, 
            wk_start.day + days_to_add)
        trip_start_clk_hr = trip_start_time_min / 60 
        if trip_start_clk_hr >= 24:
            raise ValueError("Input trip time minute %d couldn't be "\
                "converted to a clock hour." % trip_start_time_min)
        trip_start_clk_min = trip_start_time_min % 60
        trip_time = time(hour=trip_start_clk_hr, 
            minute=trip_start_clk_min)
        trip_dt = datetime.combine(trip_date, trip_time)
        return trip_dt

