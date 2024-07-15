"""
Create Raincloud plots (violionplot + boxplot + individual points) for DTI metrics (FA, MD, RD, AD) for subjects with
surgery between sessions 1 (before surgery) and 2 (after surgery).

Example usage:
    python 03_generate_raincloud_plot_DTI_metrics.py -i results/DWI_FA.csv

Authors: Jan Valosek
"""

import os
import argparse

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import ptitprince as pt

from utils import read_csv_file, read_yaml_file, fetch_participant_and_session

LABEL_FONT_SIZE = 14
TICK_FONT_SIZE = 10

# List of tracts to extract
# Legend: https://spinalcordtoolbox.com/overview/concepts/pam50.html#white-and-gray-matter-atlas
# Inspiration: Valosek et al., 2021, DOI: 10.1111/ene.15027
label_to_tract = {
    "0,1": "Fasciculus\nGracilis",
    "2,3": "Fasciculus\nCuneatus",
    "4,5": "Lateral \nCST",              # CST = corticospinal tract
    "12,13": "Spinal\nLemniscus",        # (spinothalamic and spinoreticular tracts)
    "30,31": "Ventral\nGM Horns",
    "34,35": "Dorsal\nGM Horns",
    "white matter": "White\nMatter",
    "gray matter": "Gray\nMatter",
    "dorsal columns": "Dorsal\nColumns",
    "ventral funiculi": "Ventral\nColumns",
    "lateral funiculi": "Lateral\nColumns",
}

metric_to_axis = {
    'FA': 'Fractional anisotropy',
    'MD': 'Mean diffusivity [$× 10^{-3} mm^{2}/s$]',
    'AD': 'Axial diffusivity [$× 10^{-3} mm^{2}/s$]',
    'RD': 'Radial diffusivity [$× 10^{-3} mm^{2}/s$]',
    }

color_palette = [(0.5529411764705883, 0.8274509803921568, 0.7803921568627451),      # green
                 (0.984313725490196, 0.5019607843137255, 0.4470588235294118)]       # red

def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Create Raincloud plots (violionplot + boxplot + individual points) for DTI metrics (FA, MD, RD, '
                    'AD) for subjects with surgery between sessions 1 (before surgery) and 2 (after surgery).',
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-i',
        metavar="<file>",
        required=True,
        type=str,
        help='Path to the CSV file containing the DTI metrics. Example: results/DWI_FA.csv'
    )
    parser.add_argument(
        '-yml-file',
        metavar="<file>",
        required=False,
        type=str,
        default='~/code/dcm-brno/surgery.yml',
        help='Path to the YML file listing subjects with surgery.'
    )

    return parser


def create_rainplot(df, metric, csv_file_path):
    """
    Create Raincloud plots (violionplot + boxplot + individual points)
    :param df: dataframe with DTI metrics for individual subjects and individual tracts
    :param metric: DTI metric to plot (e.g., FA, MD, RD, AD)
    :param csv_file_path: path to the input CSV file (it is used to save the output figure)
    """
    fig_size = (15, 5)
    plt.subplots(figsize=fig_size)
    ax = pt.RainCloud(data=df,
                      x='Label',
                      y='MAP()',
                      hue='Session',
                      hue_order=['Session 1', 'Session 2'],
                      dodge=True,  # move boxplots next to each other
                      linewidth=0,      # violionplot borderline (0 - no line)
                      width_viol=.5,    # violionplot width
                      #width_box=.3,     # boxplot width
                      rain_alpha=.7,    # individual points transparency - https://github.com/pog87/PtitPrince/blob/23debd9b70fca94724a06e72e049721426235f50/ptitprince/PtitPrince.py#L707
                      rain_s=2,         # individual points size
                      alpha=.7,         # violin plot transparency
                      box_showmeans=True,  # show mean value inside the boxplots
                      box_meanprops={'marker': '^', 'markerfacecolor': 'black', 'markeredgecolor': 'black',
                                     'markersize': '6'},
                      palette=color_palette
                      )

    # Change boxplot opacity (.0 means transparent)
    # https://github.com/mwaskom/seaborn/issues/979#issuecomment-1144615001
    for patch in ax.patches:
        r, g, b, a = patch.get_facecolor()
        patch.set_facecolor((r, g, b, .0))

    # Remove spines
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(True)

    # Remove x-axis label
    ax.set_xlabel('')
    # Change and increase y-axis label font size
    ax.set_ylabel(metric_to_axis[metric], fontsize=TICK_FONT_SIZE)
    # Increase ticks font size
    ax.tick_params(axis='x', labelsize=TICK_FONT_SIZE)
    ax.tick_params(axis='y', labelsize=TICK_FONT_SIZE)

    # Move legend below the figure -- we have to create a custom legend, otherwise, elements will be repeated as
    # raincloud plot contains violionplot + boxplot + individual points
    lines = list()  #
    lines.append(Line2D([0], [0], color=color_palette[0], linewidth=3, linestyle='-', label='Session 1'))
    lines.append(Line2D([0], [0], color=color_palette[1], linewidth=3, linestyle='-', label='Session 2'))
    plt.legend(handles=lines, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=TICK_FONT_SIZE, handlelength=1)

    # Add horizontal dashed grid lines
    ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.3)

    # Add title
    plt.title(f'{metric} at C3 level (i.e., above the compression)\n'
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=LABEL_FONT_SIZE)

    plt.tight_layout()
    plt.show()
    # Save figure into the same directory as the input CSV file
    output_file = f'{os.path.dirname(csv_file_path)}/{metric}_rainplot.png'
    plt.savefig(output_file, dpi=300)
    print(f'Figure saved to {output_file}')
    plt.close()


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # -------------------------------
    # Parse input args, check if the files exist
    # -------------------------------
    csv_file_path = os.path.abspath(os.path.expanduser(args.i))
    yml_file_path = os.path.abspath(os.path.expanduser(args.yml_file))

    if not os.path.isfile(csv_file_path):
        raise ValueError(f'ERROR: {args.i} does not exist.')

    if not os.path.isfile(yml_file_path):
        raise ValueError(f'ERROR: {args.yml_file} does not exist.')

    # Fetch metric from file_path, e.g., get FA from DWI_FA.csv
    metric = os.path.basename(csv_file_path).split('_')[1].split('.')[0]

    # -------------------------------
    # Read and prepare the data
    # -------------------------------
    # Read the CSV file with DTI metrics
    df = read_csv_file(csv_file_path, columns_to_read=['Filename', 'VertLevel', 'Label', 'MAP()'])

    # Fetch participant and session using lambda function
    df['Participant'], df['Session'] = zip(*df['Filename'].map(lambda x: fetch_participant_and_session(x)))
    # Drop the 'Filename' column
    df.drop(columns=['Filename'], inplace=True)

    # Rename entries in the "Label" column using label_to_tract
    df['Label'] = df['Label'].map(label_to_tract)

    # Print number of unique subjects
    print(f'Number of unique subjects before dropping: {df["Participant"].nunique()}')

    # Get the list of subjects with surgery from the input YML file
    subjects_with_surgery = read_yaml_file(file_path=yml_file_path, key='surgery')

    # Keep only subjects with surgery
    df = df[df['Participant'].isin(subjects_with_surgery)]

    # Keep only C3
    df = df[df['VertLevel'] == 3]

    # Print number of unique subjects
    print(f'Number of unique subjects after dropping: {df["Participant"].nunique()}')

    # -------------------------------
    # Plotting
    # -------------------------------
    create_rainplot(df, metric, csv_file_path)


if __name__ == '__main__':
    main()
