#!/usr/bin/env python

import csv
import os

def make_paths(template_filename):
    tfile = open(template_filename, 'rb')

    treader = csv.reader(tfile, delimiter=',', quotechar="'")
    for ii, row in enumerate(treader):
        if ii == 0: continue
        else:
            dirname = '%d_%s' % (ii-1, row[0])
            print dirname
            os.makedirs(dirname)

if __name__ == "__main__":
    make_paths('/Users/Shared/SoftwareDev/UrbanModelling-GIS/OpenTripPlanner/BatchResults/tazs-current/taz_locs.csv')
