# Data conversion scripts

## 01a. Copy DICOM files to /md3/dcm-brno/sourcedata

Copy dicom data from different folders ("DCM-PRO", "DCM-PRO_longitudinal", "DCM-PRO_NOLOST", and 
"DCM-PRO_NOLOST_2024-02-08"), all located at `/md3`, to `/md3dcm-brno/sourcedata`.

DCM and NMDC patients with two sessions:

```console
python 01a_copy_source_subjects.py -xlsx-table <XLSX_TABLE>
```

HC used the GM segmentation study (these subjects have only one session):

```console
python 01a_copy_source_subjects_HC.py
```

> [!NOTE]
> No arguments are needed as the default paths are set in the script.

## 01b. DICOM to BIDS conversion

> [!NOTE]
> When new subjects are added, you can simply rerun the scripts. They will skip subjects that are already processed.
> If you need to force the conversion for some subjects, remove the corresponding folders from the BIDS dataset 
> (`/md3/dcm-brno`), then rerun the conversion script.

> [!NOTE]
> T2star: we use the image with 2.5mm slice thickness. And we do NOT use the image with 3.0 mm slice thickness.
> DWI: we use ZOOMit sequence. And we do NOT use RESOLVE sequence.

DCM and NMDC patients with two sessions:

- for patients with two sessions, XLSX_TABLE is used to fetch sessions for each subject

```console
$ conda activate dcm2bids
$ python 01b_dcm2bids_wrapper.py -path-in /md3/dcm-brno/sourcedata -path-out /md3/dcm-brno -xlsx-table <XLSX_TABLE> -dcm2bids-config dcm2bids_config.json
```

HC used the GM segmentation study:

- for HC, TRANSCRIPT_TABLE is used to fetch SUB_ID and DICOM_ID pairs; for details see the script description

```console
$ conda activate dcm2bids
$ python 01b_dcm2bids_wrapper_HC.py -path-in /md3/dcm-brno/sourcedata/ -path-out /md3/dcm-brno -transcript-table <TRANSCRIPT_TABLE> -dcm2bids-config dcm2bids_config.json
```

## 01c. Download derivatives

```console
$ cd /md3/dcm-brno
$ git clone https://github.com/valosekj/dcm-brno_derivatives
$ mv dcm-brno_derivatives derivatives
```

## 01d. Deal with images with multiple runs

Copy images for subjects with multiple runs:

- commands T2w: https://github.com/valosekj/dcm-brno/issues/2
- commands T2star: https://github.com/valosekj/dcm-brno/issues/3
- commands T1w: https://github.com/valosekj/dcm-brno/issues/12
