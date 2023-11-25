#!/bin/bash

cd /Users/valosek/data/results/dcm-brno_2023-11-13/results/

for file in *perslice_PAM50.csv;do
    subject=${file:0:14}
    session1=${file:4:5}
    session2=${file:9:5}
    python /Users/valosek/code/dcm-brno/generate_figures_PAM50_two_sessions.py \
    -path-HC ${SCT_DIR}/data/PAM50_normalized_metrics \
    -ses1 /Users/valosek/data/results/dcm-brno_2023-11-13/results/${subject}_ses-${session1}_T2w_metrics_perslice_PAM50.csv \
    -ses2 /Users/valosek/data/results/dcm-brno_2023-11-13/results/${subject}_ses-${session2}_T2w_metrics_perslice_PAM50.csv \
    -path-out /Users/valosek/data/results/dcm-brno_2023-11-13/figures
done