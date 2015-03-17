from datetime import datetime, timedelta
import json

import time_utils

class TripItinerary:
    """This is really a lightweight wrapper class around OTP's 'itinerary'
    JSON data structure returned from calls to the OTP Planner API. See:-
    http://docs.opentripplanner.org/apidoc/0.10.0/el_ns0_response.html
    """

    def __init__(self, json_data):
        self.json = json_data
        # Initialise to empty various results to be cached later.
        self._dist_travelled = None
    
    def get_start_dt(self):
        st_raw = self.json['startTime']
        return datetime.fromtimestamp(st_raw / 1000.0) 

    def get_end_dt(self):
        et_raw = self.json['endTime']
        return datetime.fromtimestamp(et_raw / 1000.0)

    def get_total_trip_td(self, trip_req_start_dt):
        return self.get_end_dt() - trip_req_start_dt

    def get_total_trip_sec(self, trip_req_start_dt):
        return time_utils.get_total_sec(self.get_total_trip_td(trip_req_start_dt))

    def get_init_wait_td(self, trip_req_start_dt):
        return self.get_start_dt() - trip_req_start_dt

    def get_tfer_wait_td(self):
        """I am calling this 'transfer wait' since OTP records in the
        waitingTime value just time waiting for transfers, not the initial
        wait."""
        return timedelta(seconds=self.json['waitingTime'])

    def get_total_wait_td(self, trip_req_start_dt):
        return self.get_init_wait_td(trip_req_start_dt) \
            + self.get_tfer_wait_td()

    def get_transit_td(self):
        return timedelta(seconds=self.json['transitTime'])

    def get_walk_td(self):
        return timedelta(seconds=self.json['walkTime'])

    def get_dist_travelled(self):
        """Returns the total trip distance, in m."""
        if not self._dist_travelled:
            dist_travelled = 0
            for leg in self.json['legs']:
                dist_travelled += leg['distance']
            self._dist_travelled = dist_travelled
        return self._dist_travelled
 
    def get_trip_speed_along_route(self, trip_req_start_dt):
        """Returns the trip speed along route, in km/h"""
        dist = self.get_dist_travelled()
        total_trip_sec = self.get_total_trip_sec(trip_req_start_dt)
        trip_speed_along_route = (dist / 1000.0) \
            / (total_trip_sec / (60 * 60.0))
        return trip_speed_along_route

    def get_longest_walk_leg_dist_m(self):
        longest_walk_leg_m = 0.0
        for leg in self.json['legs']:
            if leg['mode'] == 'WALK':
                walk_len = leg['distance']
                if walk_len > longest_walk_leg_m:
                    longest_walk_leg_m = walk_len
        return longest_walk_leg_m

    def get_set_of_modes_used(self):
        """Returns the Set of modes used in this trip (as strings)."""
        modes_used = set()
        for leg in self.json['legs']:
            modes_used.add(leg['mode'])
        return modes_used

    def get_mode_sequence(self):
        """Returns the modes used in this trip, in the order they were
        used."""
        modes_used_seq = []
        for leg in self.json['legs']:
            modes_used_seq.append(leg['mode'])
        return modes_used_seq

    def get_first_non_walk_mode(self):
        """Returns as a string, the first mode used in the trip other than
        WALK. If the trip only contained a single walk leg, returns None."""
        first_non_walk_mode = None
        if len(self.json['legs']) > 1 \
                or self.json['legs'][0]['mode'] != 'WALK':
            for leg in self.json['legs']:
                if leg['mode'] != 'WALK':
                    first_non_walk_mode = leg['mode']
                    break
            assert first_non_walk_mode
        return first_non_walk_mode        

    def get_dist_m_by_mode(self):
        dist_m_by_mode = {}
        for leg in self.json['legs']:
            mode = leg['mode']
            if mode not in dist_m_by_mode:
                dist_m_by_mode[mode] = leg['distance']
            else:    
                dist_m_by_mode[mode] += leg['distance']
        return dist_m_by_mode

    def get_set_of_agencies_used(self):
        """Returns all the agencies used in this trip, as a Set of strings."""
        agencies_set = set()
        for leg in self.json['legs']:
            mode = leg['mode']
            if mode == 'WALK': continue
            agency = leg['agencyName']
            agencies_set.add(agency)
        return agencies_set

    def get_time_sec_by_mode(self):
        time_s_by_mode = {}
        for leg in self.json['legs']:
            mode = leg['mode']
            time_sec = leg['duration'] / 1000.0
            if mode not in time_s_by_mode:
                time_s_by_mode[mode] = time_sec
            else:    
                time_s_by_mode[mode] += time_sec
        return time_s_by_mode

    def save_to_file(self, output_fname):
        f = open(output_fname, 'w')
        f.write(json.dumps(self.json))
        f.close()
        return

def read_trip_itin_from_file(input_fname):
    f = open(input_fname, 'r')
    itin_str = f.read()
    f.close()
    itin_json = json.loads(itin_str)
    itin = TripItinerary(itin_json)
    return itin


