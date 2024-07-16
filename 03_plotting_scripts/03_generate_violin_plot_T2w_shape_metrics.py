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
import sys
import argparse
import logging

import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

from scipy.stats import normaltest, ttest_rel, wilcoxon

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import read_xlsx_file, read_yaml_file, fetch_participant_and_session, format_pvalue

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

# NOTE: for some reason, the color order must be swapped here (compared to the DTI plotting script). Maybe due to the
# `.invert_xaxis` method?
color_palette = [(0.984313725490196, 0.5019607843137255, 0.4470588235294118),       # red
                 (0.5529411764705883, 0.8274509803921568, 0.7803921568627451)]     # green

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
                    'The figure will be saved in the same directory as the input CSV file.')
    parser.add_argument(
        '-i',
        metavar="<file>",
        required=True,
        type=str,
        help='Path to the "csa-SC_T2w_perlevel" CSV file produced by sct_run_batch. '
             'Example: "/Users/user/results/dcm-brno_2024-02-19/results/"csa-SC_T2w_perlevel"')
    parser.add_argument(
'-xlsx-table',
        metavar="<file>",
        required=True,
        type=str,
        help="Path to the table.xlsx file containing 'MR B1' and 'MR B2' columns")
    parser.add_argument(
        '-yml-file',
        metavar="<file>",
        required=False,
        type=str,
        default='~/code/dcm-brno/exclude.yml',
        help='Path to the YML file listing subjects to exclude.'
    )
    return parser



def read_metrics(csv_file_path, subject_df):
    """
    Read shape metrics (CSA, diameter_AP, ...) from the "csa-SC_T2w_perlevel" CSV file
    Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
    Keep only VertLevel 3 (C3)
    """
    # Read the "csa-SC_T2w_perlevel" CSV file
    logger.info(f"Reading {csv_file_path}...")
    df = pd.read_csv(csv_file_path, dtype=METRICS_DTYPE)

    # Fetch participant and session using lambda function
    df['Participant'], df['Session'] = zip(*df['Filename'].map(lambda x: fetch_participant_and_session(x)))

    # Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
    df['MEAN(compression_ratio)'] = df['MEAN(diameter_AP)'] / df['MEAN(diameter_RL)']

    # Drop columns
    df.drop(columns=['Filename', 'Timestamp', 'SCT Version', 'DistancePMJ'], inplace=True)

    # Keep only C3 (to be consistent with DWI analysis)
    df = df[df['VertLevel'] == 3]

    return df


def compute_statistics(df):
    """
    Compute the normality test and paired test for each shape metrics between sessions 1 and 2
    :param df: DataFrame with shape metrics
    :return: Dictionary with p-values for each metric
    """

    stats_dict = {}

    for metric in METRICS:
        # Extract data separately for sessions 1 and 2
        data_session1 = df[df['Session'] == 'Session 1'][metric]
        data_session2 = df[df['Session'] == 'Session 2'][metric]

        # Compute the normality test
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.normaltest.html
        stat, p = normaltest(data_session1)
        print(f'{metric}, session 1: Normality test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')
        stat, p = normaltest(data_session2)
        print(f'{metric}, session 2: Normality test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

        # Compute the Wilcoxon signed-rank test (nonparametric, paired)
        stat, p = wilcoxon(data_session1, data_session2)
        stats_dict[metric] = p
        print(f'{metric}: Wilcoxon signed-rank test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

    return stats_dict


def generate_figure(df, number_of_subjects, stats_dict, path_in):
    """
    Generate 3x2 group figure comparing sessions 1 vs session2 for 6 shape metrics (CSA, diameter_AP, ..)
    :param df: DataFrame with shape metrics
    :param number_of_subjects: Number of unique subjects
    :param stats_dict: Dictionary with p-values for each metric
    :param path_in: Path to the input directory (will be used to save the figure)
    """

    # Generate 3x2 group figure comparing sessions 1 vs session2 for 6 shape metrics
    mpl.rcParams['font.family'] = 'Arial'

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axs = axes.ravel()
    # Loop across metrics
    for index, metric in enumerate(METRICS):
        kwargs = dict(x='Session', y=metric, ax=axs[index], data=df)
        # Plot the violin plot
        # NOTE: I'm passing hue='Session' (i.e., the same as x='Session') to prevent the following warning:
        #   "Passing `palette` without assigning `hue` is deprecated and will be removed in v0.14.0. Assign the `x`
        #    variable to `hue` and set `legend=False` for the same effect."
        sns.violinplot(palette=color_palette,
                       hue='Session',
                       legend=False,
                       **kwargs)      # palette="Blues"
        # Plot swarmplot on top of the violin plot
        sns.swarmplot(color='black',
                      alpha=0.5,
                      **kwargs)
        # Plot lineplot connecting points of the same subject between sessions
        sns.lineplot(units='Participant',
                     estimator=None,
                     legend=False,
                     linewidth=0.5,
                     color='black',
                     alpha=0.5,
                     **kwargs)

        # Invert x-axis to have MR B1 on the left and MR B2 on the right
        axs[index].invert_xaxis()

        # If the p-value is less than 0.05, add the significance annotation
        if stats_dict[metric] < 0.05:
            axs[index].annotate('*', xy=(0.5, 0.9), xycoords='axes fraction', ha='center', va='center',
                                fontsize=30, color='black')

        axs[index].set_xlabel('')
        axs[index].set_ylabel(METRIC_TO_AXIS[metric], fontsize=LABELS_FONT_SIZE)
        axs[index].tick_params(axis='both', which='major', labelsize=TICKS_FONT_SIZE)

    # Set main title with number of subjects
    fig.suptitle(f'Shape metrics at C3 level (i.e., above the compression)\n'
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=TITLE_FONT_SIZE)

    # Save the figure
    fig.tight_layout()
    fname_out = os.path.join(path_in, f'T2w_violin_plots.png')
    fig.savefig(fname_out, dpi=300)
    plt.close(fig)
    logger.info(f'Figure saved to {fname_out}')


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # -------------------------------
    # Parse input args, check if the files exist
    # -------------------------------
    # CSV with metrics
    csv_file_path = os.path.abspath(os.path.expanduser(args.i))
    # Exclude file
    yml_file_path = os.path.abspath(os.path.expanduser(args.yml_file))

    if not os.path.isfile(csv_file_path):
        raise ValueError(f'ERROR: {args.i} does not exist.')

    if not os.path.isfile(yml_file_path):
        raise ValueError(f'ERROR: {args.yml_file} does not exist.')

    # Get the path to the input directory
    path_in = os.path.dirname(csv_file_path)

    # Dump log file there
    fname_log = os.path.join(path_in, 'T2w_violin_plots.log')
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(path_in, fname_log))
    logging.root.addHandler(fh)

    # -------------------------------
    # Read and prepare the data
    # -------------------------------
    xlsx_file_path = os.path.abspath(args.xlsx_table)
    # Check if the path to the xlsx file is valid
    if not os.path.exists(xlsx_file_path):
        print(f"Path {xlsx_file_path} does not exist.")
        sys.exit(1)

    # Read the xlsx file
    logger.info(f"Reading {xlsx_file_path}...")
    subject_df = read_xlsx_file(xlsx_file_path, columns_to_read=['FUP MR měření B provedeno (ano/ne)',
                                                                 'Datum operace', 'MR B1', 'MR B2'])

    # Keep only 'FUP MR měření B provedeno (ano/ne)' == 'ano' (yes)
    subject_df = subject_df[subject_df['FUP MR měření B provedeno (ano/ne)'] == 'ano']
    # Print number of rows (subjects)
    logger.info(f'Clinical table: Number of subjects with two sessions: {len(subject_df)}')

    df = read_metrics(csv_file_path, subject_df)
    # Print number of unique subjects
    logger.info(f'CSV file: Number of unique subjects before dropping: {df["Participant"].nunique()}')

    # Get the list of subjects to exclude
    subjects_to_exclude = read_yaml_file(file_path=yml_file_path, key='T2w')
    # Remove session (after the first '_') from the list of subjects to exclude
    subjects_to_exclude = [subject.split('_')[0] for subject in subjects_to_exclude]

    # Remove subjects to exclude
    df = df[~df['Participant'].isin(subjects_to_exclude)]

    # Print number of unique subjects
    number_of_subjects = df["Participant"].nunique()
    logger.info(f'CSV file: Number of unique subjects after dropping: {number_of_subjects}')

    # -------------------------------
    # Statistical tests
    # -------------------------------
    # Compute the normality test and paired test for each shape metrics between sessions 1 and 2
    stats_dict = compute_statistics(df)

    # -------------------------------
    # Plotting
    # -------------------------------
    # violionplot + swarmplot + lineplot
    generate_figure(df, number_of_subjects, stats_dict, path_in)


if __name__ == "__main__":
    main()
