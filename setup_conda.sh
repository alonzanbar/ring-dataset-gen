#!/bin/bash
# Setup script for conda environment

echo "Creating conda environment 'ring-dataset-gen'..."
conda env create -f environment.yml

echo ""
echo "Environment created! To activate it, run:"
echo "  conda activate ring-dataset-gen"
echo ""
echo "Then you can run the dataset generator:"
echo "  python -m src.cli generate --config configs/mvp.yaml --out output --split train --count 10 --start-idx 0"

