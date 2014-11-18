#!/usr/bin/env python

import operator
import csv
import os

def make_od_matrix(output_csv_file_name, basepath, taz_infos):
    print "Starting creating OD Matrix ...\n"
    odmatfile = open(output_csv_file_name, 'w')
    matwriter = csv.writer(odmatfile, delimiter=',')
    #Special header row ...
    taznums = map(operator.itemgetter(0), taz_infos)
    matwriter.writerow(['Origin','Lon','Lat'] + taznums)

    #Now go thru each result file, and add to the list
    for ii, taz_info in enumerate(taz_infos):
        dirname = "%d_%s" % (ii, taz_info[0])
        try:
            resfile = open(os.path.join(basepath, dirname, 'res.csv'))
        except IOError:
            print "WARNING: Missing results for directory %s:- writing" \
                " blank line." % dirname
            matwriter.writerow(taz_info)
            continue
        else:
            resreader = csv.reader(resfile, delimiter=',')
            times = []
            for jj, row in enumerate(resreader):
                if jj == 0: continue
                else:
                    times += [row[4]]
            matwriter.writerow(list(taz_info) + times)        
            resfile.close()
    odmatfile.close()
