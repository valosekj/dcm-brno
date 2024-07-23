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
    # Load file with C3 and C5 labels
    t2w_discs_c3c5_img = Image(t2w_discs_c3c5).change_orientation('RPI')
    data_discs_c3c5 = t2w_discs_c3c5_img.data
    # Keep only the C3 label
    data_discs_c3c5[data_discs_c3c5 != 3] = 0
    # Find non-zero voxels
    _, _, z = data_discs_c3c5.nonzero()

    # Load the T2w image
    t2w_img = Image(t2w_img).change_orientation('RPI')

    # Load the T2w SC segmentation
    t2w_sc_seg = Image(t2w_sc_seg).change_orientation('RPI')

    # Keep only the slice corresponding to the C3 label
    # This is done by cropping the image and SC seg and properly altering the header; details:
    # https://github.com/spinalcordtoolbox/spinalcordtoolbox/blob/master/spinalcordtoolbox/image.py#L1307
    # Note: we do the cropping instead of just getting the slice (using `data_img[:, :, z]`) to be able to do the
    # resampling in the next step
    t2w_img_crop = msct_image.spatial_crop(t2w_img, dict(((2, (int(z), int(z))),)))
    sc_seg_crop = msct_image.spatial_crop(t2w_sc_seg, dict(((2, (int(z), int(z))),)))

    # Resample to 0.8 mm isotropic resolution to make the images from session 1 and session 2 comparable
    # Inspiration:
    # https://github.com/spinalcordtoolbox/spinalcordtoolbox/blob/master/spinalcordtoolbox/reports/slice.py#L282
    t2w_img_crop_r = resample_nib(t2w_img_crop, new_size=[0.8, 0.8, 0.8], new_size_type='mm', interpolation='spline')
    t2w_img_crop_r_data = t2w_img_crop_r.data
    sc_seg_crop_r = resample_nib(sc_seg_crop, new_size=[0.8, 0.8, 0.8], new_size_type='mm', interpolation='linear')
    # Binarize the segmentation using 0.5 threshold
    # https://github.com/spinalcordtoolbox/spinalcordtoolbox/blob/master/spinalcordtoolbox/reports/slice.py#L289
    sc_seg_crop_r_data = sc_seg_crop_r.data
    sc_seg_crop_r_data = (sc_seg_crop_r_data > 0.5) * 1

    # Crop the slice around the SC segmentation
    boundary = 10
    x, y, z = sc_seg_crop_r_data.nonzero()
    x_min, x_max = x.min() - boundary, x.max() + boundary
    y_min, y_max = y.min() - boundary, y.max() + boundary
    data_slice = t2w_img_crop_r_data[x_min:x_max, y_min:y_max]

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
