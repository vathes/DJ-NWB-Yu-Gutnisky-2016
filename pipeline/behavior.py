'''
Schema of behavioral information.
'''
import re
import os
from datetime import datetime
import sys

import numpy as np
import scipy.io as sio
import datajoint as dj

from . import utilities, reference, acquisition, analysis, intracellular


schema = dj.schema(dj.config['custom']['database.prefix'] + 'behavior')


@schema
class Whisker(dj.Imported):
    definition = """ # Whisker Behavior data
    -> acquisition.Session
    -> reference.WhiskerConfig
    ---
    distance_to_pole=null: longblob  #
    touch_offset=null: longblob  #
    touch_onset=null: longblob  #
    whisker_angle=null: longblob  #
    whisker_curvature=null: longblob  #
    behavior_timestamps=null: longblob  # (s)
    """

    def make(self, key):
        print(f'Inserted behavioral data for session: {key["session_id"]}')


@schema
class LickTrace(dj.Imported):
    definition = """
    -> acquisition.Session
    ---
    lick_trace: longblob   
    lick_trace_timestamps: longblob # (s) 
    """

