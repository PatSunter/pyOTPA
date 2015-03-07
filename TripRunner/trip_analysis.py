import os, os.path
from datetime import datetime, timedelta
import itertools
import json

import geom_utils
import time_utils

########################
## Analysis and Printing

def get_trip_speed_direct(origin_lon_lat, dest_lon_lat, trip_req_start_dt,
        trip_itin):
    dist_direct = geom_utils.haversine(origin_lon_lat[0], origin_lon_lat[1],
        dest_lon_lat[0], dest_lon_lat[1])
    total_trip_sec = trip_itin.get_total_trip_sec(trip_req_start_dt)
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))
    return trip_speed_direct

def print_single_trip_stats(origin_lon_lat, dest_lon_lat, trip_req_start_dt,
        trip_itin):
    ti = trip_itin
    itin_start_dt = ti.get_start_dt()
    itin_end_dt = ti.get_end_dt()
    total_trip_td = ti.get_total_trip_td(trip_req_start_dt)
    total_trip_sec = ti.get_total_trip_sec(trip_req_start_dt)

    init_wait_td = ti.get_init_wait_td(trip_req_start_dt)
    tfer_wait_td = ti.get_tfer_wait_td()
    total_wait_td = ti.get_total_wait_td(trip_req_start_dt)
    walk_td = ti.get_walk_td()
    transit_td = ti.get_transit_td()

    wait_pct = time_utils.get_td_pct(total_wait_td, total_trip_td)
    walk_pct = time_utils.get_td_pct(walk_td, total_trip_td)
    transit_pct = time_utils.get_td_pct(transit_td, total_trip_td)

    dist_travelled = ti.get_dist_travelled()
    trip_speed_along_route = ti.get_trip_speed_along_route(trip_req_start_dt)

    dist_direct = geom_utils.haversine(origin_lon_lat[0], origin_lon_lat[1],
        dest_lon_lat[0], dest_lon_lat[1])
    trip_speed_direct = (dist_direct / 1000.0) \
        / (total_trip_sec / (60 * 60.0))

    print "Trip departs at %s" % itin_start_dt 
    print "Trip arrives at %s" % itin_end_dt 
    print "%s total time (inc initial wait)" % total_trip_td
    print "  %s (%.2f%%) waiting (%s initial, %s transfers)" \
        % (total_wait_td, wait_pct, init_wait_td, tfer_wait_td)
    print "  %s (%.2f%%) walking (for %.2fm)" \
        % (walk_td, walk_pct, ti.json['walkDistance'])
    print "  %s (%.2f%%) on transit vehicles (%d transfers)" \
        % (transit_td, transit_pct, ti.json['transfers'])
    print "Total trip distance (as crow flies): %.2fm." % dist_direct
    print "Total trip distance (travelled): %.2fm." % dist_travelled
    print "(Trip directness ratio:- %.2f)" % (dist_direct / dist_travelled)
    print "Trip speed (along route, inc. init wait): %.2fkm/h." \
        % trip_speed_along_route
    print "Trip speed (as crow flies, inc. init wait): %.2fkm/h." \
        % trip_speed_direct
    return

def calc_mean_total_time(trip_itins, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: trip_itins[trip_id].get_total_trip_sec(
            trip_req_start_dts[trip_id]), trip_itins.iterkeys()))
    mean_sec = sum_val / float(len(trip_itins))
    return timedelta(seconds=mean_sec)

def calc_mean_basic_itin_attr(trip_itins, itin_attr):
    """Convenience function."""
    sum_val = sum(itertools.imap(
        lambda ti: ti.json[itin_attr], trip_itins.itervalues()))
    mean = sum_val / float(len(trip_itins))
    return mean

def calc_mean_walk_dist(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'walkDistance')

def calc_mean_transfers(trip_itins):
    return calc_mean_basic_itin_attr(trip_itins, 'transfers')

def calc_mean_direct_speed(trip_itins, trips_by_id, trip_req_start_dts):
    sum_val = sum(itertools.imap(
        lambda trip_id: get_trip_speed_direct(trips_by_id[trip_id][0],
            trips_by_id[trip_id][1], trip_req_start_dts[trip_id],
            trip_itins[trip_id]), trip_itins.iterkeys()))
    mean_spd = sum_val / float(len(trip_itins))
    return mean_spd

def calc_print_mean_results(graph_names, trip_results_by_graph,
        trips_by_id, trip_req_start_date):
    trip_req_start_dts = {}
    for trip_id, trip in trips_by_id.iteritems():
        if isinstance(trip[2], datetime):
            trip_req_start_dts[trip_id] = trip[2]
        else:
            trip_req_start_dts[trip_id] = datetime.combine(trip_req_start_date,
                trip[2])

    means = {}
    for graph_name in graph_names:
        trip_results = trip_results_by_graph[graph_name]
        means[graph_name] = {}
        means[graph_name]['total_time'] = \
            calc_mean_total_time(trip_results, trip_req_start_dts)
        means[graph_name]['direct_speed'] = \
            calc_mean_direct_speed(trip_results, trips_by_id,
                trip_req_start_dts)
        means[graph_name]['walk_dist'] = calc_mean_walk_dist(trip_results)
        means[graph_name]['transfers'] = calc_mean_transfers(trip_results)

    print "Mean results for the %d trips were:" \
        % (max(map(len, trip_results_by_graph.itervalues())))
    for graph_name in graph_names:
        print "'%s': mean trip time %s, direct speed %.2f km/h, "\
            "walk dist %.2fm, # of transfers %.1f" % \
             (graph_name,
              means[graph_name]['total_time'],
              means[graph_name]['direct_speed'],
              means[graph_name]['walk_dist'],
              means[graph_name]['transfers'])
    return

def createTripsCompShapefile(trips_by_id, graph_names, trip_req_start_date,
        trip_results_1, trip_results_2, shapefilename):
    """Creates a Shape file stating the difference between times in two
    sets of results for the same set of trips.
    Saves results to a shapefile determined by shapefilename.
    
    N.B. :- thanks for overall strategy here are due to author of
    https://github.com/glennon/FlowpyGIS"""

    import osgeo.ogr
    from osgeo import ogr

    print "Creating shapefile of trip lines with time attributes to file"\
        " %s ..." % (shapefilename)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    # create a new data source and layer
    if os.path.exists(shapefilename):
        driver.DeleteDataSource(shapefilename)
    ds = driver.CreateDataSource(shapefilename)
    if ds is None:
        print 'Could not create file'
        sys.exit(1)

    c1TimeFieldName = 't%s' % graph_names[0]
    c2TimeFieldName = 't%s' % graph_names[1]
    #Abbreviate due to Shpfile limits.
    c1TimeFieldName = c1TimeFieldName[:8]
    c2TimeFieldName = c2TimeFieldName[:8]

    layer = ds.CreateLayer('trip_comps', geom_type=ogr.wkbLineString)
    fieldDefn = ogr.FieldDefn('TripID', ogr.OFTString)
    fieldDefn.SetWidth(20)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('DepTime', ogr.OFTString)
    fieldDefn.SetWidth(8)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('OriginZ', ogr.OFTString)
    fieldDefn.SetWidth(254)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('DestZ', ogr.OFTString)
    fieldDefn.SetWidth(254)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c1TimeFieldName, ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c2TimeFieldName, ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('Diff', ogr.OFTInteger)
    layer.CreateField(fieldDefn)
    # END setup creation of shapefile

    for trip_id in sorted(trips_by_id.iterkeys()):
        trip = trips_by_id[trip_id]
        if isinstance(trip[2], datetime):
            trip_req_start_dt = trip[2]
        else:
            trip_req_start_dt = datetime.combine(trip_req_start_date, 
                trip[2])
        try:
            trip_res_1 = trip_results_1[trip_id]
            trip_res_2 = trip_results_2[trip_id]
        except KeyError:
            # For now - just skip trips not valid in both graphs.
            continue
        case1time = trip_res_1.get_total_trip_sec(trip_req_start_dt)
        case2time = trip_res_2.get_total_trip_sec(trip_req_start_dt)
        linester = ogr.Geometry(ogr.wkbLineString)
        linester.AddPoint(*trip[0])
        linester.AddPoint(*trip[1])

        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(linester)
        feature.SetField('TripId', str(trip_id))
        feature.SetField('DepTime', trip[2].strftime('%H:%M:%S'))
        feature.SetField('OriginZ', trip[3])
        feature.SetField('DestZ', trip[4])
        feature.SetField(c1TimeFieldName, case1time)
        feature.SetField(c2TimeFieldName, case2time)
        diff = case1time - case2time
        feature.SetField('Diff', diff)
        layer.CreateFeature(feature)

    # shapefile cleanup
    # destroy the geometry and feature and close the data source
    linester.Destroy()
    feature.Destroy()
    ds.Destroy()
    print "Done."
    return

