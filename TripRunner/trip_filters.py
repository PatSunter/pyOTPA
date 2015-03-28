
from osgeo import ogr, osr

import otp_config

# Chose EPSG:28355 ("GDA94 / MGA zone 55") as an appropriate projected
    # spatial ref. system, in meters, for the Melbourne region.
    #  (see http://spatialreference.org/ref/epsg/gda94-mga-zone-55/)
COMPARISON_EPSG = 28355

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

# Filters that rely purely on trips themselves (e.g. geometry, SSD ...)

def within_bbox(pt_coord, bbox):
    """Tests if geom is within the bbox envelope. Bbox of form (minx, maxx,
    miny, maxy) - IE the result of a GetEnvelope() call."""
    result = False
    if pt_coord[0] >= bbox[0] and pt_coord[0] <= bbox[1] \
            and pt_coord[1] >= bbox[2] and pt_coord[1] <= bbox[3]:
        result = True      
    return result

def get_trip_ids_near_networks(trip_dict, network_layers, buffer_dist_m,
        candidate_trip_ids=None):
    """Filter down to a list of trips that are within a max distance of any of
    the network geometries passed in."""
    
    comp_srs = osr.SpatialReference()
    comp_srs.ImportFromEPSG(COMPARISON_EPSG)

    buffered_geoms = []
    for layer in network_layers:
        # set up transform
        tform = osr.CoordinateTransformation(
            layer.GetSpatialRef(), comp_srs)
        for feat in layer:
            tform_geom = feat.GetGeometryRef()
            tform_geom.Transform(tform)
            buffer_geom = tform_geom.Buffer(buffer_dist_m)
            buffered_geoms.append(buffer_geom)
        layer.ResetReading()    
    # get the union of all the buffer shapes
    union_geom = buffered_geoms[0]
    for bgeom in buffered_geoms[1:]:
        new_union_geom = union_geom.Union(bgeom)
        union_geom.Destroy()
        bgeom.Destroy()
        union_geom = new_union_geom

    bbox = union_geom.GetEnvelope()

    trip_ids_match_criteria = []
    
    if not candidate_trip_ids:
        candidate_trip_ids = trip_dict.iterkeys()

    for trip_id in candidate_trip_ids:
        trip = trip_dict[trip_id]
        pt_o = trip[0]
        pt_d = trop[1]
        geom_o = ogr.Geometry(ogr.wkbPoint)
        geom_d = ogr.Geometry(ogr.wkbPoint)
        geom_o.AddPoint(pt_o)
        geom_d.AddPoint(pt_d)
        geom_o.Transform(tform_latlon_to_comp)
        geom_d.Transform(tform_latlon_to_comp)
        if within_bbox(geom_o, bbox) and within_bbox(geom_d, bbox) \
            and buffer_union_geom.Contains(geom_o) \
                and buffer_union_geom.Contains(geom_d):
            trip_ids_match_criteria.append(trip_id)
        geom_o.Destroy()
        geom_d.Destroy()

    return trip_ids_match_criteria

def get_trip_ids_near_network_stops(trip_dict, network_layers, test_dist_m,
        candidate_trip_ids=None):
    """Filter down to a list of trips that are within a max distance of any of
    the network geometries passed in."""
    
    comp_srs = osr.SpatialReference()
    comp_srs.ImportFromEPSG(COMPARISON_EPSG)

    stops_multipoint = ogr.Geometry(ogr.wkbMultiPoint)
    for layer in network_layers:
        # set up transform
        tform = osr.CoordinateTransformation(
            layer.GetSpatialRef(), comp_srs)
        for stop_feat in layer:
            tform_geom = stop_feat.GetGeometryRef()
            tform_geom.Transform(tform)
            stops_multipoint.AddGeometry(tform_geom)
        layer.ResetReading()

    bbox = stops_multipoint.GetEnvelope()

    trip_ids_match_criteria = []
    
    if not candidate_trip_ids:
        candidate_trip_ids = trip_dict.iterkeys()

    trips_srs = osr.SpatialReference()
    trips_srs.ImportFromEPSG(otp_config.OTP_ROUTER_EPSG)
    tform_latlon_to_comp = osr.CoordinateTransformation(
        trips_srs, comp_srs)
    for trip_id in candidate_trip_ids:
        trip = trip_dict[trip_id]
        pt_o = trip[0]
        pt_d = trip[1]
        geom_o = ogr.Geometry(ogr.wkbPoint)
        geom_d = ogr.Geometry(ogr.wkbPoint)
        geom_o.AddPoint(*pt_o)
        geom_d.AddPoint(*pt_d)
        geom_o.Transform(tform_latlon_to_comp)
        geom_d.Transform(tform_latlon_to_comp)
        pt_tform_o = geom_o.GetPoint()
        pt_tform_d = geom_d.GetPoint()
        if within_bbox(pt_tform_o, bbox) and within_bbox(pt_tform_d, bbox) \
            and geom_o.Distance(stops_multipoint) < test_dist_m \
                and geom_d.Distance(stops_multipoint) < test_dist_m:
            trip_ids_match_criteria.append(trip_id)
        geom_o.Destroy()
        geom_d.Destroy()

    return trip_ids_match_criteria
