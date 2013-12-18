#!/usr/bin/env python

import csv
import os

tfile = open('/Users/Shared/SoftwareDev/UrbanModelling-GIS/OpenTripPlanner/BatchResults/tazs-current/taz_locs.csv', 'rb')
treader = csv.reader(tfile, delimiter=',', quotechar="'")

#First we'll just assemble the list of dirnames.
dirnames = []
taznums = []
lats = []
lons = []
for ii, row in enumerate(treader):
    if ii == 0: continue
    else:
        taznums += [row[0]]
        lats += [row[1]]
        lons += [row[2]]
        dirname = '%d_%s' % (ii-1, taznums[ii-1])
        print dirname
        dirnames += [dirname]

tfile.close()

print "Starting creating OD Matrix ...\n"
odmatfile = open('tazs_od_matrix.csv', 'w')
matwriter = csv.writer(odmatfile, delimiter=',')
#Special header row ...
matwriter.writerow(['Origin','Lat','Lon'] + taznums)

#Now go thru each result file, and add to the list
for ii, dirname in enumerate(dirnames):
        #print dirname
        try:
            resfile = open(os.path.join(dirname, 'res.csv'))
        except IOError:
            print "WARNING: Missing results for directory %s:- writing" \
                " blank line." % dirname
            matwriter.writerow([taznums[ii], lats[ii], lons[ii]])
            continue
        else:
            resreader = csv.reader(resfile, delimiter=',')
            times = []
            for jj, row in enumerate(resreader):
                if jj == 0: continue
                else:
                    times += [row[4]]
            matwriter.writerow([taznums[ii], lats[ii], lons[ii]] + times)        
            resfile.close()
odmatfile.close()
