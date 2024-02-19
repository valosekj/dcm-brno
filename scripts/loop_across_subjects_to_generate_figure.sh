#!/bin/bash
#
# Usage:
#    cd ${HOME}/code/dcm-brno/scripts
#    loop_across_subjects_to_generate_figure.sh PATH_RESULTS
#


# Check if the user has provided the path to the results, if not, print the usage and exit
if [ -z "$1" ]; then
    echo "Usage: $0 PATH_RESULTS"
    echo "Example: $0 /Users/user/results/dcm-brno_2024-02-19"
    exit 1
fi

PATH_RESULTS=$1

for file in ${PATH_RESULTS}/results/*perslice_PAM50.csv;do
    subject=${file:0:14}
    session1=${file:4:5}
    session2=${file:9:5}

    # Check if the subject is listed in the exclusion list (exclude.yml), if so, skip it
    if grep -q $subject ${HOME}/code/dcm-brno/exclude.yml; then
        echo "Subject ${subject} is listed in the exclusion list. Skipping."
        continue
    fi

    echo "Processing ${subject} ${session1} ${session2} ..."
    python ${HOME}/code/dcm-brno/scripts/generate_figures_PAM50_two_sessions.py \
    -path-HC ${SCT_DIR}/data/PAM50_normalized_metrics \
    -ses1 ${PATH_RESULTS}/results/${subject}_ses-${session1}_T2w_metrics_perslice_PAM50.csv \
    -ses2 ${PATH_RESULTS}/results/${subject}_ses-${session2}_T2w_metrics_perslice_PAM50.csv \
    -path-out ${PATH_RESULTS}/figures
done