# Generate figures

## T2w and T2star

Generate figures for morphometric metrics (CSA, AP diameter, ...) for T2w and T2star contrasts. Session 1 vs session 2.
C3 only (above the compression).

```commandline
python 03_generate_violin_plot_T2w_shape_metrics.py -i results/csa-SC_T2s_perlevel.csv -xlsx-table <TABLE>.xlsx -exclude-key T2star_SC
python 03_generate_violin_plot_T2w_shape_metrics.py -i results/csa-SC_T2w_perlevel.csv -xlsx-table <TABLE>.xlsx -exclude-key T2w
```

## DWI

Generate figures for DTI metrics (FA, MD, ...) for individual tracts. Session 1 vs session 2. 
C3 only (above the compression).

```commandline
python 03_generate_violin_plot_T2w_shape_metrics.py -i results/DWI_FA.csv
python 03_generate_violin_plot_T2w_shape_metrics.py -i results/DWI_MD.csv
...
```