import os
from datetime import datetime
import re

import h5py as h5
import numpy as np

insert_size = 10

time_unit_conversion_factor = {'millisecond': 1e-3,
                               'second': 1,
                               'minute': 60,
                               'hour': 3600,
                               'day': 86400}

datetime_formats = ['%Y-%m-%d']


def parse_date(text):
    for fmt in datetime_formats:
        cover = len(datetime.now().strftime(fmt))
        try:
            return datetime.strptime(text[:cover], fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def find_session_matched_matfile(sess_data_dir, sess_key):
        sess_data_files = os.listdir(sess_data_dir)
        # Search the filenames to find a match for "this" session (based on key)
        sess_data_file = None
        for s in sess_data_files:
            if re.search(sess_key['session_id'], s):
                sess_data_file = s
        if sess_data_file:
            return sess_data_file
        else:
            return None


def split_list(arr, size):
    slice_from = 0
    while len(arr) > slice_from:
        slice_to = slice_from + size
        yield arr[slice_from:slice_to]
        slice_from = slice_to

