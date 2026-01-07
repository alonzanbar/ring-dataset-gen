#!/bin/bash
# Sample run commands for testing ring dataset generation

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BLEND_FILE="${SCRIPT_DIR}/blender/ring_shader_pos1.blend"
SCRIPT="${SCRIPT_DIR}/tools/generate_ring_dataset.py"

# Use full path to Blender to avoid Homebrew wrapper issues
# The Homebrew 'blender' command points to a binary with hardcoded build paths
if [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
elif command -v blender &> /dev/null; then
    BLENDER="blender"
else
    echo "Error: Blender not found"
    exit 1
fi

# Check if Blender is available (already set BLENDER variable above)
if [ ! -f "$BLENDER" ] && ! command -v "$BLENDER" &> /dev/null; then
    echo "Error: Blender not found"
    echo "Expected: /Applications/Blender.app/Contents/MacOS/Blender"
    echo "Or install Blender and ensure 'blender' is in PATH"
    exit 1
fi

# Check if blend file exists
if [ ! -f "$BLEND_FILE" ]; then
    echo "Error: Blend file not found: $BLEND_FILE"
    exit 1
fi

echo "=== Sample Run Commands ==="
echo ""
echo "1. Basic run with defaults (uses config.json):"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT --"
echo ""
echo "2. Generate 10 images with a seed for reproducibility:"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT -- --num-images 10 --seed 42"
echo ""
echo "3. Custom output directory and image count:"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT -- --output-dir output/test_dataset --num-images 5"
echo ""
echo "4. Override camera parameters:"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT -- --pitch-min 30 --pitch-max 60 --distance-min 15"
echo ""
echo "5. Use custom config file:"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT -- --config custom_config.json"
echo ""
echo "6. Full example with multiple overrides:"
echo "   $BLENDER -b $BLEND_FILE -P $SCRIPT -- \\"
echo "     --num-images 20 \\"
echo "     --seed 12345 \\"
echo "     --output-dir output/my_dataset \\"
echo "     --image-width 1280 \\"
echo "     --image-height 720 \\"
echo "     --pitch-min 30 \\"
echo "     --pitch-max 70"
echo ""
echo "=== Running Example ==="
echo ""
echo "Running basic test with 5 images and seed 42..."
echo ""

# Run a basic test
$BLENDER -b "$BLEND_FILE" -P "$SCRIPT" -- \
    --num-images 5 \
    --seed 42 \
    --output-dir output/test_run

echo ""
echo "Test run complete! Check output/test_run/ for results."

