import os
import sys
import argparse
import subprocess
import logging
import yaml

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
        description='Loop across CSV files with shape metrics in PAM50 space located under "-path-in/results" and'
                    'generate figures for each subject. Each figure contains two subplots, one for each session. '
                    'The figures are saved in "-path-in/figures". If the subject had surgery, the figures are saved in '
                    '"-path-in/figures/surgery". '
                    'The script uses the 02b_generate_figures_PAM50_two_sessions.py script.')
    parser.add_argument('-path-in', required=True,
                        help='Path to the folder produced by sct_run_batch. '
                             'Example: "/Users/user/results/dcm-brno_2024-02-19"')
    parser.add_argument('-xlsx-table',
                        help="Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns", required=True)
    return parser


def read_exclude_yml(exclude_yml_path):
    """
    Read the exclude.yml file and return a list of subjects to be excluded.

    Args:
    exclude_yml_path (str): Path to the exclude.yml file.

    Returns:
    list: List of subjects to be excluded.
    """
    # Read the exclude.yml file using pyaml
    with open(exclude_yml_path, 'r') as stream:
        exclude_dict = yaml.safe_load(stream)

    # Extract the list of subjects to be excluded
    exclude_list = exclude_dict['T2w']
    # Keep only subject IDs (e.g., 'sub-2390B4949B'), i.e., remove session IDs (e.g., '2390B', '4949B')
    exclude_list = [subject[:14] for subject in exclude_list]

    return exclude_list


def loop_across_subjects_to_generate_figure(path_results, subject_df, exclude_list):
    """
    Loops across subjects to generate figures based on their per-slice PAM50 CSV files.
    If the subject had surgery, the figures are saved in the "surgery" subfolder.

    Args:
    path_results (str): Path to the directory containing results.
    subject_df (pd.DataFrame): DataFrame with 'MR B1', 'MR B2', and 'Datum operace' columns.
    exclude_list (list): List of subjects to be excluded.
    """

    # Loop through each perslice_PAM50.csv file in the results directory
    for file in sorted(os.listdir(f"{path_results}/results")):
        if "perslice_PAM50.csv" in file:
            filename = file
            subject = filename[:14]         # e.g., 'sub-2390B4949B'
            session1 = filename[4:9]        # e.g., '2390B'
            session2 = filename[9:14]       # e.g., '4949B'

            logger.info(f"Processing {file}.")

            # Check if the subject is listed in the exclusion list, if so, skip it
            if subject == 'sub-2296B4806B':
                print('Here')
            if subject in exclude_list:
                logger.info(f"Subject {subject} is listed in the exclusion list. Skipping.")
                continue

            # Check if the subject had surgery (meaning that the 'Datum operace' column contains a date)
            if (subject_df.loc[subject_df['MR B1'] == session1, 'Datum operace'].notnull()).any():
                path_out = f"{path_results}/figures/surgery"
            else:
                path_out = f"{path_results}/figures"

            # Check if the figure (e.g., 1836B6029B_T2w_lineplot_PAM50.png) already exists, if so, skip it
            # The figure might indeed exist, because we are iterating across CSV files for all subjects, meaning
            # that the figure might have been already generated in the previous run
            if os.path.exists(f"{path_results}/figures/{session1}{session2}_T2w_lineplot_PAM50.png"):
                logger.info(f"Figure {session1}{session2}_T2w_lineplot_PAM50.png already exists. Skipping.")
                continue
            else:
                logger.info(f"Creating figure -- Subject: {subject}, Session 1: {session1}, Session 2: {session2}.")
                subprocess.run([
                    "python", f"{os.getenv('HOME')}/code/dcm-brno/scripts/02b_generate_figures_PAM50_two_sessions.py",
                    "-path-HC", f"{os.getenv('SCT_DIR')}/data/PAM50_normalized_metrics",
                    "-ses1", f"{path_results}/results/{subject}_ses-{session1}_T2w_metrics_perslice_PAM50.csv",
                    "-ses2", f"{path_results}/results/{subject}_ses-{session2}_T2w_metrics_perslice_PAM50.csv",
                    "-path-out", f"{path_out}"
                ])
                logger.info(f"Figure {session1}{session2}_T2w_lineplot_PAM50.png has been generated.")


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    path_in = os.path.abspath(args.path_in)

    # Check if the path to the results is valid
    if not os.path.exists(path_in):
        print(f"Path {path_in} does not exist.")
        sys.exit(1)

    # Dump log file there
    fname_log = f'generate_PAM50_figures.log'
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(path_in, fname_log))
    logging.root.addHandler(fh)

    xlsx_file_path = os.path.abspath(args.xlsx_table)
    # Check if the path to the xlsx file is valid
    if not os.path.exists(xlsx_file_path):
        print(f"Path {xlsx_file_path} does not exist.")
        sys.exit(1)

    # Read the xlsx file
    logger.info(f"Reading {xlsx_file_path}.")
    subject_df = read_xlsx_file(xlsx_file_path, columns_to_read=['FUP MR měření B provedeno (ano/ne)',
                                                                 'Datum operace', 'MR B1', 'MR B2'])

    # Keep only 'FUP MR měření B provedeno (ano/ne)' == 'ano' (yes)
    subject_df = subject_df[subject_df['FUP MR měření B provedeno (ano/ne)'] == 'ano']
    # Print number of rows (subjects)
    logger.info(f'Number of subjects with two sessions: {len(subject_df)}')

    # Read the exclude.yml file listing subjects to be excluded (due to e.g., poor image quality)
    exclude_yml_path = f"{os.getenv('HOME')}/code/dcm-brno/exclude.yml"
    exclude_list = read_exclude_yml(exclude_yml_path)

    loop_across_subjects_to_generate_figure(path_in, subject_df, exclude_list)


if __name__ == "__main__":
    main()


