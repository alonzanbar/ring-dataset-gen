"""Sampling logic for generating sample parameters."""

import numpy as np
from pydantic import BaseModel, Field
from typing import Dict, Any

from .seeds import get_sample_seed


class RingParams(BaseModel):
    """Ring geometry parameters."""
    inner_diameter_mm: float = Field(..., description="Inner diameter in millimeters")
    band_width_mm: float = Field(..., description="Band width in millimeters")
    thickness_mm: float = Field(..., description="Thickness in millimeters")


class CameraParams(BaseModel):
    """Camera parameters."""
    focal_length_mm: float = Field(..., description="Focal length in millimeters")
    distance_mm: float = Field(..., description="Distance from ring center in millimeters")
    tilt_x_deg: float = Field(..., description="Tilt around X axis in degrees")
    tilt_y_deg: float = Field(..., description="Tilt around Y axis in degrees")
    rot_z_deg: float = Field(..., description="Rotation around Z axis in degrees")


class LightingParams(BaseModel):
    """Lighting parameters."""
    type: str = Field(..., description="Lighting type")
    area_light: Dict[str, Any] = Field(default_factory=dict, description="Area light parameters")


class BackgroundParams(BaseModel):
    """Background parameters."""
    type: str = Field(..., description="Background type")
    plane: Dict[str, Any] = Field(default_factory=dict, description="Plane parameters")


class RenderParams(BaseModel):
    """Render parameters."""
    cycles_samples: int = Field(..., description="Number of Cycles samples")
    denoise: bool = Field(..., description="Enable denoising")
    device: str = Field(..., description="Render device (CPU/GPU)")
    file_format: str = Field(..., description="Output file format")


class CalibrationParams(BaseModel):
    """Calibration parameters (reserved for future use)."""
    mode: str = Field(default="none", description="Calibration mode")
    marker_id: Any = Field(default=None, description="Marker ID")
    marker_size_mm: Any = Field(default=None, description="Marker size in mm")
    pixel_to_mm: Any = Field(default=None, description="Pixel to mm conversion factor")


class SampleParams(BaseModel):
    """Complete sample parameters."""
    sample_seed: int = Field(..., description="Deterministic seed for this sample")
    ring: RingParams = Field(..., description="Ring parameters")
    camera: CameraParams = Field(..., description="Camera parameters")
    lighting: LightingParams = Field(..., description="Lighting parameters")
    background: BackgroundParams = Field(..., description="Background parameters")
    render: RenderParams = Field(..., description="Render parameters")
    calibration: CalibrationParams = Field(..., description="Calibration parameters")


def sample_uniform(rng: np.random.Generator, min_val: float, max_val: float) -> float:
    """Sample a uniform value from [min_val, max_val)."""
    return rng.uniform(min_val, max_val)


def sample_params(config: Dict[str, Any], split_name: str, idx: int) -> SampleParams:
    """
    Generate deterministic sample parameters from config.
    
    Args:
        config: Configuration dictionary
        split_name: Name of the split (train/val/test)
        idx: Sample index within the split
        
    Returns:
        SampleParams instance with all sampled parameters
    """
    base_seed = config["seeds"]["base_seed"]
    sample_seed = get_sample_seed(base_seed, split_name, idx)
    
    # Seed NumPy RNG for deterministic sampling
    rng = np.random.default_rng(sample_seed)
    
    # Sample ring parameters
    ring_config = config["ring"]
    ring = RingParams(
        inner_diameter_mm=sample_uniform(rng, ring_config["inner_diameter_mm"]["min"], 
                                         ring_config["inner_diameter_mm"]["max"]),
        band_width_mm=sample_uniform(rng, ring_config["band_width_mm"]["min"], 
                                     ring_config["band_width_mm"]["max"]),
        thickness_mm=sample_uniform(rng, ring_config["thickness_mm"]["min"], 
                                    ring_config["thickness_mm"]["max"]),
    )
    
    # Sample camera parameters
    cam_config = config["camera"]
    camera = CameraParams(
        focal_length_mm=sample_uniform(rng, cam_config["focal_length_mm"]["min"], 
                                       cam_config["focal_length_mm"]["max"]),
        distance_mm=sample_uniform(rng, cam_config["distance_mm"]["min"], 
                                   cam_config["distance_mm"]["max"]),
        tilt_x_deg=sample_uniform(rng, cam_config["tilt_x_deg"]["min"], 
                                  cam_config["tilt_x_deg"]["max"]),
        tilt_y_deg=sample_uniform(rng, cam_config["tilt_y_deg"]["min"], 
                                  cam_config["tilt_y_deg"]["max"]),
        rot_z_deg=sample_uniform(rng, cam_config["rot_z_deg"]["min"], 
                                 cam_config["rot_z_deg"]["max"]),
    )
    
    # Lighting and background from config (not sampled)
    lighting = LightingParams(**config["lighting"])
    background = BackgroundParams(**config["background"])
    
    # Render parameters from config
    render = RenderParams(**config["render"])
    
    # Calibration (reserved)
    calibration = CalibrationParams(**config.get("calibration", {}))
    
    return SampleParams(
        sample_seed=sample_seed,
        ring=ring,
        camera=camera,
        lighting=lighting,
        background=background,
        render=render,
        calibration=calibration,
    )

