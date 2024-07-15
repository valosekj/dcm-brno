"""
Given a JSON config file (which is used for sct_run_batch wrapper script):

    {
      "path_data"   : "~/data/dataset",
      "path_output" : "~/results/dataset_2024-07-09",
      "script"      : "~/code/analysis/process_data.sh",
      "jobs"        : 8
    }

The script adds a new key-value pair to the JSON config file. The key is 'exclude_list' or 'include_list' and values
are subjects listed in a YML file.

An example of the YML file (listing subjects to be excluded from T1w CSA analysis):

    csa_t1:
     - sub-001
     - sub-002
     - sub-003

Resulting JSON config file:

    {
      "path_data"   : "~/data/dataset",
      "path_output" : "~/results/dataset_2024-07-09",
      "script"      : "~/code/analysis/process_data.sh",
      "jobs"        : 8,
      "exclude_list": ["sub-001", "sub-002", "sub-003"]
    }

Author: Jan Valosek
"""

import os
import sys
import argparse

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import read_yaml_file, read_json_file, write_json_file


def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Add a list of subjects to be excluded or included to the JSON config file.',
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-config-file',
        metavar="<file>",
        required=True,
        type=str,
        help='Path to the JSON config file. The key-value pair will be added to this file. Example: config.json'
    )
    parser.add_argument(
        '-yml-file',
        metavar="<file>",
        required=True,
        type=str,
        help='Path to the YML file listing subjects to be excluded or included.'
    )
    parser.add_argument(
        '-mode',
        choices=['exclude_list', 'include_list'],
        help='Mode to use. exclude: exclude_list: exclude subjects; include_list: include subjects.',
        required=True,
        type=str
    )
    parser.add_argument(
        '-key',
        help='Key to fetch from the YML file. Example: "csa_t1"',
        required=True,
        type=str
    )

    return parser


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    json_file = os.path.abspath(os.path.expanduser(args.config_file))
    yml_file = os.path.abspath(os.path.expanduser(args.yml_file))

    if not os.path.isfile(json_file):
        print(f'ERROR: {json_file} does not exist.')

    if not os.path.isfile(yml_file):
        print(f'ERROR: {yml_file} does not exist.')

    # Read the JSON config file
    config_data = read_json_file(json_file)
    # Read the YML file
    yml_data = read_yaml_file(yml_file, key=args.key)

    # Add the key-value pair to the JSON config file
    config_data[args.mode] = yml_data

    # Write the updated JSON config file
    write_json_file(config_data, json_file)

    print(f"Key '{args.mode}' with values from '{args.key}' has been added to the JSON config file.")


if __name__ == '__main__':
    main()
