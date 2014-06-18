import os
import os.path
import string
from datetime import date
import itertools
import operator

import utils

# These determine default isochrone time maximums and increments
DEF_ISO_MAX=40
DEF_ISO_INC=10

CORRECT_NODATA_VALUE_BYTE=128

def make_average_raster(save_path, file_suffix, loc_name, timestr, 
        nearby_minutes, num_each_side, **kwargs):
    # N.B. :- there may be other kwargs passed in, not relevant here, which we ignore,
    # hence kwargs on the end.
    mins_diffs = utils.get_nearby_min_diffs(nearby_minutes, num_each_side)
    today_str = date.today().isoformat()
    date_time_str_set = utils.get_date_time_string_set(today_str, timestr,
                mins_diffs)
    fnames = utils.get_raster_filenames(loc_name, date_time_str_set, save_path,
        file_suffix)
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
    fname_main = utils.rasterName(loc_name, timestr, save_path, file_suffix)
    avg_fname = os.path.splitext(fname_main)[0] + "-avg%d.tiff" % len(fnames)

    caps = string.ascii_uppercase[:len(fnames)]
    vrts_str = " ".join(["-%s %s" % (a, b) for a, b in zip(caps, vrtnames)])
    calc_str = "("+"+".join(caps)+")"+"/"+str(len(vrtnames))
    calccmd = 'gdal_calc.py %s --outfile=%s --NoDataValue=%d --calc="%s" '\
        '--type=Byte --overwrite' \
        % (vrts_str, avg_fname, CORRECT_NODATA_VALUE_BYTE, calc_str)
    print "Running %s:" % calccmd    
    os.system(calccmd)
    return

def make_contours_isobands(save_path, file_suffix, loc_name, timestr,
        num_each_side, iso_max, iso_inc, **kwargs):
    # N.B. :- again kwargs is needed at the end to ignore unneeded args.
    iso_timeset = range(0, iso_max+1, iso_inc)[1:]
    numavg = 1 + 2*num_each_side
    fname_base = utils.rasterName(loc_name, timestr, save_path, file_suffix)
    avg_fname = os.path.splitext(fname_base)[0] + "-avg%d.tiff" % numavg
    ctr_fname = os.path.splitext(fname_base)[0] + "-avg%d-isos.shp" % numavg
    if os.path.exists(ctr_fname):
        os.unlink(ctr_fname)
    timeset_str = " ".join([str(tval+0.1) for tval in iso_timeset])
    contourcmd = 'gdal_contour -a time %s %s -nln isochrones -fl %s' \
        % (avg_fname, ctr_fname, timeset_str)
    print "Running %s:" % contourcmd
    os.system(contourcmd)
    isob_fname = os.path.splitext(fname_base)[0] \
        + "-avg%d-isobands-mp.shp" % numavg
    # Line below calls script that relies on Matplotlib
    # Sourced from:
    # https://github.com/rveciana/geoexamples/tree/master/python/raster_isobands
    isobandscmd = 'isobands_matplotlib.py -a time %s %s -nln isochrones ' \
        '-i %d' % (avg_fname, isob_fname, iso_inc)
    print "Running %s:" % isobandscmd 
    os.system(isobandscmd)
    # These isobands will include all isobands up to OTP's max (128 mins). 
    # For the sake of this project we just want a subset, defined by 
    #  our timeset list.
    # Thanks to https://github.com/dwtkns/gdal-cheat-sheet for this
    isob2_fname = os.path.splitext(fname_base)[0] \
        + "-avg%d-isobands-mp2.shp" % numavg
    if os.path.exists(isob2_fname):
        os.unlink(isob2_fname)
    # Watch out that ogr2ogr takes _dest_ file before _src_ file.
    isobandssubsetcmd = 'ogr2ogr -where "time <= %d" %s %s' \
        % (iso_timeset[-2], isob2_fname, isob_fname)
    print "Running %s:" % isobandssubsetcmd 
    os.system(isobandssubsetcmd)

def generate_avg_rasters_and_isobands(multi_graph_iso_set):
    for server_url, otp_router_id, save_path, save_suffix, isos_spec in \
            multi_graph_iso_set:
        for placename in \
                itertools.imap(operator.itemgetter(0), isos_spec['locations']):
            for timestr in isos_spec['times']:
                make_average_raster(save_path, save_suffix, placename, timestr,
                    **isos_spec)
                make_contours_isobands(save_path, save_suffix, placename, timestr,
                    **isos_spec)
