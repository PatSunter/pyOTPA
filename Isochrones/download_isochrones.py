#!/usr/bin/env python2

import urllib
import urllib2
from datetime import datetime, timedelta
import os
import os.path

"""A Python script to help download a series of Isochrone files from
an OpenTripPlanner server"""

def buildRequestStringRaster(server_url, paramsDict, date, time, lon_lat,
        img_bbox, res, router_id=None):
    reqStr = "/opentripplanner-api-webapp/ws" + "/wms" + '?'
    # General OTP routing request stuff
    reqStr += "&".join([name+'='+urllib2.quote(str(val)) for name, val \
        in paramsDict.iteritems()])
    reqStr += '&'+'fromPlace'+'='+str(lon_lat[1])+','+str(lon_lat[0])
    reqStr += '&'+'toPlace'+'='+str(lon_lat[1])+','+str(lon_lat[0])
    reqStr += '&'+'time'+'='+date+'T'+urllib2.quote(time)
    # Stuff specific to raster output
    reqStr += '&'+'format'+'='+"image/geotiff"
    reqStr += '&'+'srs'+'='+"EPSG:4326"
    reqStr += '&'+'resolution'+'='+str(res)
    reqStr += '&'+'bbox'+'='+','.join(str(ii) for ii in img_bbox[0] + \
        img_bbox[1])
    if router_id is not None:
        reqStr += '&'+'routerId'+'='+router_id
    # Add server URL
    url = server_url + reqStr
    return url

def buildRequestStringVector(server_url, paramsDict, date, time, lon_lat,
        time_radius, vec_type, router_id=None):
    reqStr = "/opentripplanner-api-webapp/ws" + "/iso" + '?'
    # General OTP routing request stuff
    reqStr += "&".join([name+'='+urllib2.quote(str(val)) for name, val \
        in paramsDict.iteritems()])
    reqStr += '&'+'fromPlace'+'='+str(lon_lat[1])+','+str(lon_lat[0])
    reqStr += '&'+'toPlace'+'='+str(lon_lat[1])+','+str(lon_lat[0])
    reqStr += '&'+'time'+'='+date+'T'+urllib2.quote(time)
    # Stuff specific to raster output
    reqStr += '&'+'walkTime'+'='+str(time_radius)
    reqStr += '&'+'output'+'='+vec_type
    if router_id is not None:
        reqStr += '&'+'routerId'+'='+router_id
    # Add server URL
    url = server_url + reqStr
    return url

def rasterName(loc_name, time, rel_dir=None, suffix=""):
    fname =  str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_')
    if suffix and suffix != "":
        fname += '-' + suffix
    fname += '.tiff'
    if rel_dir is not None:
        path = os.path.join(".", rel_dir, fname)
    else:
        path = fname
    return path

def vectorName(loc_name, time, iso, vec_type, rel_dir=None):
   fname = str.replace(loc_name, ' ', '_') \
        + '-' + str.replace(time, ':', '_') \
        + '-' + str(iso) +"min" \
        + '-' + str.lower(vec_type) \
        + '.geojson'
   if rel_dir is not None:
       path = os.path.join(".", rel_dir, fname)
   else:
       path = fname
   return path

def get_nearby_min_diffs(nearby_minutes, num_each_side):
    inc_range = range(1, num_each_side+1)
    mins_before = [-nearby_minutes * ii/float(num_each_side) \
        for ii in reversed(inc_range)]
    mins_after = [nearby_minutes * ii/float(num_each_side) \
        for ii in inc_range]
    mins_diffs = mins_before + [0] + mins_after
    return mins_diffs

def get_date_time_string_set(base_date, base_time, mins_diffs):
    y_m_d = [int(ii) for ii in base_date.split('-')]
    h_m_s = [int(ii) for ii in base_time.split(':')]
    dtime_orig = datetime(year=y_m_d[0], month=y_m_d[1],
        day=y_m_d[2], hour=h_m_s[0], minute=h_m_s[1],
        second=h_m_s[2])
    date_time_set = []
    for mins_diff in mins_diffs:
        time_diff = timedelta(minutes=mins_diff)
        mt = dtime_orig + time_diff
        date_mod = "%d-%02d-%02d" % (mt.year, mt.month, mt.day)
        time_mod = "%02d:%02d:%02d" % (mt.hour, mt.minute, mt.second)
        date_time_set.append((date_mod, time_mod))
    return date_time_set    
                
#TODO: Might be good to set default values for some of these.
def saveIsosForLocations(server_url, locations, paramsDict, date, times,
        save_nearby_times, nearby_minutes, num_each_side,
        img_buf, res, isochrones, vec_types,
        router_id=None, output_subdir=None, suffix=None):

    if output_subdir is not None and os.path.exists(output_subdir) is False: 
        os.makedirs(output_subdir)

    for loc in locations:
        loc_name_orig = loc[0]
        lon_lat = loc[1]
        img_bbox = [(lon_lat[0] - img_buf[0], lon_lat[1] - img_buf[1]),
            (lon_lat[0] + img_buf[0], lon_lat[1] + img_buf[1])]

        print "Saving info for location %s" % loc_name_orig
        for time in times:
            print "For time %s:" % time
            if save_nearby_times is None:
                mins_diffs = 0
            else:
                mins_diffs = get_nearby_min_diffs(nearby_minutes, num_each_side)

            date_time_str_set = get_date_time_string_set(date, time, mins_diffs)

            print "About to save rasters at dates and times:"
            for date_mod, time_mod in date_time_str_set:
                print "   %s - %s" % (date_mod, time_mod) 

            for date_mod, time_mod in date_time_str_set:
                url = buildRequestStringRaster(server_url, paramsDict,
                    date_mod, time_mod, lon_lat, img_bbox, res, router_id)
                print url
                response = urllib2.urlopen(url)
                data = response.read()
                f = open(rasterName(loc_name_orig, time_mod, output_subdir,
                    suffix), "w")
                f.write(data)
                f.close()

            # Now get the vectors, at different time radius.
            print "About to save vectors:"
            for iso in isochrones:
                for vec_type in vec_types:
                    url = buildRequestStringVector(server_url, paramsDict, 
                        date, time, lon_lat, iso, vec_type, router_id)
                    print url
                    response = urllib2.urlopen(url)
                    data = response.read()
                    f = open(vectorName(loc_name_orig, time, iso, vec_type,
                        output_subdir), "w")
                    f.write(data)
                    f.close()
            print "DONE!\n"
    return

def download_isochrone_set(base_subdir, router_subdirs=None, **kwargs):
    # We just pass thru most arguments directly.
    if router_subdirs is not None and len(router_subdirs) > 0:
        for router_id, output_subdir in router_subdirs:
            full_output_subdir = os.path.join(base_subdir, output_subdir)
            dl_isos.saveIsosForLocations(output_subdir=full_output_subdir,
                **kwargs)
    else:
        dl_isos.saveIsosForLocations(output_subdir=base_subdir, **kwargs)
