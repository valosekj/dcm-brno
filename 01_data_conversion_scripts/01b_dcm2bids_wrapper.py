#
# Convert dataset of DICOM images into BIDS using dcm2bids tool
#
# The script uses XLXS table (provided by '-xlsx-table') to fetch 'MR B1' and 'MR B2' columns and then runs dcm2bids
# for each subject
#
# NOTE: The script is run only on subjects with two MRI sessions (MR B1 and MR B2)
#
# USAGE:
#     01b_dcm2bids_wrapper.py
#           -path-in <PATH_TO_DATASET>/sourcedata
#           -path-out <PATH_TO_DATASET>
#           -xlsx-table table.xlsx
#           -dcm2bids-config dcm2bids_config.json
#
# ARGUMENTS:
#     -path-in              Path to the folder with dicom folders, e.g., <PATH_TO_DATASET>/sourcedata
#     -path-out             Path where BIDS dataset will be saved
#     -xlsx-table           Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns
#     -dcm2bids-config      Path to the dcm2bids_config.json file
#
# DEPENDENCIES:
#     pip install pandas
#     pip install openpyxl
#
# NOTE: The script requires the dcm2bids conda environment to be activated:
#    conda activate dcm2bids
#
# Authors: Jan Valosek
#

import os
import sys
import argparse
import logging

from utils import read_xlsx_file

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
        description='Convert dicom folders into BIDS format using dcm2bids tool.')
    parser.add_argument('-path-in',
                        help='Path to the folder with dicom folders, e.g., <PATH_TO_DATASET>/sourcedata', required=True)
    parser.add_argument('-path-out',
                        help='Path where BIDS dataset will be saved. Example: <PATH_TO_DATASET>', required=True)
    parser.add_argument('-xlsx-table',
                        help="Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns", required=True)
    parser.add_argument('-dcm2bids-config',
                        help='Path to the dcm2bids_config.json file', required=True)
    return parser


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Get abs path to the dcm2bids_config.json file
    config_path = os.path.abspath(args.dcm2bids_config)

    # Fetch input arguments
    dicom_folder_path = os.path.abspath(args.path_in)
    bids_folder = os.path.join(os.path.abspath(args.path_out))
    xlsx_file_path = os.path.abspath(args.xlsx_table)

    # Read "MR B1" and "MR B2" columns from the input xlsx file
    subject_df = read_xlsx_file(xlsx_file_path)

    # Keep only 'FUP MR měření B provedeno (ano/ne)' == 'ano' (yes)
    subject_df = subject_df[subject_df['FUP MR měření B provedeno (ano/ne)'] == 'ano']

    # Print number of rows (subjects)
    logger.info(f'Number of subjects: {len(subject_df)}')

    # Dump log file there
    fname_log = f'dcm2bids.log'
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(os.path.abspath(bids_folder), fname_log))
    logging.root.addHandler(fh)

    # Loop across rows
    for index, row in subject_df.iterrows():
        source_id_ses_01 = row['MR B1']
        source_id_ses_02 = row['MR B2']

        # Construct subject ID
        subject_id = source_id_ses_01 + source_id_ses_02

        # session 1
        sub_dicom_folder_path = os.path.join(dicom_folder_path, 'sub-' + source_id_ses_01)
        # Check if the dicom folder exists
        if os.path.exists(sub_dicom_folder_path):
            # Check if subject exists in the output BIDS folder, if so, skip
            if not os.path.exists(os.path.join(bids_folder, 'sub-' + subject_id, 'ses-' + source_id_ses_01)):
                # Construct shell command
                command = 'dcm2bids -d ' + sub_dicom_folder_path + \
                          ' -p ' + f'sub-{subject_id}' + \
                          ' -s ' + f'ses-{source_id_ses_01}' + \
                          ' -o ' + bids_folder + \
                          ' -c ' + config_path
                #   -d -- source DICOM directory
                #   -p -- output participant ID
                #   -s -- output session ID
                #   -c -- JSON configuration file
                #   -o -- output BIDS directory
                logger.info('Running dcm2bids for {}'.format(sub_dicom_folder_path))
                # Run shell command (NB - conda dcm2bids env has to be activated)
                os.system(command)
            else:
                logger.info('Subject {} already exists in {}'.format(source_id_ses_01, bids_folder))
        else:
            logger.info('Subject {} does not exist in {}'.format(source_id_ses_01, dicom_folder_path))

        # session 2
        sub_dicom_folder_path = os.path.join(dicom_folder_path,  'sub-' + source_id_ses_02)
        # Check if the dicom folder exists
        if os.path.exists(sub_dicom_folder_path):
            # Check if subject exists in the output BIDS folder, if so, skip
            if not os.path.exists(os.path.join(bids_folder, 'sub-' + subject_id, 'ses-' + source_id_ses_02)):
                # Construct shell command
                command = 'dcm2bids' + \
                          ' --dicom_dir ' + sub_dicom_folder_path + \
                          ' --participant ' + f'sub-{subject_id}' + \
                          ' --session ' + f'ses-{source_id_ses_02}' + \
                          ' --output_dir ' + bids_folder + \
                          ' --config ' + config_path
                #   --dicom_dir -- source DICOM directory
                #   --participant -- output participant ID
                #   --session -- output session ID
                #   --config -- JSON configuration file
                #   --output_dir -- output BIDS directory
                logger.info('Running dcm2bids for {}'.format(sub_dicom_folder_path))
                # Run shell command (NB - conda dcm2bids env has to be activated)
                os.system(command)
            else:
                logger.info('Subject {} already exists in {}'.format(source_id_ses_02, bids_folder))
        else:
            logger.info('Subject {} does not exist in {}'.format(source_id_ses_02, dicom_folder_path))


if __name__ == "__main__":
    main()
