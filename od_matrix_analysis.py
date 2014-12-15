# A set of functions helpful for analysing the OD matrices produced from tools
# such as OpenTripPlanner, NetView, etc.
# Patrick Sunter, 2013-2014.

# Uses OGR library for shape file manipulation aspects.

import csv
import os
import operator
import itertools

import numpy

import taz_files

### General utility functions - OTP

def readLatLons(otpfilename, nPoints):
    """Read a set of latitute and longitude points for a set of 
    Travel Analysis Zones (TAZs) - from the first columns of an OTP O-D
    matrix file. Return these as a two-dimensional array,
    where primary index is ID of each TAZ."""
    latlons = numpy.zeros((nPoints+1,2))

    otpfile = open(otpfilename)
    otpreader = csv.reader(otpfile, delimiter=',')
    print "Reading Lat-lons from OTP CSV ... "
    #header row
    header_row = otpreader.next()
    for ii, row in enumerate(otpreader):
        originID = int(row[0])
        latlons[originID] = (float(row[1]), float(row[2]))
    print "Done."    
    otpfile.close()
    return latlons

### General utility functions - Netview

def readNVRouteIDs(nvfilename, nroutes):
    docstring = """Returns an array containing the OriginID, DestID pair for \
        each route in the Netview CSV file."""

    nvroutes = numpy.zeros((nroutes,2))
    nvfile = open(nvfilename)
    nvreader = csv.reader(nvfile, delimiter=';')
    #There are three mostly blank lines at the start
    for ii in range(3):
        nvreader.next()
    #Then headers row
    nv_header_row = nvreader.next()

    #OK, now process rest of rows
    nroutes = 0
    for ii, row in enumerate(nvreader):
        originIDText = row[0]
        originID = int(originIDText[1:])
        destIDText = row[1]
        destID = int(destIDText[1:])
        nvroutes[ii] = [originID, destID]
    nvfile.close()
    return nvroutes


### Entire OD Matrix reading

def readOTPMatrix(otpfilename, mat):
    """Read in an OD matrix from results created by OpenTripPlanner, and
    then post-processed by the make_od_matrix.py script. 
    matrix 'mat' must be in numpy format, and already be of the correct
    size."""
    otpfile = open(otpfilename)
    otpreader = csv.reader(otpfile, delimiter=',')
    print "Reading OTP O-D matrix from CSV ..."
    #Create lookup table from header row
    header_row = otpreader.next()
    destlookups = header_row[3:]
    for ii, row in enumerate(otpreader):
        if ii % 100 == 0:
            print "Reading %dth row of O-Ds" % (ii)
        originID = int(row[0])
        timesToDests = row[3:]
        for jj, time in enumerate(timesToDests):
            mat[originID, int(destlookups[jj])] = int(float(time)+0.5)
    print "Done."
    otpfile.close()
    return

    
def readNVMatrix(nvfilename, mat):    
    """Read in an OD matrix in the format created by the Netview routing
    tool. Matrix must be of the correct size.
    Note: converts the Netview output (in minutes) into seconds."""
    nvfile = open(nvfilename)
    nvreader = csv.reader(nvfile, delimiter=';')
    print "Reading Netview O-D matrix ..."
    #There are three mostly blank lines at the start
    for ii in range(3):
        nvreader.next()
    #Then headers row
    nv_header_row = nvreader.next()

    #OK, now process rest of rows
    nroutes = 0
    for ii, row in enumerate(nvreader):
        if ii % 1000 == 0:
            print "Reading and processing %dth row ... " % (ii)
        originIDText = row[0]
        originID = int(originIDText[1:])
        destIDText = row[1]
        destID = int(destIDText[1:])
        time_min = row[9]
        time_sec = float(time_min) * 60.0
        mat[originID, destID] = time_sec
        nroutes += 1
    print "Done."
    nvfile.close()
    return nroutes

# High-level analysis functions.

def saveComparisonFile(routesArray, od_mat_1, od_mat_2, compfilename,
        case_names):
    compfile = open(compfilename, "w")
    compwriter = csv.writer(compfile, delimiter=',')
    # Header row
    compwriter.writerow(['OriginID','DestID', '%s Time (s)' % case_names[0], \
        '%s Time (s)' % case_names[1], 'Difference (s)', 'Abs. Diff (s)',
        'Abs. Diff (%)','Diff (%)'])
    for ii, route in enumerate(routesArray):
        originID = route[0]
        destID = route[1]
        time_1 = int(od_mat_1[originID, destID])
        time_2 = int(od_mat_2[originID, destID])
        
        # Checking for OTP times that are null for some reason.
        # NB: ideally would be good to keep some info with a matrix so
        #  we can interpret if it was created by OTP etc how to handle.
        #  would require more complex data structures, or an object-oriented
        #  wrapper with an is_valid() function etc.
        if time_1 in [0,-1,-2] or time_2 in [0,-1,-2]:
            diff = "NA"
            diff_percent = "NA"
            absdiff = "NA"
            absdiff_percent = "NA"
        else:
            diff = time_1 - time_2
            diff_percent = diff / float(time_1)
            absdiff = abs(diff)
            absdiff_percent = absdiff / float(time_1)

        compwriter.writerow([originID, destID, time_1, time_2, diff, absdiff,\
            absdiff_percent, diff_percent])
    compfile.close()
    return

def readComparisonFile(compfilename):
    """Read in a comparison file created by saveComparisonFile().
    Returns a tuple containing 3 numpy arrays:- first being the routes
    in terms of TAZ O-D pairs, the second being times for those routes
    in the first case, the second being times in the second case.
    Requires format of saved comparison file's first 4 columns to be origin ID,
    dest ID, time in case 1, time in case 2 
    (e.g. case 1 being OTP, case 2 being Netview)."""
    
    compfile = open(compfilename)
    compreader = csv.reader(compfile, delimiter=',')
    #headers
    compreader.next()
    nrows = 0
    for ii, row in enumerate(compreader):
        nrows += 1

    routesArray = []
    case1Times = []
    case2Times = []
    #Restart, now we know array sizes
    compfile.seek(0)
    compreader = csv.reader(compfile, delimiter=',')
    #headers
    compreader.next()
    for ii, row in enumerate(compreader):
        routesArray.append((int(row[0]), int(row[1])))
        case1Times.append(int(row[2]))
        case2Times.append(int(row[3]))
    compfile.close()
    return routesArray, case1Times, case2Times

def createShapefile(routesArray, lonlats, case1Times, case2Times, caseNames,
        shapefilename):
    """Creates a Shape file stating the difference between times in two
    OD matrices, which have been 'unrolled' as large arrays listing 
    travel time between OD pairs. 'caseNames' should be short strings
    describing the cases, eg. 'OTP' and 'NV'.
    Saves results to a shapefile determined by shapefilename.
    
    N.B. :- thanks for overall strategy here are due to author of
    https://github.com/glennon/FlowpyGIS"""

    import osgeo.ogr
    from osgeo import ogr

    print "Creating shapefile of route lines with time attributes to file"\
        " %s ..." % (shapefilename)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    # create a new data source and layer
    if os.path.exists(shapefilename):
        driver.DeleteDataSource(shapefilename)
    ds = driver.CreateDataSource(shapefilename)
    if ds is None:
        print 'Could not create file'
        sys.exit(1)

    c1TimeFieldName = 't %s' % caseNames[0]
    c2TimeFieldName = 't %s' % caseNames[1]

    layer = ds.CreateLayer('routeinfos', geom_type=ogr.wkbLineString)
    fieldDefn = ogr.FieldDefn('OriginID', ogr.OFTReal)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('DestID', ogr.OFTReal)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c1TimeFieldName, ogr.OFTReal)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn(c2TimeFieldName, ogr.OFTReal)
    layer.CreateField(fieldDefn)
    fieldDefn = ogr.FieldDefn('Diff', ogr.OFTReal)
    layer.CreateField(fieldDefn)
    # END setup creation of shapefile

    for ii, routePair in enumerate(routesArray):
        originID = routePair[0]
        destID = routePair[1]
        case1time = case1Times[ii]
        case2time = case2Times[ii]
        linester = ogr.Geometry(ogr.wkbLineString)
        linester.AddPoint(lonlats[originID][0], lonlats[originID][1])
        linester.AddPoint(lonlats[destID][0], lonlats[destID][1])

        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(linester)
        feature.SetField('OriginID', originID)
        feature.SetField('DestID', destID)
        feature.SetField(c1TimeFieldName, case1time)
        feature.SetField(c2TimeFieldName, case2time)
        if case1time in [0,-1,-2] or case2time in [0,-1,-2]:
            diff = 0
        else:
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

MINUTE_BREAKS = [1, 10, 20, 30, 60]

def compute_comparison_stats(comp_csv_filename):
    routesArray, otp_curr_times, otp_new_times = \
        readComparisonFile(comp_csv_filename)
    otp_diffs = [curr - new for new, curr \
        in zip(otp_new_times, otp_curr_times)]
    st = {
        'total_trips' : len(otp_curr_times),
        'lost_trips' : 0,
        'added_trips' : 0,
        'valid_trips_both' : 0,
        'faster_trips' : 0,
        'slower_trips' : 0,
        'same_trips' : 0,
        'slower_total_change' : 0,
        'faster_total_change' : 0,
        'valid_total_curr' : 0,
        'valid_total_new' : 0,
        'valid_total_diff' : 0,
        'trips_in_range' : {}
        }
    for min_break in MINUTE_BREAKS:
        st['trips_in_range'][-min_break] = 0
        st['trips_in_range'][min_break] = 0
    st['trips_in_range']['-inf'] = 0
    st['trips_in_range']['inf'] = 0
        
    for ii, (otp_curr_t, otp_new_t, otp_diff) in enumerate(zip(otp_curr_times,
            otp_new_times, otp_diffs)):
        if otp_curr_t <= 0 and otp_new_t <= 0:
            # Trip is invalid in both.
            continue
        if otp_curr_t > 0 and otp_new_t <= 0:
            st['lost_trips'] += 1
        elif otp_curr_t <= 0 and otp_new_t > 0:
            st['added_trips'] += 1
        else:
            st['valid_trips_both'] += 1
            st['valid_total_curr'] += otp_curr_t 
            st['valid_total_new'] += otp_new_t
            st['valid_total_diff'] += otp_diff
            abs_diff_min = abs(otp_diff / 60.0)
            if otp_diff == 0:
                st['same_trips'] += 1
            elif otp_curr_t < otp_new_t: 
                st['slower_trips'] += 1
                st['slower_total_change'] += otp_diff
                range_found = False
                for min_break in MINUTE_BREAKS:
                    if abs_diff_min <= abs(min_break):
                        st['trips_in_range'][-min_break] += 1
                        range_found = True
                        break
                if range_found == False:
                    st['trips_in_range']["-inf"] += 1
            elif otp_new_t < otp_curr_t:
                st['faster_trips'] += 1
                st['faster_total_change'] += otp_diff
                range_found = False
                for min_break in MINUTE_BREAKS:
                    if abs_diff_min <= abs(min_break):
                        st['trips_in_range'][min_break] += 1
                        range_found = True
                        break
                if range_found == False:
                    st['trips_in_range']["inf"] += 1
    # Compute averages.
    if st['valid_trips_both'] > 0:
        st['avg_curr_min'] = \
            (st['valid_total_curr'] / float(st['valid_trips_both'])) / 60.0
        st['avg_new_min'] = \
            (st['valid_total_new'] / float(st['valid_trips_both'])) / 60.0
        st['avg_diff_min'] = \
            (st['valid_total_diff'] / float(st['valid_trips_both'])) / 60.0
        st['same_trips_pct'] = \
            st['same_trips'] / float(st['valid_trips_both']) * 100.0
        st['slower_trips_pct'] = \
            st['slower_trips'] / float(st['valid_trips_both']) * 100.0
        st['faster_trips_pct'] = \
            st['faster_trips'] / float(st['valid_trips_both']) * 100.0
    else:
        st['avg_curr_min'] = 0
        st['avg_new_min'] = 0
        st['avg_diff_min'] = 0
        st['same_trips_pct'] = 0
        st['slower_trips_pct'] = 0
        st['faster_trips_pct'] = 0
    if st['valid_total_curr']:
        st['avg_diff_perc'] = \
            st['valid_total_diff'] / float(st['valid_total_curr']) * 100.0
    else:        
        st['avg_diff_perc'] = 0
    if st['slower_trips']:
        st['avg_slower'] = st['slower_total_change'] / float(st['slower_trips'])
    else:
        st['avg_slower'] = 0
    if st['faster_trips']:          
        st['avg_faster'] = st['faster_total_change'] / float(st['faster_trips'])
    else:
        st['avg_faster'] = 0
    return st

def print_comparison_stats(stats_dict):
    st = stats_dict
    print "Total trips:-"
    print " %d total, %d both valid, %d lost, %d added." % \
        (st['total_trips'], st['valid_trips_both'], \
         st['lost_trips'], st['added_trips'])
    print "Aggregate change:-"
    print " For trips valid in both, avg trip time changed from %.1f "\
        "minutes to %.1f minutes.\n" \
        " A change of %.1f min (%.2f%%)." \
        % (st['avg_curr_min'], st['avg_new_min'], \
           st['avg_diff_min'], st['avg_diff_perc'])
    print "Trip breakdown:"
    print "%5d trips (%.2f%%) of unchanged duration.\n"\
        "%5d trips (%.2f%%) were slower (avg change of %.1f sec (%.1f min)).\n"\
        "%5d trips (%.2f%%) were faster (avg change of %.1f sec (%.1f min))."\
        % (st['same_trips'], st['same_trips_pct'], \
           st['slower_trips'], st['slower_trips_pct'], \
           st['avg_slower'], st['avg_slower'] / 60.0, \
           st['faster_trips'], st['faster_trips_pct'], \
           st['avg_faster'], st['avg_faster'] / 60.0 )
    print "Detailed trip breakdown:"
    sign_word_pairs = [(-1, "slower"), (1, "faster")]
    for sign, speed_word in sign_word_pairs:
        prev_tval = 0
        for tval in MINUTE_BREAKS:
            trips_in_range = st['trips_in_range'][sign * tval]
            perc_in_range = trips_in_range / float(st['valid_trips_both']) * 100
            print "%5d trips (%5.2f%%) in range (%d,%d] mins %s." % \
                (trips_in_range, perc_in_range, prev_tval, tval, speed_word)
            prev_tval = tval
        inf_word = "-inf" if sign < 0 else "inf"
        trips_in_last_range = st['trips_in_range'][inf_word]
        print "%5d trips > %d mins %s." % \
            (trips_in_last_range, prev_tval, speed_word)
    print ""
