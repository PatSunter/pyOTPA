#!/usr/bin/env python

import os
import os.path

def make_paths(taz_ids, base_path):
    """Make all needed paths for an OTP batch analysis run, to-from every OD
    specified in the given CSV :- where row 0 of the CSV is an ID."""
    print 'Making results paths under dir %s' % base_path
    for ii, taz_id in enumerate(taz_ids):
        dirname = '%d_%s' % (ii, taz_id)
        respath = os.path.join(base_path, dirname)
        if not os.path.exists(respath):
            os.makedirs(respath)
    return

