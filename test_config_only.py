#!/usr/bin/env python3
"""
Test script to verify configuration system works without Blender.
Run this to verify the config loading and CLI parsing work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from datasetgen.config import (
    parse_cli_args,
    create_config_from_args,
    load_config_from_json,
    DatasetConfig
)

def test_config_loading():
    """Test that config.json can be loaded."""
    print("Testing config.json loading...")
    try:
        config_dict = load_config_from_json()
        print("✓ Config loaded successfully")
        print(f"  Ring object: {config_dict.get('ring_object_name')}")
        print(f"  Num images: {config_dict.get('num_images')}")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False

def test_cli_parsing():
    """Test that CLI arguments can be parsed."""
    print("\nTesting CLI argument parsing...")
    try:
        # Simulate command-line arguments
        test_args = [
            '--num-images', '10',
            '--seed', '42',
            '--output-dir', 'output/test'
        ]
        args = parse_cli_args(test_args)
        print("✓ CLI parsing successful")
        print(f"  Num images: {args.num_images}")
        print(f"  Seed: {args.seed}")
        print(f"  Output dir: {args.output_dir}")
        return True
    except Exception as e:
        print(f"✗ CLI parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_creation():
    """Test that DatasetConfig can be created from args."""
    print("\nTesting DatasetConfig creation...")
    try:
        test_args = [
            '--num-images', '5',
            '--seed', '123'
        ]
        args = parse_cli_args(test_args)
        config = create_config_from_args(args)
        print("✓ DatasetConfig created successfully")
        print(f"  Ring object: {config.ring_object_name}")
        print(f"  Num images: {config.num_images}")
        print(f"  Seed: {config.seed}")
        print(f"  Camera pitch: {config.camera.pitch_min}° - {config.camera.pitch_max}°")
        return True
    except Exception as e:
        print(f"✗ Config creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Configuration System Test (No Blender Required)")
    print("=" * 60)
    print()
    
    results = []
    results.append(("Config Loading", test_config_loading()))
    results.append(("CLI Parsing", test_cli_parsing()))
    results.append(("Config Creation", test_config_creation()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed! Configuration system is working.")
        return 0
    else:
        print("✗ Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

