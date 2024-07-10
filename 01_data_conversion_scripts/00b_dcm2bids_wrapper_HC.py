#
# Convert dataset of DICOM images into BIDS using dcm2bids tool
#
# NOTE: the script is designed to selectively convert only the HC subjects used for the GM segmentation study.
# Subject IDs (SUB_ID) of these subjects are fetched from /md2/T1w_CNN/derivatives/labels. Then, the subject IDs are
# converted to the source IDs (DICOM_ID) using the transcript table (`-transcript-table` argument). Finally, the script
# runs dcm2bids for each subject.
#
# USAGE:
#     00b_dcm2bids_wrapper_HC.py
#           -path-in <PATH_TO_DATASET>/sourcedata       # e.g., /md3/dcm-brno/sourcedata
#           -path-out <PATH_TO_DATASET>                 # e.g., /md3/dcm-brno
#           -transcript-table table.tsv
#           -dcm2bids-config dcm2bids_config.json
#
# ARGUMENTS:
#     -path-in              Path to the folder with dicom folders, e.g., <PATH_TO_DATASET>/sourcedata
#     -path-out             Path where BIDS dataset will be saved
#     -transcript-table     Path to the transcript table file containing 'DICOM_ID' and 'SUB_ID' columns
#     -dcm2bids-config      Path to the dcm2bids_config.json file
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
import pandas as pd

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
    parser.add_argument('-transcript-table',
                        help="Path to the transcript table file containing 'DICOM_ID' and 'SUB_ID' columns",
                        required=True)
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
    transcript_table_path = os.path.abspath(args.transcript_table)

    # Dump log file there
    fname_log = f'dcm2bids_HC_' + pd.Timestamp.now().strftime("%Y%m%d-%H%M%S") + '.log'
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(dicom_folder_path,fname_log))
    logging.root.addHandler(fh)

    # Get the list of HC subjects in the input folder
    in_path = os.path.abspath('/md2/T1w_CNN/derivatives/labels')
    list_of_subjects = os.listdir(in_path)
    # Sort the list
    list_of_subjects.sort()
    logger.info(f'The following subjects found in {in_path}: {list_of_subjects}')

    # Print number of subjects
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

        # Path to the dicom folder of the subject
        sub_dicom_folder_path = os.path.join(dicom_folder_path, f'sub-{subject}')
        # Check if the dicom folder exists
        if os.path.exists(sub_dicom_folder_path):
            # Check if subject exists in the output BIDS folder, if so, skip
            if not os.path.exists(os.path.join(bids_folder, f'sub-{subject}', f'ses-{subject}')):
                # Construct shell command
                command = 'dcm2bids -d ' + sub_dicom_folder_path + \
                          ' -p ' + f'sub-{subject}' + \
                          ' -s ' + f'ses-{subject}' + \
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
                logger.info('Subject {} already exists in {}'.format(subject, bids_folder))
        else:
            logger.info('Subject {} does not exist in {}'.format(subject, dicom_folder_path))


if __name__ == "__main__":
    main()
