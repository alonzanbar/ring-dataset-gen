"""Orchestration logic for generating samples."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from .sampling import sample_params
from .io_utils import get_sample_dir, write_json, ensure_dir


def find_blender() -> str:
    """
    Find Blender executable path.
    
    Returns:
        Path to blender executable
        
    Raises:
        FileNotFoundError: If blender is not found
    """
    import os
    
    # Check environment variable first
    blender_path = os.environ.get("BLENDER_PATH")
    if blender_path:
        if os.path.exists(blender_path):
            return blender_path
    
    # Common Blender paths
    common_paths = [
        "blender",  # In PATH
        "/Applications/Blender.app/Contents/MacOS/Blender",  # macOS default
        "/usr/bin/blender",  # Linux default
        "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",  # Windows default
    ]
    
    for path in common_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    raise FileNotFoundError(
        "Blender not found. Please install Blender and ensure it's in PATH, "
        "or set BLENDER_PATH environment variable."
    )


def generate_sample(
    config: Dict[str, Any],
    split_name: str,
    sample_idx: int,
    output_dir: Path,
    blender_path: str = None,
) -> bool:
    """
    Generate a single sample.
    
    Args:
        config: Configuration dictionary
        split_name: Name of the split
        sample_idx: Index of the sample
        output_dir: Root output directory
        blender_path: Path to Blender executable (auto-detected if None)
        
    Returns:
        True if successful, False otherwise
    """
    # Get sample directory
    sample_dir = get_sample_dir(output_dir, split_name, sample_idx)
    ensure_dir(sample_dir)
    
    # Generate sample parameters
    params = sample_params(config, split_name, sample_idx)
    
    # Add image dimensions from config
    params_dict = params.model_dump(mode='json')
    params_dict["image_width"] = config["dataset"]["image_width"]
    params_dict["image_height"] = config["dataset"]["image_height"]
    
    # Write sample parameters to temporary JSON file
    sample_json_path = sample_dir / "sample_params.json"
    write_json(params_dict, sample_json_path)
    
    # Find Blender if not provided
    if blender_path is None:
        blender_path = find_blender()
    
    # Get Blender script path
    script_dir = Path(__file__).parent
    blender_script = script_dir / "blender" / "render_scene.py"
    
    # Invoke Blender headless
    cmd = [
        blender_path,
        "-b",  # Background mode
        "-P", str(blender_script),  # Run Python script
        "--",  # Pass arguments after this
        "--sample_json", str(sample_json_path),
        "--out_dir", str(sample_dir),
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per sample
        )
        
        if result.returncode != 0:
            print(f"Error rendering sample {sample_idx}: {result.stderr}", file=sys.stderr)
            return False
        
        # Verify outputs exist
        rgb_path = sample_dir / "rgb.png"
        mask_ring_path = sample_dir / "mask_ring.png"
        mask_inner_path = sample_dir / "mask_inner.png"
        meta_path = sample_dir / "meta.json"
        
        if not all(p.exists() for p in [rgb_path, mask_ring_path, mask_inner_path, meta_path]):
            print(f"Warning: Some output files missing for sample {sample_idx}", file=sys.stderr)
            return False
        
        # Basic QA: check masks are non-empty (simple file size check)
        if mask_ring_path.stat().st_size == 0 or mask_inner_path.stat().st_size == 0:
            print(f"Warning: Empty mask files for sample {sample_idx}", file=sys.stderr)
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"Timeout rendering sample {sample_idx}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error rendering sample {sample_idx}: {e}", file=sys.stderr)
        return False


def generate_samples(
    config: Dict[str, Any],
    split_name: str,
    start_idx: int,
    count: int,
    output_dir: Path,
    blender_path: str = None,
) -> None:
    """
    Generate multiple samples.
    
    Args:
        config: Configuration dictionary
        split_name: Name of the split
        start_idx: Starting sample index
        count: Number of samples to generate
        output_dir: Root output directory
        blender_path: Path to Blender executable (auto-detected if None)
    """
    from tqdm import tqdm
    
    success_count = 0
    for idx in tqdm(range(start_idx, start_idx + count), desc=f"Generating {split_name} samples"):
        if generate_sample(config, split_name, idx, output_dir, blender_path):
            success_count += 1
    
    print(f"\nGenerated {success_count}/{count} samples successfully")

