'''
Schema of intracellular information.
'''
import re
import os
import sys
from datetime import datetime

import numpy as np
import scipy.io as sio
from scipy import sparse
import datajoint as dj

from . import reference, utilities, acquisition, analysis

schema = dj.schema(dj.config['custom']['database.prefix'] + 'intracellular')


@schema
class CellType(dj.Lookup):
    definition = """
    cell_type: varchar(12)
    """
    contents = zip(['excitatory', 'inhibitory', 'FSIN', 'fast-spiking', 'N/A'])


@schema
class Cell(dj.Manual):
    definition = """ # A cell undergone intracellular recording in this session
    -> acquisition.Session
    ---
    -> CellType
    -> reference.ActionLocation
    -> reference.WholeCellDevice
    """


@schema
class MembranePotential(dj.Imported):
    definition = """ # Membrane potential recording from a cell
    -> Cell
    ---
    membrane_potential: longblob  # (mV)
    membrane_potential_timestamps: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class CurrentInjection(dj.Imported):
    definition = """ # Membrane potential recording from a cell
    -> Cell
    ---
    current_injection: longblob  # (mV)
    current_injection_timestamps: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class UnitSpikeTimes(dj.Imported):
    definition = """ # Spike-train recording of this Cell
    -> Cell
    unit_id: smallint
    ---
    spike_times: longblob  # (s)
    """

    def make(self, key):
        return NotImplementedError


@schema
class TrialSegmentedMembranePotential(dj.Computed):
    definition = """
    -> MembranePotential
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_mp=null: longblob   
    """

    key_source = MembranePotential * acquisition.TrialSet * analysis.TrialSegmentationSetting

    def make(self, key):
        # get event, pre/post stim duration
        event_name, pre_stim_dur, post_stim_dur = (analysis.TrialSegmentationSetting & key).fetch1(
            'event', 'pre_stim_duration', 'post_stim_duration')
        # get raw
        mp, timestamps = (MembranePotential & key).fetch1('membrane_potential', 'membrane_potential_timestamps')

        # Limit to insert size of 15 per insert
        trial_lists = utilities.split_list((acquisition.TrialSet.Trial & key).fetch('KEY'), utilities.insert_size)

        for b_idx, trials in enumerate(trial_lists):
            segmented_mp = [dict(trial_key,
                                 segmented_mp=analysis.perform_trial_segmentation(trial_key, event_name,
                                                                                  pre_stim_dur, post_stim_dur,
                                                                                  mp, timestamps)
                                 if not isinstance(analysis.get_event_time(event_name, trial_key,
                                                                           return_exception=True), Exception) else None)
                            for trial_key in trials]
            self.insert({**key, **s} for s in segmented_mp if s['segmented_mp'] is not None)
            print(f'Segmenting Membrane Potential: {b_idx * utilities.insert_size + len(trials)}/' +
                  f'{(acquisition.TrialSet & key).fetch1("trial_counts")}')


@schema
class TrialSegmentedUnitSpikeTimes(dj.Computed):
    definition = """
    -> UnitSpikeTimes
    -> acquisition.TrialSet.Trial
    -> analysis.TrialSegmentationSetting
    ---
    segmented_spike_times=null: longblob
    """

    def make(self, key):
        return NotImplementedError
