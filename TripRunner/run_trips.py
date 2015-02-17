#!/usr/bin/env python2

import urllib
import urllib2
import os.path
import json
from datetime import datetime, date, time

import trip_analysis

OTP_DATE_FMT = "%Y-%m-%d"
OTP_TIME_FMT = "%H:%M:%S"

def build_trip_request_url(server_url, routing_params, trip_date, trip_time,
        origin_lon_lat, dest_lon_lat, otp_router_id=None):
    date_str = trip_date.strftime(OTP_DATE_FMT)
    time_str = trip_time.strftime(OTP_TIME_FMT)

    reqStr = "/opentripplanner-api-webapp/ws" + "/plan" + '?'
    # General OTP routing request stuff
    reqStr += "&".join([name+'='+urllib2.quote(str(val)) for name, val \
        in routing_params.iteritems()])
    reqStr += '&'+'fromPlace'+'='+str(origin_lon_lat[1]) \
        + ','+str(origin_lon_lat[0])
    reqStr += '&'+'toPlace'+'='+str(dest_lon_lat[1])+','+str(dest_lon_lat[0])
    reqStr += '&'+'time'+'='+date_str+'T'+urllib2.quote(time_str)
    if otp_router_id is not None:
        reqStr += '&'+'routerId'+'='+otp_router_id
    # Add server URL
    url = server_url + reqStr
    return url

def run_trip(server_url, routing_params, trip_req_start_date,
        trip_req_start_time, origin_lon_lat, dest_lon_lat, otp_router_id):

    url = build_trip_request_url(server_url, routing_params,
        trip_req_start_date, 
        trip_req_start_time, origin_lon_lat, dest_lon_lat,
        otp_router_id)
    #print url

    response = urllib2.urlopen(url)
    data = response.read()
    return data

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

def run_single_trip_multi_graphs_test():    
    server_url = 'http://130.56.248.56'

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
    trip_req_start_time = time(11,45)
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
        res_str = run_trip(server_url, routing_params,
            trip_req_start_date, trip_req_start_time, origin_lon_lat,
            dest_lon_lat, otp_router_id=graph_full)

        #f = open("trip.txt", 'w')
        #f.write(data)
        #f.close()
        res = json.loads(res_str)
        #import pprint
        #pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(res)
        
        itin = res['plan']['itineraries'][0]
        print "\nRouting on the %s network/timetable, Requested trip stats:" \
            % graph_short
        trip_analysis.print_single_trip_stats(origin_lon_lat, dest_lon_lat,
            trip_req_start_dt, itin)
    return

if __name__ == "__main__":
    run_single_trip_multi_graphs_test()
