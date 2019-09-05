#!/usr/bin/env python3
import os

import sys
from datetime import datetime
from dateutil.tz import tzlocal
import pytz
import re
import numpy as np
import pandas as pd
import warnings
import tqdm

from pipeline import (reference, subject, acquisition, stimulation, analysis,
                      intracellular, extracellular, behavior, utilities)
import pynwb
from pynwb import NWBFile, NWBHDF5IO

warnings.filterwarnings('ignore', module='pynwb')

# ============================== SET CONSTANTS ==========================================
default_nwb_output_dir = os.path.join('data', 'NWB 2.0')
zero_zero_time = datetime.strptime('00:00:00', '%H:%M:%S').time()  # no precise time available
hardware_filter = 'Bandpass filtered 300-6K Hz'
institution = 'Janelia Research Campus'

def export_to_nwb(session_key, nwb_output_dir=default_nwb_output_dir, save=False, overwrite=False):
    this_session = (acquisition.Session & session_key).fetch1()

    identifier = '_'.join([this_session['subject_id'],
                           this_session['session_time'].strftime('%Y-%m-%d'),
                           this_session['session_id']])

    # =============== General ====================
    # -- NWB file - a NWB2.0 file for each session
    nwbfile = NWBFile(
        session_description=this_session['session_note'],
        identifier=identifier,
        session_start_time=datetime.combine(this_session['session_date'], zero_zero_time),
        file_create_date=datetime.now(tzlocal()),
        experimenter='; '.join((acquisition.Session.Experimenter & session_key).fetch('experimenter')),
        institution=institution,
        related_publications='')
    # -- subject
    subj = (subject.Subject & session_key).fetch1()
    nwbfile.subject = pynwb.file.Subject(
        subject_id=this_session['subject_id'],
        description=subj['subject_description'],
        genotype=' x '.join((subject.Subject.Allele & session_key).fetch('allele')),
        sex=subj['sex'],
        species=subj['species'])
    # =============== Intracellular ====================
    cell = ((intracellular.Cell & session_key).fetch1()
            if intracellular.Cell & session_key
            else None)
    if cell:
        # metadata
        whole_cell_device = nwbfile.create_device(name=cell['device_name'])
        ic_electrode = nwbfile.create_ic_electrode(
            name=cell['session_id'],
            device=whole_cell_device,
            description='N/A',
            filtering='N/A',
            location='; '.join([f'{k}: {str(v)}'
                                for k, v in (reference.ActionLocation & cell).fetch1().items()]))
        # acquisition - membrane potential
        mp, mp_timestamps = (intracellular.MembranePotential & cell).fetch1(
            'membrane_potential', 'membrane_potential_timestamps')
        nwbfile.add_acquisition(pynwb.icephys.PatchClampSeries(name='membrane_potential',
                                                               electrode=ic_electrode,
                                                               unit='mV',
                                                               conversion=1.0,
                                                               gain=1.0,
                                                               data=mp,
                                                               timestamps=mp_timestamps))
        # acquisition - current injection
        if (intracellular.CurrentInjection & cell):
            current_injection, ci_timestamps = (intracellular.CurrentInjection & cell).fetch1(
                'current_injection', 'current_injection_timestamps')
            nwbfile.add_stimulus(pynwb.icephys.CurrentClampStimulusSeries(name='current_injection',
                                                                          electrode=ic_electrode,
                                                                          unit='nA',
                                                                          conversion=1e-6,
                                                                          gain=1.0,
                                                                          data=current_injection,
                                                                          timestamps=ci_timestamps))

    # =============== Extracellular ====================
    probe_insertion = ((extracellular.ProbeInsertion & session_key).fetch1()
                       if extracellular.ProbeInsertion & session_key
                       else None)
    if probe_insertion:
        probe = nwbfile.create_device(name = probe_insertion['probe_name'])
        electrode_group = nwbfile.create_electrode_group(
            name='; '.join([f'{probe_insertion["probe_name"]}: {str(probe_insertion["channel_counts"])}']),
            description = 'N/A',
            device = probe,
            location = '; '.join([f'{k}: {str(v)}' for k, v in
                                  (reference.BrainLocation & probe_insertion).fetch1().items()]))

        for chn in (reference.Probe.Channel & probe_insertion).fetch(as_dict=True):
            nwbfile.add_electrode(id=chn['channel_id'],
                                  group=electrode_group,
                                  filtering=hardware_filter,
                                  imp=-1.,
                                  x=0.0,  # not available from data
                                  y=0.0,  # not available from data
                                  z=0.0,  # not available from data
                                  location=electrode_group.location)

        # --- unit spike times ---
        nwbfile.add_unit_column(name='depth', description='depth this unit')
        nwbfile.add_unit_column(name='spike_width', description='spike width of this unit')
        nwbfile.add_unit_column(name='cell_type', description='cell type (e.g. wide width, narrow width spiking)')

        for unit in (extracellular.UnitSpikeTimes & probe_insertion).fetch(as_dict=True):
            # make an electrode table region (which electrode(s) is this unit coming from)
            nwbfile.add_unit(id=unit['unit_id'],
                             electrodes=(unit['channel_id']
                                         if isinstance(unit['channel_id'], np.ndarray) else [unit['channel_id']]),
                             depth=unit['unit_depth'],
                             spike_width=unit['unit_spike_width'],
                             cell_type=unit['unit_cell_type'],
                             spike_times=unit['spike_times'],
                             waveform_mean=unit['spike_waveform'])

    # =============== Behavior ====================
    lick_trace_data = ((behavior.LickTrace & session_key).fetch1()
                       if behavior.LickTrace & session_key
                       else None)
    if lick_trace_data:
        behav_acq = pynwb.behavior.BehavioralTimeSeries(name = 'lick_trace')
        nwbfile.add_acquisition(behav_acq)
        [lick_trace_data.pop(k) for k in behavior.LickTrace.primary_key]
        timestamps = lick_trace_data.pop('lick_trace_timestamps')
        for b_k, b_v in lick_trace_data.items():
            behav_acq.create_timeseries(name=b_k,
                                        unit='a.u.',
                                        conversion=1.0,
                                        data=b_v,
                                        timestamps=timestamps)

    if behavior.Whisker & session_key:
        for whisker_data in (behavior.Whisker & session_key).fetch(as_dict=True):
            behav_acq = pynwb.behavior.BehavioralTimeSeries(name = 'principal_'*whisker_data.pop('principal_whisker') + 'whisker_' + whisker_data['whisker_config'])
            nwbfile.add_acquisition(behav_acq)
            [whisker_data.pop(k) for k in behavior.Whisker.primary_key]
            timestamps = whisker_data.pop('behavior_timestamps')
            for b_k, b_v in whisker_data.items():
                behav_acq.create_timeseries(name = b_k,
                                            unit = 'a.u.',
                                            conversion = 1.0,
                                            data = b_v,
                                            timestamps = timestamps)

    # =============== Photostimulation ====================
    photostim = ((stimulation.PhotoStimulation & session_key).fetch()
                       if stimulation.PhotoStimulation & session_key
                       else None)
    if stimulation.PhotoStimulation & session_key:
        for photostim in (stimulation.PhotoStimulation & session_key).fetch(as_dict=True):
            photostim_device = (stimulation.PhotoStimDevice & photostim).fetch1()
            stim_device = (nwbfile.devices.get(photostim_device['device_name'])
                           if photostim_device['device_name'] in nwbfile.devices.keys()
                           else nwbfile.create_device(name=photostim_device['device_name']))
            stim_site = pynwb.ogen.OptogeneticStimulusSite(
                name=photostim['photostim_id'],
                device=stim_device,
                excitation_lambda=float((stimulation.PhotoStimProtocol & photostim).fetch1('photo_stim_excitation_lambda')),
                location = '; '.join([f'{k}: {str(v)}' for k, v in
                                      (reference.ActionLocation & photostim).fetch1().items()]),
                description=(stimulation.PhotoStimProtocol & photostim).fetch1('photo_stim_notes'))
            nwbfile.add_ogen_site(stim_site)

            if photostim['photostim_timeseries'] is not None:
                nwbfile.add_stimulus(pynwb.ogen.OptogeneticSeries(
                    name='photostimulation_' + photostim['photostim_id'],
                    site=stim_site,
                    unit='mW',
                    resolution=0.0,
                    conversion=1e-6,
                    data=photostim['photostim_timeseries'],
                    timestamps=photostim['photostim_timestamps']))

    # =============== TrialSet ====================
    # NWB 'trial' (of type dynamic table) by default comes with three mandatory attributes:
    #                                                                       'id', 'start_time' and 'stop_time'.
    # Other trial-related information needs to be added in to the trial-table as additional columns (with column name
    # and column description)
    if acquisition.TrialSet & session_key:
        # Get trial descriptors from TrialSet.Trial and TrialStimInfo
        trial_columns = [{'name': tag,
                          'description': re.sub('\s+:|\s+', ' ', re.search(
                              f'(?<={tag})(.*)', str((acquisition.TrialSet.Trial * stimulation.TrialPhotoStimParam).heading)).group())}
                         for tag in (acquisition.TrialSet.Trial * stimulation.TrialPhotoStimParam).fetch(as_dict=True, limit=1)[0].keys()
                         if tag not in (acquisition.TrialSet.Trial & stimulation.TrialPhotoStimParam).primary_key + ['start_time', 'stop_time']]

        # Trial Events - discard 'trial_start' and 'trial_stop' as we already have start_time and stop_time
        trial_events = set(((acquisition.TrialSet.EventTime & session_key)
                            - [{'trial_event': 'trial_start'}, {'trial_event': 'trial_stop'}]).fetch('trial_event'))
        event_names = [{'name': e, 'description': d}
                       for e, d in zip(*(reference.ExperimentalEvent & [{'event': k}
                                                                        for k in trial_events]).fetch('event',
                                                                                                      'description'))]
        # Add new table columns to nwb trial-table for trial-label
        for c in trial_columns + event_names:
            nwbfile.add_trial_column(**c)

        photostim_tag_default = {tag: '' for tag in stimulation.TrialPhotoStimParam().fetch(as_dict=True, limit=1)[0].keys()
                                 if tag not in stimulation.TrialPhotoStimParam.primary_key}
        # Add entry to the trial-table
        for trial in (acquisition.TrialSet.Trial & session_key).fetch(as_dict=True):
            events = dict(zip(*(acquisition.TrialSet.EventTime & trial
                                & [{'trial_event': e} for e in trial_events]).fetch('trial_event', 'event_time')))
            photostim_tag = (stimulation.TrialPhotoStimParam & trial).fetch(as_dict=True)
            trial_tag_value = ({**trial, **events, **photostim_tag[0]}
                               if len(photostim_tag) == 1 else {**trial, **events, **photostim_tag_default})

            trial_tag_value['id'] = trial_tag_value['trial_id']  # rename 'trial_id' to 'id'
            # convert None to np.nan since nwb fields does not take None
            for k, v in trial_tag_value.items():
                trial_tag_value[k] = v if v is not None else np.nan
            [trial_tag_value.pop(k) for k in acquisition.TrialSet.Trial.primary_key]
            nwbfile.add_trial(**trial_tag_value)

        # =============== Write NWB 2.0 file ===============
        if save:
            save_file_name = ''.join([nwbfile.identifier, '.nwb'])
            if not os.path.exists(nwb_output_dir):
                os.makedirs(nwb_output_dir)
            if not overwrite and os.path.exists(os.path.join(nwb_output_dir, save_file_name)):
                return nwbfile
            with NWBHDF5IO(os.path.join(nwb_output_dir, save_file_name), mode = 'w') as io:
                io.write(nwbfile)
                print(f'Write NWB 2.0 file: {save_file_name}')

        return nwbfile


# ============================== EXPORT ALL ==========================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        nwb_outdir = sys.argv[1]
    else:
        nwb_outdir = default_nwb_output_dir

    for skey in acquisition.Session.fetch('KEY'):
        export_to_nwb(skey, nwb_output_dir = nwb_outdir, save = True)

