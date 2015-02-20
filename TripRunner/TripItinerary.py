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

    def save_to_file(self, output_fname):
        f = open(output_fname, 'w')
        f.write(json.dumps(self.json))
        f.close()
        return

def read_trip_itin_from_file(input_fname):
    f = open(input_fname, 'r')
    itin_str = f.read()
    itin_json = json.loads(itin_str)
    itin = TripItinerary(itin_json)
    return itin


