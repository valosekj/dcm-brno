#!/bin/bash
#
# Process data anatomical and DWI data
#
# Requirements:
#   SCT v6.2 and higher (containing the SCIseg and contrast-agnostic models as part of 'sct_deepseg')
#
# Usage:
#   ./02_process_data.sh <SUBJECT>
#
#
# Manual segmentations or labels should be located under:
# PATH_DATA/derivatives/labels/SUBJECT/SESSION/<CONTRAST>/
#
# Author: Jan Valosek
#
# Inspired by:
# https://github.com/spine-generic/spine-generic/blob/master/process_data.sh
# https://github.com/sct-pipeline/spine-park/blob/main/batch_processing.sh
#


# The following global variables are retrieved from the caller sct_run_batch
# but could be overwritten by uncommenting the lines below:
# PATH_DATA_PROCESSED="~/data_processed"
# PATH_RESULTS="~/results"
# PATH_LOG="~/log"
# PATH_QC="~/qc"

# Parameters
vertebral_levels="2:6"  # Vertebral levels to extract metrics from. "2:6" means from C2 to C6 (included)
# List of tracts to extract
# Legend: https://spinalcordtoolbox.com/overview/concepts/pam50.html#white-and-gray-matter-atlas
# Inspiration: Valosek et al., 2021, DOI: 10.1111/ene.15027
# https://github.com/valosekj/valosek_2021_paper/blob/main/extract_metrics_dMRI.sh
tracts=(
  "51"\     # white matter
  "52"\     # gray matter
  "53"\     # dorsal columns
  "54"\     # lateral columns
  "55"\     # ventral columns
  "0,1"\    # left and right fasciculus gracilis
  "2,3"\    # left and right fasciculus cuneatus
  "4,5"\    # left and right lateral corticospinal tract
  "12,13"\  # left and right spinal lemniscus (spinothalamic and spinoreticular tracts)
  "30,31"\  # ventral GM horns
  "34,35"\  # dorsal GM horns
)

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
    echo "${FILELABEL}.nii.gz found --> using manual disc labels" >> "${PATH_LOG}/T2w_disc_labels.log"
  else
    echo "❌ Manual disc labels not found. Proceeding with automatic labeling."
    # Generate labeled segmentation
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -c ${contrast} -qc ${PATH_QC} -qc-subject ${file}
    # Add into to log file
    echo "${FILELABEL}.nii.gz NOT found --> using automatic labeling" >> "${PATH_LOG}/T2w_disc_labels.log"
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
    echo "${FILESEG}.nii.gz found --> using manual segmentation" >> "${PATH_LOG}/${contrast}_SC_segmentations.log"
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
    echo "${FILESEG}.nii.gz NOT found --> segmenting automatically" >> "${PATH_LOG}/${contrast}_SC_segmentations.log"

    if [[ $contrast == "t2" ]]; then
      # Generate sagittal SC QC report (https://github.com/ivadomed/canproco/issues/37#issuecomment-1644497220)
      sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -d ${FILESEG}.nii.gz -p sct_deepseg_lesion -plane sagittal -qc ${PATH_QC} -qc-subject ${file}
    fi

  fi
}

# Check if manual segmentation already exists (under /derivatives/labels/). If it does, copy it locally. If
# it does not, perform segmentation using the contrast-agnostic model (part of SCT v6.2)
segment_sc_CA_if_does_not_exist(){
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
    echo "✅ Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "❌ Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg -i ${file}.nii.gz -task seg_sc_contrast_agnostic -qc ${PATH_QC} -qc-subject ${file}
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
    echo "✅ Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}.nii.gz
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_gm -qc ${PATH_QC} -qc-subject ${file}
  else
    echo "❌ Not found. Proceeding with automatic segmentation."
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

# -------------------------------------------------------------------------
# T2w
# -------------------------------------------------------------------------
# Steps:
#   - segment spinal cord using the SCIseg nnUNet model (part of SCT v6.2)
#   - perform vertebral labeling and create C3 and C5 mid-vertebral levels in the cord
#   - register T2w to PAM50 template using C3 and C5 mid-vertebral levels
#   - compute cord CSA perlevel and perslice

file_t2="${file}_T2w"
echo "👉 Processing: ${file_t2}"

# Segment spinal cord (only if it does not exist) using the SCIseg nnUNet model (part of SCT v6.2)
segment_sc_SCIseg_if_does_not_exist $file_t2 "t2"

# Perform vertebral labeling (using sct_label_vertebrae) and create C3 and C5 mid-vertebral levels in the cord
label_if_does_not_exist ${file_t2} ${file_t2}_seg "t2"
file_label=${file_t2}_label-disc_c3c5
# Generate QC report for C3 and C5 mid-vertebral levels
# https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4166#issuecomment-1793499115
sct_qc -i ${file_t2}.nii.gz -s ${file_label}.nii.gz -p sct_label_utils -qc ${PATH_QC} -qc-subject ${file}

# Register T2w to PAM50 template using C3 and C5 mid-vertebral levels
# TODO: consider removing step 3 (https://github.com/sct-pipeline/spine-park/blob/e3cc60adec6aff45e8f9b716aaa58fd8860effbd/batch_processing.sh#L146 uses only step 1 and 2)
#-param step=1,type=seg,algo=centermassrot:step=2,type=seg,algo=syn,slicewise=1,smooth=0,iter=5:step=3,type=im,algo=syn,slicewise=1,smooth=0,iter=3 \
sct_register_to_template -i ${file_t2}.nii.gz -s ${file_t2}_seg.nii.gz -l ${file_label}.nii.gz -c t2 \
                         -param step=1,type=seg,algo=centermassrot:step=2,type=im,algo=syn,iter=5,slicewise=1,metric=CC,smooth=0 \
                         -qc ${PATH_QC} -qc-subject ${file}
# Rename warping fields for clarity
mv warp_template2anat.nii.gz warp_template2T2w.nii.gz
mv warp_anat2template.nii.gz warp_T2w2template.nii.gz

# Compute cord CSA perlevel
sct_process_segmentation -i ${file_t2}_seg.nii.gz -perlevel 1 -vert 2:7 -vertfile ${file_t2}_seg_labeled.nii.gz -o ${PATH_RESULTS}/csa-SC_T2w_perlevel.csv -append 1
# Compute cord CSA perslice
sct_process_segmentation -i ${file_t2}_seg.nii.gz -perslice 1 -o ${PATH_RESULTS}/csa-SC_T2w_perslice.csv -append 1
# Normalize to PAM50 template
sct_process_segmentation -i ${file_t2}_seg.nii.gz -vertfile ${file_t2}_seg_labeled.nii.gz -perslice 1 -normalize-PAM50 1 -o ${PATH_RESULTS}/${file_t2}_metrics_perslice_PAM50.csv

echo "✅ Done: ${file_t2}"

# -------------------------------------------------------------------------
# T2s
# ------------------------------------------------------------------------------
# Steps:
#   - bring T2w vertebral levels into T2s space (using `-identity 1`)
#   - segment gray matter (only if it does not exist)
#   - segment spinal cord (only if it does not exist) using the SCIseg nnUNet model (part of SCT v6.2)
#   - compute the gray matter and cord CSA perlevel

# Skip T2s processing for problematic subjects listed in exclude.yml
# Note: we have to skip the analysis because we still want to perform DWI processing
if [[ ! $file =~ "sub-3056B6483B_ses-6483B" ]] && [[ ! $file =~ "sub-3758B6378B_ses-6378B" ]] && [[ ! $file =~ "sub-3998B6406B_ses-6406B" ]]; then

    file_t2s="${file}_T2star"
    echo "👉 Processing: ${file_t2s}"

    # Bring T2w vertebral levels into T2s space
    sct_register_multimodal -i ${file_t2}_seg_labeled.nii.gz -d ${file_t2s}.nii.gz -o ${file_t2}_seg_labeled2${file_t2s}.nii.gz -identity 1 -x nn
    sct_qc -i ${file_t2s}.nii.gz -s ${file_t2}_seg_labeled2${file_t2s}.nii.gz -p sct_label_vertebrae -qc ${PATH_QC} -qc-subject ${file}

    # Segment gray matter (only if it does not exist)
    #segment_gm_if_does_not_exist $file_t2s "t2s"
    #file_t2s_seg=$FILESEG
    # Segment spinal cord (only if it does not exist) using the SCIseg nnUNet model (part of SCT v6.2)
    segment_sc_SCIseg_if_does_not_exist $file_t2s "t2s"
    file_t2s_scseg=$FILESEG

    # Compute the gray matter and cord CSA perlevel
    # NB: Here we set -no-angle 1 because we do not want angle correction: it is too
    # unstable with GM seg, and t2s data were acquired orthogonal to the cord anyways.
    #sct_process_segmentation -i ${file_t2s_seg}.nii.gz -perlevel 1 -vert 3:4 -vertfile ${file_t2}_seg_labeled2${file_t2s}.nii.gz -o ${PATH_RESULTS}/csa-GM_T2s_perlevel.csv -append 1
    sct_process_segmentation -i ${file_t2s_scseg}.nii.gz -perlevel 1 -vert 3:4 -vertfile ${file_t2}_seg_labeled2${file_t2s}.nii.gz -o ${PATH_RESULTS}/csa-SC_T2s_perlevel.csv -append 1

    echo "✅ Done: ${file_t2s}"
else
    echo "⚠️ Skipping T2s processing for ${file}."
    echo "⚠️ Skipping T2s processing for ${file}." >> $PATH_LOG/skipped_processing.log
fi
# DWI
# ------------------------------------------------------------------------------
# Steps:
#   - average DWI volumes
#   - get centerline on averaged DWI scan (this is just an initial segmentation to crop the data)
#   - crop data for faster processing
#   - motion correction
#   - average DWI moco volumes
#   - segment spinal cord on averaged DWI moco scan
#   - register to PAM50 template via T2w registration
#   - warp atlas to DWI space
#   - compute DTI model on the cropped moco data
cd ../dwi

# ZOOMit AP phase encoding
file_dwi="${file}_acq-ZOOMit_dir-AP_dwi"
echo "👉 Processing: ${file_dwi}"

file_bval=${file_dwi}.bval
file_bvec=${file_dwi}.bvec

# TODO: try patch2self denoising

# Separate b=0 and DWI volumes; the command will create also a file with the mean DWI ('_dwi_mean.nii.gz')
sct_dmri_separate_b0_and_dwi -i ${file_dwi}.nii.gz -bvec ${file_bvec}

# Get the centerline
# Comparison "contrast-agnostic SC" vs "sct_get_centerline":
# https://github.com/valosekj/dcm-brno/issues/13
sct_get_centerline -i "${file_dwi}"_dwi_mean.nii.gz -c dwi

# Crop data around the centerline for faster processing
# The effect of `-dilate`: https://github.com/valosekj/dcm-brno/issues/14#issuecomment-2210748905
sct_crop_image -i "${file_dwi}".nii.gz -m "${file_dwi}"_dwi_mean_centerline.nii.gz -dilate 35x35x0 -o "${file_dwi}"_crop.nii.gz
file_dwi="${file_dwi}_crop"

# Remove the last six slices due to strong signal dropout
# Context: https://github.com/valosekj/dcm-brno/issues/16#issuecomment-2214198715
sct_crop_image -i "${file_dwi}".nii.gz  -zmin 6 -zmax -1 -o "${file_dwi}_crop".nii.gz
file_dwi="${file_dwi}_crop"

# Motion correction on the cropped data
# Context for 'metric=CC':
# https://github.com/sct-pipeline/spine-park/commit/924e332c3b4836baa087ea740a7837120d0b7cbf
# https://forum.spinalcordmri.org/t/spacing-error-when-running-sct-dmri-moco/487
# https://github.com/valosekj/dcm-brno/issues/16#issuecomment-2217795988
sct_dmri_moco -i ${file_dwi}.nii.gz -bvec ${file_bvec} -x spline -param metric=CC
file_dwi=${file_dwi}_moco
file_dwi_mean=${file_dwi}_dwi_mean

# Segment spinal cord (only if it does not exist) using the contrast-agnostic model (part of SCT v6.2)
segment_sc_CA_if_does_not_exist ${file_dwi_mean} "dwi"
file_dwi_seg=$FILESEG

# Register template->dwi (using T2w-to-template as initial transformation)
# Note: in general for DWI we use the PAM50_t1 contrast, which is close to the dwi contrast; see SCT Course for details
sct_register_multimodal -i $SCT_DIR/data/PAM50/template/PAM50_t1.nii.gz \
                        -iseg $SCT_DIR/data/PAM50/template/PAM50_cord.nii.gz \
                        -d ${file_dwi_mean}.nii.gz -dseg ${file_dwi_seg}.nii.gz \
                        -param step=1,type=seg,algo=centermass:step=2,type=seg,algo=bsplinesyn,slicewise=1,iter=3 \
                        -initwarp ../anat/warp_template2T2w.nii.gz -initwarpinv ../anat/warp_T2w2template.nii.gz \
                        -owarp warp_template2dwi.nii.gz -owarpinv warp_dwi2template.nii.gz \
                        -qc "${PATH_QC}" -qc-subject "${SUBJECT}"

# Warp template and white matter atlas to DWI space
sct_warp_template -d ${file_dwi_mean}.nii.gz -w warp_template2dwi.nii.gz -ofolder label_${file_dwi} -qc ${PATH_QC} -qc-subject ${SUBJECT}

# Generate additional QC to check the registration
# Native DWI image overlaid with warped PAM50_levels
# https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/4166#issuecomment-1773810021
sct_qc -i ${file_dwi_mean}.nii.gz -s label_${file_dwi}/template/PAM50_levels.nii.gz -p sct_label_vertebrae -qc ${PATH_QC} -qc-subject ${SUBJECT}

# Compute DTI metrics on the cropped moco data; the following files will be created: ${file_dwi}_FA, ${file_dwi}_MD, ...
sct_dmri_compute_dti -i ${file_dwi}.nii.gz -bvec ${file_bvec} -bval ${file_bval} -method standard -o ${file_dwi}_

# Bring DRI metrics in the PAM50 space
dti_metrics=(FA MD RD AD)
for dti_metric in ${dti_metrics[@]}; do
  sct_apply_transfo -i ${file_dwi}_${dti_metric}.nii.gz -d $SCT_DIR/data/PAM50/template/PAM50_t1.nii.gz -w warp_dwi2template.nii.gz -o ${file_dwi}_${dti_metric}_PAM50.nii.gz
done

# TODO: compute group DTI maps in the PAM50 space

# Compute DTI metrics in various tracts
for dti_metric in ${dti_metrics[@]}; do
  file_out=${PATH_RESULTS}/DWI_${dti_metric}.csv
  for tract in ${tracts[@]}; do
    sct_extract_metric -i ${file_dwi}_${dti_metric}.nii.gz -f label_${file_dwi}/atlas \
                       -l ${tract} -combine 1 -method map \
                       -vert "${vertebral_levels}" -vertfile label_${file_dwi}/template/PAM50_levels.nii.gz -perlevel 1 \
                       -o ${file_out} -append 1
  done
done

# Go back to parent folder
cd ..

echo "✅ Done: ${file_bval/.bval/}"

# ------------------------------------------------------------------------------
# Verify presence of output files and write log file if error
# ------------------------------------------------------------------------------
FILES_TO_CHECK=(
  "anat/${file_t2}_seg.nii.gz"
  "anat/warp_template2T2w.nii.gz"
  "dwi/${file_dwi}_FA.nii.gz"
)
for file_to_check in ${FILES_TO_CHECK[@]}; do
  if [[ ! -e $file_to_check ]]; then
    echo "${SUBJECT}/${file_to_check} does not exist" >> $PATH_LOG/_error_check_output_files.log
  fi
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