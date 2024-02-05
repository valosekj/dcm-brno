#!/bin/bash

# Copy dicom data from "DCM-PRO", "DCM-PRO_longitudinal", and "DCM-PRO_NOLOST" (all located at /md3) to
# "dcm-brno/sourcedata"
#
# Usage:
#   cd /md3/
#   ./00a_copy_source_subjects.sh
#

folders="DCM-PRO DCM-PRO_longitudinal DCM-PRO_NOLOST"

list_of_subjects="2413B 4629B 2330B 6137B 2372B 2863B 2779B 4786B 2319B 4634B 2249B 4725B 2479B 6195B 2296B 4806B 2383B 6196B 1836B 6029B 2060B 4733B 2390B 4949B 2316B 5038B 2315B 4686B 2259B 4883B 2886B 5253B 2334B 4627B 2284B 4723B 2321B 6243B 2295B 4676B 2407B 5757B 2371B 4687B 2333B 2333B 2417B 2417B 2416B 6027B 2654B 4633B 2450B 6177B 2723B 4648B 2418B 4628B 2411B 4591B 2741B 4963B 2446B 6192B 2481B 6079B 2348B 4595B 2804B 4632B 2590B 4647B 2884B 4714B 2887B 4699B 2599B 4623B 2358B 4598B 2600B 4616B 2902B 4626B 2774B 4763B 2644B 5869B 2667B 6188B 3075B 6206B 2988B 6186B 2773B 4661B 3132B 4599B 3281B 4590B 3207B 4664B 3427B 4966B 3232B 5049B 3261B 4658B 3289B 4615B 3782B 6193B 4196B 5202B 4403B 5238B 4793B 6025B 3793B 4681B 2825B 4881B 2750B 4646B"

# Iterate through the subjects
for subject in $list_of_subjects;do
	# Iterate through the folders
	for folder in $folders;do
	    if [ -d "${folder}/dicom/sub-${subject}" ]; then
	        echo "$subject exists in $folder."
	        cp -r ${folder}/dicom/sub-${subject} dcm-brno/sourcedata
	    fi
	done
done
