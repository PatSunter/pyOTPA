"""
pyOTPA's representation of a single trip.

Currently just using a Tuple to keep storage overhead low, given there are
potentially 100K plus trips we're going to deal with.
"""

import copy
from datetime import datetime
from osgeo import osr

import otp_config

#Note that trip's Origin and Dest coords are in the EPSG of otp_config
#OTP_ROUTER_EPSG
TRIP_EPSG = otp_config.OTP_ROUTER_EPSG

ORIGIN = 0              # This is a tuple in X, Y format:- trip origin.
DEST = ORIGIN+1         # This is a tuple in X, Y format:- trip destination.
START_DTIME = DEST+1    # A python datetime object
O_ZONE = START_DTIME+1  # A string representing a zone, origin
D_ZONE = O_ZONE+1       # A string representing a zone, destination
ID = D_ZONE+1           # A trip ID (string)

def new_trip(origin_geom, dest_geom, start_date_time, origin_zone,
        dest_zone, trip_id):
    trip = (origin_geom, dest_geom, start_date_time, origin_zone, \
        dest_zone, trip_id)
    return trip

def new_trip_with_updated_start(exist_trip, new_start_dt):
    upd_time_trip = new_trip(
        exist_trip[ORIGIN],
        exist_trip[DEST],
        new_start_dt,
        exist_trip[O_ZONE],
        exist_trip[D_ZONE],
        exist_trip[ID])
    return upd_time_trip

def get_trips_srs():
    trips_srs = osr.SpatialReference()
    trips_srs.ImportFromEPSG(TRIP_EPSG)
    return trips_srs

def print_trip(trip):
    print "trip '%s': %f,%f to %f,%f at %s ('%s'->'%s')" \
        % (str(trip[ID]), trip[ORIGIN][0], trip[ORIGIN][1],
           trip[DEST][0], trip[DEST][1], 
           trip[START_DTIME], trip[O_ZONE], trip[D_ZONE])
    return

################
# Useful Ops on a list of trips.

def get_trip_req_start_dts(trips_by_id, trip_req_start_date):
    """This function is a result of earlier storing only a time for each trip,
    not a datetime."""
    trip_req_start_dts = {}
    for trip_id, trip in trips_by_id.iteritems():
        if isinstance(trip[START_DTIME], datetime):
            trip_req_start_dts[trip_id] = trip[START_DTIME]
        else:
            trip_req_start_dts[trip_id] = datetime.combine(trip_req_start_date,
                trip[START_DTIME])
    return trip_req_start_dts

def get_trips_subset_by_ids(trip_results_dict, trip_ids_to_select):
    trip_results_filtered = {}
    for trip_id in trip_ids_to_select:
        try:
            trip_results_filtered[trip_id] = trip_results_dict[trip_id]
        except KeyError:
            raise ValueError("Input trip_results_dict didn't contain at "\
                "least one of the trip IDs ('%s') you requested in "\
                "trip_ids_to_select." % trip_id)
    return trip_results_filtered

def get_trips_subset_by_ids_to_exclude(trip_results_dict, trip_ids_to_exclude):
    # In the excluding IDs case:- start by creating a copy of the entire 
    # first dict:- since it will be faster to just delete dictionary entries
    # that are excluded. copy.copy just creates a new dictionary pointing to
    # the same actual entries in memory, so this won't waste lots of space.
    trip_results_filtered = copy.copy(trip_results_dict)
    for trip_id in trip_ids_to_exclude:
        try:
            del(trip_results_filtered[trip_id])
        except KeyError:
            print "Warning: Input trip_results_dict didn't contain at "\
                "least one of the trip IDs ('%s') you requested to exclude "\
                "in trip_ids_to_exclude." % trip_id
    return trip_results_filtered

    
