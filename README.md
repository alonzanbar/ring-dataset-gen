# Ring Dataset Generation

Generate a dataset of RGB images from a Blender scene with camera-only randomization.

## Overview

This tool generates a dataset of images from a Blender scene containing a ring object. The camera pose is randomized while ensuring the ring is always fully visible and properly framed. The tool supports two modes: **validate** (sampling and validation only) and **render** (full pipeline with image rendering and annotations). See `SPEC.md` for full requirements.

## Quick Start

### Basic Usage (Validate Mode)

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py --
```

This will use default settings from `config.json` and validate 100 camera poses (no rendering).

### Render Mode (Full Pipeline)

```bash
# Generate 10 images with rendering and annotations
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode render \
    --num-images 10 \
    --seed 42 \
    --output-dir output/my_dataset
```

### Validate Mode (No Rendering)

```bash
# Test camera sampling and validation without rendering
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode validate \
    --num-images 10 \
    --seed 42
```

### Override Camera Settings

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode render \
    --pitch-min 30 \
    --pitch-max 60 \
    --distance-min 15 \
    --distance-max 30
```

### Use Custom Config File

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode render \
    --config custom_config.json
```

## Modes

The tool supports two operation modes:

- **`validate`** (default): Samples and validates camera poses without rendering. Useful for testing camera sampling parameters and visibility constraints.
- **`render`**: Full pipeline - samples poses, validates them, renders RGB images, and generates annotations. Use this mode to generate the actual dataset.

## Configuration

Default configuration is loaded from `config.json`. All parameters can be overridden via command-line arguments.

### Key Parameters

- `--mode`: Operation mode - `validate` or `render` (default: `validate`)
- `--num-images`: Number of images/poses to generate (default: 100)
- `--seed`: Random seed for reproducibility (default: None)
- `--output-dir`: Output directory (default: output/dataset)
- `--ring-object-name`: Name of ring object in scene (default: "ring")
- `--pitch-min`, `--pitch-max`: Camera elevation range in degrees (default: 15-85)
- `--distance-min`, `--distance-max`: Distance multipliers relative to ring size (default: 5-50)
- `--image-width`, `--image-height`: Image dimensions (default: 1920x1080)
- `--edge-margin`: Safety margin from image edges as fraction (default: 0.07)
- `--min-projected-size`, `--max-projected-size`: Projected size fraction range (default: 0.20-0.35)
- `--max-attempts`: Maximum attempts per sample before rejection (default: 50)

See `--help` for full list of options:

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- --help
```

## Output Structure

### Render Mode Output

```
output/dataset/
├── images/
│   ├── 000000.png
│   ├── 000001.png
│   └── ...
├── annotations.jsonl
└── run_config.json
```

- **`images/`**: Rendered RGB images with deterministic naming (`000000.png`, `000001.png`, etc.)
- **`annotations.jsonl`**: One JSON object per line containing:
  - Image path (relative)
  - Camera extrinsics (matrix_world, position, look_at)
  - Camera intrinsics (width, height, format)
  - Sampled parameters (yaw, pitch, distance, look_at_jitter)
  - Visibility metrics (margin_used, projected_size_fraction, projected_bbox)
  - Sample metadata (index, attempts)
- **`run_config.json`**: Complete run configuration including:
  - Effective config (all values used)
  - Seed
  - Blender version
  - Ring object name

### Validate Mode Output

```
output/dataset/
└── run_config.json
```

Only `run_config.json` is written in validate mode (no images or annotations).

## Features

- **Camera Sampling**: Hemisphere-based sampling with configurable yaw, pitch, and distance ranges
- **Visibility Validation**: Ensures ring is fully visible with margin and proper size constraints
- **Auto-correction**: Automatically adjusts camera pose to satisfy visibility constraints
- **Rejection Tracking**: Tracks and reports rejection reasons for diagnostics
- **GPU Acceleration**: Automatic GPU detection and usage for faster rendering (falls back to CPU)
- **Reproducibility**: Complete configuration tracking for exact reproduction of results

## Testing

### Quick Test (Validate Mode)

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode validate \
    --num-images 5 \
    --seed 42
```

### Full Test (Render Mode)

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --mode render \
    --num-images 5 \
    --seed 42 \
    --output-dir output/test
```

### Test Render Pipeline Only

```bash
./test_render.sh
```

## Requirements

- Blender 5.0+ (headless mode)
- Python 3.x
- See `SPEC.md` for detailed requirements

## Project Structure

```
ring-dataset-gen/
├── datasetgen/          # Core modules
│   ├── config.py        # Configuration management
│   ├── scene_introspection.py  # Ring object analysis
│   ├── camera_sampling.py      # Camera pose sampling
│   ├── visibility_checks.py    # Visibility validation
│   ├── render_pipeline.py      # RGB rendering
│   └── annotations.py          # Annotation writing
├── tools/
│   └── generate_ring_dataset.py  # Main entrypoint
├── config.json          # Default configuration
├── SPEC.md             # Full specification
└── README.md           # This file
```

