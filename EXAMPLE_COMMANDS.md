# Example Run Commands

## Basic Examples

### 1. Minimal test run (5 images, seed 42)
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/test
```

### 2. Default run (uses config.json)
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py --
```

### 3. Custom image count and seed
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 10 \
    --seed 12345
```

## Advanced Examples

### 4. Override camera parameters
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 20 \
    --pitch-min 30 \
    --pitch-max 60 \
    --distance-min 15 \
    --distance-max 30
```

### 5. Custom image resolution
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 10 \
    --image-width 1280 \
    --image-height 720
```

### 6. Full parameter override
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 50 \
    --seed 999 \
    --output-dir output/custom_dataset \
    --ring-object-name ring \
    --pitch-min 25 \
    --pitch-max 75 \
    --yaw-min 0 \
    --yaw-max 360 \
    --distance-min 10 \
    --distance-max 35 \
    --image-width 1920 \
    --image-height 1080 \
    --edge-margin 0.07 \
    --min-projected-size 0.20 \
    --max-projected-size 0.35 \
    --max-attempts 50
```

### 7. Use custom config file
```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --config my_custom_config.json \
    --num-images 10
```

### 8. Reproducible test run
```bash
# First run
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/run1

# Second run with same seed (should produce identical results)
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/run2
```

## Quick Test Command

For a quick test, use this minimal command:

```bash
blender -b blender/ring_shader_pos1.blend -P tools/generate_ring_dataset.py -- --num-images 1 --seed 42
```

This generates a single image with a fixed seed, useful for verifying the setup works.

