import os
import os.path
import string
from datetime import date
import itertools
import operator

import utils

TIME_FIELD="time"

# These determine default isochrone time maximums and increments
DEF_ISO_MAX=40
DEF_ISO_INC=10

CORRECT_NODATA_VALUE_BYTE=128

def avgRasterName(loc_name, datestr, timestr, save_path, save_suffix,
        num_each_side):
    numavg = 1 + 2*num_each_side
    fname_base = utils.rasterName(loc_name, datestr, timestr, save_path,
        save_suffix)
    return os.path.splitext(fname_base)[0] + "-avg%d.tiff" % numavg

def isoContoursName(loc_name, datestr, timestr, save_path, save_suffix,
        num_each_side):
    avg_fname = avgRasterName(loc_name, datestr, timestr, save_path,
        save_suffix, num_each_side)
    return os.path.splitext(avg_fname)[0] + "-isocontours.shp"

def isoBandsName(loc_name, datestr, timestr, save_path, save_suffix, 
        num_each_side):
    avg_fname = avgRasterName(loc_name, datestr, timestr, save_path,
        save_suffix, num_each_side)
    return os.path.splitext(avg_fname)[0] + "-isobands.shp"

def polysIsoBandsName(loc_name, datestr, timestr, save_path, save_suffix,
        num_each_side, iso_level):
    isob_fname = isoBandsName(loc_name, datestr, timestr, save_path,
        save_suffix, num_each_side)
    return os.path.splitext(isob_fname)[0] + "-%d-polys.shp" % iso_level

def smoothedIsoBandsName(loc_name, datestr, timestr, save_path, 
        save_suffix, num_each_side, iso_level):
    isob_fname = isoBandsName(loc_name, datestr, timestr, save_path,
        save_suffix, num_each_side)
    smoothed_fname = os.path.splitext(isob_fname)[0] + "-%d-smoothed.shp"\
        % (iso_level)
    return smoothed_fname

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
    avg_fname = avgRasterName(loc_name, datestr, timestr, save_path, 
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
    avg_fname = avgRasterName(loc_name, datestr, timestr, 
        save_path, save_suffix, num_each_side)
    ctr_fname = isoContoursName(loc_name, datestr, timestr, 
        save_path, save_suffix, num_each_side)
    if os.path.exists(ctr_fname):
        os.unlink(ctr_fname)
    timeset_str = " ".join([str(tval+0.1) for tval in iso_timeset])
    contourcmd = 'gdal_contour -a %s %s %s -nln isochrones -fl %s' \
        % (TIME_FIELD, avg_fname, ctr_fname, timeset_str)
    print "Running %s:" % contourcmd
    os.system(contourcmd)
    isob_fname = isoBandsName(loc_name, datestr, timestr, save_path, 
        save_suffix, num_each_side)
    isob_all_fname = os.path.splitext(isob_fname)[0] + "-all.shp"
    # Line below calls script that relies on Matplotlib
    # Sourced from:
    # https://github.com/rveciana/geoexamples/tree/master/python/raster_isobands
    isobandscmd = 'isobands_matplotlib.py -up True -a %s %s %s '\
        '-nln isochrones -i %d' % (TIME_FIELD, avg_fname, isob_all_fname, iso_inc)
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
        % (TIME_FIELD, iso_timeset[-1], isob_fname, isob_all_fname)
    print "Running %s:" % isobandssubsetcmd 
    os.system(isobandssubsetcmd)

def extract_and_smooth_isobands(save_path, save_suffix, loc_name, datestr,
        timestr, num_each_side, iso_max, iso_inc, **kwargs):
    isob_fname = isoBandsName(loc_name, datestr, timestr, save_path, 
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
        polys_fname = polysIsoBandsName(loc_name, datestr,
            timestr, save_path, save_suffix, num_each_side, iso_level)
        print "Extract polygons for iso level %d to %s:" % \
            (iso_level, polys_fname)
        get_polys_at_level.get_polys_at_level(isob_fname, polys_fname,
            TIME_FIELD, iso_level)
        smoothed_fname = smoothedIsoBandsName(loc_name, datestr, 
            timestr, save_path, save_suffix, num_each_side, iso_level)
        print "Smoothing these and saving to file %s:" % \
            (smoothed_fname)
        shapely_smoother.smooth_all_polygons(polys_fname, smoothed_fname)
    print "Done."

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
