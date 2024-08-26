#!/bin/bash
#
# Compare T2w images with different resolutions (`run-01`, `run-02`) scanned within the same session:
#   `run-01`: 0.279018 x 0.279018 x 1.300000 mm
#   `run-02`: 0.800000 x 0.800000 x 0.800000 mm
#
# The script does the following steps for each run:
#   - segment the spinal cord using the SCIseg nnUNet model (part of SCT v6.2)
#   - perform vertebral labeling and create C3 and C5 mid-vertebral levels in the cord
#   - compute shape metrics perlevel and perslice
#
# Usage:
#    sct_run_batch \
#     -script 02_compare_T2w_resolutions.sh \
#     -path-data ~/data/experiments/dcm-brno/t2w_resolution_comparison \
#     -path-output ~/data/experiments/dcm-brno/t2w_resolution_comparison_2024-08-26 -jobs 2
#
#
# Manual segmentations or labels should be located under:
# PATH_DATA/derivatives/labels/SUBJECT/SESSION/<CONTRAST>/
#
# Author: Jan Valosek
#

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
# FUNCTIONS
# ------------------------------------------------------------------------------

# Check if manual label already exists. If it does, copy it locally. If it does
# not, perform labeling.
# Create labels in the cord at C3 and C5 mid-vertebral levels (needed for template registration)
label_if_does_not_exist(){
  local file="$1"
  local file_seg="$2"
  local contrast="$3"
  # Copy manual disc labels from derivatives/labels if they exist
  FILELABEL="${file}_label-disc"
  FILELABELMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILELABEL}.nii.gz"
  echo "Looking for manual disc labels: $FILELABELMANUAL"
  if [[ -e $FILELABELMANUAL ]]; then
    echo "✅ Found! Using manual disc labels."
    rsync -avzh $FILELABELMANUAL ${FILELABEL}.nii.gz
    # Generate labeled segmentation using init disc labels
    # Comparison "sct_label_vertebrae -discfile" vs "sct_label_utils -disc":
    # https://github.com/valosekj/dcm-brno/issues/10
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -discfile ${FILELABEL}.nii.gz -c ${contrast} -qc ${PATH_QC} -qc-subject ${file}
    # Add into to log file
    echo "✅ ${FILELABEL}.nii.gz found --> using manual disc labels" >> "${PATH_LOG}/T2w_disc_labels.log"
  else
    echo "❌ Manual disc labels not found. Proceeding with automatic labeling."
    # Generate labeled segmentation
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -c ${contrast} -qc ${PATH_QC} -qc-subject ${file}
    # Add into to log file
    echo "❌ ${FILELABEL}.nii.gz NOT found --> using automatic labeling" >> "${PATH_LOG}/T2w_disc_labels.log"
  fi

  # Create labels in the cord at C3 and C5 mid-vertebral levels (needed for template registration)
  sct_label_utils -i ${file_seg}_labeled.nii.gz -vert-body 3,5 -o ${file}_label-disc_c3c5.nii.gz

}

# Check if manual segmentation already exists (under /derivatives/labels/). If it does, copy it locally. If
# it does not, perform segmentation using SCIseg nnUNet model (part of SCT v6.2).
segment_sc_SCIseg_if_does_not_exist(){
  local file="$1"
  local contrast="$2"   # note that contrast is used only for QC purposes and logging

  FILESEG="${file}_seg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILESEG}.nii.gz"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "✅ Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    # Generate axial QC report
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}
    # Add into to log file
    echo "✅ ${FILESEG}.nii.gz found --> using manual segmentation" >> "${PATH_LOG}/${contrast}_SC_segmentations.log"
  else
    echo "❌ Not found. Proceeding with automatic segmentation using the SCIseg nnUNet model."
    # Run SC segmentation
    sct_deepseg -i ${file}.nii.gz -o ${file}_seg.nii.gz -task seg_sc_lesion_t2w_sci
    # Rename outputs
    mv ${file}_seg_sc_seg.nii.gz ${FILESEG}.nii.gz
    mv ${file}_seg_lesion_seg.nii.gz ${file}_lesion.nii.gz

    # Generate axial QC report
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}
    # Generate lesion QC report -- SC seg has to be provided to crop the image
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -d ${file}_lesion.nii.gz -p sct_deepseg_lesion -qc ${PATH_QC} -qc-subject ${file} -plane axial
    # Add into to log file
    echo "❌ ${FILESEG}.nii.gz NOT found --> segmenting automatically" >> "${PATH_LOG}/${contrast}_SC_segmentations.log"

    if [[ $contrast == "t2" ]]; then
      # Generate sagittal SC QC report (https://github.com/ivadomed/canproco/issues/37#issuecomment-1644497220)
      sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -d ${FILESEG}.nii.gz -p sct_deepseg_lesion -plane sagittal -qc ${PATH_QC} -qc-subject ${file}
    fi

  fi
}

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

cd anat

# Define variables
# We do a substitution '/' --> '_' in case there is a subfolder 'ses-0X/'
file="${SUBJECT//[\/]/_}"

# -------------------------------------------------------------------------
# T2w
# -------------------------------------------------------------------------
# Steps:
#   - segment spinal cord using the SCIseg nnUNet model (part of SCT v6.2)
#   - perform vertebral labeling and create C3 and C5 mid-vertebral levels in the cord
#   - compute shape metrics perlevel and perslice

# Loop over runs
runs=("run-01" "run-02")
for run in ${runs[@]}; do
    file_t2="${file}_${run}_T2w"
    echo "👉 Processing: ${file_t2}"

    # Segment spinal cord (only if it does not exist) using the SCIseg nnUNet model (part of SCT v6.2)
    segment_sc_SCIseg_if_does_not_exist $file_t2 "t2"

    # Perform vertebral labeling (using sct_label_vertebrae) and create C3 and C5 mid-vertebral levels in the cord
    label_if_does_not_exist ${file_t2} ${file_t2}_seg "t2"
    file_label=${file_t2}_label-disc_c3c5
    # Generate QC report for C3 and C5 mid-vertebral levels
    # https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4166#issuecomment-1793499115
    sct_qc -i ${file_t2}.nii.gz -s ${file_label}.nii.gz -p sct_label_utils -qc ${PATH_QC} -qc-subject ${file}

    # --------------
    # Compute shape metrics
    # --------------
    # Compute cord CSA perlevel
    sct_process_segmentation -i ${file_t2}_seg.nii.gz -perlevel 1 -vert 2:7 -vertfile ${file_t2}_seg_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T2w_perlevel.csv -angle-corr 1 -append 1
    # Compute cord CSA perslice
    # Note: we use '-vertfile' to have the information about vertebral levels in the output CSV  file, otherwise the 'VertLevel' column would be empty
    sct_process_segmentation -i ${file_t2}_seg.nii.gz -vertfile ${file_t2}_seg_labeled.nii.gz -perslice 1 -o ${PATH_RESULTS}/csa-SC_T2w_perslice.csv -angle-corr 1 -append 1
    # Normalize to PAM50 template
    sct_process_segmentation -i ${file_t2}_seg.nii.gz -vertfile ${file_t2}_seg_labeled.nii.gz -perslice 1 -normalize-PAM50 1 -angle-corr 1 -o ${PATH_RESULTS}/${file_t2}_metrics_perslice_PAM50.csv

    echo "✅ Done: ${file_t2}"
done

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