#!/usr/bin/env python2

import urllib
import urllib2
import os.path
import json
from datetime import datetime, date, time, timedelta
from math import radians, cos, sin, asin, sqrt

OTP_DATE_FMT = "%Y-%m-%d"
OTP_TIME_FMT = "%H:%M:%S"

# Note:- could possibly also use the shapely length function, or 
# geopy has a Vincenty Distance implementation
# see:- http://gis.stackexchange.com/questions/4022/looking-for-a-pythonic-way-to-calculate-the-length-of-a-wkt-linestring
def haversine(lon1, lat1, lon2, lat2):
    """
     Calculate the great circle distance between two points 
     on the earth (specified in decimal degrees) - return in metres
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    metres = km * 1000
    return metres 

def build_trip_request_url(server_url, routing_params, trip_date, trip_time,
        origin_lon_lat, dest_lon_lat, otp_router_id=None):
    date_str = trip_date.strftime(OTP_DATE_FMT)
    time_str = trip_time.strftime(OTP_TIME_FMT)

    reqStr = "/opentripplanner-api-webapp/ws" + "/plan" + '?'
    # General OTP routing request stuff
    reqStr += "&".join([name+'='+urllib2.quote(str(val)) for name, val \
        in routing_params.iteritems()])
    reqStr += '&'+'fromPlace'+'='+str(origin_lon_lat[1])+','+str(origin_lon_lat[0])
    reqStr += '&'+'toPlace'+'='+str(dest_lon_lat[1])+','+str(dest_lon_lat[0])
    reqStr += '&'+'time'+'='+date_str+'T'+urllib2.quote(time_str)
    if otp_router_id is not None:
        reqStr += '&'+'routerId'+'='+otp_router_id
    # Add server URL
    url = server_url + reqStr
    return url

def route_trips_and_save_details(server_url, otp_router_id, save_path,
        save_suffix, trips, date, routing_params): 

    if os.path.exists(save_path) is False: 
        os.makedirs(save_path)

    for trip_id, trip_tuple in trips.iteritems():
            print "About to request routes for trip %d,and save results:" \
                % (trip_id)

            date_mod, time_mod = date_time_tuple
            url = build_trip_request_url(server_url, routing_params,
                date_mod, time_mod, origin_lon_lat, dest_lon_lat, 
                otp_router_id)
            print url
            response = urllib2.urlopen(url)
            data = response.read()
            f = open(fname, "w")
            f.write(data)
            f.close()

            print "DONE!\n"
    return

def save_trip_stats(multi_graph_iso_set):
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        route_trips_and_save_details(server_url, otp_router_id, save_path,
            save_suffix, **isos_spec)

def get_total_sec(td):
    return td.days * 24 * 3600 + td.seconds + td.microseconds / float(10**6)

def get_td_pct(td1, td2):
    return get_total_sec(td1) / float(get_total_sec(td2)) * 100

def print_trip_stats(origin_lon_lat, dest_lon_lat, trip_req_start_dt, itin):
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
    dist_direct = haversine(origin_lon_lat[0], origin_lon_lat[1],
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

if __name__ == "__main__":
    server_url = 'http://130.56.248.56'
    routing_params = {}

    routing_params = {
    }
    # See RoutingRequest.java in OTP for comments on each of these.
    routing_params = {
        'arriveBy':'false',
        'mode':'TRANSIT,WALK',
        'maxTransfers':4,
        #'maxWalkDistance':4000,
        'maxWalkDistance':1000,
        'clampInitialWait':0,
        'walkSpeed':1.38, # Default for OTP, also seems quite close to Google
        # See
        # http://www.quora.com/Google-Maps/What-is-the-assumed-walking-speed-in-Google-Mapss-time-estimates
        # for more on Google walk speed
        #parameter rep. ratio of how much worse walking is than waiting.
        # Does have an impact, closer to 1.0 will be more 'walk-like' round
        # origin, but seems to mean missing some possible places at the end.
        'waitReluctance':0.95,   # Default is 0.95
        'walkReluctance':1.01, 
        'walkBoardCost':30, # Suggsted by Albert Steiner to reduce disutility
          # of transfers. Default is 60 * 5 - ~5 minutes??
        'bikeBoardCost':30, # Default is 60 * 10 = 600.  
        'transferPenalty':0, # Default 0. Apparently can be an "extra" penalty 
          # above and beyond walkBoardCost and bikeBoardCost?
    }

    trip_req_start_date = date(year=2015,month=2,day=16)
    trip_req_start_time = time(7,45)
    trip_req_start_dt = datetime.combine(trip_req_start_date,
        trip_req_start_time)
    #origin_lon_lat = (144.876791,-37.749236) 
    #dest_lon_lat = (145.091024,-37.897849)
    origin_lon_lat = (144.941184,-37.700166)
    dest_lon_lat = (145.089924,-37.717540)

    graphs = {
        'PTV':'MelbTrainTramBus-2014_06-metro_bus',
        'BZE':'MelbTrainTramBus-BZE-autostops-withcongestion-WithMotorways-updated-20140724',
        'PTUA':'MelbTrainTramBus-PTUA-add_upgraded_extended_trains_upgraded_extended_auto_600_trams_upgraded_buses-v2-20141115',
        }

    for graph_short, graph_full in graphs.iteritems():
        url = build_trip_request_url(server_url, routing_params,
            trip_req_start_date, 
            trip_req_start_time, origin_lon_lat, dest_lon_lat,
            otp_router_id=graph_full)
        print url

        response = urllib2.urlopen(url)
        data = response.read()

        #f = open("trip.txt", 'w')
        #f.write(data)
        #f.close()

        jdata = json.loads(data)

        #import pprint
        #pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(jdata)
        
        itin = jdata['plan']['itineraries'][0]
        
        print "Routing on the %s network/timetable, Requested trip took:" \
            % graph_short
        print_trip_stats(origin_lon_lat, dest_lon_lat, trip_req_start_dt, itin)
