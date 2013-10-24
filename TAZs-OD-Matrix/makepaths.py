#!/usr/bin/env python

import csv
import os

tfile = open('/Users/Shared/SoftwareDev/UrbanModelling-GIS/OpenTripPlanner/BatchResults/tazs/taz_locs.csv', 'rb')

treader = csv.reader(tfile, delimiter=',', quotechar="'")
for ii, row in enumerate(treader):
    if ii == 0: continue
    else:
        dirname = '%d_%s' % (ii-1, row[0])
        print dirname
        os.makedirs(dirname)
