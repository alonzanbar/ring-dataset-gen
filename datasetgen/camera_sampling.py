"""
Camera pose sampling for ring dataset generation.

Samples camera poses from a hemisphere above the table, centered on the ring.
"""

import random
import math
from typing import Tuple, Optional
from mathutils import Vector, Matrix
import bpy

from datasetgen.config import CameraSamplingConfig
from datasetgen.scene_introspection import RingGeometry


class CameraPose:
    """Represents a camera pose with position and orientation."""
    
    def __init__(
        self,
        position: Vector,
        rotation_matrix: Matrix,
        look_at: Vector,
        up: Vector
    ):
        """
        Initialize camera pose.
        
        Args:
            position: Camera position in world space
            rotation_matrix: Camera rotation matrix (3x3)
            look_at: Point the camera is looking at
            up: Camera up vector (world up)
        """
        self.position = position
        self.rotation_matrix = rotation_matrix
        self.look_at = look_at
        self.up = up
    
    def to_matrix_world(self) -> Matrix:
        """
        Convert to Blender's matrix_world format (4x4).
        
        Returns:
            4x4 transformation matrix
        """
        # Create 4x4 matrix
        mat = Matrix.Identity(4)
        
        # Set rotation (3x3 top-left)
        for i in range(3):
            for j in range(3):
                mat[i][j] = self.rotation_matrix[i][j]
        
        # Set translation
        mat[0][3] = self.position.x
        mat[1][3] = self.position.y
        mat[2][3] = self.position.z
        
        return mat
    
    def __repr__(self) -> str:
        return (
            f"CameraPose(position={self.position}, "
            f"look_at={self.look_at})"
        )


class SampledCameraParameters:
    """Sampled camera parameters for a pose."""
    
    def __init__(
        self,
        yaw: float,
        pitch: float,
        distance: float,
        look_at_jitter: Optional[Vector] = None
    ):
        """
        Initialize sampled parameters.
        
        Args:
            yaw: Azimuth angle in degrees (0-360)
            pitch: Elevation angle in degrees (25-75 default)
            distance: Distance from ring center (in units, not multiples of R)
            look_at_jitter: Optional jitter offset applied to look-at point
        """
        self.yaw = yaw
        self.pitch = pitch
        self.distance = distance
        self.look_at_jitter = look_at_jitter or Vector((0, 0, 0))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "yaw": self.yaw,
            "pitch": self.pitch,
            "distance": self.distance,
            "look_at_jitter": {
                "x": self.look_at_jitter.x,
                "y": self.look_at_jitter.y,
                "z": self.look_at_jitter.z
            }
        }
    
    def __repr__(self) -> str:
        return (
            f"SampledCameraParameters(yaw={self.yaw:.2f}°, "
            f"pitch={self.pitch:.2f}°, distance={self.distance:.4f})"
        )


def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return math.radians(degrees)


def sample_camera_pose(
    ring_geom: RingGeometry,
    config: CameraSamplingConfig,
    rng: Optional[random.Random] = None
) -> Tuple[CameraPose, SampledCameraParameters]:
    """
    Sample a camera pose from the hemisphere above the table.
    
    According to SPEC.md:
    - Section 5.2: Sample from hemisphere above table, centered on ring
    - Section 5.2: Yaw 0-360°, Pitch 25-75° (default), Distance 10×R to 35×R
    - Section 6: Look at ring center with jitter ≤ 10% of R
    - Section 6: Camera up = world up (no roll)
    
    Args:
        ring_geom: Ring geometry (center, radius, table_plane_z)
        config: Camera sampling configuration
        rng: Optional random number generator (for reproducibility)
    
    Returns:
        Tuple of (CameraPose, SampledCameraParameters)
    """
    if rng is None:
        rng = random.Random()
    
    # Sample angles (SPEC.md section 5.2)
    yaw_deg = rng.uniform(config.yaw_min, config.yaw_max)
    pitch_deg = rng.uniform(config.pitch_min, config.pitch_max)
    
    # Sample distance relative to ring radius R (SPEC.md section 5.2)
    distance_multiplier = rng.uniform(
        config.distance_min_multiplier,
        config.distance_max_multiplier
    )
    distance = distance_multiplier * ring_geom.radius
    
    # Convert to radians
    yaw_rad = degrees_to_radians(yaw_deg)
    pitch_rad = degrees_to_radians(pitch_deg)
    
    # Compute camera position in spherical coordinates
    # Hemisphere above table: pitch is elevation from horizontal
    # x = distance * cos(pitch) * cos(yaw)
    # y = distance * cos(pitch) * sin(yaw)
    # z = distance * sin(pitch)  (positive = above)
    cos_pitch = math.cos(pitch_rad)
    sin_pitch = math.sin(pitch_rad)
    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)
    
    # Camera position relative to ring center
    camera_offset = Vector((
        distance * cos_pitch * cos_yaw,
        distance * cos_pitch * sin_yaw,
        distance * sin_pitch
    ))
    
    # Camera position in world space (above table)
    camera_position = ring_geom.center + camera_offset
    
    # Ensure camera is above table plane
    if camera_position.z < ring_geom.table_plane_z:
        # If somehow below table, raise to just above
        camera_position.z = ring_geom.table_plane_z + 0.1 * ring_geom.radius
    
    # Sample look-at jitter (SPEC.md section 6: ≤ 10% of R)
    max_jitter = config.look_at_jitter_max_fraction * ring_geom.radius
    look_at_jitter = Vector((
        rng.uniform(-max_jitter, max_jitter),
        rng.uniform(-max_jitter, max_jitter),
        rng.uniform(-max_jitter, max_jitter)
    ))
    
    # Look-at point = ring center + jitter (SPEC.md section 6)
    look_at_point = ring_geom.center + look_at_jitter
    
    # Compute camera orientation (look-at with world up)
    # Camera forward = normalize(look_at - position)
    forward = (look_at_point - camera_position).normalized()
    
    # World up vector (SPEC.md section 6: camera up = world up)
    world_up = Vector((0, 0, 1))
    
    # Compute right vector (perpendicular to forward and up)
    right = forward.cross(world_up).normalized()
    
    # Recompute up to ensure orthogonality
    up = right.cross(forward).normalized()
    
    # Build rotation matrix (camera to world)
    # In Blender, camera looks down -Z in local space
    # So we need: local -Z -> forward, local Y -> up, local X -> right
    rotation_matrix = Matrix((
        right,      # X axis
        up,         # Y axis
        -forward    # -Z axis (camera looks down -Z)
    )).transposed()  # Transpose to get world-to-camera, then we'll invert
    
    # Actually, for matrix_world, we want camera-to-world
    # So columns are the camera axes in world space
    rotation_matrix = Matrix((
        (right.x, up.x, -forward.x),
        (right.y, up.y, -forward.y),
        (right.z, up.z, -forward.z)
    ))
    
    # Create camera pose
    camera_pose = CameraPose(
        position=camera_position,
        rotation_matrix=rotation_matrix,
        look_at=look_at_point,
        up=up
    )
    
    # Create sampled parameters
    sampled_params = SampledCameraParameters(
        yaw=yaw_deg,
        pitch=pitch_deg,
        distance=distance,
        look_at_jitter=look_at_jitter
    )
    
    return (camera_pose, sampled_params)


def apply_camera_pose_to_scene(
    camera_pose: CameraPose,
    camera_object: Optional[bpy.types.Object] = None
) -> None:
    """
    Apply camera pose to a camera object in the scene.
    
    This is a utility function for testing/debugging. The actual rendering
    pipeline will handle camera setup.
    
    Args:
        camera_pose: Camera pose to apply
        camera_object: Camera object to update (defaults to active camera)
    """
    if camera_object is None:
        if bpy.context.scene.camera is None:
            # Create camera if none exists
            bpy.ops.object.camera_add()
            camera_object = bpy.context.active_object
        else:
            camera_object = bpy.context.scene.camera
    
    # Set camera matrix_world
    camera_object.matrix_world = camera_pose.to_matrix_world()


def sample_multiple_poses(
    ring_geom: RingGeometry,
    config: CameraSamplingConfig,
    num_samples: int,
    seed: Optional[int] = None
) -> list[Tuple[CameraPose, SampledCameraParameters]]:
    """
    Sample multiple camera poses.
    
    Args:
        ring_geom: Ring geometry
        config: Camera sampling configuration
        num_samples: Number of poses to sample
        seed: Optional random seed for reproducibility
    
    Returns:
        List of (CameraPose, SampledCameraParameters) tuples
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    
    poses = []
    for _ in range(num_samples):
        pose, params = sample_camera_pose(ring_geom, config, rng)
        poses.append((pose, params))
    
    return poses


