#!/bin/bash
#
# Resample T2w image, SC seg, and discs from session 1 to 0.8 mm isotropic resolution (to match session 2 resolution)
# and compute cord CSA perlevel for the original and resampled resolution.
#
# Usage:
#   ./02_resample_T2w_session1.sh <SUBJECT>
#
#
# Manual segmentations or labels should be located under:
# PATH_DATA/derivatives/labels/SUBJECT/SESSION/<CONTRAST>/
#
# Author: Jan Valosek
#

# The following global variables are retrieved from the caller sct_run_batch
# but could be overwritten by uncommenting the lines below:
# PATH_DATA_PROCESSED="~/data_processed"
# PATH_RESULTS="~/results"
# PATH_LOG="~/log"
# PATH_QC="~/qc"

# Uncomment for full verbose
set -x

# Immediately exit if error
set -e -o pipefail

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT

# Print retrieved variables from the sct_run_batch script to the log (to allow easier debug)
echo "Retrieved variables from from the caller sct_run_batch:"
echo "PATH_DATA: ${PATH_DATA}"
echo "PATH_DATA_PROCESSED: ${PATH_DATA_PROCESSED}"
echo "PATH_RESULTS: ${PATH_RESULTS}"
echo "PATH_LOG: ${PATH_LOG}"
echo "PATH_QC: ${PATH_QC}"

SUBJECT=$1

echo "SUBJECT: ${SUBJECT}"

# get starting time:
start=`date +%s`

# ------------------------------------------------------------------------------
# SCRIPT STARTS HERE
# ------------------------------------------------------------------------------
# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Go to folder where data will be copied and processed
cd $PATH_DATA_PROCESSED

# Copy source images
# Note: we use '/./' in order to include the sub-folder 'ses-0X'
rsync -Ravzh $PATH_DATA/./$SUBJECT .

# Go to subject folder for source images
cd ${SUBJECT}
# remove dwi to save space
rm -r dwi
cd anat

# Define variables
# We do a substitution '/' --> '_' in case there is a subfolder 'ses-0X/'
file="${SUBJECT//[\/]/_}"

# -------------------------------------------------------------------------
# T2w
# -------------------------------------------------------------------------
# Steps:
#   - copy SC seg from derivatives/labels
#   - copy disc labels from derivatives/labels
#   - generate labeled segmentation using init disc labels
#   - resample T2w image, SC seg, and discs to 0.8 mm isotropic resolution (to match session 2 resolution)
#   - compute cord CSA perlevel on original resolution
#   - compute cord CSA perlevel on resampled resolution

file_t2="${file}_T2w"
echo "👉 Processing: ${file_t2}"

# --------------
# Copy SC seg from derivatives/labels
# --------------
FILESEG="${file_t2}_seg"
FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILESEG}.nii.gz"
rsync -avzh ${FILESEGMANUAL} ${FILESEG}.nii.gz

# Copy disc labels from derivatives/labels
FILELABEL="${file_t2}_label-disc"
FILELABELMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILELABEL}.nii.gz"
rsync -avzh ${FILELABELMANUAL} ${FILELABEL}.nii.gz

# Generate labeled segmentation using init disc labels
sct_label_vertebrae -i ${file_t2}.nii.gz -s ${FILESEG}.nii.gz -discfile ${FILELABEL}.nii.gz -c t2 -qc ${PATH_QC} -qc-subject ${file_t2}

# --------------
# Resample T2w image, SC seg, and discs to 0.8 mm isotropic resolution (to match session 2 resolution)
# --------------
# Image
sct_resample -i ${file_t2}.nii.gz -mm 0.8x0.8x0.8 -x spline -o ${file_t2}_r.nii.gz

# For discs, we need to dilate the labels before resampling to avoid losing the labels
# Inspiration: https://github.com/sct-pipeline/csa-atrophy/pull/75
# Note: -x nn is used
sct_maths -i ${FILELABEL}.nii.gz -dilate 2 -o ${FILELABEL}_dilated.nii.gz
sct_resample -i ${FILELABEL}_dilated.nii.gz -mm 0.8x0.8x0.8 -x nn -o ${FILELABEL}_dilated_r.nii.gz
# Use `-cubic-to-point` to make sure the disc label is a single pixel point
sct_label_utils -i ${FILELABEL}_dilated_r.nii.gz -cubic-to-point -o ${FILELABEL}_dilated_r_point.nii.gz

# SC seg
sct_resample -i ${FILESEG}.nii.gz -mm 0.8x0.8x0.8 -x linear -o ${FILESEG}_r.nii.gz
# Binarize the segmentation using 0.5 threshold
sct_maths -i ${FILESEG}_r.nii.gz -thr 0.5 -o ${FILESEG}_r_bin.nii.gz

# Generate labeled segmentation using init disc labels
sct_label_vertebrae -i ${file_t2}_r.nii.gz -s ${FILESEG}_r_bin.nii.gz -discfile ${FILELABEL}_dilated_r_point.nii.gz -c t2 -qc ${PATH_QC} -qc-subject ${file_t2}

# --------------
# Compute cord CSA perlevel on original resolution
# --------------
sct_process_segmentation -i ${FILESEG}.nii.gz -perlevel 1 -vert 2:7 -vertfile ${FILESEG}_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T2w_perlevel.csv -angle-corr 1 -append 1
# Compute cord CSA perlevel on resampled resolution
sct_process_segmentation -i ${FILESEG}_r_bin.nii.gz -perlevel 1 -vert 2:7 -vertfile ${FILESEG}_r_bin_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T2w_perlevel_r.csv -angle-corr 1 -append 1

echo "✅ Done: ${file_t2}"

# ------------------------------------------------------------------------------
# End
# ------------------------------------------------------------------------------
# Display useful info for the log
end="$(date +%s)"
runtime="$((end-start))"
echo
echo "~~~"
echo "SCT version: $(sct_version)"
echo "Ran on:      $(uname -nsr)"
echo "Duration:    $((runtime / 3600))hrs $(( (runtime / 60) % 60))min $((runtime % 60))sec"
echo "~~~"