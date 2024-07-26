#!/usr/bin/env python
# -*- coding: utf-8

# Generate lineplot for T2w metrics normalized to PAM50 space
# Session 1 vs Session 2

# Author: Sandrine Bédard, Jan Valosek
# Adapted from:
# https://github.com/sct-pipeline/dcm-oklahoma/blob/sb/add-scripts/analyse_structural.py

import os
import logging
import argparse
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import fetch_participant_and_session


FNAME_LOG = 'log_stats.txt'

# Initialize logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # default: logging.DEBUG, logging.INFO
hdlr = logging.StreamHandler(sys.stdout)
logging.root.addHandler(hdlr)


METRICS = ['MEAN(area)', 'MEAN(diameter_AP)', 'MEAN(diameter_RL)', 'MEAN(compression_ratio)', 'MEAN(eccentricity)',
           'MEAN(solidity)']


METRICS_TO_YLIM = {
    'MEAN(area)': (30, 95),
    'MEAN(diameter_AP)': (4, 9.3),
    'MEAN(diameter_RL)': (8.5, 16),
    'MEAN(compression_ratio)': (0.3, 0.8),
    'MEAN(eccentricity)': (0.6, 0.95),
    'MEAN(solidity)': (0.912, 0.999),
}


METRIC_TO_AXIS = {
    'MEAN(area)': 'Cross-Sectional Area [mm²]',
    'MEAN(diameter_AP)': 'AP Diameter [mm]',
    'MEAN(diameter_RL)': 'Transverse Diameter [mm]',
    'MEAN(compression_ratio)': 'Compression Ratio [a.u.]',
    'MEAN(eccentricity)': 'Eccentricity [a.u.]',
    'MEAN(solidity)': 'Solidity [%]',
}


PALETTE = {
    'sex': {'M': 'blue', 'F': 'red'},
    'Session': {
        'Pre-surgery': (0.984313725490196, 0.5019607843137255, 0.4470588235294118),     # red
        'Post-surgery': 'green'    # green
        }
    }

LABELS_FONT_SIZE = 14
TICKS_FONT_SIZE = 12


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i-folder",
                        required=True,
                        type=str,
                        help="Results folder of spinal cord preprocessing")
    parser.add_argument("-o-folder",
                        type=str,
                        required=False,
                        default='~/code/dcm-brno/figures',
                        help="Folder to right results. Default: ~/code/dcm-brno/figures")
    return parser


def get_vert_indices(df):
    """
    Get indices of slices corresponding to mid-vertebrae
    Args:
        df (pd.dataFrame): dataframe with CSA values
    Returns:
        vert (pd.Series): vertebrae levels across slices
        ind_vert (np.array): indices of slices corresponding to the beginning of each level (=intervertebral disc)
        ind_vert_mid (np.array): indices of slices corresponding to mid-levels
    """
    # Get unique participant IDs
    subjects = df['participant_id'].unique()
    # Get vert levels for one certain subject
    vert = df[(df['participant_id'] == subjects[0]) & (df['Session'] == 'Post-surgery')]['VertLevel']
    # Get indexes of where array changes value
    ind_vert = vert.diff()[vert.diff() != 0].index.values
    # Get the beginning of C1
    ind_vert = np.append(ind_vert, vert.index.values[-1])
    ind_vert_mid = []
    # Get indexes of mid-vertebrae
    for i in range(len(ind_vert)-1):
        ind_vert_mid.append(int(ind_vert[i:i+2].mean()))

    return vert, ind_vert, ind_vert_mid


def read_t2w_pam50(folder):
    """
    Read CSV files with morphometrics normalized to PAM50 space
    One file per subject
    """
    dir_list = os.listdir(folder)
    # Get only PAM50 csv files
    dir_list = [file for file in dir_list if '.csv' in file]
    combined_df = pd.DataFrame()
    for file in dir_list:
        print(f'Reading file: {file}')
        df = pd.read_csv(os.path.join(folder, file))

        # Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
        df['MEAN(compression_ratio)'] = df['MEAN(diameter_AP)'] / df['MEAN(diameter_RL)']

        # Combine dataframes
        combined_df = pd.concat([combined_df, df], ignore_index=True)

    # Fetch participant and session using lambda function
    combined_df['participant_id'], combined_df['Session'] = (
        zip(*combined_df['Filename'].map(lambda x: fetch_participant_and_session(x))))

    # Keep only relevant columns
    combined_df = combined_df[['participant_id', 'Session', 'VertLevel', 'Slice (I->S)', 'MEAN(area)',
                               'MEAN(diameter_AP)', 'MEAN(diameter_RL)', 'MEAN(eccentricity)',
                               'MEAN(solidity)', 'MEAN(compression_ratio)']].drop(0)

    return combined_df


def create_lineplot(df, fname_out):
    """
    Create lineplot for individual metrics per vertebral levels.
    Note: we are ploting slices not levels to avoid averaging across levels.
    Args:
        df (pd.dataFrame): dataframe with metric values
        fname_out (str): output filename
    """

    #mpl.rcParams['font.family'] = 'Arial'

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axs = axes.ravel()

    hue = 'Session'

    # Loop across metrics
    for index, metric in enumerate(METRICS):
        # Note: we are ploting slices not levels to avoid averaging across levels
        if hue == 'sex' or hue == 'Session':
            sns.lineplot(ax=axs[index], x="Slice (I->S)", y=metric, data=df, errorbar='sd', hue=hue, linewidth=2,
                         palette=PALETTE[hue])
            if index == 0:
                axs[index].legend(loc='upper right', fontsize=TICKS_FONT_SIZE)
            else:
                axs[index].get_legend().remove()
        else:
            sns.lineplot(ax=axs[index], x="Slice (I->S)", y=metric, data=df, errorbar='sd', hue=hue, linewidth=2)

        axs[index].set_ylim(METRICS_TO_YLIM[metric][0], METRICS_TO_YLIM[metric][1])
        ymin, ymax = axs[index].get_ylim()

        # Add labels
        axs[index].set_ylabel(METRIC_TO_AXIS[metric], fontsize=LABELS_FONT_SIZE)
        axs[index].set_xlabel('Axial Slice #', fontsize=LABELS_FONT_SIZE)
        # Increase xticks and yticks font size
        axs[index].tick_params(axis='both', which='major', labelsize=TICKS_FONT_SIZE)

        # Remove spines
        axs[index].spines['right'].set_visible(False)
        axs[index].spines['left'].set_visible(False)
        axs[index].spines['top'].set_visible(False)
        axs[index].spines['bottom'].set_visible(True)

        # Get indices of slices corresponding vertebral levels
        vert, ind_vert, ind_vert_mid = get_vert_indices(df)
        # Insert a vertical line for each intervertebral disc
        for idx, x in enumerate(ind_vert[1:-1]):
            axs[index].axvline(df.loc[x, 'Slice (I->S)'], color='black', linestyle='--', alpha=0.5, zorder=0)

        # Insert a text label for each vertebral level
        for idx, x in enumerate(ind_vert_mid, 0):
            # Deal with T1 label (C8 -> T1)
            if vert[x] > 7:
                level = 'T' + str(vert[x] - 7)
                axs[index].text(df.loc[ind_vert_mid[idx], 'Slice (I->S)'], ymin, level, horizontalalignment='center',
                                verticalalignment='bottom', color='black', fontsize=TICKS_FONT_SIZE)
            else:
                level = 'C' + str(vert[x])
                axs[index].text(df.loc[ind_vert_mid[idx], 'Slice (I->S)'], ymin, level, horizontalalignment='center',
                                verticalalignment='bottom', color='black', fontsize=TICKS_FONT_SIZE)

        # Invert x-axis
        axs[index].invert_xaxis()
        # Add only horizontal grid lines
        axs[index].yaxis.grid(True)
        # Move grid to background (i.e. behind other elements)
        axs[index].set_axisbelow(True)

    # Save figure
    if hue:
        filename = fname_out.replace('.png', f'_{hue}.png')
    else:
        filename = fname_out
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    logger.info('Figure saved: ' + filename)


def main():

    args = get_parser().parse_args()
    # Get input argments
    path_in = os.path.abspath(args.i_folder)


    # Dump log file there
    if os.path.exists(FNAME_LOG):
        os.remove(FNAME_LOG)
    fh = logging.FileHandler(os.path.join(FNAME_LOG))
    logging.root.addHandler(fh)

    # Read CSV files with morphometrics normalized to PAM50 space
    df_t2_pam50 = read_t2w_pam50(path_in)

    # Keep only VertLevel from C2 to T1
    df_t2_pam50 = df_t2_pam50[df_t2_pam50['VertLevel'] <= 8]
    df_t2_pam50 = df_t2_pam50[df_t2_pam50['VertLevel'] > 1]

    # Rename Session 1 and Session 2 to Pre-surgery and Post-surgery
    df_t2_pam50['Session'] = df_t2_pam50['Session'].replace({'Session 1': 'Pre-surgery', 'Session 2': 'Post-surgery'})

    fname_out = os.path.join(path_in, f'T2w_metrics_perslice_PAM50.png')
    create_lineplot(df_t2_pam50, fname_out)


if __name__ == "__main__":
    main()
