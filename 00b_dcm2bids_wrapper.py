#
# Convert dataset of DICOM images into BIDS using dcm2bids tool
# The script accepts DICOM images stored across several directories, see -path-in flag
#
# The script utilizes the participant.tsv file
# The participant.tsv can be created using create_participants_table.py script
#
# USAGE:
#     00b_dcm2bids_wrapper.py -path-in <PATH_TO_DATASET>/sourcedata
#                         -path-out <PATH_TO_DATASET>
#                         -xlsx-table table.xlsx
# ARGUMENTS:
#     -path-in              Path to the folder with dicom folders, e.g., <PATH_TO_DATASET>/sourcedata
#     -path-out             Path where BIDS dataset will be saved
#     -participant-table    Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns
#
#
# Authors: Jan Valosek
#

import os
import argparse
import pandas as pd


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
    subject_df = pd.read_excel(xlsx_file_path, sheet_name='LAP', usecols=['MR B1', 'MR B2'])

    # Loop across rows
    for index, row in subject_df.iterrows():
        source_id_ses_01 = row['MR B1']
        source_id_ses_02 = row['MR B2']

        # Construct subject ID
        subject_id = source_id_ses_01 + source_id_ses_02

        # session 1
        sub_dicom_folder_path = os.path.join(dicom_folder_path, 'sub-' + source_id_ses_01)
        # Check if subject exists
        if os.path.exists(sub_dicom_folder_path):
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
            print('Running dcm2bids for {}'.format(sub_dicom_folder_path))
            # Run shell command (NB - conda dcm2bids env has to be activated)
            os.system(command)
        else:
            print('Subject {} does not exist in {}'.format(source_id_ses_01, dicom_folder_path))

        # session 2
        sub_dicom_folder_path = os.path.join(dicom_folder_path,  'sub-' + source_id_ses_02)
        # Check if subject exists
        if os.path.exists(sub_dicom_folder_path):
            # Construct shell command
            command = 'dcm2bids -d ' + sub_dicom_folder_path + \
                      ' -p ' + f'sub-{subject_id}' + \
                      ' -s ' + f'ses-{source_id_ses_02}' + \
                      ' -o ' + bids_folder + \
                      ' -c ' + config_path
            #   -d -- source DICOM directory
            #   -p -- output participant ID
            #   -s -- output session ID
            #   -c -- JSON configuration file
            #   -o -- output BIDS directory
            print('Running dcm2bids for {}'.format(sub_dicom_folder_path))
            # Run shell command (NB - conda dcm2bids env has to be activated)
            os.system(command)
        else:
            print('Subject {} does not exist in {}'.format(source_id_ses_02, dicom_folder_path))


if __name__ == "__main__":
    main()
