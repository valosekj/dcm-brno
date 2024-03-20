"""
Load "csa-SC_T2w_perlevel" CSV file with shape metrics perlevel located under "-path-in/results" and generate group
figures comparing sessions 1 vs session 2.

Currently, the figures are generated for VertLevel 2 only.
Two figures are generated for each metric:
    - one for subjects without surgery
    - one for subjects with surgery

The figures are saved in "-path-out".
"""

import os
import re
import sys
import argparse
import logging
import yaml

import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

from utils import read_xlsx_file

METRICS = ['MEAN(area)', 'MEAN(diameter_AP)', 'MEAN(diameter_RL)', 'MEAN(compression_ratio)', 'MEAN(eccentricity)',
           'MEAN(solidity)']

METRICS_DTYPE = {
    'MEAN(diameter_AP)': 'float64',
    'MEAN(area)': 'float64',
    'MEAN(diameter_RL)': 'float64',
    'MEAN(eccentricity)': 'float64',
    'MEAN(solidity)': 'float64'
}

METRIC_TO_AXIS = {
    'MEAN(diameter_AP)': 'AP Diameter [mm]',
    'MEAN(area)': 'Cross-Sectional Area [mm²]',
    'MEAN(diameter_RL)': 'Transverse Diameter [mm]',
    'MEAN(eccentricity)': 'Eccentricity [a.u.]',
    'MEAN(solidity)': 'Solidity [%]',
    'MEAN(compression_ratio)': 'Compression Ratio [a.u.]',
}

TITLE_FONT_SIZE = 16
LABELS_FONT_SIZE = 14
TICKS_FONT_SIZE = 12

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
        description='Load "csa-SC_T2w_perlevel" CSV file with shape metrics perlevel located under "-path-in/results" '
                    'and generate group figure comparing sessions 1 vs session 2.'
                    'The figure is saved in "-path-out".')
    parser.add_argument('-path-in', required=True,
                        help='Path to the "csa-SC_T2w_perlevel" CSV file produced by sct_run_batch. '
                             'Example: "/Users/user/results/dcm-brno_2024-02-19/results/"csa-SC_T2w_perlevel"')
    parser.add_argument('-path-out', required=True,
                        help='Path to the output directory where the group figure will be saved. '
                             'Example: "/Users/user/results/dcm-brno_2024-02-19/figure_T2w_C2"')
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


def read_metrics(path_in, subject_df):
    # Read the "csa-SC_T2w_perlevel" CSV file
    df_metrics = pd.read_csv(path_in, dtype=METRICS_DTYPE)

    # Add columns 'SessionID', 'SubjectID', and 'Session' to df_metrics with dtype string
    df_metrics['SessionID'] = ''
    df_metrics['SubjectID'] = ''
    df_metrics['Session'] = ''
    # Add column 'Surgery' to df_metrics with dtype bool
    df_metrics['Surgery'] = False

    # Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
    df_metrics['MEAN(compression_ratio)'] = df_metrics['MEAN(diameter_AP)'] / df_metrics['MEAN(diameter_RL)']

    # Drop Timestamp, SCT Version, and DistancePMJ columns
    df_metrics = df_metrics.drop(columns=['Timestamp', 'SCT Version', 'DistancePMJ'])

    # Keep only VertLevel 2
    df_metrics = df_metrics[df_metrics['VertLevel'] == 2]

    # Add new columns 'SessionID', 'SubjectID', and 'Session' to df_metrics
    # Loop across rows in df_metrics
    for index, row in df_metrics.iterrows():
        filename = row['Filename']
        # Extract session_id, e.g., 'ses-1234B' from the filename using regular expression
        session_id = re.search(r'ses-\d{4}[A-Z]', filename).group(0)
        session_id = session_id.replace('ses-', '')  # Remove 'ses-' prefix
        df_metrics.at[index, 'SessionID'] = session_id

        # Extract subject_id, e.g., 'sub-1836B6029B' from the filename using regular expression
        # NOTE: subject_id is needed for 'sns.lineplot' to connect points of the same subject between sessions
        subject_id = re.search(r'sub-\d{4}[A-Z]\d{4}[A-Z]', filename).group(0)
        df_metrics.at[index, 'SubjectID'] = subject_id

        # Check whether the session_id is in MR B1 or MR B2 column in the subject_df
        if session_id in subject_df['MR B1'].values:
            # Add a new column 'Session' with value 'MR B1'
            df_metrics.at[index, 'Session'] = 'MR B1'
        elif session_id in subject_df['MR B2'].values:
            # Add a new column 'Session' with value 'MR B2'
            df_metrics.at[index, 'Session'] = 'MR B2'

        # Check if the session_id had surgery (meaning that the 'Datum operace' column contains a date)
        if (subject_df.loc[subject_df['MR B1'] == session_id, 'Datum operace'].notnull()).any():
            df_metrics.at[index, 'Surgery'] = True
        elif (subject_df.loc[subject_df['MR B2'] == session_id, 'Datum operace'].notnull()).any():
            df_metrics.at[index, 'Surgery'] = True
        else:
            df_metrics.at[index, 'Surgery'] = False

    return df_metrics


def generate_figure(df_metrics, path_out):
    """
    Generate 3x2 group figure comparing sessions 1 vs session2 for 6 shape metrics.
    """

    # Generate 3x2 group figure comparing sessions 1 vs session2 for 6 shape metrics
    mpl.rcParams['font.family'] = 'Arial'

    # Loop across no surgery and surgery
    for surgery in [False, True]:

        num_of_subjects = len(df_metrics[df_metrics['Surgery'] == surgery]['SubjectID'].unique())
        logger.info(f"Surgery: {surgery} , number of subjects: {num_of_subjects}")

        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        axs = axes.ravel()
        # Loop across metrics
        for index, metric in enumerate(METRICS):
            kwargs = dict(x='Session', y=metric, ax=axs[index], data=df_metrics[df_metrics['Surgery'] == surgery])
            # Plot the violin plot
            # NOTE: I'm passing hue='Session' (i.e., the same as x='Session') to prevent the following warning:
            #   "Passing `palette` without assigning `hue` is deprecated and will be removed in v0.14.0. Assign the `x`
            #    variable to `hue` and set `legend=False` for the same effect."
            sns.violinplot(palette="Blues", hue='Session', legend=False, **kwargs)
            # Plot swarmplot on top of the violin plot
            sns.swarmplot(color='black', alpha=0.5, **kwargs)
            # Plot lineplot connecting points of the same subject between sessions
            sns.lineplot(units='SubjectID', estimator=None, legend=False, linewidth=0.5, color='black', alpha=0.5,
                         **kwargs)

            # Invert x-axis to have MR B1 on the left and MR B2 on the right
            axs[index].invert_xaxis()

            # Set main title with number of subjects
            fig.suptitle(f'Shape metrics at C2 level (i.e., above the compression)\n'
                         f'Number of subjects: {num_of_subjects}, '
                         f'Surgery: {surgery}',
                         fontsize=TITLE_FONT_SIZE)

            axs[index].set_xlabel('')
            axs[index].set_ylabel(METRIC_TO_AXIS[metric], fontsize=LABELS_FONT_SIZE)
            axs[index].tick_params(axis='both', which='major', labelsize=TICKS_FONT_SIZE)

        # Save the figure
        fig.tight_layout()
        fname_out = os.path.join(path_out, f'group_violin_plots_sessions1_vs_session2_surgery_{surgery}.png')
        fig.savefig(fname_out, dpi=300)
        plt.close(fig)
        logger.info(f"Group figure saved to {fname_out}")


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    path_in = os.path.abspath(args.path_in)
    path_out = os.path.abspath(args.path_out)

    # Check if the path to the input CSV file is valid
    if not os.path.isfile(path_in):
        print(f"File {path_in} does not exist.")
        sys.exit(1)

    # Create the output directory if it does not exist
    if not os.path.exists(path_out):
        os.makedirs(path_out)

    # Dump log file there
    fname_log = os.path.join(path_out, 'generate_group_violion_plots_sessions1_vs_session2.log')
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
    logger.info(f'Clinical table: Number of subjects with two sessions: {len(subject_df)}')

    # Read the exclude.yml file listing subjects to be excluded (due to e.g., poor image quality)
    exclude_yml_path = f"{os.getenv('HOME')}/code/dcm-brno/exclude.yml"
    exclude_list = read_exclude_yml(exclude_yml_path)

    df_metrics = read_metrics(path_in, subject_df)
    # Get number of subjects based on unique SubjectID
    num_of_subjects = len(df_metrics['SubjectID'].unique())
    logger.info(f'CSV file with metrics: Number of subjects: {num_of_subjects}')

    # Exclude subjects from df_metrics based on exclude_list
    df_metrics = df_metrics[~df_metrics['SubjectID'].isin(exclude_list)]
    # Get number of subjects based on unique SubjectID after excluding subjects
    num_of_subjects = len(df_metrics['SubjectID'].unique())
    logger.info(f'CSV file with metrics after excluding subjects: Number of subjects: {num_of_subjects}')

    generate_figure(df_metrics, path_out)


if __name__ == "__main__":
    main()
