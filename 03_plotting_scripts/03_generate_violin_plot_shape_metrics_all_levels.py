"""
Load "csa-SC_T2w_perlevel" CSV file with shape metrics perlevel located under "-path-in/results" and generate group
figures comparing sessions 1 vs session 2.

Rows represent vertebral levels (C2-C7)
Columns represent shape metrics (CSA, diameter_AP, ..)

The figures are saved in "-path-out".

Authors: Jan Valosek
"""

import os
import sys
import argparse
import logging

import pandas as pd
import seaborn as sns       # seaborn>=0.13.0 is required to properly create the figure
import matplotlib as mpl
import matplotlib.pyplot as plt

from scipy.stats import normaltest, ttest_rel, wilcoxon

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import read_yaml_file, format_pvalue, read_metrics

# Vertebral levels (C2-C7)
LEVELS = [2, 3, 4, 5, 6, 7]

METRICS = ['MEAN(area)', 'MEAN(diameter_AP)', 'MEAN(diameter_RL)', 'MEAN(compression_ratio)', 'MEAN(eccentricity)',
           'MEAN(solidity)']

METRIC_TO_AXIS = {
    'MEAN(diameter_AP)': 'AP Diameter [mm]',
    'MEAN(area)': 'Cross-Sectional Area [mm²]',
    'MEAN(diameter_RL)': 'Transverse Diameter [mm]',
    'MEAN(eccentricity)': 'Eccentricity [a.u.]',
    'MEAN(solidity)': 'Solidity [%]',
    'MEAN(compression_ratio)': 'Compression Ratio [a.u.]',
}

TITLE_FONT_SIZE = 12
LABELS_FONT_SIZE = 10
TEXT_FONT_SIZE = 8

# NOTE: for some reason, the color order must be swapped here. Maybe due to the `.invert_xaxis` method?
color_palette = {
    'Post-surgery': (0.5529411764705883, 0.8274509803921568, 0.7803921568627451),    # red
    'Pre-surgery': (0.984313725490196, 0.5019607843137255, 0.4470588235294118)      # green
     }

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
        '-exclude-file',
        metavar="<file>",
        required=False,
        type=str,
        default='~/code/dcm-brno/exclude.yml',
        help='Path to the YML file listing subjects to exclude. Default: ~/code/dcm-brno/exclude.yml'
    )
    parser.add_argument(
        '-exclude-key',
        metavar="<str>",
        required=True,
        type=str,
        help='Key in the YML file listing subjects to exclude. Examples: "T2w", "T2star_SC"'
    )
    return parser


def compute_statistics(df):
    """
    Compute the normality test and paired test for each shape metrics between sessions 1 and 2
    :param df: DataFrame with shape metrics
    :return: Dictionary with p-values for each metric
    """

    stats_dict = {}

    # Loop across vertebral levels (C2-C7)
    for level in LEVELS:
        df_level = df[df['VertLevel'] == level]
        # Loop across metrics (CSA, diameter_AP, ...)
        for metric in METRICS:
            # Extract data separately for sessions 1 and 2
            data_session1 = df_level[df_level['Session'] == 'Session 1'][metric]
            data_session2 = df_level[df_level['Session'] == 'Session 2'][metric]

            # Compute the normality test
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.normaltest.html
            stat, p = normaltest(data_session1)
            print(f'C{level}, {metric}, session 1: Normality test p-value'
                  f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')
            stat, p = normaltest(data_session2)
            print(f'C{level}, {metric}, session 2: Normality test p-value'
                  f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

            # Compute the Wilcoxon signed-rank test (nonparametric, paired)
            stat, p = wilcoxon(data_session1, data_session2)
            stats_dict[level, metric] = p
            print(f'C{level}, {metric}: Wilcoxon signed-rank test p-value'
                  f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

    return stats_dict


def generate_figure(df, number_of_subjects, stats_dict, fname_out):
    """
    Generate 6x6 group figure (violionplot + swarmplot + lineplot) comparing sessions 1 vs session2 for 6 shape metrics
    Rows represent vertebral levels (C2-C7)
    Columns represent shape metrics (CSA, diameter_AP, ..)
    :param df: DataFrame with shape metrics
    :param number_of_subjects: Number of unique subjects
    :param stats_dict: Dictionary with p-values for each metric
    :param fname_out: Output figure file name
    """

    # Generate 6x6 group figure comparing sessions 1 vs session2 for 6 shape metrics
    mpl.rcParams['font.family'] = 'Arial'

    fig, axes = plt.subplots(6, 6, figsize=(16, 16))
    axs = axes
    # Loop across vertebral levels (C2-C7)
    for index_row, level in enumerate(LEVELS):
        # Keep only one specific vert level
        df_level = df[df['VertLevel'] == level]
        # Loop across metrics (CSA, diameter_AP, ...)
        for index_col, metric in enumerate(METRICS):
            print(f'Plotting C{level}, {metric}...')
            kwargs = dict(x='Session', y=metric, ax=axs[index_row, index_col], data=df_level)
            # Plot the violin plot
            # NOTE: I'm passing hue='Session' (i.e., the same as x='Session') to prevent the following warning:
            #   "Passing `palette` without assigning `hue` is deprecated and will be removed in v0.14.0. Assign the `x`
            #    variable to `hue` and set `legend=False` for the same effect."
            sns.violinplot(palette=color_palette,
                           hue='Session',
                           legend=False,
                           cut=0,
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
            axs[index_row, index_col].invert_xaxis()

            # If the p-value is less than 0.05, add the significance annotation
            if stats_dict[level, metric] < 0.05:
                axs[index_row, index_col].annotate(f'*',
                                        xy=(0.35, 0.93), xycoords='axes fraction',
                                        ha='center', va='center',
                                        fontsize=TEXT_FONT_SIZE+3, color='black')
                # change background color to light yellow
                axs[index_row, index_col].set_facecolor('#FFFFCC')

            axs[index_row, index_col].annotate(
                f'p{format_pvalue(stats_dict[level, metric], alpha=.001, include_space=False)}',
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', va='center',
                fontsize=TEXT_FONT_SIZE, color='black')

            axs[index_row, index_col].set_xlabel('')
            # Add title to each row, (i.e., y-axis)
            if index_col == 0:
                ylabel = f'C{level}\n{METRIC_TO_AXIS[metric]}'
            else:
                ylabel = METRIC_TO_AXIS[metric]
            axs[index_row, index_col].set_ylabel(ylabel, fontsize=LABELS_FONT_SIZE)

            axs[index_row, index_col].tick_params(axis='both', which='major', labelsize=TEXT_FONT_SIZE)

            # remove x-axis label
            axs[index_row, index_col].set_xlabel('')

    # Set main title with number of subjects
    fig.suptitle(f'T2w shape metrics across vertebral levels. '
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=TITLE_FONT_SIZE)

    # Save the figure
    fig.tight_layout()
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
    exclude_file_path = os.path.abspath(os.path.expanduser(args.exclude_file))

    if not os.path.isfile(csv_file_path):
        raise ValueError(f'ERROR: {args.i} does not exist.')

    if not os.path.isfile(exclude_file_path):
        raise ValueError(f'ERROR: {args.exclude_file} does not exist.')

    # Get the path to the input directory
    path_in = os.path.dirname(csv_file_path)

    # Dump log file there
    fname_log = os.path.join(path_in, f'{args.exclude_key}_violin_plots_all_levels.log')
    if os.path.exists(fname_log):
        os.remove(fname_log)
    fh = logging.FileHandler(os.path.join(path_in, fname_log))
    logging.root.addHandler(fh)

    # -------------------------------
    # Read and prepare the data
    # -------------------------------
    logger.info(f"Reading {csv_file_path}...")
    df = read_metrics(csv_file_path)
    # Print number of unique subjects
    logger.info(f'CSV file: Number of unique subjects before dropping: {df["Participant"].nunique()}')

    # Get the list of subjects to exclude
    subjects_to_exclude = read_yaml_file(file_path=exclude_file_path, key=args.exclude_key)
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
    # Rename Session 1 and Session 2 to Pre-surgery and Post-surgery
    df['Session'] = df['Session'].replace({'Session 1': 'Pre-surgery', 'Session 2': 'Post-surgery'})

    fname_out = os.path.join(path_in, f'{args.exclude_key}_violin_plots_all_levels.png')
    # violionplot + swarmplot + lineplot
    generate_figure(df, number_of_subjects, stats_dict, fname_out)


if __name__ == "__main__":
    main()
