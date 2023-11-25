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

## 0. Create symlinks for subjects with multiple runs

Create symlinks for subjects with multiple runs (context: [T2w](https://github.com/valosekj/dcm-brno/issues/2), 
[T2star](https://github.com/valosekj/dcm-brno/issues/3)):

```console
# T2w
$ cd /md3/dcm-brno/sub-2315B4686B/ses-4686B/anat/
$ ln -s  sub-2315B4686B_ses-4686B_run-01_T2w.nii.gz sub-2315B4686B_ses-4686B_T2w.nii.gz
$ cd /md3/dcm-brno/sub-2321B6243B/ses-6243B/anat/
$ ln -s sub-2321B6243B_ses-6243B_run-02_T2w.nii.gz sub-2321B6243B_ses-6243B_T2w.nii.gz
$ cd /md3/dcm-brno/sub-2407B5757B/ses-2407B/anat/
$ ln -s sub-2407B5757B_ses-2407B_run-02_T2w.nii.gz sub-2407B5757B_ses-2407B_T2w.nii.gz

# T2star
$ cd /md3/dcm-brno/sub-2741B4963B/ses-4963B/anat/
$ ln -s sub-2741B4963B_ses-4963B_run-02_T2star.nii.gz sub-2741B4963B_ses-4963B_T2star.nii.gz
```

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
