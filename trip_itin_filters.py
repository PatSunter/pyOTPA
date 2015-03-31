"""Filters on a dict of TripItinerarys :- to produce a list of trip IDs that
match the criteria."""

# Filters that rely on trip itinerary results
DEFAULT_LONGEST_WALK_LEN_KM = 1.2

def get_trip_ids_with_walk_leg_gr_than_dist_km(trip_results, dist_km):
    trip_ids_match_criteria = []
    for trip_id, trip_result in trip_results.iteritems():
        longest_walk_m = trip_result.get_longest_walk_leg_dist_m()
        if longest_walk_m / 1000.0 > dist_km:
            trip_ids_match_criteria.append(trip_id)
            #print "(trip %s matches since it's longest walk leg "\
            #    "was %fm.)" % (trip_id, longest_walk_m)
    return trip_ids_match_criteria

def get_trip_ids_with_total_time_gr_than(trip_results, trip_req_start_dts,
        comp_td):
    trip_ids_match_criteria = []
    for trip_id, trip_result in trip_results.iteritems():
        trip_req_start_dt = trip_req_start_dts[trip_id]
        trip_total_time = trip_result.get_total_trip_td(trip_req_start_dt)
        if trip_total_time > comp_td:
            trip_ids_match_criteria.append(trip_id)
            #print "(trip %s matches since it's total time "\
            #    "was %s.)" % (trip_id, trip_total_time)
    return trip_ids_match_criteria

