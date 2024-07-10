#
# Copy dicom data from "DCM-PRO", "DCM-PRO_longitudinal", "DCM-PRO_NOLOST", and "DCM-PRO_NOLOST_2024-02-08"
# (all located at /md3) to "dcm-brno/sourcedata" (also located at /md3).
#
# Authors: Jan Valosek
#

import os
import sys
import argparse
import pandas as pd
import logging
import shutil

from utils import read_xlsx_file

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
    parser.add_argument('-xlsx-table',
                        help="Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns", required=True)

    return parser


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    xlsx_file_path = os.path.abspath(args.xlsx_table)

    # Create the necessary directory if it doesn't exist
    os.makedirs(os.path.join(DISC, 'dcm-brno/sourcedata'), exist_ok=True)

    # Dump log file there
    fname_log = f'copy_source_data.log'
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(DISC, 'dcm-brno/sourcedata', fname_log))
    logging.root.addHandler(fh)

    # Read "MR B1" and "MR B2" columns from the input xlsx file
    subject_df = read_xlsx_file(xlsx_file_path)

    # Keep only 'FUP MR měření B provedeno (ano/ne)' == 'ano' (yes)
    subject_df = subject_df[subject_df['FUP MR měření B provedeno (ano/ne)'] == 'ano']

    # Print number of rows (subjects)
    logger.info(f'Number of subjects: {len(subject_df)}')

    list_of_subjects = pd.concat([subject_df['MR B1'], subject_df['MR B2']]).dropna().reset_index(drop=True)

    # Iterate through the subjects
    for subject in list_of_subjects:
        # Iterate through the folders
        for folder in FOLDERS:
            source_path = os.path.join(DISC, folder, 'dicom', f'sub-{subject}')
            dest_path = os.path.join(DISC, 'dcm-brno', 'sourcedata', f'sub-{subject}')
            # Copy the subject data if it does not exist in dcm-brno/sourcedata
            if os.path.isdir(source_path) and not os.path.isdir(dest_path):
                logger.info(f"{subject} exists in {folder}.")
                shutil.copytree(source_path, dest_path)

    # Check whether all subjects from list_of_subjects were copied to dcm-brno/sourcedata
    for subject in list_of_subjects:
        if not os.path.isdir(os.path.join(DISC, 'dcm-brno', 'sourcedata', f'sub-{subject}')):
            logger.info(f"ERROR: {subject} was not copied to dcm-brno/sourcedata.")


if __name__ == "__main__":
    main()
