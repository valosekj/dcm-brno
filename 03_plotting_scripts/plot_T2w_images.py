"""
Plot axial slice from T2w image corresponding to the C3 mid-vertebral level.
The slices are plotted for session 1 (before surgery) and session 2 (after surgery).

The script:
    - reads T2w.nii.gz, T2w_seg.nii.gz and T2w_label-disc_c3c5.nii.gz files
    - gets slice from the T2w.nii.gz image corresponding to C3 label from the T2w_label-disc_c3c5.nii.gz image
    - crops the slice around the SC segmentation from the T2w_seg.nii.gz image
    - plots the slices from all subjects into a single figure with number of rows equal to the number of subjects and
        two columns (one for each session)


The script requires the SCT conda environment to be activated:
    source ${SCT_DIR}/python/etc/profile.d/conda.sh
    conda activate venv_sct

Example usage:
    python plot_T2w_images.py -i ~/data_processed

Author: Jan Valosek
"""

import os
import argparse
import collections
import pickle

import numpy as np
from matplotlib import pyplot as plt

import spinalcordtoolbox.image as msct_image
from spinalcordtoolbox.image import Image
from spinalcordtoolbox.resampling import resample_nib


def get_parser():
    """
    parser function
    """

    parser = argparse.ArgumentParser(
        description='Plot axial slice from T2w image corresponding to the C3 mid-vertebral level.'
                    'The slices are plotted for session 1 (before surgery) and session 2 (after surgery).',
        prog=os.path.basename(__file__).strip('.py')
    )
    parser.add_argument(
        '-i',
        metavar="<folder>",
        required=True,
        type=str,
        help='Path to BIDS-organized data_processed folder containing T2w.nii.gz and T2w_label-disc_c3c5.nii.gz '
             'images. '
             'Example: ~/<your_dataset>/data_processed'
    )

    return parser


def get_c3_slice(t2w_discs_c3c5, t2w_img, t2w_sc_seg):
    """
    Get the axial slice from the T2w image corresponding to the C3 mid-vertebral level.
    :param t2w_discs_c3c5: Path to the T2w_label-disc_c3c5.nii.gz image with C3 and C5 mid-vertebral labels
    :param t2w_img: Path to the T2w
    :param t2w_sc_seg: Path to the T2w SC segmentation
    :return: Axial slice from the T2w image corresponding to the C3 mid-vertebral level
    """
    # Create a temporary folder based on t2w_discs_c3c5 path
    tmp_folder = os.path.join(os.path.dirname(t2w_discs_c3c5), 'tmp')
    # Create a temporary folder
    os.makedirs(tmp_folder, exist_ok=True)

    # Resample images to 0.8 mm isotropic resolution to make the images from session 1 and session 2 comparable
    # For discs, we need to dilate the labels before resampling to avoid losing the labels
    # Inspiration: https://github.com/sct-pipeline/csa-atrophy/pull/75
    # Note: -x nn is used
    os.system(f'sct_maths -i {t2w_discs_c3c5} -dilate 2 -o {os.path.join(tmp_folder, "discs_c3c5_dilated.nii.gz")}')
    os.system(f'sct_resample -i {os.path.join(tmp_folder, "discs_c3c5_dilated.nii.gz")} -mm 0.8x0.8x0.8 -x nn -o '
              f'{os.path.join(tmp_folder, "discs_c3c5_dilated_r.nii.gz")}')
    os.system(f'sct_label_utils -i {os.path.join(tmp_folder, "discs_c3c5_dilated_r.nii.gz")} -cubic-to-point -o '
              f'{os.path.join(tmp_folder, "discs_c3c5_dilated_r_point.nii.gz")}')
    t2w_discs_c3c5_tmp = os.path.join(tmp_folder, "discs_c3c5_dilated_r_point.nii.gz")

    # Image
    os.system(f'sct_resample -i {t2w_img} -mm 0.8x0.8x0.8 -x spline -o {os.path.join(tmp_folder, "t2w_r.nii.gz")}')
    t2w_img_tmp = os.path.join(tmp_folder, "t2w_r.nii.gz")

    # SC seg
    os.system(f'sct_resample -i {t2w_sc_seg} -mm 0.8x0.8x0.8 -x linear -o {os.path.join(tmp_folder, "sc_seg_r.nii.gz")}')
    # Binarize the segmentation using 0.5 threshold
    os.system(f'sct_maths -i {os.path.join(tmp_folder, "sc_seg_r.nii.gz")} -thr 0.5 -o '
              f'{os.path.join(tmp_folder, "sc_seg_r_bin.nii.gz")}')
    t2w_sc_seg_tmp = os.path.join(tmp_folder, "sc_seg_r_bin.nii.gz")

    # Load file with C3 and C5 labels
    t2w_discs_c3c5_img = Image(t2w_discs_c3c5_tmp).change_orientation('RPI')
    data_discs_c3c5 = t2w_discs_c3c5_img.data
    # Keep only the C3 label
    data_discs_c3c5[data_discs_c3c5 != 3] = 0
    # Find non-zero voxels
    _, _, c3_z = data_discs_c3c5.nonzero()
    c3_z = int(c3_z)      # ndarray --> int

    # Load the T2w image
    t2w_img = Image(t2w_img_tmp).change_orientation('RPI')

    # Load the T2w SC segmentation
    t2w_sc_seg = Image(t2w_sc_seg_tmp).change_orientation('RPI')

    # Keep only the slice corresponding to the C3 label
    t2w_img_slice = t2w_img.data[:, :, c3_z]
    t2w_sc_seg_slice = t2w_sc_seg.data[:, :, c3_z]

    # Crop the slice around the SC segmentation
    boundary = 10
    x, y = t2w_sc_seg_slice.nonzero()
    x_min, x_max = x.min() - boundary, x.max() + boundary
    y_min, y_max = y.min() - boundary, y.max() + boundary
    data_slice = t2w_img_slice[x_min:x_max, y_min:y_max]

    # Remove the temporary folder
    os.system(f'rm -rf {tmp_folder}')

    return data_slice


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    dir_path = os.path.abspath(args.i)

    if not os.path.isdir(dir_path):
        raise ValueError(f'ERROR: {args.i} does not exist.')

    dict_slices = collections.defaultdict(dict)

    # Loop across subjects
    for subject in os.listdir(dir_path):
        # Extract session 1 and session 2 from the subject ID
        session1 = 'ses-' + subject[4:9]
        session2 = 'ses-' + subject[9:]
        t2w_session1 = os.path.join(dir_path, subject, session1, 'anat', f'{subject}_{session1}_T2w.nii.gz')
        t2w_session2 = os.path.join(dir_path, subject, session2, 'anat', f'{subject}_{session2}_T2w.nii.gz')
        t2w_sc_session1 = os.path.join(dir_path, subject, session1, 'anat', f'{subject}_{session1}_T2w_seg.nii.gz')
        t2w_sc_session2 = os.path.join(dir_path, subject, session2, 'anat', f'{subject}_{session2}_T2w_seg.nii.gz')
        t2w_discs_c3c5_session1 = os.path.join(dir_path, subject, session1, 'anat',
                                               f'{subject}_{session1}_T2w_label-disc_c3c5.nii.gz')
        t2w_discs_c3c5_session2 = os.path.join(dir_path, subject, session2, 'anat',
                                               f'{subject}_{session2}_T2w_label-disc_c3c5.nii.gz')

        # Check if the files exist
        # If so, get the axial slice from the T2w image corresponding to the C3 mid-vertebral level.
        if os.path.isfile(t2w_session1) and os.path.isfile(t2w_discs_c3c5_session1) and os.path.isfile(t2w_sc_session1):
            print(f'Processing subject: {subject}, session 1')
            dict_slices[subject]['session1'] = get_c3_slice(t2w_discs_c3c5_session1, t2w_session1, t2w_sc_session1)
        if os.path.isfile(t2w_session2) and os.path.isfile(t2w_discs_c3c5_session2) and os.path.isfile(t2w_sc_session2):
            print(f'Processing subject: {subject}, session 2')
            dict_slices[subject]['session2'] = get_c3_slice(t2w_discs_c3c5_session2, t2w_session2, t2w_sc_session2)

    # Save dict_slices to a pickle file
    # This is useful in case you want to plot the slices later without re-running the script
    with open('dict_slices.pkl', 'wb') as f:
        pickle.dump(dict_slices, f)

    # Plot the slices from all subjects into a single figure with number of rows equal to the number of subjects and
    # two columns (one for each session)
    # The slices are plotted for session 1 (before surgery) and session 2 (after surgery)
    # The figure is saved as c3_slices.png
    fig, axs = plt.subplots(len(dict_slices), 2, figsize=(6, 3*len(dict_slices)))
    for i, (subject, slices) in enumerate(dict_slices.items()):
        axs[i, 0].imshow(np.rot90(slices['session1']), cmap='gray')
        axs[i, 0].set_title(f'{subject} - session 1')
        axs[i, 0].axis('off')
        axs[i, 1].imshow(np.rot90(slices['session2']), cmap='gray')
        axs[i, 1].set_title(f'{subject} - session 2')
        axs[i, 1].axis('off')
    plt.tight_layout()
    plt.savefig('c3_slices.png')


if __name__ == '__main__':
    main()
