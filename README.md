# Ring Dataset Generator

A reproducible computer-rendered dataset generator for ring inner-diameter estimation. This tool uses Blender with Cycles rendering to generate synthetic ring images with corresponding masks and metadata.

## Features

- **Deterministic rendering**: Fixed configuration and seed produce identical outputs
- **Parametric ring geometry**: Configurable inner diameter, band width, and thickness
- **Multiple outputs per sample**:
  - `rgb.png`: Rendered RGB image
  - `mask_ring.png`: Binary mask of the ring body
  - `mask_inner.png`: Binary mask of the inner hole area
  - `meta.json`: Complete metadata including all parameters
- **CPU-based rendering**: Ensures reproducibility (GPU may be non-deterministic)

## Requirements

- Python 3.8+
- Blender 3.0+ (headless installation)
- Python dependencies: `numpy`, `pyyaml`, `pydantic`, `tqdm`

## Installation

1. **Install Blender**:
   - **macOS**: Download from [blender.org](https://www.blender.org/download/) or use Homebrew: `brew install --cask blender`
   - **Linux**: `sudo apt-get install blender` or download from blender.org
   - **Windows**: Download installer from blender.org

2. **Install Python dependencies**:
   ```bash
   pip install -e .
   ```

   Or install manually:
   ```bash
   pip install numpy pyyaml pydantic tqdm
   ```

3. **Set Blender path** (optional):
   If Blender is not in your PATH, set the `BLENDER_PATH` environment variable:
   ```bash
   export BLENDER_PATH="/path/to/blender"
   ```

   On macOS, the default path is usually:
   ```bash
   export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
   ```

## Usage

### Basic Generation

Generate samples for a dataset split:

```bash
python -m src.cli generate \
    --config configs/mvp.yaml \
    --out output \
    --split train \
    --count 100 \
    --start-idx 0
```

### Command-Line Arguments

- `--config`: Path to YAML configuration file (required)
- `--out`: Output directory root (required)
- `--split`: Dataset split name: `train`, `val`, or `test` (required)
- `--count`: Number of samples to generate (required)
- `--start-idx`: Starting sample index (default: 0)
- `--blender-path`: Path to Blender executable (optional, auto-detected if not provided)

### Configuration File

The configuration file (`configs/mvp.yaml`) defines:

- **Dataset settings**: Image dimensions, split sizes
- **Seeds**: Base seed for deterministic generation
- **Ring parameters**: Ranges for inner diameter, band width, thickness
- **Camera parameters**: Focal length, distance, tilt, and rotation ranges
- **Render settings**: Cycles samples, denoising, device (CPU/GPU)
- **Lighting**: Area light configuration
- **Background**: Plane material and size

### Output Structure

```
output/
  train/
    sample_000000/
      rgb.png
      mask_ring.png
      mask_inner.png
      meta.json
    sample_000001/
      ...
  val/
    ...
  test/
    ...
```

### Metadata Format

Each `meta.json` contains:

```json
{
  "sample_seed": 1234567890,
  "ring": {
    "inner_diameter_mm": 15.5,
    "band_width_mm": 3.2,
    "thickness_mm": 2.1
  },
  "camera": {
    "focal_length_mm": 50.0,
    "distance_mm": 200.0,
    "tilt_x_deg": 5.0,
    "tilt_y_deg": -10.0,
    "rot_z_deg": 45.0
  },
  "lighting": {...},
  "background": {...},
  "render": {...},
  "calibration": {
    "mode": "none",
    "marker_id": null,
    "marker_size_mm": null,
    "pixel_to_mm": null
  },
  "image_width": 512,
  "image_height": 512
}
```

## Determinism

For fixed `(config, base_seed, sample_idx)`, re-running the generator produces:
- **Identical** `meta.json` and masks
- **Reproducible** RGB images when using CPU rendering (GPU may be non-deterministic)

The seed strategy uses SHA-256 hashing:
```
sample_seed = stable_hash(base_seed, split_name, sample_idx)
```

This seed is used for:
- NumPy random number generation (parameter sampling)
- Blender Cycles rendering (`scene.cycles.seed`)

## Notes

- **CPU rendering**: Recommended for reproducibility. GPU rendering may produce slightly different results due to floating-point precision differences.
- **Rendering time**: CPU rendering is slower but deterministic. Expect ~10-30 seconds per sample depending on cycle samples and image resolution.
- **Calibration**: The calibration block in metadata is reserved for future pixel-to-mm conversion features.

## Troubleshooting

**Blender not found**:
- Ensure Blender is installed and in PATH, or set `BLENDER_PATH` environment variable
- Verify Blender works: `blender --version`

**Rendering errors**:
- Check that Blender version is 3.0 or higher
- Verify all paths in configuration are valid
- Check Blender console output for detailed error messages

**Mask issues**:
- Ensure object indices are properly set (ring=1, inner=2)
- Verify compositor nodes are correctly configured

## License

This project is provided as-is for research and development purposes.

