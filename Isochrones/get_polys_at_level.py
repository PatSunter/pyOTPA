#!/usr/bin/env python

import os, os.path
from argparse import ArgumentParser

import osgeo.ogr
from osgeo import ogr, osr
from shapely.wkb import loads
from shapely.geometry import Polygon, MultiPolygon, CAP_STYLE, JOIN_STYLE

#Popular vis EPSG
DEF_OUTPUT_EPSG = 3785

def get_polys_at_level(in_file_name, out_file_name, level_field,
        level_max_val, out_epsg=DEF_OUTPUT_EPSG): 
    source = ogr.Open(in_file_name)
    in_layer = source.GetLayer(0)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(out_file_name):
        os.remove(out_file_name)
    ds = driver.CreateDataSource(out_file_name)
    in_srs = in_layer.GetSpatialRef() 
    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(out_epsg)
    out_layer = ds.CreateLayer('polys', out_srs, ogr.wkbPolygon)
    out_layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    defn = out_layer.GetLayerDefn()

    where_clause = "%s <= %d" % (level_field, level_max_val)
    in_layer.SetAttributeFilter(where_clause)

    # First build a multipolygon, since many will be adjacent.
    polygon_list = []
    for ii, poly_feat in enumerate(in_layer):        
        poly_geom = poly_feat.GetGeometryRef()
        transform = osr.CoordinateTransformation(in_srs, out_srs)
        poly_geom.Transform(transform)
        polygon = loads(poly_geom.ExportToWkb())
        # Occasionally, might be a multi-polygon to unpack
        if type(polygon) == Polygon:
            polygon_list.append(polygon)
        elif type(polygon) == MultiPolygon:
            for sub_poly in polygon.geoms:
                polygon_list.append(sub_poly)
        else:
            print "Error: unexpected geom type %s in list." %\
                repr(type(polygon))

    assert False not in [type(p) == Polygon for p in polygon_list]
    multi_polygon = MultiPolygon(polygon_list)

    # Now buffer it, which should merge adjacent shapes together
    all_polys = multi_polygon.buffer(0, cap_style = CAP_STYLE.round,
            join_style=JOIN_STYLE.round)
    if type(all_polys) is Polygon:
        # Just in case, we potentially only have one polygon here, so force
        # convert if so
        if all_polys.area == 0:
            # Needed to add since shapely can't handle an empty polygon passed
            #  as a constructor.
            all_polys = MultiPolygon()
        else:    
            all_polys = MultiPolygon([all_polys]) 
    # Now save individual polygons within the multi_p_buffer to file.
    for jj, out_poly in enumerate(all_polys.geoms):
        new_feat = ogr.Feature(defn)
        new_feat.SetField('id', jj)
        new_geom = ogr.CreateGeometryFromWkb(out_poly.wkb)
        new_feat.SetGeometry(new_geom)
        out_layer.CreateFeature(new_feat)
        new_feat = None
        new_geom = None
        poly_geom = None

    # Save and close
    in_layer = None
    out_layer = None
    ds = None

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Gets a set of polygons where level value is < "\
        "a desired value.")
    parser.add_argument("in_file", help="The vector source file.")
    parser.add_argument("out_file", help="The output shapefile.")
    parser.add_argument("lev_field", help="The level field in in_file.")
    parser.add_argument("max_level", help="The max level to include.")
    parser.add_argument("-e",
        help="The EPSG code to use for created output file SRS.",
        type=int, default=DEF_OUTPUT_EPSG)
    args = parser.parse_args()
    get_polys_at_level(args.in_file, args.out_file, args.lev_field,
        int(args.max_level), out_epsg=args.e) 
