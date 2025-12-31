# Quick Start Guide

## Step 1: Create and Activate Conda Environment

```bash
cd /Users/azanbar/code/jewelrai/ring-dataset-gen

# Create the conda environment
conda env create -f environment.yml

# Activate the environment
conda activate ring-dataset-gen
```

## Step 2: Verify Blender is Available

```bash
# Check if Blender is in PATH
blender --version

# If not found, set the BLENDER_PATH environment variable
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

## Step 3: Run Dataset Generation

### Test Run (10 samples)
```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split train \
    --count 10 \
    --start-idx 0
```

### Full Dataset Generation

**Train split (1000 samples):**
```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split train \
    --count 1000 \
    --start-idx 0
```

**Validation split (200 samples):**
```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split val \
    --count 200 \
    --start-idx 0
```

**Test split (200 samples):**
```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split test \
    --count 200 \
    --start-idx 0
```

## Command-Line Options

- `--config`: Path to YAML configuration file (required)
- `--out`: Output directory root (required)
- `--split`: Dataset split name: `train`, `val`, or `test` (required)
- `--count`: Number of samples to generate (required)
- `--start-idx`: Starting sample index (default: 0)
- `--blender-path`: Path to Blender executable (optional, auto-detected if not provided)

## Output Structure

After generation, you'll have:

```
output/
  train/
    sample_000000/
      rgb.png          # Rendered RGB image
      mask_ring.png    # Ring body mask (binary)
      mask_inner.png   # Inner hole mask (binary)
      meta.json        # Complete metadata
    sample_000001/
      ...
```

## Expected Runtime

- **CPU rendering**: ~10-30 seconds per sample
- **10 samples**: ~2-5 minutes
- **1000 samples**: ~3-5 hours

## Troubleshooting

**If Blender is not found:**
```bash
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

**If you get import errors:**
```bash
conda activate ring-dataset-gen
pip install -e .
```

**To resume from a specific index:**
```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split train \
    --count 100 \
    --start-idx 500  # Resume from sample 500
```

