"""Functions to filter down a list of trips - and return a list of IDs that
match the criteria."""

from osgeo import ogr, osr

import otp_config
import geom_utils
import Trip

def get_trip_ids_near_networks(trip_dict, network_layers, buffer_dist_m,
        candidate_trip_ids=None):
    """Filter down to a list of trips that are within a max distance of any of
    the network geometries passed in."""
    
    comp_srs = osr.SpatialReference()
    comp_srs.ImportFromEPSG(geom_utils.COMPARISON_EPSG)

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
        pt_o = trip[Trip.ORIGIN]
        pt_d = trip[Trip.DEST]
        geom_o = ogr.Geometry(ogr.wkbPoint)
        geom_d = ogr.Geometry(ogr.wkbPoint)
        geom_o.AddPoint(*pt_o)
        geom_d.AddPoint(*pt_d)
        geom_o.Transform(tform_latlon_to_comp)
        geom_d.Transform(tform_latlon_to_comp)
        if geom_utils.within_bbox(geom_o, bbox) \
                and geom_utils.within_bbox(geom_d, bbox) \
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
    comp_srs.ImportFromEPSG(geom_utils.COMPARISON_EPSG)

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

    trips_srs = Trip.get_trips_srs()

    tform_latlon_to_comp = osr.CoordinateTransformation(
        trips_srs, comp_srs)
    for trip_id in candidate_trip_ids:
        trip = trip_dict[trip_id]
        pt_o = trip[Trip.ORIGIN]
        pt_d = trip[Trip.DEST]
        geom_o = ogr.Geometry(ogr.wkbPoint)
        geom_d = ogr.Geometry(ogr.wkbPoint)
        geom_o.AddPoint(*pt_o)
        geom_d.AddPoint(*pt_d)
        geom_o.Transform(tform_latlon_to_comp)
        geom_d.Transform(tform_latlon_to_comp)
        pt_tform_o = geom_o.GetPoint()
        pt_tform_d = geom_d.GetPoint()
        if geom_utils.within_bbox(pt_tform_o, bbox) \
                and geom_utils.within_bbox(pt_tform_d, bbox) \
                and geom_o.Distance(stops_multipoint) < test_dist_m \
                and geom_d.Distance(stops_multipoint) < test_dist_m:
            trip_ids_match_criteria.append(trip_id)
        geom_o.Destroy()
        geom_d.Destroy()

    return trip_ids_match_criteria
