#!/usr/bin/env python2

import urllib
import urllib2
import os.path

import utils

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
                mins_diffs = utils.get_nearby_min_diffs(nearby_minutes,
                    num_each_side)

            date_time_str_set = utils.get_date_time_string_set(date, time,
                mins_diffs)
            fname_set = utils.get_raster_filenames(loc_name_orig,
                date_time_str_set, output_subdir, suffix)

            print "About to save rasters at dates and times, to files:"
            for date_time_tuple, fname in zip(date_time_str_set, fname_set):
                date_mod, time_mod = date_time_tuple
                print "   %s - %s -> %s" % (date_mod, time_mod, fname) 

            for date_time_tuple, fname in zip(date_time_str_set, fname_set):
                date_mod, time_mod = date_time_tuple
                url = buildRequestStringRaster(server_url, paramsDict,
                    date_mod, time_mod, lon_lat, img_bbox, res, router_id)
                print url
                response = urllib2.urlopen(url)
                data = response.read()
                f = open(fname, "w")
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
                    f = open(utils.vectorName(loc_name_orig, time, iso, vec_type,
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
