#!/bin/bash
# Test script for render pipeline

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BLEND_FILE="${SCRIPT_DIR}/blender/ring_shader_pos1.blend"
RENDER_PIPELINE="${SCRIPT_DIR}/datasetgen/render_pipeline.py"

# Use full path to Blender to avoid Homebrew wrapper issues
if [ -f "/Applications/Blender.app/Contents/MacOS/Blender" ]; then
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
elif command -v blender &> /dev/null; then
    BLENDER="blender"
else
    echo "Error: Blender not found"
    exit 1
fi

# Check if blend file exists
if [ ! -f "$BLEND_FILE" ]; then
    echo "Error: Blend file not found: $BLEND_FILE"
    exit 1
fi

echo "============================================================"
echo "Testing Render Pipeline"
echo "============================================================"
echo ""
echo "This will test the render pipeline by rendering a single test image."
echo "Output will be saved to: output/test_render.png"
echo ""

# Run the test
$BLENDER -b "$BLEND_FILE" -P "$RENDER_PIPELINE"

echo ""
echo "Test complete! Check output/test_render.png for the rendered image."

