from datetime import datetime, timedelta

import geom_utils

def get_total_sec(td):
    return td.days * 24 * 3600 + td.seconds + td.microseconds / float(10**6)

def get_td_pct(td1, td2):
    return get_total_sec(td1) / float(get_total_sec(td2)) * 100

def print_single_trip_stats(origin_lon_lat, dest_lon_lat, trip_req_start_dt, itin):
    st_raw = itin['startTime']
    et_raw = itin['endTime']
    itin_start_dt = datetime.fromtimestamp(st_raw / 1000.0) 
    itin_end_dt = datetime.fromtimestamp(et_raw / 1000.0)

    total_trip_dt = itin_end_dt - trip_req_start_dt
    total_trip_sec = get_total_sec(total_trip_dt)
    init_wait_dt = itin_start_dt - trip_req_start_dt    
    tfer_wait_dt = timedelta(seconds=itin['waitingTime'])
    total_wait_dt = init_wait_dt + tfer_wait_dt
    wait_pct = get_td_pct(total_wait_dt, total_trip_dt)
    walk_dt = timedelta(seconds=itin['walkTime'])
    walk_pct = get_td_pct(walk_dt, total_trip_dt)
    transit_dt = timedelta(seconds=itin['transitTime'])
    transit_pct = get_td_pct(transit_dt, total_trip_dt)

    dist_travelled = 0
    for leg in itin['legs']:
        dist_travelled += leg['distance']
    dist_direct = geom_utils.haversine(origin_lon_lat[0], origin_lon_lat[1],
        dest_lon_lat[0], dest_lon_lat[1])

    trip_speed_along_route = (dist_travelled / 1000.0) \
        / (total_trip_sec / (60 * 60.0))
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))

    print "Trip departs at %s" % itin_start_dt 
    print "Trip arrives at %s" % itin_end_dt 
    print "%s total time (inc initial wait)" % total_trip_dt
    print "  %s (%.2f%%) waiting (%s initial, %s transfers)" \
        % (total_wait_dt, wait_pct, init_wait_dt, tfer_wait_dt)
    print "  %s (%.2f%%) walking (for %.2fm)" \
        % (walk_dt, walk_pct, itin['walkDistance'])
    print "  %s (%.2f%%) on transit vehicles (%d transfers)" \
        % (transit_dt, transit_pct, itin['transfers'])
    print "Total trip distance (as crow flies): %.2fm." % dist_direct
    print "Total trip distance (travelled): %.2fm." % dist_travelled
    print "(Trip directness ratio:- %.2f)" % (dist_direct / dist_travelled)
    print "Trip speed (along route, inc. init wait): %.2fkm/h." \
        % trip_speed_along_route
    print "Trip speed (as crow flies, inc. init wait): %.2fkm/h." \
        % trip_speed_direct
    return


