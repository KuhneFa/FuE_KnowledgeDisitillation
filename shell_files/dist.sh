#!/bin/bash

echo "Start of the script"
conda init
source ~/.bashrc
conda activate /home/faku637g/user-kernel/conda-ollama-kernel
cd /data/horse/ws/faku637g-specimen
python3 distillation.py
echo "The script is running"
