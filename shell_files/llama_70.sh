#!/bin/bash

echo "Start of the script"
conda init
source ~/.bashrc
conda activate /home/faku637g/user-kernel/conda-ollama-kernel
cd /data/horse/ws/faku637g-specimen
echo "Now the pwd follows"
pwd
python hf_create_llama_70.py
echo "The script works"
