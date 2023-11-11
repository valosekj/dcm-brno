# dcm-brno

## 0. Copy source subjects to /md3/dcm-brno/sourcedata

```console
./copy_source_subjects.sh
```

## 0. DICOM to BIDS conversion

```console
$ conda activate dcm2bids
$ python dcm2bids_wrapper.py -path-in /md3/dcm-brno/sourcedata -path-out /md3/dcm-brno -xlsx-table /md3/dcm-brno/code/LAP_longitudinal_anatomical_parametres.xlsx -dcm2bids-config dcm2bids_config.json
```

## 1. Process data

Process data with [the process_data.sh script](process_data.sh). The script is run across all subjects in the 
BIDS dataset using the `sct_run_batch` wrapper script:

```console
sct_run_batch -config process_data_config.json
```