#!/usr/bin/env python

import csv
import os

sfile = open('/Users/pds_phd/Dropbox/PhD-TechnicalProjectWork/OSSTIP_Common/GIS-Network-Data-Melb/GTFS-ExtractedData-201307/melb-train-gtfs/stops.txt', 'rb')

sreader = csv.reader(sfile, delimiter=',', quotechar="'")
for ii, row in enumerate(sreader):
    if ii == 0: continue
    else:
        dirname = '%d_%s' % (ii-1, row[1])
        print dirname
        os.makedirs(dirname)
