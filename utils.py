import re
import json
import yaml     # pip install pyyaml
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


def read_csv_file(csv_file_path, columns_to_read):
    """
    Read CSV file with 'DICOM_ID' and 'SUB_ID' columns
    Args:
        csv_file_path: Path to the CSV table
        columns_to_read: List of columns to read

    Returns:

    """
    # Exit if columns_to_read is not provided
    if columns_to_read is None:
        raise ValueError("columns_to_read is not provided")
    subject_df = pd.read_csv(csv_file_path, usecols=columns_to_read)

    return subject_df


def read_yaml_file(file_path, key):
    """
    Read YAML file
    Args:
        file_path: Path to the YAML file
        key: Key to fetch from the JSON file

    Returns:
        list of subjects with surgery
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    # Check if the key exists in the YAML file
    if key not in data:
        raise ValueError(f'ERROR: {key} does not exist in {file_path}')

    return data[key]


def read_json_file(file_path):
    """
    Read JSON file
    Args:
        file_path: Path to the JSON file

    Returns:
        data: JSON data
    """
    with open(file_path, 'r') as file:
        data = json.load(file)

    return data


def write_json_file(data, file_path):
    """
    Write JSON file
    Args:
        data: JSON data
        file_path: Path to the JSON file
    """
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def fetch_participant_and_session(filename_path):
    """
    Get participant_id and session_id from the input BIDS-compatible filename or file path
    The function works both on absolute file path and filename
    More about BIDS - https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#anatomy-imaging-data

    :param filename_path: e.g., '~/data_processed/sub-1860B6472B/ses-6472B/dwi/sub-1860B6472B_ses-6472B_acq-ZOOMit_dir-AP_dwi_crop_crop_moco_FA.nii.gz'
    :return: participant_id: e.g., 'sub-1860B6472B'. The participant_id also contains info about sessions: the first 4
    digits represent session 1, the next 4 digits represent session 2
    :return: session_id: session ID (e.g., ses-01)
    """

    participant_tmp = re.search('sub-(.*?)[_/]', filename_path)     # [_/] slash or underscore
    participant_id = participant_tmp.group(0)[:-1] if participant_tmp else ""    # [:-1] removes the last underscore or slash

    session_tmp = re.search('ses-(.*?)[_/]', filename_path)     # [_/] means either underscore or slash
    session_id = session_tmp.group(0)[:-1] if session_tmp else ""    # [:-1] removes the last underscore or slash
    # REGEX explanation
    # . - match any character (except newline)
    # *? - match the previous element as few times as possible (zero or more times)

    # Determine whether session_id corresponds to session 1 or session 2
    # Debug:
    #   participant_id, participant_id[4:9], participant_id[9:]
    #   ('sub-1860B6472B', '1860B', '6472B')
    #   session_id[4:]
    #   '6472B'
    if session_id[4:] == participant_id[4:9]:
        session = 'Session 1'
    elif session_id[4:] == participant_id[9:]:
        session = 'Session 2'

    return participant_id, session


def format_pvalue(p_value, alpha=0.05, decimal_places=3, include_space=True, include_equal=True):
    """
    Format p-value.
    If the p-value is lower than alpha, format it to "<0.001", otherwise, round it to three decimals

    :param p_value: input p-value as a float
    :param alpha: significance level
    :param decimal_places: number of decimal places the p-value will be rounded
    :param include_space: include space or not (e.g., ' = 0.06')
    :param include_equal: include equal sign ('=') to the p-value (e.g., '=0.06') or not (e.g., '0.06')
    :return: p_value: the formatted p-value (e.g., '<0.05') as a str
    """
    if include_space:
        space = ' '
    else:
        space = ''

    # If the p-value is lower than alpha, return '<alpha' (e.g., <0.001)
    if p_value < alpha:
        p_value = space + "<" + space + str(alpha)
    # If the p-value is greater than alpha, round it number of decimals specified by decimal_places
    else:
        if include_equal:
            p_value = space + '=' + space + str(round(p_value, decimal_places))
        else:
            p_value = space + str(round(p_value, decimal_places))

    return p_value


def read_metrics(csv_file_path, vert_level=None):
    """
    Read shape metrics (CSA, diameter_AP, ...) from the "csa-SC_T2w_perlevel" CSV file generated by
    SCT's sct_process_segmentation
    Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
    Keep only VertLevel specified by vert_level

    :param csv_file_path: Path to the "csa-SC_T2w_perlevel" CSV file
    :param vert_level: Vertebrae level to keep. Examples: 3 (meaning C3), 4 (meaning C4), etc.
    :return: df: DataFrame with shape metrics
    """

    metrics_dtype = {
        'MEAN(diameter_AP)': 'float64',
        'MEAN(area)': 'float64',
        'MEAN(diameter_RL)': 'float64',
        'MEAN(eccentricity)': 'float64',
        'MEAN(solidity)': 'float64'
    }

    # Read the "csa-SC_T2w_perlevel" CSV file
    df = pd.read_csv(csv_file_path, dtype=metrics_dtype)

    # Fetch participant and session using lambda function
    df['Participant'], df['Session'] = zip(*df['Filename'].map(lambda x: fetch_participant_and_session(x)))

    # Compute compression ratio (CR) as MEAN(diameter_AP) / MEAN(diameter_RL)
    df['MEAN(compression_ratio)'] = df['MEAN(diameter_AP)'] / df['MEAN(diameter_RL)']

    # Drop columns
    df.drop(columns=['Filename', 'Timestamp', 'SCT Version', 'DistancePMJ'], inplace=True)

    # Keep specific vert level if vert_level is provided
    if vert_level is not None:
        df = df[df['VertLevel'] == vert_level]

    return df
