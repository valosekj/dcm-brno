"""
From an input XLSX table, fetch demographics data (i.e., selected columns) for subjects listed in a YML file and
save them into a CSV file.
"""

import os
import sys
import argparse

import seaborn as sns
import matplotlib.pyplot as plt

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import read_xlsx_file, read_yaml_file


def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Fetch demographics data from the XLSX table and save them into a CSV file.',
        prog=os.path.basename(__file__).strip('.py')
    )
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
        default='~/code/dcm-brno/surgery.yml',
        help='Path to the YML file listing subjects to process. Default: ~/code/dcm-brno/surgery.yml'
    )
    parser.add_argument(
        '-o',
        metavar="<folder>",
        required=False,
        type=str,
        default='~/data/fmri-lab_olomouc/dcm-brno',
        help='Output folder where the fetched demographics will be saved as CSV file. '
             'Default: ~/data/fmri-lab_olomouc/dcm-brno'
    )

    return parser


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # -------------------------------
    # Parse input args, check if the files exist
    # -------------------------------
    # XLSX file with mJOA scores
    xlsx_file_path = os.path.abspath(os.path.expanduser(args.xlsx_table))

    # Exclude file
    yml_file_path = os.path.abspath(os.path.expanduser(args.yml_file))

    if not os.path.isfile(xlsx_file_path):
        raise ValueError(f'ERROR: {args.xlsx_table} does not exist.')

    if not os.path.isfile(yml_file_path):
        raise ValueError(f'ERROR: {args.yml_file} does not exist.')

    # Get the path to the input directory
    path_out = os.path.abspath(os.path.expanduser(args.o))
    # Create the output directory if it does not exist
    os.makedirs(path_out, exist_ok=True)

    # -------------------------------
    # Read and prepare the data
    # -------------------------------
    # Read the xlsx file
    print(f"Reading {xlsx_file_path}...")
    df = read_xlsx_file(xlsx_file_path, columns_to_read=['Datum operace ',
                                                         'Group těsně před operací',
                                                         'mJOA těsně před operací',
                                                         'Věk v době MRI baseline B',
                                                         'Pohlaví',
                                                         'Etáž nejtěžší komprese',
                                                         'MR B1',
                                                         'Datum MRI baseline B',
                                                         'MR B2',
                                                         'Datum MRI FUP1 B',
                                                         'Interval baseline-FUP MRI B (měsíce)',
                                                         'Group - baseline',
                                                         'Group + 6M',
                                                         'Group +12M',
                                                         'Group + 24M',
                                                         'Group + 36M'])


    # Read the YML file with subjects to process
    subject_list = read_yaml_file(yml_file_path, key='surgery')
    # From 'sub-1860B6472B', keep only '1860B'; this will correspond with 'MR B1' in the XLSX file
    subject_list = [sub.split('-')[1][:5] for sub in subject_list]

    # Remove white spaces at the end of the columns
    df.columns = df.columns.str.strip()

    # Rename 'Group +12M' to 'Group + 12M'
    df.rename(columns={'Group +12M': 'Group + 12M'}, inplace=True)

    # Remove time from columns with dates
    df['Datum operace'] = df['Datum operace'].dt.date
    df['Datum MRI baseline B'] = df['Datum MRI baseline B'].dt.date

    # Keep only the subjects that are in the YML file
    df = df[df['MR B1'].isin(subject_list)]

    # Reorder columns into the following order 'MR B1', 'Datum MRI baseline B', 'MR B2', 'Datum MRI FUP1 B',
    # 'Věk v době MRI baseline B', 'Pohlaví', 'Datum operace', 'Group - baseline', 'Group + 6M', 'Group +12M',
    # 'Group + 24M', 'Group + 36M'
    df = df[['MR B1', 'Datum MRI baseline B', 'MR B2', 'Datum MRI FUP1 B', 'Interval baseline-FUP MRI B (měsíce)',
             'Datum operace', 'Group těsně před operací',
             'Věk v době MRI baseline B', 'Pohlaví',
             'Etáž nejtěžší komprese', 'mJOA těsně před operací',
             'Group - baseline', 'Group + 6M', 'Group + 12M', 'Group + 24M', 'Group + 36M']]

    # Save the fetched demographics into a CSV file
    df.to_csv(os.path.join(path_out, 'demographics.csv'), index=False)
    print(f'Demographics saved to {os.path.join(path_out, "demographics.csv")}')

    # Print min, max, mean, std, and median of the age
    print(f"Age: min={df['Věk v době MRI baseline B'].min()}, max={df['Věk v době MRI baseline B'].max()}, "
          f"mean={df['Věk v době MRI baseline B'].mean():.2f}, std={df['Věk v době MRI baseline B'].std():.2f}"
          f", median={df['Věk v době MRI baseline B'].median()}")

    # Create age histogram
    plt.figure(figsize=(10, 6))
    sns.histplot(df['Věk v době MRI baseline B'], bins=10, kde=True)
    plt.title('Age distribution')
    plt.xlabel('Age')
    plt.ylabel('Count')
    plt.savefig(os.path.join(path_out, 'age_distribution.png'))


if __name__ == '__main__':
    main()
