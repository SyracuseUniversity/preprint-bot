#!/bin/bash
# Activate Conda environment and run the fine-tuning script

eval "$(${HOME}/miniconda3/bin/conda shell.bash hook)"
conda activate gpt2_finetune

python finetune_gpt2.py
  