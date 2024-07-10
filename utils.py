import pandas as pd


def read_xlsx_file(xlsx_file_path, columns_to_read=None):
    """
    Read XLSX file with 'MR B1' and 'MR B2' columns and clinical data
    Args:
        xlsx_file_path: Path to the XLSX table
        columns_to_read: List of columns to read

    Returns:

    """
    if columns_to_read is None:
        columns_to_read = ['FUP MR měření B provedeno (ano/ne)', 'MR B1', 'MR B2']
    subject_df = pd.read_excel(xlsx_file_path,
                               sheet_name='Databáze',
                               usecols=columns_to_read,
                               header=1)

    return subject_df
