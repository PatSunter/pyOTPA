# A set of functions helpful for analysing the OD matrices produced from tools
# such as OpenTripPlanner, NetView, etc.
# Patrick Sunter, 2013-2014.

# Uses OGR library for shape file manipulation aspects.

import numpy
import csv
import os

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
        time_1 = od_mat_1[originID, destID]
        time_2 = od_mat_2[originID, destID]
        
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

    routesArray = numpy.zeros((nrows, 2))
    case1Times = numpy.zeros(nrows)
    case2Times = numpy.zeros(nrows)
    #Restart, now we know array sizes
    compfile.seek(0)
    compreader = csv.reader(compfile, delimiter=',')
    #headers
    compreader.next()
    for ii, row in enumerate(compreader):
        routesArray[ii] = [row[0], row[1]]
        case1Times[ii] = row[2]
        case2Times[ii] = row[3]

    compfile.close()
    return routesArray, case1Times, case2Times

def createShapefile(routesArray, latlons, case1Times, case2Times, caseNames,
        shapefilename):
    """Creates a Shape file stating the difference between times in two
    OD matrices, which have been 'unrolled' as large arrays listing 
    travel time between OD pairs. 'caseNames' should be short strings
    describing the cases, eg. 'OTP' and 'NV'.
    Saves results to a shapefile determined by shapefilename.
    
    N.B. :- thanks for overall strategy here are due to author of
    https://github.com/glennon/FlowpyGIS"""

    import ogr

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
        linester.AddPoint(latlons[originID][1], latlons[originID][0])
        linester.AddPoint(latlons[destID][1], latlons[destID][0])

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

