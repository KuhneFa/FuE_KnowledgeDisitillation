#!/bin/bash

#SBATCH --job-name="CreateEPK"
#SBATCH --account="p_htw_aim"
#SBATCH --time=00-24:00:00
#SBATCH --partition=alpha
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=6
#SBATCH --gpus-per-node=8
#SBATCH --mem-per-cpu=10312

./llama_70.sh
echo "It works!"
