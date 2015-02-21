"""Module to run selected trips in OTP."""

import urllib
import urllib2
import os.path
import json
from datetime import datetime

import otp_config
import TripItinerary
import trip_analysis

PROGRESS_PRINT_PERCENTAGE = 5

def build_trip_request_url(server_url, routing_params, trip_date, trip_time,
        origin_lon_lat, dest_lon_lat, otp_router_id=None):
    date_str = trip_date.strftime(otp_config.OTP_DATE_FMT)
    time_str = trip_time.strftime(otp_config.OTP_TIME_FMT)

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

def route_trip(server_url, routing_params, trip_req_start_date,
        trip_req_start_time, origin_lon_lat, dest_lon_lat, otp_router_id):

    url = build_trip_request_url(server_url, routing_params,
        trip_req_start_date, 
        trip_req_start_time, origin_lon_lat, dest_lon_lat,
        otp_router_id)
    #print url

    response = urllib2.urlopen(url)
    data = response.read()
    return data

def route_single_trip_multi_graphs_print_stats(server_url, routing_params,
        graph_specs, trip_req_start_date, trip_req_start_time,
        origin_lon_lat, dest_lon_lat):    
    trip_req_start_dt = datetime.combine(trip_req_start_date,
        trip_req_start_time)

    print "\nCalling server to route a trip from %s to %s, leaving "\
        "at %s:" % (origin_lon_lat, dest_lon_lat, trip_req_start_dt)

    for graph_name, graph_full in graph_specs.iteritems():
        res_str = route_trip(server_url, routing_params,
            trip_req_start_date, trip_req_start_time, origin_lon_lat,
            dest_lon_lat, otp_router_id=graph_full)
        res = json.loads(res_str)
        #import pprint
        #pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(res)
        itin_json = res['plan']['itineraries'][0]
        print "\nRouting on the %s network/timetable, Requested trip stats:" \
            % graph_name
        ti = TripItinerary.TripItinerary(itin_json)
        trip_analysis.print_single_trip_stats(origin_lon_lat, dest_lon_lat,
            trip_req_start_dt, ti)
    return

def route_trip_set_on_graphs(server_url, routing_params,
        graph_specs, trip_req_start_date, trips, trips_by_id, output_base_dir,
        save_incrementally=True, resume_existing=False):

    trip_results_by_graph = {}
    trip_req_start_dts = {}
    for trip_id, trip in trips_by_id.iteritems():
        trip_req_start_dts[trip_id] = datetime.combine(trip_req_start_date,
            trip[2])

    for graph_name, graph_full in graph_specs.iteritems():
        output_subdir = os.path.join(output_base_dir, graph_name)
        if save_incrementally:
            if not os.path.exists(output_subdir):
                os.makedirs(output_subdir)

        print "\nRouting the %d requested trips on the %s network/timetable: " \
            % (len(trips_by_id), graph_name)
        trip_results = {}
        trips_routed = 0
        trips_processed = 0
        print_increment = len(trips_by_id) * (PROGRESS_PRINT_PERCENTAGE / 100.0)
        next_print_total = print_increment
        for trip_id, trip in sorted(trips_by_id.iteritems()):
            output_fname = os.path.join(output_subdir, "%s.json" % trip_id)
            if resume_existing and os.path.exists(output_fname):
                trips_processed += 1
                continue
            trip_req_start_dt = trip_req_start_dts[trip_id]
            res_str = route_trip(server_url, routing_params,
                trip_req_start_date, trip[2], trip[0],
                trip[1], otp_router_id=graph_full)
            res = json.loads(res_str)
            if not res['plan']:
                print "Warning:- requested trip ID %d from %s to %s at %s "\
                    "time on graph %s failed to generate valid itererary. "\
                    "Error msg returned by OTP router was:\n%s"\
                    % (trip_id, trip[0], trip[1], trip[2], graph_name,
                       res['error']['msg'])
                ti = None
            else:    
                try:
                    itin_json = res['plan']['itineraries'][0]
                    ti = TripItinerary.TripItinerary(itin_json)
                except TypeError, IndexError:
                    print "Unexpected failure to get trip itinerary from "\
                        "received result."
                    ti = None
            trip_results[trip_id] = ti    
            if ti and save_incrementally:
                ti.save_to_file(output_fname)
            #print "\nTrip from %s to %s, leaving "\
            #    "at %s:" % (trip[0], trip[1], trip_req_start_dt)
            #trip_analysis.print_single_trip_stats(trip[0], trip[1],
            #    trip_req_start_dt, ti) 
            trips_routed += 1
            trips_processed += 1

            if trips_processed >= next_print_total:
                while trips_processed >= next_print_total:
                    next_print_total += print_increment
                percent_done = trips_processed / float(len(trips_by_id)) * 100.0
                print "...processed %d trips (%.1f%% of total.)" \
                    % (trips_processed, percent_done)
        trip_results_by_graph[graph_name] = trip_results
    return trip_results_by_graph
    

