"""
Generate plots for DTI metrics (FA, MD, RD, AD) for subjects with surgery between sessions 1 (before surgery) and 2
(after surgery).

The script generates:
 - Raincloud plots (violionplot + boxplot + individual points)
 - violionplot + swarmplot + lineplot

Example usage:
    python 03_generate_plots_DTI_metrics.py -i results/DWI_FA.csv

Authors: Jan Valosek
"""

import os
import sys
import argparse

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import normaltest, wilcoxon, ttest_rel

# Get the name of the directory where this script is present
current = os.path.dirname(os.path.realpath(__file__))
# Get the parent directory name
parent = os.path.dirname(current)
# Add the parent directory to the sys.path to import the utils module
sys.path.append(parent)

from utils import read_csv_file, read_xlsx_file, read_yaml_file, fetch_participant_and_session, format_pvalue

LABEL_FONT_SIZE = 14
TICK_FONT_SIZE = 9

# List of tracts to extract
# Legend: https://spinalcordtoolbox.com/overview/concepts/pam50.html#white-and-gray-matter-atlas
# Inspiration: Valosek et al., 2021, DOI: 10.1111/ene.15027
label_to_tract = {
    "white matter": "White\nMatter",
    "gray matter": "Gray\nMatter",
    "dorsal columns": "Dorsal\nColumns",
    "ventral funiculi": "Ventral\nColumns",
    "lateral funiculi": "Lateral\nColumns",
    "0,1": "Fasciculus\nGracilis",
    "2,3": "Fasciculus\nCuneatus",
    "4,5": "Lateral Corticospinal\nTracts",
    "12,13": "Spinal\nLemniscus",        # (spinothalamic and spinoreticular tracts)
    "30,31": "Ventral\nGM Horns",
    "34,35": "Dorsal\nGM Horns"
}

metric_to_axis = {
    'FA': 'Fractional anisotropy',
    'MD': 'Mean diffusivity [$× 10^{-3} mm^{2}/s$]',
    'AD': 'Axial diffusivity [$× 10^{-3} mm^{2}/s$]',
    'RD': 'Radial diffusivity [$× 10^{-3} mm^{2}/s$]',
    }

# scaling factor (for display)
scaling_factor = {
    'FA': 1,
    'MD': 1000,
    'AD': 1000,
    'RD': 1000,
    }


def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Create Raincloud plots (violionplot + boxplot + individual points) for DTI metrics (FA, MD, RD, '
                    'AD) for subjects with surgery between sessions 1 (before surgery) and 2 (after surgery).'
                    'The figure will be saved in the same directory as the input CSV file.',
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
        '-vert-level',
        metavar="<int>",
        required=True,
        type=int,
        help='Vert level to generate the figure for. Examples: 3 (meaning C3), 4 (meaning C4), etc.'
    )
    parser.add_argument(
        '-xlsx-table',
        metavar="<file>",
        required=True,
        type=str,
        help="Path to the table.xlsx file containing 'MR B1', 'MR B2', group, and sex columns")
    parser.add_argument(
        '-exclude-file',
        metavar="<file>",
        required=False,
        type=str,
        default='~/code/dcm-brno/exclude.yml',
        help='Path to the YML file listing subjects to exclude and subjects with T2w hyperintensities. '
             'Default: ~/code/dcm-brno/exclude.yml'
    )

    return parser


def compute_statistics(df):
    """
    Compute the normality test and Wilcoxon signed-rank test (nonparametric, paired) between sessions 1 and 2 for each
    tract.
    :param df: DataFrame with shape metrics
    :return: Dictionary with p-values for each metric
    """

    stats_dict = dict()

    # Loop through each tract
    for tract in label_to_tract.values():
        # Extract data for each tract, separately for sessions 1 and 2
        data_session1 = df[(df['Label'] == tract) & (df['Session'] == 'Session 1')]['MAP()']
        data_session2 = df[(df['Label'] == tract) & (df['Session'] == 'Session 2')]['MAP()']

        tract_name = tract.replace('\n', ' ')

        # Compute the normality test
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.normaltest.html
        stat, p = normaltest(data_session1)
        print(f'{tract_name}, session 1: Normality test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')
        stat, p = normaltest(data_session2)
        print(f'{tract_name}, session 2: Normality test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

        # Compute the Wilcoxon signed-rank test (nonparametric, paired)
        stat, p = wilcoxon(data_session1, data_session2)
        stats_dict[tract] = p
        print(f'{tract_name}: Wilcoxon signed-rank test p-value'
              f'{format_pvalue(p, alpha=0.05, decimal_places=3, include_space=True, include_equal=True)}')

    return stats_dict


def create_rainplot(df, metric, number_of_subjects, fname_out):
    """
    Create Raincloud plots (violionplot + boxplot + individual points)
    :param df: dataframe with DTI metrics for individual subjects and individual tracts
    :param metric: DTI metric to plot (e.g., FA, MD, RD, AD)
    :param number_of_subjects: number of unique subjects (will be shown in the title)
    :param fname_out: path to the output figure
    """

    import ptitprince as pt     # seaborn==0.11 is required for the ptitprince package (https://github.com/pog87/PtitPrince/blob/master/requirements.txt)

    color_palette = [(0.5529411764705883, 0.8274509803921568, 0.7803921568627451),  # green
                     (0.984313725490196, 0.5019607843137255, 0.4470588235294118)]  # red

    mpl.rcParams['font.family'] = 'Arial'

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
    plt.title(f'{metric} at C3 level (above the compression)\n'
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=LABEL_FONT_SIZE)

    plt.tight_layout()
    # Save figure into the same directory as the input CSV file
    plt.savefig(fname_out, dpi=300)
    print(f'Figure saved to {fname_out}')
    plt.close()


def create_scatterplot(df, metric, number_of_subjects, hue, fname_out):
    """
    Create scatterplot with lines connecting the same subject between sessions 1 and 2
    The x-axis represents the time from surgery (in days) and the y-axis represents the DTI metric (e.g., FA, ...)
    :param df: dataframe with DTI metrics for individual subjects and individual tracts
    :param metric: DTI metric to plot (e.g., FA, MD, RD, AD)
    :param number_of_subjects: number of unique subjects (will be shown in the title)
    :param hue: hue to distinguish groups (e.g., 'Group before surgery', 'T2w hyperintensity', ...)
    :param fname_out: path to the output figure
    """
    def _plot_data(ax, data, color, marker):
        # Loop across participants
        participants = data['Participant'].unique()
        for participant in participants:
            data_tmp = data[data['Participant'] == participant]

            x_session1 = data_tmp[data_tmp['Session'] == 'Pre-surgery']['Days between surgery and baseline MRI']
            y_session1 = data_tmp[data_tmp['Session'] == 'Pre-surgery']['MAP()']
            x_session2 = data_tmp[data_tmp['Session'] == 'Post-surgery']['Days between surgery and follow-up MRI']
            y_session2 = data_tmp[data_tmp['Session'] == 'Post-surgery']['MAP()']

            # Plot scatterplot
            ax.plot([x_session1, x_session2], [y_session1, y_session2],
                    color=color,
                    marker=marker,
                    alpha=0.5,
                    linewidth=1.5)

    # Compute the difference in days between the surgery and the MRI scans
    df['Days between surgery and baseline MRI'] = (df['Date of baseline MRI'] - df['Date of surgery']).dt.days
    df['Days between surgery and follow-up MRI'] = (df['Date of follow-up MRI'] - df['Date of surgery']).dt.days

    mpl.rcParams['font.family'] = 'Arial'

    # Scale the 'MAP()' column (containing FA, MD, ...) by the scaling factor
    df['MAP()'] = df['MAP()'] * scaling_factor[metric]

    fig, axes = plt.subplots(1, 6, figsize=(18, 6), sharey=True)
    axs = axes.ravel()
    # Loop across metrics
    for index, tract in enumerate(label_to_tract.values()):
        # 3 groups
        if hue in ['Maximum compressed level']:
            unique_groups = df[hue].unique()
            colors = ['black', 'red', 'blue']
            markers = ['o', 's', 'D']
        # 1 group
        elif hue is None:
            unique_groups = [None]
            colors = ['black']
            markers = ['o']
        # 2 groups
        else:
            unique_groups = df[hue].unique()
            colors = ['black', 'red']
            markers = ['o', 's']
        color_map = dict(zip(unique_groups, colors))
        marker_map = dict(zip(unique_groups, markers))

        for group in unique_groups:
            data = df[df['Label'] == tract]
            if hue is not None:
                data = data[data[hue] == group]
            _plot_data(axs[index], data, color_map[group], marker_map[group])

        # Plot vertical dashed line at x=0
        axs[index].axvline(x=0, color='black', linestyle='--', alpha=0.5)

        # Change x-axis limits to [-500, 2500]
        axs[index].set_xlim([-1000, 2500])

        axs[index].set_xlabel('Time from surgery [days]', fontsize=TICK_FONT_SIZE)
        # Set y-axis label only for the first subplot
        if index == 0:
            axs[index].set_ylabel(metric_to_axis[metric], fontsize=TICK_FONT_SIZE)
        axs[index].tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)

        # Add title
        axs[index].set_title(tract.replace('\n', ' '), fontsize=LABEL_FONT_SIZE - 2, y=1)

        # Add horizontal dashed grid
        axs[index].yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.3)

        # Remove spines
        axs[index].spines['right'].set_visible(False)
        axs[index].spines['top'].set_visible(False)

    # Create custom legend for hue
    # Create marker and label for the surgery day
    markers = [Line2D([0], [0], color='black', linestyle='--', linewidth=2, alpha=0.5)]
    labels = ['surgery day']
    # If hue is specified, add the groups to the legend
    if hue:
        markers_groups = [Line2D([0], [0], color=value, linestyle='-', linewidth=2, alpha=0.5)
                          for value in colors]
        markers = markers + markers_groups
        labels = labels + list(unique_groups)

    legend = fig.legend(markers, labels, loc='lower left',
                        bbox_to_anchor=(0.7, 0.91), bbox_transform=plt.gcf().transFigure,
                        ncol=len(labels), fontsize=TICK_FONT_SIZE)
    # Change box's frame color to black
    frame = legend.get_frame()
    frame.set_edgecolor('black')
    # Add title to the legend
    legend.set_title(hue, prop={'size': TICK_FONT_SIZE})

    # Set main title with number of subjects
    fig.suptitle(f'{metric} at C3 level (above the compression)\n'
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=LABEL_FONT_SIZE)

    # Save the figure
    fig.tight_layout()
    fig.savefig(fname_out, dpi=300)
    plt.close(fig)
    print(f'Figure saved to {fname_out}')


def create_violinplot(df, metric, number_of_subjects, hue, fname_out):
    """
    Create violionplot + swarmplot + lineplot comparing sessions 1 vs session2 for DTI metrics
    :param df: dataframe with DTI metrics for individual subjects and individual tracts
    :param metric: DTI metric to plot (e.g., FA, MD, RD, AD)
    :param number_of_subjects: number of unique subjects (will be shown in the title)
    :param stats_dict: dictionary with p-values for each metric
    :param hue: hue to distinguish groups (e.g., 'Group before surgery', 'T2w hyperintensity', )
    :param fname_out: path to the output figure
    """

    # NOTE: for some reason, the color order must be swapped here. Maybe due to the `.invert_xaxis` method?
    color_palette = {
        'Post-surgery': (0.727, 0.727, 0.727, 0.5),  # light gray with transparency
        'Pre-surgery': (0.9, 0.9, 0.9, 0.5)  # different tone of light gray with transparency
    }

    import seaborn as sns  # seaborn>=0.13.0 is required to properly create the figure

    # Generate 3x2 group figure comparing sessions 1 vs session2 for 6 shape metrics
    mpl.rcParams['font.family'] = 'Arial'

    # Scale the 'MAP()' column (containing FA, MD, ...) by the scaling factor
    df['MAP()'] = df['MAP()'] * scaling_factor[metric]

    fig, axes = plt.subplots(2, 6, figsize=(14, 8), sharey=True)
    axs = axes.ravel()
    # Loop across metrics
    for index, tract in enumerate(label_to_tract.values()):
        kwargs = dict(x='Session', y='MAP()', ax=axs[index], data=df[df['Label'] == tract])
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

        # Loop across groups to distinguish asymptomatic (1) and symptomatic (2) subjects
        unique_groups = df[hue].unique()
        for group in unique_groups:
            # Filter data for the current tract and group
            data = df[(df['Label'] == tract) & (df[hue] == group)]
            kwargs = dict(x='Session', y='MAP()', ax=axs[index], data=data)

            # Plot lineplot connecting points of the same subject between sessions
            sns.lineplot(units='Participant',
                         estimator=None,
                         legend=False,
                         linewidth=1.5,
                         color='black' if group == unique_groups[0] else 'red',
                         alpha=0.5,
                         **kwargs)

        # Invert x-axis to have MR B1 on the left and MR B2 on the right
        axs[index].invert_xaxis()

        # If the p-value is less than 0.05, add the significance annotation
        if stats_dict[tract] < 0.05:
            axs[index].annotate('*', xy=(0.5, 0.9), xycoords='axes fraction', ha='center', va='center',
                                fontsize=30, color='black')

        axs[index].set_xlabel('')
        axs[index].set_ylabel(metric_to_axis[metric], fontsize=TICK_FONT_SIZE)
        axs[index].tick_params(axis='both', which='major', labelsize=TICK_FONT_SIZE)

        # Add title
        axs[index].set_title(tract.replace('\n', ' '), fontsize=LABEL_FONT_SIZE-2)

        # Add horizontal grid
        axs[index].yaxis.grid(True)

    axs[11].remove()  # remove the last unused subplot

    # Create custom legend for hue
    markers = [Line2D([0], [0], color=value, linestyle='-', linewidth=2, alpha=0.5)
               for value in ['black', 'red']]
    # Insert legend below subplots, NB - this line has to be below the plt.tight_layout()
    legend = fig.legend(markers, unique_groups, loc='lower left', bbox_to_anchor=(0.7, 0.93),
                        bbox_transform=plt.gcf().transFigure, ncol=len(unique_groups), fontsize=TICK_FONT_SIZE)
    # Change box's frame color to black
    frame = legend.get_frame()
    frame.set_edgecolor('black')
    # Add title to the legend
    legend.set_title(hue, prop={'size': TICK_FONT_SIZE})

    # Set main title with number of subjects
    fig.suptitle(f'{metric} at C3 level (above the compression)\n'
                 f'Number of subjects: {number_of_subjects}',
                 fontsize=LABEL_FONT_SIZE)

    # Save the figure
    fig.tight_layout()
    fig.savefig(fname_out, dpi=300)
    plt.close(fig)
    print(f'Figure saved to {fname_out}')


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
    # XLSX file with the group and sex columns
    xlsx_file_path = os.path.abspath(os.path.expanduser(args.xlsx_table))

    if not os.path.isfile(csv_file_path):
        raise ValueError(f'ERROR: {args.i} does not exist.')

    if not os.path.isfile(exclude_file_path):
        raise ValueError(f'ERROR: {args.exclude_file} does not exist.')

    if not os.path.isfile(xlsx_file_path):
        raise ValueError(f'ERROR: {args.xlsx_table} does not exist.')

    # Fetch metric from file_path, e.g., get FA from DWI_FA.csv
    metric = os.path.basename(csv_file_path).split('_')[1].split('.')[0]

    # -------------------------------
    # Read and prepare the data
    # -------------------------------
    # Read the CSV file with DTI metrics
    print(f'Reading {csv_file_path}...')
    df = read_csv_file(csv_file_path, columns_to_read=['Filename', 'VertLevel', 'Label', 'MAP()'])

    # Fetch participant and session using lambda function
    df['Participant'], df['Session'] = zip(*df['Filename'].map(lambda x: fetch_participant_and_session(x)))
    # Drop the 'Filename' column
    df.drop(columns=['Filename'], inplace=True)

    # Rename entries in the "Label" column using label_to_tract
    df['Label'] = df['Label'].map(label_to_tract)

    # Print number of unique subjects
    print(f'Number of unique subjects before dropping: {df["Participant"].nunique()}')

    # Get the list of subjects to exclude
    subjects_to_exclude = read_yaml_file(file_path=exclude_file_path, key='DWI')
    # Get the list of subjects with hyperintense lesions on T2w images
    subject_lesions = read_yaml_file(file_path=exclude_file_path, key='T2w_lesions')

    # Remove session (after the first '_') from the list of subjects to exclude
    subjects_to_exclude = [subject.split('_')[0] for subject in subjects_to_exclude]
    # Remove session (after the first '_') from the list of subjects with hyperintense lesions
    subject_lesions = [subject.split('_')[0] for subject in subject_lesions]

    # Remove subjects to exclude
    df = df[~df['Participant'].isin(subjects_to_exclude)]

    # Create a new column "T2w hyperintensity" and set it to 1 for subjects in the `subject_lesions` list
    df['T2w hyperintensity'] = 0
    df.loc[df['Participant'].isin(subject_lesions), 'T2w hyperintensity'] = 1

    VERT_LEVEL = args.vert_level
    # Keep only VertLevel specified by VERT_LEVEL
    print(f'VertLevel: {VERT_LEVEL}')
    df = df[df['VertLevel'] == VERT_LEVEL]

    # Read the xlsx file with group and sex
    print(f"Reading {xlsx_file_path}...")
    df_group = read_xlsx_file(xlsx_file_path, columns_to_read=['Group těsně před operací',
                                                               'Datum operace ',
                                                               'Etáž nejtěžší komprese',
                                                               'Pohlaví',
                                                               'Věk v době MRI baseline B',
                                                               'MR B1',
                                                               'MR B2',
                                                               'Datum MRI baseline B',
                                                               'Datum MRI FUP1 B'])

    # Remove white spaces at the end of the columns
    df_group.columns = df_group.columns.str.strip()
    # Remove time from columns with dates
    df_group['Datum operace'] = df_group['Datum operace'].dt.date
    df_group['Datum MRI baseline B'] = df_group['Datum MRI baseline B'].dt.date
    df_group['Datum MRI FUP1 B'] = df_group['Datum MRI FUP1 B'].dt.date

    # Combine 'MR B1' and 'MR B2' into participant_id by 'sub-' + 'MR B1' + 'MR B2'
    df_group['Participant'] = 'sub-' + df_group['MR B1'] + df_group['MR B2']
    # Rename columns
    df_group = df_group.rename(columns={'Group těsně před operací': 'Group before surgery',
                                        'Etáž nejtěžší komprese': 'Maximum compressed level',
                                        'Pohlaví': 'Sex',
                                        'Věk v době MRI baseline B': 'age',
                                        'Datum operace': 'Date of surgery',
                                        'Datum MRI baseline B': 'Date of baseline MRI',
                                        'Datum MRI FUP1 B': 'Date of follow-up MRI'})

    # Merge the df_group into the dataframe with shape metrics (df)
    df = pd.merge(df, df_group[['Participant', 'Group before surgery', 'Maximum compressed level', 'Sex', 'age',
                                'Date of surgery', 'Date of baseline MRI', 'Date of follow-up MRI']],
                  on='Participant', how='left')

    # Recode age into categories
    age_cutoff = 59
    df['Age groups'] = pd.cut(df['age'], bins=[0, age_cutoff, 100], labels=[f'<{age_cutoff}', f'>={age_cutoff}'])

    # Keep only subject with Group before surgery == 1
    #df = df[df['Group before surgery'] == 1]

    # Exclude sub-2284B4723B -- surgery after MR B2 --> see surgery.yml
    df = df[df['Participant'] != 'sub-2284B4723B']

    # Print number of unique subjects
    number_of_subjects = df["Participant"].nunique()
    print(f'CSV file: Number of unique subjects after dropping: {number_of_subjects}')

    # -------------------------------
    # Statistical tests
    # -------------------------------
    # Compute the normality test and paired test for each tract between sessions 1 and 2
    stats_dict = compute_statistics(df)

    # -------------------------------
    # Plotting
    # -------------------------------
    hue_options = [
        None,
        'Group before surgery',
        'T2w hyperintensity',
        'Sex',
        'Maximum compressed level',
        'Age groups'
    ]

    # Raincloud plot (violionplot + boxplot + individual points)
    # fname_out = os.path.join(os.path.dirname(csv_file_path), f'{metric}_rainplot_C{VERT_LEVEL}.png')
    # create_rainplot(df, metric, number_of_subjects, fname_out)

    # Rename Session 1 and Session 2 to Pre-surgery and Post-surgery
    df['Session'] = df['Session'].replace({'Session 1': 'Pre-surgery', 'Session 2': 'Post-surgery'})

    # ----------
    # longitudinal scatter plot
    # ----------
    for hue in hue_options:
        hue_suffix = f'_{hue.lower().replace(" ", "_")}' if hue else ''
        fname_out = os.path.join(os.path.dirname(csv_file_path), f'{metric}_scatter_plots_C{VERT_LEVEL}{hue_suffix}.png')
        create_scatterplot(df, metric, number_of_subjects, hue=hue, fname_out=fname_out)

    # ----------
    # violionplot + swarmplot + lineplot
    # Group before surgery: 1 (asymptomatic), 2 (symptomatic)
    fname_out = os.path.join(os.path.dirname(csv_file_path),
                             f'{metric}_violin_plots_C{VERT_LEVEL}_group_before_surgery.png')
    create_violinplot(df, metric, number_of_subjects, stats_dict, hue='Group before surgery', fname_out=fname_out)
    # T2w hyperintensity: 0 (no hyperintensity), 1 (hyperintensity)
    fname_out = os.path.join(os.path.dirname(csv_file_path),
                             f'{metric}_violin_plots_C{VERT_LEVEL}_T2w_hyperintensity.png')
    create_violinplot(df, metric, number_of_subjects, stats_dict, hue='T2w hyperintensity', fname_out=fname_out)
    # Sex
    fname_out = os.path.join(os.path.dirname(csv_file_path),
                             f'{metric}_violin_plots_C{VERT_LEVEL}_sex.png')
    create_violinplot(df, metric, number_of_subjects, stats_dict, hue='sex', fname_out=fname_out)


if __name__ == '__main__':
    main()
