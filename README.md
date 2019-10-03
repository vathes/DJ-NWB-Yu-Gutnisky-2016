# Yu-Gutnisky-2016 - A DataJoint example
This notebook presents data and results associated with the following papers:

>Jianing Yu, Diego A Gutnisky, S Andrew Hires & Karel Svoboda1. "Layer 4 fast-spiking interneurons filter thalamocortical signals during active somatosensation" (2016) Nat Neurosci (https://dx.doi.org/10.1038/nn.4412)

In this study, membrane potential and spikes recordings were performed ventral posteromedial nucleus (VPM) neurons and layer 4 (L4) neurons of the barrel cortex, during an object-locating with whiskers task. The study reported a movement-related suppression mechanism of the thalamocortical circuit. Specifically, the L4 fast-spiking interneurons, inherited from the sensory input driven VPM activity, suppressed movement-related activity of the L4 excitatory neurons. This movement-related suppression thus improved selectivity for touch-related information during active tactile sensation.

A ***DataJoint*** data pipeline has been constructed for this study, with the presented data ingested into this pipeline. This notebook demonstrates the queries, processing, and reproduction of several figures from the paper. From the pipeline, export capability to NWB 2.0 format is also available.

## About the data

The dataset comprises of membrane potential, extracellular recordings and spike sorted results of the mouse's VPM and L4 neurons a whisker-based object locating task. The behavior data includes detailed description of the trial structure (e.g. trial timing, trial instruction, trial response, etc.), lick trace data and a variety of whisker movement related tracking data: whisker angle, whisker curavture, touch times, etc. Trial information also includes optogenetic photostimulation details.

Original data shared here: http://crcns.org/data-sets/ssc/ssc-7

The data in original NWB 1 format (.nwb) have been ingested into a DataJoint data pipeline presented below. This notebook demonstrates the queries, processing, and reproduction of several figures from the paper.

Data are also exported into NWB 2.0 format. 

## Design DataJoint data pipeline 
This repository will contain the Python 3.6+ code of the DataJoint data pipeline design for this dataset, as well as scripts for data ingestions and visualization

## Conversion to NWB 2.0
This repository will contain the Python 3.6+ code to convert the DataJoint pipeline into NWB 2.0 format (See https://neurodatawithoutborders.github.io/)
See NWB export code [here](../scripts/datajoint_to_nwb.py)

## Data Pipeline Architecture
![ERD of the entire data pipeline](images/all_erd.png)


