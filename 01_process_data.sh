#!/bin/bash
#
# Process data.
#
# Note: conda environment with nnUNetV2 is required to run this script.
# For details how to install nnUNetV2, see:
# https://github.com/ivadomed/utilities/blob/main/quick_start_guides/nnU-Net_quick_start_guide.md#installation
#
# Usage:
#   ./01_process_data.sh <SUBJECT>
#
#
# Manual segmentations or labels should be located under:
# PATH_DATA/derivatives/labels/SUBJECT/<CONTRAST>/
#
# Author: Jan Valosek
# Inspired by: https://github.com/spine-generic/spine-generic/blob/master/process_data.sh
#

# The following global variables are retrieved from the caller sct_run_batch
# but could be overwritten by uncommenting the lines below:
# PATH_DATA_PROCESSED="~/data_processed"
# PATH_RESULTS="~/results"
# PATH_LOG="~/log"
# PATH_QC="~/qc"
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
PATH_NNUNET_SCRIPT=$2
PATH_NNUNET_MODEL=$3

echo "SUBJECT: ${SUBJECT}"
echo "PATH_NNUNET_SCRIPT: ${PATH_NNUNET_SCRIPT}"
echo "PATH_NNUNET_MODEL: ${PATH_NNUNET_MODEL}"

# get starting time:
start=`date +%s`

# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------

# Check if manual label already exists. If it does, copy it locally. If it does
# not, perform labeling.
label_if_does_not_exist(){
  local file="$1"
  local file_seg="$2"
  local contrast="$3"
  # Update global variable with segmentation file name
  FILELABEL="${file}_label-disc"
  FILELABELMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILELABEL}.nii.gz"
  echo "Looking for manual disc labels: $FILELABELMANUAL"
  if [[ -e $FILELABELMANUAL ]]; then
    echo "Found! Using manual disc labels."
    rsync -avzh $FILELABELMANUAL ${FILELABEL}.nii.gz
    # Generate labeled segmentation using init disc labels
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -discfile ${FILELABEL}.nii.gz -c ${contrast} -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "Manual disc labels not found. Proceeding with automatic labeling."
    # Generate labeled segmentation
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -c ${contrast} -qc ${PATH_QC} -qc-subject ${file}
  fi

  # Create labels in the cord at C3 and C5 mid-vertebral levels (needed for template registration)
  sct_label_utils -i ${file_seg}_labeled.nii.gz -vert-body 3,5 -o ${file}_label-disc_c3c5.nii.gz

}

# Check if manual segmentation already exists (under /derivatives/labels/). If it does, copy it locally. If
# it does not, perform segmentation using SCIseg nnUNet model
# https://github.com/ivadomed/model_seg_sci/tree/r20231108
segment_sc_nnUNet_if_does_not_exist(){
  local file="$1"
  local contrast="$2"   # note that contrast is used only for QC purposes

  FILESEG="${file}_seg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/${folder_contrast}/${FILESEG}.nii.gz"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "Not found. Proceeding with automatic segmentation using the SCIseg nnUNet model."
    # Run SC segmentation
    python ${PATH_NNUNET_SCRIPT} -i ${file}.nii.gz -o ${FILESEG}.nii.gz -path-model ${PATH_NNUNET_MODEL} -pred-type sc
    # Generate axial QC report
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}

    if [[ $contrast == "t2" ]]; then
      # Generate sagittal QC report
      sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -d ${FILESEG}.nii.gz -p sct_deepseg_lesion -plane sagittal -qc ${PATH_QC} -qc-subject ${file}
    fi

  fi
}

# Check if manual segmentation already exists (under /derivatives/labels/). If it does, copy it locally. If
# it does not, perform segmentation using sct_deepseg_sc.
segment_if_does_not_exist(){
  local file="$1"
  local contrast="$2"
  # Find contrast
  if [[ $contrast == "dwi" ]]; then
    folder_contrast="dwi"
  else
    folder_contrast="anat"
  fi
  # Update global variable with segmentation file name
  FILESEG="${file}_seg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/${folder_contrast}/${FILESEG}.nii.gz"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg_sc -i ${file}.nii.gz -c $contrast -qc ${PATH_QC} -qc-subject ${file}
  fi
}

# Check if manual segmentation already exists. If it does, copy it locally. If
# it does not, perform seg.
segment_gm_if_does_not_exist(){
  local file="$1"
  local contrast="$2"
  # Update global variable with segmentation file name
  FILESEG="${file}_gmseg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT}/anat/${FILESEG}-manual.nii.gz"
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_gm -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg_gm -i ${file}.nii.gz -qc ${PATH_QC} -qc-subject ${file}
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
cd ${SUBJECT}/anat

# Define variables
# We do a substitution '/' --> '_' in case there is a subfolder 'ses-0X/'
file="${SUBJECT//[\/]/_}"

## -------------------------------------------------------------------------
## T1w
## -------------------------------------------------------------------------
#file_t1="${file}_T1w"
#
## Check the resolution of the T1w image
## The following command returns the voxel size in mm, e.g. [1.0,  1.0,  1.0,  1.0]
#pixdim_val=$(sct_image -i ${file_t1}.nii.gz -header | grep pixdim | awk -F'[\t,]' '{printf "%s, %s, %s, %s]\n", $3, $4, $5, $6}')
#if [[ $pixdim_val == "[1.0,  1.0,  1.0,  1.0]" ]];then
#    echo "spine-generic resolution. Continuing...";
#    echo "$file" >> $PATH_LOG/spine-generic_protocol.log
#else
#    echo "non spine-generic resolution. Exiting...";
#    echo "$file" >> $PATH_LOG/non_spine-generic_protocol.log
#    exit 1;
#fi
#
## Segment spinal cord (only if it does not exist)
#segment_if_does_not_exist $file_t1 "t1"
#
## Perform vertebral labeling and create mid-vertebral levels in the cord
#label_if_does_not_exist ${file_t1} ${file_t1}_seg "t1"
#file_label=${file_t1}_label-disc_c3c5
## Register to PAM50 template
#sct_register_to_template -i ${file_t1}.nii.gz -s ${file_t1}_seg.nii.gz -l ${file_label}.nii.gz -c t1 -param step=1,type=seg,algo=centermassrot:step=2,type=seg,algo=syn,slicewise=1,smooth=0,iter=5:step=3,type=im,algo=syn,slicewise=1,smooth=0,iter=3 -qc ${PATH_QC} -qc-subject ${file}
## Rename warping fields for clarity
#mv warp_template2anat.nii.gz warp_template2T1w.nii.gz
#mv warp_anat2template.nii.gz warp_T1w2template.nii.gz
#
## Compute cord CSA perlevel and perslice
#sct_process_segmentation -i ${file_t1}_seg.nii.gz -perlevel 1 -vertfile ${file_t1}_seg_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T1w_perlevel.csv -append 1
#sct_process_segmentation -i ${file_t1}_seg.nii.gz -perslice 1 -o ${PATH_RESULTS}/csa-SC_T1w_perslice.csv -append 1

# -------------------------------------------------------------------------
# T2w
# -------------------------------------------------------------------------
file_t2="${file}_T2w"

# Segment spinal cord (only if it does not exist) using the SCIseg nnUNet model
segment_sc_nnUNet_if_does_not_exist $file_t2 "t2"

# Perform vertebral labeling and create mid-vertebral levels in the cord
label_if_does_not_exist ${file_t2} ${file_t2}_seg "t2"
file_label=${file_t2}_label-disc_c3c5
# Generate QC report: https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4166#issuecomment-1793499115
sct_qc -i ${file_t2}.nii.gz -s ${file_label}.nii.gz -p sct_label_utils  -qc ${PATH_QC} -qc-subject ${file}

# Register to PAM50 template
sct_register_to_template -i ${file_t2}.nii.gz -s ${file_t2}_seg.nii.gz -l ${file_label}.nii.gz -c t2 -param step=1,type=seg,algo=centermassrot:step=2,type=seg,algo=syn,slicewise=1,smooth=0,iter=5:step=3,type=im,algo=syn,slicewise=1,smooth=0,iter=3 -qc ${PATH_QC} -qc-subject ${file}
# Rename warping fields for clarity
mv warp_template2anat.nii.gz warp_template2T2w.nii.gz
mv warp_anat2template.nii.gz warp_T2w2template.nii.gz

# Compute cord CSA perlevel
sct_process_segmentation -i ${file_t2}_seg.nii.gz -perlevel 1 -vertfile ${file_t2}_seg_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T2w_perlevel.csv -append 1
# Compute cord CSA perslice
sct_process_segmentation -i ${file_t2}_seg.nii.gz -perslice 1 -o ${PATH_RESULTS}/csa-SC_T2w_perslice.csv -append 1
# Normalize to PAM50 template
sct_process_segmentation -i ${file_t2}_seg.nii.gz -vertfile ${file_t2}_seg_labeled.nii.gz -perslice 1 -normalize-PAM50 1 -o ${PATH_RESULTS}/${file_t2}_metrics_perslice_PAM50.csv

# -------------------------------------------------------------------------
# T2s
# ------------------------------------------------------------------------------
file_t2s="${file}_T2star"

# Bring T2w vertebral levels into T2s space
sct_register_multimodal -i ${file_t2}_seg_labeled.nii.gz -d ${file_t2s}.nii.gz -o ${file_t2}_seg_labeled2${file_t2s}.nii.gz -identity 1 -x nn
sct_qc -i ${file_t2s}.nii.gz -s ${file_t2}_seg_labeled2${file_t2s}.nii.gz -p sct_label_vertebrae -qc ${PATH_QC} -qc-subject ${file}

# Segment gray matter (only if it does not exist)
segment_gm_if_does_not_exist $file_t2s "t2s"
file_t2s_seg=$FILESEG
# Segment spinal cord (only if it does not exist) using the SCIseg nnUNet model
segment_sc_nnUNet_if_does_not_exist $file_t2s "t2s"
file_t2s_scseg=$FILESEG

# Compute the gray matter and cord CSA perlevel
# NB: Here we set -no-angle 1 because we do not want angle correction: it is too
# unstable with GM seg, and t2s data were acquired orthogonal to the cord anyways.
sct_process_segmentation -i ${file_t2s_seg}.nii.gz -perlevel 1 -vert 3:4 -vertfile ${file_t2}_seg_labeled2${file_t2s}.nii.gz -o ${PATH_RESULTS}/csa-GM_T2s_perlevel.csv -append 1
sct_process_segmentation -i ${file_t2s_scseg}.nii.gz -perlevel 1 -vert 3:4 -vertfile ${file_t2}_seg_labeled2${file_t2s}.nii.gz -o ${PATH_RESULTS}/csa-SC_T2s_perlevel.csv -append 1

# DWI
# ------------------------------------------------------------------------------
cd ../dwi

echo "Done"
exit

file_dwi="${file}_dwi"

file_bval=${file_dwi}.bval
file_bvec=${file_dwi}.bvec
# Separate b=0 and DW images
sct_dmri_separate_b0_and_dwi -i ${file_dwi}.nii.gz -bvec ${file_bvec}
# Get centerline
sct_get_centerline -i ${file_dwi}_dwi_mean.nii.gz -c dwi -qc ${PATH_QC} -qc-subject ${file}
# Create mask to help motion correction and for faster processing
sct_create_mask -i ${file_dwi}_dwi_mean.nii.gz -p centerline,${file_dwi}_dwi_mean_centerline.nii.gz -size 30mm
# Motion correction
sct_dmri_moco -i ${file_dwi}.nii.gz -bvec ${file_dwi}.bvec -m mask_${file_dwi}_dwi_mean.nii.gz -x spline
file_dwi=${file_dwi}_moco
file_dwi_mean=${file_dwi}_dwi_mean
# Segment spinal cord (only if it does not exist)
segment_if_does_not_exist ${file_dwi_mean} "dwi"
file_dwi_seg=$FILESEG
# Register template->dwi (using template-T1w as initial transformation)
sct_register_multimodal -i $SCT_DIR/data/PAM50/template/PAM50_t1.nii.gz -iseg $SCT_DIR/data/PAM50/template/PAM50_cord.nii.gz -d ${file_dwi_mean}.nii.gz -dseg ${file_dwi_seg}.nii.gz -param step=1,type=seg,algo=centermass:step=2,type=im,algo=syn,metric=CC,iter=5,gradStep=0.5 -initwarp ../anat/warp_template2T1w.nii.gz -initwarpinv ../anat/warp_T1w2template.nii.gz
# Rename warping field for clarity
mv warp_PAM50_t12${file_dwi_mean}.nii.gz warp_template2dwi.nii.gz
mv warp_${file_dwi_mean}2PAM50_t1.nii.gz warp_dwi2template.nii.gz
# Warp template
sct_warp_template -d ${file_dwi_mean}.nii.gz -w warp_template2dwi.nii.gz -qc ${PATH_QC} -qc-subject ${file}
# Create mask around the spinal cord (for faster computing)
sct_maths -i ${file_dwi_seg}.nii.gz -dilate 1 -shape ball -o ${file_dwi_seg}_dil.nii.gz

# Compute DTI model
sct_dmri_compute_dti -i ${file_dwi}.nii.gz -bvec ${file_bvec} -bval ${file_bval} -method standard -m ${file_dwi_seg}_dil.nii.gz

# Compute FA, MD and RD in white matter (WM) between C2 and C5 vertebral levels
sct_extract_metric -i dti_FA.nii.gz -f label/atlas -l 51 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_FA.csv -append 1
sct_extract_metric -i dti_MD.nii.gz -f label/atlas -l 51 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_MD.csv -append 1
sct_extract_metric -i dti_RD.nii.gz -f label/atlas -l 51 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_RD.csv -append 1
# Compute FA, MD and RD in lateral corticospinal tracts (LCST) between C2 and C5 vertebral levels
sct_extract_metric -i dti_FA.nii.gz -f label/atlas -l 4,5 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_FA_LCST.csv -append 1 -combine 1
sct_extract_metric -i dti_MD.nii.gz -f label/atlas -l 4,5 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_MD_LCST.csv -append 1 -combine 1
sct_extract_metric -i dti_RD.nii.gz -f label/atlas -l 4,5 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_RD_LCST.csv -append 1 -combine 1
# Compute FA, MD and RD in dorsal columns (DC) between C2 and C5 vertebral levels
sct_extract_metric -i dti_FA.nii.gz -f label/atlas -l 53 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_FA_DC.csv -append 1
sct_extract_metric -i dti_MD.nii.gz -f label/atlas -l 53 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_MD_DC.csv -append 1
sct_extract_metric -i dti_RD.nii.gz -f label/atlas -l 53 -vert 2:5 -method map -o ${PATH_RESULTS}/DWI_RD_DC.csv -append 1

# See this file for more info about labels and tracts:
# https://github.com/spinalcordtoolbox/spinalcordtoolbox/blob/master/documentation/source/overview/concepts/info_label-atlas.txt

# Go back to parent folder
cd ..

# ------------------------------------------------------------------------------
# Verify presence of output files and write log file if error
# ------------------------------------------------------------------------------
FILES_TO_CHECK=(
  "anat/${file}_T1w_seg.nii.gz"
  "anat/${file}_T2w_seg.nii.gz"
  "anat/label_axT1w/template/PAM50_levels.nii.gz"
  "anat/${file}_T2star_gmseg.nii.gz"
  "dwi/dti_FA.nii.gz"
  "dwi/dti_MD.nii.gz"
  "dwi/dti_RD.nii.gz"
  "dwi/label/atlas/PAM50_atlas_00.nii.gz"
)
for file_to_check in ${FILES_TO_CHECK[@]}; do
  if [[ ! -e $file ]]; then
    echo "${SUBJECT}/${file_to_check} does not exist" >> $PATH_LOG/_error_check_output_files.log
  fi
done

# ------------------------------------------------------------------------------
# End
# ------------------------------------------------------------------------------
# Display useful info for the log
end=`date +%s`
runtime=$((end-start))
echo
echo "~~~"
echo "SCT version: `sct_version`"
echo "Ran on:      `uname -nsr`"
echo "Duration:    $(($runtime / 3600))hrs $((($runtime / 60) % 60))min $(($runtime % 60))sec"
echo "~~~"