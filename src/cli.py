"""Command-line interface for ring dataset generation."""

import argparse
import yaml
from pathlib import Path
from typing import Dict, Any

from .orchestrator import generate_samples


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Ring dataset generator")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate dataset samples')
    gen_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        help='Path to configuration YAML file'
    )
    gen_parser.add_argument(
        '--out',
        type=Path,
        required=True,
        help='Output directory'
    )
    gen_parser.add_argument(
        '--split',
        type=str,
        required=True,
        choices=['train', 'val', 'test'],
        help='Dataset split name'
    )
    gen_parser.add_argument(
        '--count',
        type=int,
        required=True,
        help='Number of samples to generate'
    )
    gen_parser.add_argument(
        '--start-idx',
        type=int,
        default=0,
        help='Starting sample index (default: 0)'
    )
    gen_parser.add_argument(
        '--blender-path',
        type=str,
        default=None,
        help='Path to Blender executable (auto-detected if not provided)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        config = load_config(args.config)
        generate_samples(
            config=config,
            split_name=args.split,
            start_idx=args.start_idx,
            count=args.count,
            output_dir=args.out,
            blender_path=args.blender_path,
        )
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

