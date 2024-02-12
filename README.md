# dcm-brno

## 0. Copy source subjects to /md3/dcm-brno/sourcedata

```console
./00a_copy_source_subjects.sh
```

## 0. DICOM to BIDS conversion

```console
$ conda activate dcm2bids
$ python 00b_dcm2bids_wrapper.py -path-in /md3/dcm-brno/sourcedata -path-out /md3/dcm-brno -xlsx-table /md3/dcm-brno/code/LAP_longitudinal_anatomical_parametres.xlsx -dcm2bids-config dcm2bids_config.json
```

## 0. Download derivatives

```console
$ cd /md3/dcm-brno
$ git clone https://github.com/valosekj/dcm-brno_derivatives
$ mv dcm-brno_derivatives derivatives
```

## 0. Copy images for subjects with multiple runs

Copy images for subjects with multiple runs (context: [T2w](https://github.com/valosekj/dcm-brno/issues/2), 
[T2star](https://github.com/valosekj/dcm-brno/issues/3)):

- commands T2w: https://github.com/valosekj/dcm-brno/issues/2

## 1. Process data

Process data with [the process_data.sh script](process_data.sh). The script is run across all subjects in the 
BIDS dataset using the `sct_run_batch` wrapper script:

```console
sct_run_batch -config process_data_config.json
```

## 2. Do manual corrections

Intervertebral disc labels:

```console
$ python manual_correction.py -path-img data_to_correct -config dcm-brno_2023-11-11_disc_label_to_correct.yml -path-out dcm-brno/derivatives/labels
```
