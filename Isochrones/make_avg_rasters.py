import os
import os.path
import sys
import string
from datetime import date
import itertools
import operator

import osgeo
from osgeo import ogr

import utils

# These determine default isochrone time maximums and increments
DEF_ISO_MAX=40
DEF_ISO_INC=10

CORRECT_NODATA_VALUE_BYTE=128

def make_average_raster(save_path, save_suffix, loc_name, datestr, timestr, 
        nearby_minutes, num_each_side, **kwargs):
    # N.B. :- there may be other kwargs passed in, not relevant here, which we ignore,
    # hence kwargs on the end.
    mins_diffs = utils.get_nearby_min_diffs(nearby_minutes, num_each_side)
    date_time_str_set = utils.get_date_time_string_set(datestr, timestr,
        mins_diffs)
    fnames = utils.get_raster_filenames(loc_name, date_time_str_set, save_path,
        save_suffix)
    # This VRT step is necessary since :- for this kind of 'raster algebra',
    # the problem is that the original type is Byte, and it won't hold a value
    # of over 128 properly. So we temporarily transform to Float32 using the
    # "VRT" feature of GDAL before doing the calculation. See:
    # http://gis.stackexchange.com/questions/33152/why-do-i-get-different-results-with-gdal-calc-within-the-osgeo4w-shell-and-qgis
    vrtnames = []
    for fname in fnames:
        vrtname = os.path.splitext(fname)[0]+".vrt"
        vrtnames.append(vrtname)
    
    for fname in fnames:
        editcmd = "gdal_edit.py -a_nodata %d %s" \
            % (CORRECT_NODATA_VALUE_BYTE, fname)
        print "Running %s:" % editcmd
        os.system(editcmd)
    for ii in range(len(fnames)):
        transcmd = "gdal_translate -ot Float32 -of VRT %s %s" \
            % (fnames[ii], vrtnames[ii])
        print "Running %s:" % transcmd
        os.system(transcmd)

    # Now do the big average
    avg_fname = utils.avgRasterName(loc_name, datestr, timestr, save_path, 
        save_suffix, num_each_side)

    caps = string.ascii_uppercase[:len(fnames)]
    vrts_str = " ".join(["-%s %s" % (a, b) for a, b in zip(caps, vrtnames)])
    calc_str = "("+"+".join(caps)+")"+"/"+str(len(vrtnames))
    calccmd = 'gdal_calc.py %s --outfile=%s --NoDataValue=%d --calc="%s" '\
        '--type=Byte --overwrite' \
        % (vrts_str, avg_fname, CORRECT_NODATA_VALUE_BYTE, calc_str)
    print "Running %s:" % calccmd    
    os.system(calccmd)
    return

def make_contours_isobands(save_path, save_suffix, loc_name, datestr, timestr,
        num_each_side, iso_max, iso_inc, **kwargs):
    # N.B. :- again kwargs is needed at the end to ignore unneeded args.
    iso_timeset = range(0, iso_max+1, iso_inc)[1:]
    avg_fname = utils.avgRasterName(loc_name, datestr, timestr, 
        save_path, save_suffix, num_each_side)
    ctr_fname = utils.isoContoursName(loc_name, datestr, timestr, 
        save_path, save_suffix, num_each_side)
    if os.path.exists(ctr_fname):
        os.unlink(ctr_fname)
    timeset_str = " ".join([str(tval+0.1) for tval in iso_timeset])
    contourcmd = 'gdal_contour -a %s %s %s -nln isochrones -fl %s' \
        % (utils.TIME_FIELD, avg_fname, ctr_fname, timeset_str)
    print "Running %s:" % contourcmd
    os.system(contourcmd)
    isob_fname = utils.isoBandsName(loc_name, datestr, timestr,
        save_path, save_suffix, num_each_side)
    isob_all_fname = utils.isoBandsAllName(loc_name, datestr, timestr,
        save_path, save_suffix, num_each_side)
    # Line below calls script that relies on Matplotlib
    # Sourced from:
    # https://github.com/rveciana/geoexamples/tree/master/python/raster_isobands
    isobandscmd = 'isobands_matplotlib.py -up True -a %s %s %s '\
        '-nln isochrones -i %d' \
        % (utils.TIME_FIELD, avg_fname, isob_all_fname, iso_inc)
    print "Running %s:" % isobandscmd
    os.system(isobandscmd)
    # These isobands will include all isobands up to OTP's max (128 mins). 
    # For the sake of this project we just want a subset, defined by 
    #  our timeset list.
    # Thanks to https://github.com/dwtkns/gdal-cheat-sheet for this
    if os.path.exists(isob_fname):
        os.unlink(isob_fname)
    # Watch out that ogr2ogr takes _dest_ file before _src_ file.
    isobandssubsetcmd = 'ogr2ogr -where "%s <= %d" %s %s' \
        % (utils.TIME_FIELD, iso_timeset[-1], isob_fname, isob_all_fname)
    print "Running %s:" % isobandssubsetcmd 
    os.system(isobandssubsetcmd)

def extract_and_smooth_isobands(save_path, save_suffix, loc_name, datestr,
        timestr, num_each_side, iso_max, iso_inc, **kwargs):
    isob_fname = utils.isoBandsName(loc_name, datestr, timestr, save_path, 
        save_suffix, num_each_side)
    if not os.path.exists(isob_fname):
        print "Warning: need pre-existing vector isobands file to extract "\
            "from and smooth, generating now ..."
        make_contours_isobands(save_path, save_suffix, loc_name, datestr,
            timestr, num_each_side, iso_max, iso_inc, **kwargs)
        
    # Import these here in case user doesn't have shapely installed.
    import shapely_smoother
    import get_polys_at_level

    print "Beginning extracting and smoothing isoband vectors ..."
    for iso_level in range(iso_inc, iso_max+1, iso_inc):
        polys_fname = utils.polysIsoBandsName(loc_name, datestr,
            timestr, save_path, save_suffix, num_each_side, iso_level)
        print "Extract polygons for iso level %d to %s:" % \
            (iso_level, polys_fname)
        get_polys_at_level.get_polys_at_level(isob_fname, polys_fname,
            utils.TIME_FIELD, iso_level)
        smoothed_fname = utils.smoothedIsoBandsName(loc_name, datestr, 
            timestr, save_path, save_suffix, num_each_side, iso_level)
        print "Smoothing these and saving to file %s:" % \
            (smoothed_fname)
        shapely_smoother.smooth_all_polygons(polys_fname, smoothed_fname)
    print "Done."

def combine_smoothed_isoband_files(save_path, save_suffix, loc_name,
        datestr, timestr, num_each_side, iso_max, iso_inc, **kwargs):
    #print "Combining smoothed isoband files into a single file:"
    combined_smoothed_fname = utils.smoothedIsoBandsNameCombined(loc_name,
        datestr, timestr, save_path, save_suffix, num_each_side) 

    # Open the first of the smoothed isobands files to get EPSG
    first_smoothed_iso_fname = utils.smoothedIsoBandsName(loc_name, datestr, 
        timestr, save_path, save_suffix, num_each_side, iso_inc)
    source = ogr.Open(first_smoothed_iso_fname)
    if not source:
        print "Error:- can't open individual smoothed isochrone shapefiles "\
            "for location '%s' - file %s ." \
            % (loc_name, first_smoothed_iso_fname)
        sys.exit(1)
    in_layer = source.GetLayer(0)
    smoothed_srs = in_layer.GetSpatialRef()

    # Create new file
    import shapely_smoother
    comb_ds, comb_layer = shapely_smoother.create_smoothed_isobands_shpfile(
        combined_smoothed_fname, smoothed_srs, time_field=True)
    comb_defn = comb_layer.GetLayerDefn()
    in_layer = None

    feat_id = 0
    for iso_level in range(iso_inc, iso_max+1, iso_inc):
        smoothed_iso_fname = utils.smoothedIsoBandsName(loc_name, datestr, 
            timestr, save_path, save_suffix, num_each_side, iso_level)
        source = ogr.Open(smoothed_iso_fname)
        in_layer = source.GetLayer(0)
        # TODO:- potentially need to subtract polygons in previous layers
        # during the process below, to support transparencies in visualisation
        # etc.
        for poly in in_layer:
            # We need to adjust muiltipoly IDs for use in the combined file.
            new_poly = ogr.Feature(comb_defn)
            new_poly.SetField(utils.ID_FIELD, feat_id)
            feat_id += 1
            new_poly.SetField(utils.TIME_FIELD, iso_level)
            poly_geom = poly.GetGeometryRef()
            new_poly.SetGeometry(poly_geom)
            comb_layer.CreateFeature(new_poly)
        in_layer = None
    # Close, save the new shapefile.    
    comb_layer = None
    comb_ds = None
    #print "...done."
    print "combined smoothed isochrones saved to file %s ." \
        % combined_smoothed_fname
    return

def generate_avg_rasters_and_isobands(multi_graph_iso_set):
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        datestr = isos_spec['date']
        for loc_name in \
                itertools.imap(operator.itemgetter(0), isos_spec['locations']):
            for timestr in isos_spec['times']:
                make_average_raster(save_path, save_suffix, loc_name, datestr,
                    timestr, **isos_spec)
                make_contours_isobands(save_path, save_suffix, loc_name,
                    datestr, timestr, **isos_spec)

def generate_smoothed_isobands(multi_graph_iso_set):
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        datestr = isos_spec['date']
        for loc_name in \
                itertools.imap(operator.itemgetter(0), isos_spec['locations']):
            for timestr in isos_spec['times']:
                extract_and_smooth_isobands(save_path, save_suffix, loc_name,
                    datestr, timestr, **isos_spec)

def combine_smoothed_isobands_files(multi_graph_iso_set):
    """Combines all the separate smoothed isoband files (with e.g. -10, -20
    extensions) into a single Shapefile with multiple multi-polygon shapes
    defined (which makes consistent styling etc easier)."""
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        datestr = isos_spec['date']
        print "Creating combined smoothed isochrones shapefiles for "\
            "results from graph '%s', at date '%s', times %s:" \
            % (otp_router_id, datestr, isos_spec['times'])
        for loc_name in \
                itertools.imap(operator.itemgetter(0), isos_spec['locations']):
            print "Creating combined smoothed isochrones shapefile for "\
                "location '%s':" % loc_name
            for timestr in isos_spec['times']:
                print "Creating combined shapefile at date, time %s - %s" % \
                    (datestr, timestr)
                combine_smoothed_isoband_files(save_path, save_suffix, loc_name,
                    datestr, timestr, **isos_spec)
    return
