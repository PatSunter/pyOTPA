#!/usr/bin/env python

import csv
import os

sfile = open('/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_Common/GIS-Network-Data-Melb/GTFS-ExtractedData-201307/melb-train-gtfs/stops.txt', 'rb')
sreader = csv.reader(sfile, delimiter=',', quotechar="'")

#First we'll just assemble the list of dirnames.
dirnames = []
stations = []
lats = []
lons = []
for ii, row in enumerate(sreader):
    if ii == 0: continue
    else:
        stations += [row[1]]
        lats += [row[2]]
        lons += [row[0]]
        dirname = '%d_%s' % (ii-1, row[1])
        print dirname
        dirnames += [dirname]

sfile.close()

print "Starting creating OD Matrix ...\n"
odmatfile = open('stations_od_matrix.csv', 'w')
matwriter = csv.writer(odmatfile, delimiter=',')
#Special header row ...
matwriter.writerow(['Origin','Lat','Lon'] + stations)

#Now go thru each result file, and add to the list
for ii, dirname in enumerate(dirnames):
        print dirname
        resfile = open(os.path.join(dirname, 'res.csv'))
        resreader = csv.reader(resfile, delimiter=',')
        times = []
        for jj, row in enumerate(resreader):
            if jj == 0: continue
            else:
                times += [row[4]]
        matwriter.writerow([stations[ii], lats[ii], lons[ii]] + times)        
        resfile.close()
odmatfile.close()
