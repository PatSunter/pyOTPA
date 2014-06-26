#!/usr/bin/env python

"""Small script to create a 'smoother', more rounded area shape.
Uses the shapely library and its flexible buffer function for this."""

import os, os.path
from argparse import ArgumentParser

import osgeo.ogr
from osgeo import ogr, osr
from shapely.wkb import loads
from shapely.geometry import Polygon, MultiPolygon, CAP_STYLE, JOIN_STYLE
from shapely.ops import cascaded_union

#Popular vis EPSG
DEF_OUTPUT_EPSG = 3785

EDGE_PROC_AREA_CUTOFF = 3 * 1e4

# Hand-rolled to generate sensible results
# Consider re change warn levels, sometimes involves filling internal holes.
ERODE_AMT_ENTRIES = [
    #{"area":10 * 1e6,   "erode_amt":200,    "dilate_erode" : [.7, -1.4, .75],
    {"area":10 * 1e6,   "erode_amt":300,    "dilate_erode" : [.7, -1.4, .70],
     "change_percent_ok":(-10,15), "post_proc_edges":True},
    {"area":1e6,        "erode_amt":200,    "dilate_erode" : [.7, -1.4, .75],    
     "change_percent_ok":(-10,25), "post_proc_edges":True},
    {"area":1e4*50,    "erode_amt":100,    "dilate_erode" : [.7, -1.4, .75],    
     "change_percent_ok":(-20,30), "post_proc_edges":False},
    {"area":1e4*10,     "erode_amt":50,    "dilate_erode" : [.7, -1.4, .75],    
     "change_percent_ok":(-20,40), "post_proc_edges":False},
    {"area":1e4,        "erode_amt":30,     "dilate_erode" : [.75, -1.35, .75],
     "change_percent_ok":(-20,50), "post_proc_edges":False},
    {"area":1e3*3,      "erode_amt":30,     "dilate_erode" : [.75, -1.35, .75],
     "change_percent_ok":(-20,90), "post_proc_edges":False},
    {"area":1e3*1,      "erode_amt":5,      "dilate_erode" : [.75, -1.4, .75],
     "change_percent_ok":(-20,100), "post_proc_edges":False},
    # Enlarge these bottom two to be properly visible - seems reasonable.
    {"area":100,       "erode_amt":3,      "dilate_erode" : [.75, -1.4, 2.00],
     "change_percent_ok":(-40,300), "post_proc_edges":False},
    {"area":0.00,       "erode_amt":1,      "dilate_erode" : [.75, -1.4, 2.0],
     "change_percent_ok":(-50,1000), "post_proc_edges":False},
    ]  

def smooth_polygon(polygon, log_full=False):
    erode_amt_iter = iter(ERODE_AMT_ENTRIES)
    erode_amt_entry = erode_amt_iter.next()
    if polygon.area == 0:
        return None
    try:
        while polygon.area < erode_amt_entry["area"]:
            erode_amt_entry = erode_amt_iter.next()
    except StopIteration:
        print "Warning, shape had %.2f area, can't smooth." % polygon.area
        return None
    erode_amt = erode_amt_entry["erode_amt"]
    if log_full == True:
        print "Doing shape processing:"
        print "Polygon area in=%.1f, length=%.1f, hence erode_amt=%.1f" % \
            (polygon.area, polygon.length, erode_amt)
    d_e = erode_amt_entry["dilate_erode"]
    new_polygon = polygon
    dilated = new_polygon.buffer(d_e[0]*erode_amt, cap_style = CAP_STYLE.round,
        join_style=JOIN_STYLE.round)
    eroded = dilated.buffer(d_e[1]*erode_amt, cap_style = CAP_STYLE.round,
        join_style=JOIN_STYLE.round)
    dilated_2 = eroded.buffer(d_e[2]*erode_amt, cap_style = CAP_STYLE.round,
        join_style=JOIN_STYLE.round)
    new_polygon = dilated_2
    sub_areas = 0
    if erode_amt_entry["post_proc_edges"]:
        # This is to avoid too many meaningful feature parts being
        # smoothed away for very large shapes.
        snipped_outside = polygon.difference(new_polygon)
        if type(snipped_outside) == Polygon:
            snipped_multi_p = MultiPolygon([snipped_outside])
        else:
            snipped_multi_p = snipped_outside
        # We want to recursively smooth these polygons separately.
        smoothed_polys_to_re_add = []
        for sub_poly in snipped_multi_p:
            if sub_poly.area > EDGE_PROC_AREA_CUTOFF:
                # Recursive call to work out sub_poly area.
                smoothed_sub_poly = smooth_polygon(sub_poly)
                if smoothed_sub_poly and smoothed_sub_poly.area > 0:
                    smoothed_polys_to_re_add.append(smoothed_sub_poly)
                    sub_areas += smoothed_sub_poly.area
        if len(smoothed_polys_to_re_add) > 0:
            # Now we want to turn the new polygon into a multipolygon
            # Only do this when there are actually candidates worthwhile.
            new_polygon = cascaded_union([new_polygon]+smoothed_polys_to_re_add)

    new_area = new_polygon.area
    area_change_percent = 0
    if polygon.area > 0:
        area_change_percent = (new_polygon.area - polygon.area) / polygon.area \
            * 100
    if log_full == True:
        print "Polygon area after = %.2f (Change of %.2f%%)" \
            % (new_polygon.area, area_change_percent)
    ok_range = erode_amt_entry["change_percent_ok"]
    if area_change_percent < ok_range[0] or\
            area_change_percent > ok_range[1]:
        print "WARNING: during smoothing a polygon changed in area "\
            "from %.2f to %.2f (change of %.2f%%). Consider tuning "\
            "ERODE_AMT_ENTRIES values." \
            % (polygon.area, new_polygon.area, area_change_percent)
    return new_polygon

def smooth_all_polygons(in_file_name, out_file_name, out_epsg=DEF_OUTPUT_EPSG,
        fill_holes=True, log_full=False): 
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

    smoothed_polys = []
    for ii, poly_feat in enumerate(in_layer):
        poly_geom = poly_feat.GetGeometryRef()
        transform = osr.CoordinateTransformation(in_srs, out_srs)
        poly_geom.Transform(transform)
        polygon = loads(poly_geom.ExportToWkb())
        poly_geom = None
        # convert to a smoothed polygon
        smoothed_poly = smooth_polygon(polygon)
        if smoothed_poly and smoothed_poly.area > 0:
            smoothed_polys.append(smoothed_poly)

    # Now do a cascaded union, to join overlapping polygons.
    all_polys = cascaded_union(smoothed_polys)
    if type(all_polys) is Polygon:
        # Just in case, we potentially only have one polygon here, so force
        # convert if so
        all_polys = MultiPolygon([all_polys]) 

    # Finally, optionally fill in inner holes.
    if fill_holes == True:
        all_polys_new_list = []
        for poly in all_polys:
            if len(poly.interiors) > 0:
                # Create new poly with just exteriors
                new_poly = Polygon(poly.exterior)
                all_polys_new_list.append(new_poly)
            else:
                all_polys_new_list.append(poly)
        # And now, create new M.P. with all having holes filled.
        all_polys = MultiPolygon(all_polys_new_list)

    # Now write out to output file individually.
    for out_poly in all_polys:
        new_feat = ogr.Feature(defn)
        new_feat.SetField('id', ii)
        new_geom = ogr.CreateGeometryFromWkb(out_poly.wkb)
        new_feat.SetGeometry(new_geom)
        out_layer.CreateFeature(new_feat)
        new_feat = None
        new_geom = None

    # Save and close
    in_layer = None
    out_layer = None
    ds = None

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Smooths the edges of a set of polygons to be more "\
        "circular - using the 'shapely' library.")
    parser.add_argument("in_file", help="The vector source file.")
    parser.add_argument("out_file", help="The output shapefile.")
    parser.add_argument("-e",
        help="The EPSG code to use for created output file SRS.",
        type=int, default=DEF_OUTPUT_EPSG) 
    args = parser.parse_args()
    smooth_all_polygons(args.in_file, args.out_file, out_epsg=args.e) 
