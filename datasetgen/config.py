"""
Configuration management for ring dataset generation.

Handles CLI argument parsing, configuration schema, and reproducibility tracking.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class CameraSamplingConfig:
    """Configuration for camera pose sampling."""
    
    # Angular constraints
    yaw_min: float = 0.0  # degrees
    yaw_max: float = 360.0  # degrees
    pitch_min: float = 25.0  # degrees (default: 25-75)
    pitch_max: float = 75.0  # degrees
    
    # Distance constraints (relative to ring bounding sphere radius R)
    distance_min_multiplier: float = 10.0  # 10 × R
    distance_max_multiplier: float = 35.0  # 35 × R
    
    # Look-at jitter (relative to R)
    look_at_jitter_max_fraction: float = 0.1  # ≤ 10% of R
    
    # Roll control
    allow_roll: bool = False  # default: no roll


@dataclass
class VisibilityConfig:
    """Configuration for visibility and framing constraints."""
    
    # Safety margin from image edges
    edge_margin_fraction: float = 0.07  # 7% margin
    
    # Minimum projected size fraction (20-35% of image width or height)
    min_projected_size_fraction: float = 0.20
    max_projected_size_fraction: float = 0.35


@dataclass
class SamplingConfig:
    """Configuration for sampling and rejection strategy."""
    
    # Maximum attempts per sample before rejection
    max_attempts_per_sample: int = 50  # default: 30-60, using middle value
    
    # Track rejection reasons
    track_rejection_reasons: bool = True


@dataclass
class ImageOutputConfig:
    """Configuration for image output."""
    
    width: int = 1920
    height: int = 1080
    format: str = "PNG"  # RGB images only


@dataclass
class DatasetConfig:
    """Main configuration schema for dataset generation."""
    
    # Target object
    ring_object_name: str = "ring"
    
    # Camera sampling
    camera: CameraSamplingConfig = field(default_factory=CameraSamplingConfig)
    
    # Visibility constraints
    visibility: VisibilityConfig = field(default_factory=VisibilityConfig)
    
    # Sampling strategy
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    
    # Image output
    image_output: ImageOutputConfig = field(default_factory=ImageOutputConfig)
    
    # Output directory
    output_dir: Path = field(default_factory=lambda: Path("output/dataset"))
    
    # Reproducibility
    seed: Optional[int] = None
    blender_version: Optional[str] = None  # Will be populated at runtime
    
    # Number of images to generate
    num_images: int = 100
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert Path to string for JSON
        result["output_dir"] = str(self.output_dir)
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "DatasetConfig":
        """Create config from dictionary."""
        # Convert string back to Path
        if "output_dir" in data and isinstance(data["output_dir"], str):
            data["output_dir"] = Path(data["output_dir"])
        
        # Handle nested configs
        if "camera" in data and isinstance(data["camera"], dict):
            data["camera"] = CameraSamplingConfig(**data["camera"])
        if "visibility" in data and isinstance(data["visibility"], dict):
            data["visibility"] = VisibilityConfig(**data["visibility"])
        if "sampling" in data and isinstance(data["sampling"], dict):
            data["sampling"] = SamplingConfig(**data["sampling"])
        if "image_output" in data and isinstance(data["image_output"], dict):
            data["image_output"] = ImageOutputConfig(**data["image_output"])
        
        return cls(**data)


def parse_cli_args(args: Optional[list] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Optional list of arguments (defaults to sys.argv[1:])
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate a dataset of RGB images from a Blender scene with camera-only randomization."
    )
    
    # Configuration file
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to JSON configuration file (default: config.json in project root)"
    )
    
    # Mode selection
    parser.add_argument(
        "--mode",
        type=str,
        choices=["validate", "render"],
        default="validate",
        help="Operation mode: 'validate' (sampling and validation only) or 'render' (full pipeline with rendering)"
    )
    
    # Output configuration
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/dataset"),
        help="Output directory for dataset (overrides JSON config)"
    )
    
    parser.add_argument(
        "--num-images",
        type=int,
        default=100,
        help="Number of images to generate (overrides JSON config)"
    )
    
    # Reproducibility
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (overrides JSON config)"
    )
    
    # Ring object
    parser.add_argument(
        "--ring-object-name",
        type=str,
        default="ring",
        help="Name of the ring object in the Blender scene (overrides JSON config)"
    )
    
    # Camera sampling
    camera_group = parser.add_argument_group("Camera sampling (overrides JSON config)")
    camera_group.add_argument(
        "--yaw-min",
        type=float,
        default=0.0,
        help="Minimum yaw angle in degrees"
    )
    camera_group.add_argument(
        "--yaw-max",
        type=float,
        default=360.0,
        help="Maximum yaw angle in degrees"
    )
    camera_group.add_argument(
        "--pitch-min",
        type=float,
        default=25.0,
        help="Minimum pitch/elevation angle in degrees"
    )
    camera_group.add_argument(
        "--pitch-max",
        type=float,
        default=75.0,
        help="Maximum pitch/elevation angle in degrees"
    )
    camera_group.add_argument(
        "--distance-min",
        type=float,
        default=10.0,
        help="Minimum distance multiplier relative to ring radius"
    )
    camera_group.add_argument(
        "--distance-max",
        type=float,
        default=35.0,
        help="Maximum distance multiplier relative to ring radius"
    )
    camera_group.add_argument(
        "--look-at-jitter-max",
        type=float,
        default=0.1,
        help="Maximum look-at jitter as fraction of ring radius"
    )
    camera_group.add_argument(
        "--allow-roll",
        action="store_true",
        help="Allow camera roll"
    )
    
    # Visibility constraints
    visibility_group = parser.add_argument_group("Visibility constraints (overrides JSON config)")
    visibility_group.add_argument(
        "--edge-margin",
        type=float,
        default=0.07,
        help="Safety margin from image edges as fraction"
    )
    visibility_group.add_argument(
        "--min-projected-size",
        type=float,
        default=0.20,
        help="Minimum projected size fraction"
    )
    visibility_group.add_argument(
        "--max-projected-size",
        type=float,
        default=0.35,
        help="Maximum projected size fraction"
    )
    
    # Sampling strategy
    sampling_group = parser.add_argument_group("Sampling strategy (overrides JSON config)")
    sampling_group.add_argument(
        "--max-attempts",
        type=int,
        default=50,
        help="Maximum attempts per sample before rejection"
    )
    
    # Image output
    image_group = parser.add_argument_group("Image output (overrides JSON config)")
    image_group.add_argument(
        "--image-width",
        type=int,
        default=1920,
        help="Image width in pixels"
    )
    image_group.add_argument(
        "--image-height",
        type=int,
        default=1080,
        help="Image height in pixels"
    )
    
    if args is None:
        args = sys.argv[1:]
    
    # Handle Blender's argument parsing: everything after '--' is passed to our script
    if '--' in args:
        idx = args.index('--')
        args = args[idx + 1:]
    
    return parser.parse_args(args)


def load_config_from_json(config_path: Optional[Path] = None) -> dict:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to JSON config file. If None, looks for config.json in project root.
    
    Returns:
        Dictionary with configuration values
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if config_path is None:
        # Default to config.json in project root
        # Assume we're in datasetgen/, so go up one level
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r") as f:
        config_dict = json.load(f)
    
    return config_dict or {}


def create_config_from_json(config_path: Optional[Path] = None) -> DatasetConfig:
    """
    Create DatasetConfig from JSON file.
    
    Args:
        config_path: Path to JSON config file. If None, looks for config.json in project root.
    
    Returns:
        DatasetConfig instance
    """
    json_dict = load_config_from_json(config_path)
    
    # Extract nested configs
    camera_dict = json_dict.get("camera", {})
    visibility_dict = json_dict.get("visibility", {})
    sampling_dict = json_dict.get("sampling", {})
    image_output_dict = json_dict.get("image_output", {})
    
    # Convert output_dir string to Path if present
    output_dir = json_dict.get("output_dir", "output/dataset")
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    
    config = DatasetConfig(
        ring_object_name=json_dict.get("ring_object_name", "ring"),
        output_dir=output_dir,
        num_images=json_dict.get("num_images", 100),
        seed=None,  # Seed is runtime, not static config
        camera=CameraSamplingConfig(**camera_dict) if camera_dict else CameraSamplingConfig(),
        visibility=VisibilityConfig(**visibility_dict) if visibility_dict else VisibilityConfig(),
        sampling=SamplingConfig(**sampling_dict) if sampling_dict else SamplingConfig(),
        image_output=ImageOutputConfig(**image_output_dict) if image_output_dict else ImageOutputConfig(),
    )
    
    return config


def create_config_from_args(args: argparse.Namespace) -> DatasetConfig:
    """
    Create DatasetConfig from parsed CLI arguments.
    Loads defaults from JSON config file, then overrides with CLI arguments.
    CLI arguments always take precedence over JSON values.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        DatasetConfig instance
    """
    # Load base config from JSON (if available)
    try:
        config = create_config_from_json(args.config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Fall back to defaults if JSON not available
        if isinstance(e, FileNotFoundError):
            print(f"Warning: {e}. Using default configuration.", file=sys.stderr)
        elif isinstance(e, json.JSONDecodeError):
            print(f"Warning: Invalid JSON in config file: {e}. Using default configuration.", file=sys.stderr)
        config = DatasetConfig()
    
    # Override with CLI arguments (CLI args always take precedence over JSON)
    config.ring_object_name = args.ring_object_name
    config.output_dir = args.output_dir
    config.num_images = args.num_images
    config.seed = args.seed
    
    # Override camera config
    config.camera.yaw_min = args.yaw_min
    config.camera.yaw_max = args.yaw_max
    config.camera.pitch_min = args.pitch_min
    config.camera.pitch_max = args.pitch_max
    config.camera.distance_min_multiplier = args.distance_min
    config.camera.distance_max_multiplier = args.distance_max
    config.camera.look_at_jitter_max_fraction = args.look_at_jitter_max
    config.camera.allow_roll = args.allow_roll
    
    # Override visibility config
    config.visibility.edge_margin_fraction = args.edge_margin
    config.visibility.min_projected_size_fraction = args.min_projected_size
    config.visibility.max_projected_size_fraction = args.max_projected_size
    
    # Override sampling config
    config.sampling.max_attempts_per_sample = args.max_attempts
    
    # Override image output config
    config.image_output.width = args.image_width
    config.image_output.height = args.image_height
    
    return config


def get_blender_version() -> Optional[str]:
    """
    Get Blender version string.
    
    This will be implemented when Blender logic is added.
    For now, returns None.
    
    Returns:
        Blender version string or None if not available
    """
    # TODO: Implement Blender version detection
    # import bpy
    # return bpy.app.version_string
    return None


def write_run_config(config: DatasetConfig, output_path: Path) -> None:
    """
    Write run configuration to JSON file for reproducibility.
    
    According to SPEC.md section 9.4, each run must record:
    - Seed
    - Blender version
    - Config values (effective config)
    - Ring object name
    
    The run_config.json contains the effective configuration used for the run,
    including all CLI overrides and runtime values.
    
    Args:
        config: DatasetConfig instance with all effective values
        output_path: Path to write run_config.json (typically in output directory)
    """
    import json
    from pathlib import Path
    
    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Update Blender version if not set
    if config.blender_version is None:
        config.blender_version = get_blender_version()
    
    # Get effective config dictionary (contains all actual values used)
    effective_config = config.to_dict()
    
    # Create run config dictionary with required fields
    # Top-level fields for quick access, full config for complete reproducibility
    run_config = {
        "seed": config.seed,
        "blender_version": config.blender_version,
        "ring_object_name": config.ring_object_name,
        "config": effective_config,  # Complete effective configuration
    }
    
    # Write to JSON file with consistent formatting
    with open(output_path, "w") as f:
        json.dump(run_config, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"Run configuration written to: {output_path}")


def load_run_config(config_path: Path) -> Tuple[DatasetConfig, dict]:
    """
    Load run configuration from JSON file.
    
    Args:
        config_path: Path to run_config.json
    
    Returns:
        Tuple of (DatasetConfig, full run config dict)
    """
    with open(config_path, "r") as f:
        run_config = json.load(f)
    
    # Extract and reconstruct DatasetConfig
    config_dict = run_config.get("config", {})
    config = DatasetConfig.from_dict(config_dict)
    
    # Restore seed and blender_version from run config
    config.seed = run_config.get("seed")
    config.blender_version = run_config.get("blender_version")
    
    return config, run_config

