# Process data

## Process data

Process data with [the process_data.sh script](process_data.sh). The script is run across all subjects in the 
BIDS dataset using the `sct_run_batch` wrapper script:

```console
sct_run_batch -config process_data_config.json
```

## Do manual corrections

Intervertebral disc labels:

```console
$ python manual_correction.py -path-img data_to_correct -config dcm-brno_2023-11-11_disc_label_to_correct.yml -path-out dcm-brno/derivatives/labels
```
