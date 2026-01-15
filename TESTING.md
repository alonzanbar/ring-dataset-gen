# Testing Guide

## Quick Tests (No Blender Required)

### 1. Test Configuration System
```bash
python3 test_config_only.py
```
This verifies that config loading, CLI parsing, and config creation all work correctly.

### 2. Test Config Loading Directly
```bash
python3 -c "from datasetgen.config import load_config_from_json; import json; print(json.dumps(load_config_from_json(), indent=2))"
```

### 3. Test CLI Help
```bash
python3 tools/generate_ring_dataset.py --help
```

## Blender Tests

### 4. Test with GPU Disabled (Recommended First)
```bash
blender -b --disable-gpu blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 1 \
    --seed 42 \
    --output-dir output/test
```

### 5. Test Minimal Run (GPU Disabled)
```bash
blender -b --disable-gpu -P tools/generate_ring_dataset.py -- --num-images 1
```

### 6. Test with Full Parameters (GPU Disabled)
```bash
blender -b --disable-gpu blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/test_run \
    --image-width 1280 \
    --image-height 720
```

## Using the Test Script

### Run the test script (with GPU disabled)
Edit `test_run.sh` to add `--disable-gpu` flag, or run manually:

```bash
blender -b --disable-gpu blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/test_run
```

## Expected Output (When Working)

When the script runs successfully, you should see:
```
============================================================
Ring Dataset Generation
============================================================
Ring object name: ring
Number of images: 1
Output directory: output/test
Seed: 42
Blender version: 5.0.0
Image size: 1920x1080
Camera pitch range: 25.0° - 75.0°
Camera distance range: 10.0x - 35.0x
============================================================

Output directory created: output/test
Images directory: output/test/images

NOTE: Blender logic not yet implemented.
...
```

## Troubleshooting

If Blender still crashes:
1. Check crash log: `cat /var/folders/*/blender.crash.txt | tail -50`
2. Try without blend file: `blender -b --disable-gpu -P tools/generate_ring_dataset.py -- --num-images 1`
3. Try a stable Blender release instead of development build
4. Run outside sandbox environment


