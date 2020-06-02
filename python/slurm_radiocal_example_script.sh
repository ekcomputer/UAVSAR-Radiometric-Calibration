#!/usr/local/bin/bash

# #SBATCH -e ~/slurm-logs/radiocal_example_script.py.%J.err # -e is stderr
# #SBATCH -o ~/slurm-logs/radiocal_example_script.py.%J.out # -o is stdout
#SBATCH --job-name=radiocal_workflow
#SBATCH --mem-per-cpu=32G
#SBATCH --cpus-per-task=8
#SBATCH --export=ALL

## Reporting  start #############################
start_time="$(date -u +%s)"
echo "  Job: $SLURM_ARRAY_JOB_ID"
echo
echo "  Started on:           " `/bin/hostname -s`
echo "  Started at:           " `/bin/date`
#################################################

source activate base

# srun allows printing in real time? No
python /home/ekyzivat/scripts/UAVSAR-Radiometric-Calibration-fork/python/radiocal_example_script_ek.py

## Reporting stop ###############################
echo "  Finished at:           " `date`
end_time="$(date -u +%s)"
elapsed="$(($end_time-$start_time))"
echo "  Minutes elapsed:       " $(($elapsed / 60))
echo
#################################################