#!/usr/bin/env python

import csv
import os
import os.path

def make_paths(template_filename, base_path):
    print 'Making results paths under dir %s' % base_path
    tfile = open(template_filename, 'rb')
    treader = csv.reader(tfile, delimiter=',', quotechar="'")
    for ii, row in enumerate(treader):
        if ii == 0: continue
        else:
            dirname = '%d_%s' % (ii-1, row[0])
            #print dirname
            respath = os.path.join(base_path, dirname)
            if not os.path.exists(respath):
                os.makedirs(respath)

if __name__ == "__main__":
    make_paths('/Users/Shared/SoftwareDev/UrbanModelling-GIS/OpenTripPlanner/BatchResults/tazs-current/taz_locs.csv')
