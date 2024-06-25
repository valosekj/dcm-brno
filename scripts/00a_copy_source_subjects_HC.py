#
# Copy dicom data from "DCM-PRO", "DCM-PRO_longitudinal", "DCM-PRO_NOLOST", and "DCM-PRO_NOLOST_2024-02-08"
# (all located at /md3) to "dcm-brno/sourcedata" (also located at /md3).
#
# NOTE: the script is designed to selectively copy only the HC subjects used for the GM segmentation study. Subject IDs
# (SUB_ID) of these subjects are fetched from /md2/T1w_CNN/derivatives/labels. Then, the subject IDs are converted to
# the source IDs (DICOM_ID) using the transform table (`-transcript-table` argument).
#
# NOTE: The HC subjects also have manual GT segmentations. These segmentations are renamed and copied to
# dcm-brno/derivatives/labels.
#
# Authors: Jan Valosek
#

import os
import sys
import argparse
import pandas as pd
import logging
import shutil

DISC = '/md3'

# Folders with the dicom data
FOLDERS = [
    "DCM-PRO",
    "DCM-PRO_longitudinal",
    "DCM-PRO_NOLOST",
    "DCM-PRO_NOLOST_2024-02-08"
]

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # default: logging.DEBUG, logging.INFO
hdlr = logging.StreamHandler(sys.stdout)
logging.root.addHandler(hdlr)


def get_parser():
    """
    Input argument parser function
    """
    parser = argparse.ArgumentParser(
        description='Copy dicom data into dcm-brno/sourcedata.')
    parser.add_argument('-hc-path',
                        help="Abs path to the 'derivatives/labels' folder of HC subjects to copy",
                        default='/md2/T1w_CNN/derivatives/labels',
                        required=False)
    parser.add_argument('-transcript-table',
                        help="Path to the transcript table file containing 'DICOM_ID' and 'SUB_ID' columns",
                        default='/md2/DCM-PRO/transcript_table.tsv',
                        required=False)

    return parser


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    in_path = os.path.abspath(args.hc_path)
    transcript_table_path = os.path.abspath(args.transcript_table)

    # Create the necessary directory if it doesn't exist
    os.makedirs(os.path.join(DISC, 'dcm-brno/sourcedata'), exist_ok=True)

    # Dump log file there
    fname_log = f'copy_source_data' + pd.Timestamp.now().strftime("%Y%m%d-%H%M%S") + '.log'
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(DISC, 'dcm-brno/sourcedata', fname_log))
    logging.root.addHandler(fh)

    # Get the list of HC subjects in the input folder
    list_of_subjects = os.listdir(in_path)
    # Sort the list
    list_of_subjects.sort()
    logger.info(f'The following subjects found in {in_path}: {list_of_subjects}')

    # Print number of rows (subjects)
    logger.info(f'Number of subjects in "{in_path}": {len(list_of_subjects)}')

    # Read the transcript table if it exists
    if os.path.isfile(transcript_table_path):
        transcript_table = pd.read_csv(transcript_table_path, sep='\t')
        logger.info(f"Transcript table read from {transcript_table_path}")
    else:
        logger.info(f"ERROR: The transcript table {transcript_table_path} does not exist.")
        sys.exit(1)

    # Iterate through the subjects found in the input folder
    for subject_tmp in list_of_subjects:
        subject = transcript_table[transcript_table['SUB_ID'] == subject_tmp]['DICOM_ID'].values[0]
        logger.info(f'Processing: {subject_tmp}, {subject}')
        # Iterate through the folders
        for folder in FOLDERS:
            source_path = os.path.join(DISC, folder, 'dicom', f'sub-{subject}')
            dest_path = os.path.join(DISC, 'dcm-brno', 'sourcedata', f'sub-{subject}')
            # Copy the subject data if it does not exist in dcm-brno/sourcedata
            if os.path.isdir(source_path) and not os.path.isdir(dest_path):
                # Copy source images
                logger.info(f"{subject} exists in {os.path.join(DISC, folder)} --> copying the subject...")
                shutil.copytree(source_path, dest_path)
                # Copy derivatives/labels
                derivatives_path = os.path.join(in_path, subject_tmp, 'ses-01', 'anat')
                dest_path = os.path.join(DISC, 'dcm-brno', 'derivatives', 'labels', f'sub-{subject}', f'ses-{subject}',
                                         'anat')
                os.makedirs(dest_path, exist_ok=True)
                # Get all files under derivatives_path
                files = [f for f in os.listdir(derivatives_path) if os.path.isfile(os.path.join(derivatives_path, f))]
                # Copy the files from '-hc-path' to dcm-brno/derivatives/labels
                for file in files:
                    # Copy and rename
                    # Example: sub-0001_ses-01_T1w_gmseg-manual.nii.gz --> sub-2613B_ses-2613B_T1w_gmseg-manual.nii.gz
                    out_file = (file.replace(f'{subject_tmp}', f'sub-{subject}').
                                replace(f'ses-01', f'ses-{subject}'))
                    print(out_file)
                    shutil.copy(os.path.join(derivatives_path, file),
                                os.path.join(dest_path, out_file))
                    logger.info(f"Copying {derivatives_path}/{file} to {dest_path}/{out_file}")

    # Check whether all subjects from list_of_subjects were copied to dcm-brno/sourcedata
    for subject_tmp in list_of_subjects:
        subject = transcript_table[transcript_table['SUB_ID'] == subject_tmp]['DICOM_ID'].values[0]
        if not os.path.isdir(os.path.join(DISC, 'dcm-brno', 'sourcedata', f'sub-{subject}')):
            logger.info(f"ERROR: {subject} was not copied to dcm-brno/sourcedata")


if __name__ == "__main__":
    main()
