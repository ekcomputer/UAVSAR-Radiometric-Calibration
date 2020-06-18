#!/usr/local/bin/bash

#SBATCH --job-name=radiocal_workflow
#SBATCH --mem-per-cpu=32G
#SBATCH --cpus-per-task=8
#SBATCH --export=ALL
# #SBATCH -n 1 -c 4 -N 1
#SBATCH -o /home/ekyzivat/slurm-logs/stdout/slurm_radiocal_example_script.j.%J.out # -o is stdout # must use full, absolute path
#SBATCH -e /home/ekyzivat/slurm-logs/stderr/slurm_radiocal_example_script.j.%J.err # -e is stderr

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