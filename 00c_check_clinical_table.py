#
# The script reads the CLINICAL_TABLE.xlsx and LAP.xlsx files and checks if the 'MR B1' and 'MR B2' columns are in the
# same row in the clinical table. If not, it prints the MR B1 and MR B2 that are not in the clinical table.
# This is basically check if session 1 (MR B1) and session 2 (MR B2) match within subjects (rows).
#
# Jan Valosek
#

import os
import argparse
import pandas as pd


def get_parser():
    """
    Input argument parser function
    """
    parser = argparse.ArgumentParser(
        description='TODO.')
    parser.add_argument('-clinical-table',
                        help="Path to the CLINICAL_TABLE.xlsx file containing 'MR B1' and 'MR B2' columns",
                        required=True)
    parser.add_argument('-lap-table',
                        help="Path to the LAP.xlsx file containing 'MR B1' and 'MR B2' columns",
                        required=True)
    return parser


def main():

    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Fetch input arguments
    clinical_table = os.path.abspath(args.clinical_table)
    lap_table = os.path.abspath(args.lap_table)

    # Read "MR B1" and "MR B2" columns from the input xlsx files
    # Check if the clinical table contains the 'FUP MR měření B provedeno (ano/ne)' column, if so, read it
    # `header=1` skips the first row
    if 'FUP MR měření B provedeno (ano/ne)' in pd.read_excel(clinical_table, sheet_name='Databáze', header=1).columns:
        clinical_table_df = pd.read_excel(clinical_table, sheet_name='Databáze',
                                          usecols=['FUP MR měření B provedeno (ano/ne)',
                                                   'MR B1',
                                                   'MR B2'],
                                          header=1)
    else:
        clinical_table_df = pd.read_excel(clinical_table, sheet_name='Databáze', usecols=['MR B1', 'MR B2'], header=1)

    # Keep only 'FUP MR měření B provedeno (ano/ne)' == 'ano' (yes)
    if 'FUP MR měření B provedeno (ano/ne)' in clinical_table_df.columns:
        clinical_table_df = clinical_table_df[clinical_table_df['FUP MR měření B provedeno (ano/ne)'] == 'ano']

    lap_table_df = pd.read_excel(lap_table, sheet_name='LAP', usecols=['MR B1', 'MR B2'])

    # Iterate over the rows of the lap_table_df and check if the MR B1 and MR B2 are in the same row in the
    # clinical_table_df
    for index, row in lap_table_df.iterrows():
        mr_b1 = row['MR B1']
        mr_b2 = row['MR B2']
        #print(f'Checking if {mr_b1} and {mr_b2} are in the clinical table')
        if mr_b1 in clinical_table_df.values and mr_b2 in clinical_table_df.values:
            pass
            #print(f'{mr_b1} and {mr_b2} are in the clinical table')
        else:
            print(f'{mr_b1} and {mr_b2} are not in the clinical table')


if __name__ == "__main__":
    main()
