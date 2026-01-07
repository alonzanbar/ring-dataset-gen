"""
Visibility and framing constraint checks for ring dataset generation.

Enforces full visibility with margin and minimum projected size requirements.
"""

from enum import Enum
from typing import Tuple, Optional, List
from mathutils import Vector, Matrix
import bpy
from bpy_extras.object_utils import world_to_camera_view

from datasetgen.config import VisibilityConfig, ImageOutputConfig
from datasetgen.scene_introspection import RingGeometry
from datasetgen.camera_sampling import CameraPose


class RejectionReason(Enum):
    """Reasons for rejecting a camera pose."""
    CROPPED = "Cropped"  # Ring bounding box clipped or outside image
    TOO_SMALL = "Too small"  # Projected size below minimum
    TOO_LARGE = "Too large"  # Projected size above maximum
    BELOW_TABLE_PLANE = "Below table plane"  # Camera below table
    INVALID_PROJECTION = "Invalid projection"  # Projection error
    VALID = "Valid"  # No rejection (for success cases)


class VisibilityResult:
    """Result of visibility check."""
    
    def __init__(
        self,
        is_valid: bool,
        rejection_reason: RejectionReason,
        margin_used: Optional[float] = None,
        projected_size_fraction: Optional[float] = None,
        projected_bbox: Optional[Tuple[float, float, float, float]] = None  # (min_x, min_y, max_x, max_y) in image space
    ):
        """
        Initialize visibility result.
        
        Args:
            is_valid: Whether the pose satisfies all constraints
            rejection_reason: Reason for rejection (or VALID if valid)
            margin_used: Actual margin used (fraction)
            projected_size_fraction: Projected size as fraction of image dimension
            projected_bbox: Projected bounding box in image space [0-1]
        """
        self.is_valid = is_valid
        self.rejection_reason = rejection_reason
        self.margin_used = margin_used
        self.projected_size_fraction = projected_size_fraction
        self.projected_bbox = projected_bbox
    
    def __repr__(self) -> str:
        if self.is_valid:
            return f"VisibilityResult(VALID, margin={self.margin_used:.4f}, size={self.projected_size_fraction:.4f})"
        else:
            return f"VisibilityResult(INVALID: {self.rejection_reason.value})"


def get_bounding_box_vertices(ring_geom: RingGeometry) -> List[Vector]:
    """
    Get all 8 vertices of the ring's world-space bounding box.
    
    Args:
        ring_geom: Ring geometry
    
    Returns:
        List of 8 vertices (corners of bounding box)
    """
    bbox_min, bbox_max = ring_geom.bounding_box_world
    
    # Generate all 8 corners of the bounding box
    vertices = [
        Vector((bbox_min.x, bbox_min.y, bbox_min.z)),
        Vector((bbox_max.x, bbox_min.y, bbox_min.z)),
        Vector((bbox_min.x, bbox_max.y, bbox_min.z)),
        Vector((bbox_max.x, bbox_max.y, bbox_min.z)),
        Vector((bbox_min.x, bbox_min.y, bbox_max.z)),
        Vector((bbox_max.x, bbox_min.y, bbox_max.z)),
        Vector((bbox_min.x, bbox_max.y, bbox_max.z)),
        Vector((bbox_max.x, bbox_max.y, bbox_max.z)),
    ]
    
    return vertices


def project_to_image_space(
    world_point: Vector,
    camera_pose: CameraPose,
    image_width: int,
    image_height: int
) -> Optional[Tuple[float, float]]:
    """
    Project a world-space point to image space coordinates.
    
    Uses Blender's camera projection. Returns normalized coordinates [0-1]
    where (0,0) is bottom-left and (1,1) is top-right.
    
    Args:
        world_point: Point in world space
        camera_pose: Camera pose
        image_width: Image width in pixels
        image_height: Image height in pixels
    
    Returns:
        Tuple of (x, y) in normalized image space [0-1], or None if behind camera
    """
    # Create a temporary camera object for projection
    # We'll use Blender's built-in projection utilities
    scene = bpy.context.scene
    
    # Get or create camera
    if scene.camera is None:
        bpy.ops.object.camera_add()
        camera_obj = bpy.context.active_object
        scene.camera = camera_obj
    else:
        camera_obj = scene.camera
    
    # Set camera pose
    camera_obj.matrix_world = camera_pose.to_matrix_world()
    
    # Set camera properties for projection
    camera_obj.data.sensor_width = 36.0  # Default sensor width
    camera_obj.data.lens = 50.0  # Default lens (will be overridden by render settings)
    
    # Project point to camera view space
    try:
        # world_to_camera_view returns (x, y, depth) where x,y are in [0-1]
        co_2d = world_to_camera_view(scene, camera_obj, world_point)
        
        # Check if point is behind camera (depth < 0)
        if len(co_2d) >= 3 and co_2d[2] < 0:
            return None
        
        # Return normalized coordinates [0-1]
        return (co_2d[0], co_2d[1])
    
    except Exception:
        return None


def check_visibility(
    ring_geom: RingGeometry,
    camera_pose: CameraPose,
    visibility_config: VisibilityConfig,
    image_config: ImageOutputConfig
) -> VisibilityResult:
    """
    Check if camera pose satisfies visibility constraints.
    
    According to SPEC.md section 7:
    - 7.1: All bounding box vertices must be inside image with 7% margin
    - 7.2: Projected size must be 20-35% of image width or height
    
    Args:
        ring_geom: Ring geometry
        camera_pose: Camera pose to check
        visibility_config: Visibility constraints configuration
        image_config: Image output configuration
    
    Returns:
        VisibilityResult with validation status and metrics
    """
    # Check if camera is below table plane (SPEC.md section 8)
    if camera_pose.position.z < ring_geom.table_plane_z:
        return VisibilityResult(
            is_valid=False,
            rejection_reason=RejectionReason.BELOW_TABLE_PLANE
        )
    
    # Get all bounding box vertices
    bbox_vertices = get_bounding_box_vertices(ring_geom)
    
    # Project all vertices to image space
    projected_points = []
    for vertex in bbox_vertices:
        proj = project_to_image_space(
            vertex,
            camera_pose,
            image_config.width,
            image_config.height
        )
        if proj is None:
            # Point is behind camera or projection failed
            return VisibilityResult(
                is_valid=False,
                rejection_reason=RejectionReason.INVALID_PROJECTION
            )
        projected_points.append(proj)
    
    if not projected_points:
        return VisibilityResult(
            is_valid=False,
            rejection_reason=RejectionReason.INVALID_PROJECTION
        )
    
    # Find bounding box in image space
    min_x = min(p[0] for p in projected_points)
    max_x = max(p[0] for p in projected_points)
    min_y = min(p[1] for p in projected_points)
    max_y = max(p[1] for p in projected_points)
    
    projected_bbox = (min_x, min_y, max_x, max_y)
    
    # Check full visibility with margin (SPEC.md section 7.1)
    margin = visibility_config.edge_margin_fraction
    
    # Check if all points are inside image with margin
    if min_x < margin or max_x > (1.0 - margin) or \
       min_y < margin or max_y > (1.0 - margin):
        # Calculate actual margin used (minimum margin from any edge)
        actual_margin = min(
            min_x,
            min_y,
            1.0 - max_x,
            1.0 - max_y
        )
        return VisibilityResult(
            is_valid=False,
            rejection_reason=RejectionReason.CROPPED,
            margin_used=actual_margin,
            projected_size_fraction=None,
            projected_bbox=projected_bbox
        )
    
    # Calculate actual margin used
    actual_margin = min(
        min_x,
        min_y,
        1.0 - max_x,
        1.0 - max_y
    )
    
    # Check projected size (SPEC.md section 7.2)
    bbox_width = max_x - min_x
    bbox_height = max_y - min_y
    projected_size = max(bbox_width, bbox_height)  # Use larger dimension
    
    # Check if size is within range
    if projected_size < visibility_config.min_projected_size_fraction:
        return VisibilityResult(
            is_valid=False,
            rejection_reason=RejectionReason.TOO_SMALL,
            margin_used=actual_margin,
            projected_size_fraction=projected_size,
            projected_bbox=projected_bbox
        )
    
    if projected_size > visibility_config.max_projected_size_fraction:
        return VisibilityResult(
            is_valid=False,
            rejection_reason=RejectionReason.TOO_LARGE,
            margin_used=actual_margin,
            projected_size_fraction=projected_size,
            projected_bbox=projected_bbox
        )
    
    # All checks passed
    return VisibilityResult(
        is_valid=True,
        rejection_reason=RejectionReason.VALID,
        margin_used=actual_margin,
        projected_size_fraction=projected_size,
        projected_bbox=projected_bbox
    )


def attempt_auto_correction(
    ring_geom: RingGeometry,
    camera_pose: CameraPose,
    sampled_params,
    visibility_config: VisibilityConfig,
    image_config: ImageOutputConfig,
    camera_config,  # CameraSamplingConfig for pitch limits
    max_corrections: int = 5
) -> Tuple[Optional[CameraPose], Optional[object], VisibilityResult]:
    """
    Attempt to auto-correct a camera pose that violates constraints.
    
    According to SPEC.md section 7.3:
    - Increase distance slightly
    - Reduce pitch if near extremes
    - Re-check visibility
    
    Args:
        ring_geom: Ring geometry
        camera_pose: Original camera pose
        sampled_params: Original sampled parameters
        visibility_config: Visibility constraints
        image_config: Image configuration
        camera_config: Camera sampling config (for pitch limits)
        max_corrections: Maximum number of correction attempts
    
    Returns:
        Tuple of (corrected_pose, corrected_params, visibility_result)
        Returns (None, None, result) if correction fails
    """
    from datasetgen.camera_sampling import CameraPose, SampledCameraParameters
    import math
    
    # Get original parameters
    original_yaw = sampled_params.yaw
    original_pitch = sampled_params.pitch
    original_distance = sampled_params.distance
    
    # First, check what the rejection reason was to determine correction strategy
    initial_result = check_visibility(
        ring_geom,
        camera_pose,
        visibility_config,
        image_config
    )
    
    # Determine correction strategy based on rejection reason
    if initial_result.rejection_reason == RejectionReason.TOO_SMALL:
        # Too small: decrease distance (move camera closer)
        # Use more aggressive correction: if size is 8.75% and we need 20%, 
        # we need ~2.3× larger, so decrease distance by ~56% (1/2.3)
        # But we'll do it incrementally: 0.7 factor = 30% closer per attempt
        distance_factor = 0.7  # Decrease distance by 30% (more aggressive)
        pitch_adjustment = 0.0  # Don't change pitch for size issues
    elif initial_result.rejection_reason == RejectionReason.TOO_LARGE:
        # Too large: increase distance (move camera farther)
        distance_factor = 1.1  # Increase distance by 10%
        pitch_adjustment = 0.0
    elif initial_result.rejection_reason == RejectionReason.CROPPED:
        # Cropped: increase distance and/or adjust pitch
        distance_factor = 1.1  # Increase distance by 10%
        pitch_adjustment = -5.0  # Reduce pitch by 5 degrees
    else:
        # For other reasons, use default strategy
        distance_factor = 1.1
        pitch_adjustment = -5.0
    
    # Get distance limits
    min_distance = camera_config.distance_min_multiplier * ring_geom.radius
    max_distance = camera_config.distance_max_multiplier * ring_geom.radius
    
    for attempt in range(max_corrections):
        # Calculate correction based on strategy
        # Apply distance factor: >1.0 increases distance, <1.0 decreases distance
        new_distance = original_distance * (distance_factor ** (attempt + 1))
        new_pitch = original_pitch + (pitch_adjustment * (attempt + 1))
        
        # Clamp pitch to valid range from config
        new_pitch = max(camera_config.pitch_min, min(camera_config.pitch_max, new_pitch))
        
        # Clamp distance to valid range
        new_distance = max(min_distance, min(max_distance, new_distance))
        
        # If distance hit the limit and we're trying to decrease, correction won't help
        if (initial_result.rejection_reason == RejectionReason.TOO_SMALL and 
            new_distance >= min_distance and 
            abs(new_distance - min_distance) < 0.001 * ring_geom.radius):
            # Already at minimum distance, can't get closer
            # Try increasing pitch instead (more direct view = larger apparent size)
            if attempt == 0:
                # Switch strategy: increase pitch to get more direct view
                pitch_adjustment = 10.0  # Increase pitch by 10 degrees
                new_pitch = min(camera_config.pitch_max, original_pitch + 10.0)
                new_distance = original_distance  # Keep original distance
            else:
                # Continue with pitch adjustment
                new_pitch = min(camera_config.pitch_max, new_pitch + 10.0)
        
        # Recompute camera pose with corrected parameters
        # Convert to spherical coordinates
        yaw_rad = math.radians(original_yaw)
        pitch_rad = math.radians(new_pitch)
        
        cos_pitch = math.cos(pitch_rad)
        sin_pitch = math.sin(pitch_rad)
        cos_yaw = math.cos(yaw_rad)
        sin_yaw = math.sin(yaw_rad)
        
        # Camera position relative to ring center
        camera_offset = Vector((
            new_distance * cos_pitch * cos_yaw,
            new_distance * cos_pitch * sin_yaw,
            new_distance * sin_pitch
        ))
        
        new_position = ring_geom.center + camera_offset
        
        # Ensure above table
        if new_position.z < ring_geom.table_plane_z:
            new_position.z = ring_geom.table_plane_z + 0.1 * ring_geom.radius
        
        # Recompute look-at and orientation (same as original)
        look_at_point = camera_pose.look_at
        forward = (look_at_point - new_position).normalized()
        world_up = Vector((0, 0, 1))
        right = forward.cross(world_up).normalized()
        up = right.cross(forward).normalized()
        
        rotation_matrix = Matrix((
            (right.x, up.x, -forward.x),
            (right.y, up.y, -forward.y),
            (right.z, up.z, -forward.z)
        ))
        
        corrected_pose = CameraPose(
            position=new_position,
            rotation_matrix=rotation_matrix,
            look_at=look_at_point,
            up=up
        )
        
        corrected_params = SampledCameraParameters(
            yaw=original_yaw,
            pitch=new_pitch,
            distance=new_distance,
            look_at_jitter=sampled_params.look_at_jitter
        )
        
        # Re-check visibility
        result = check_visibility(
            ring_geom,
            corrected_pose,
            visibility_config,
            image_config
        )
        
        if result.is_valid:
            return (corrected_pose, corrected_params, result)
    
    # All correction attempts failed
    return (None, None, result)


def validate_with_auto_correction(
    ring_geom: RingGeometry,
    camera_pose: CameraPose,
    sampled_params,
    visibility_config: VisibilityConfig,
    image_config: ImageOutputConfig,
    camera_config,  # CameraSamplingConfig for pitch limits
    enable_auto_correction: bool = True,
    max_corrections: int = 5
) -> Tuple[bool, Optional[CameraPose], Optional[object], VisibilityResult]:
    """
    Validate camera pose with optional auto-correction.
    
    Args:
        ring_geom: Ring geometry
        camera_pose: Camera pose to validate
        sampled_params: Sampled camera parameters
        visibility_config: Visibility constraints
        image_config: Image configuration
        camera_config: Camera sampling config (for pitch limits in auto-correction)
        enable_auto_correction: Whether to attempt auto-correction
        max_corrections: Maximum correction attempts
    
    Returns:
        Tuple of (is_valid, corrected_pose, corrected_params, visibility_result)
    """
    # Initial check
    result = check_visibility(
        ring_geom,
        camera_pose,
        visibility_config,
        image_config
    )
    
    if result.is_valid:
        return (True, camera_pose, sampled_params, result)
    
    # Attempt auto-correction if enabled
    if enable_auto_correction:
        corrected_pose, corrected_params, corrected_result = attempt_auto_correction(
            ring_geom,
            camera_pose,
            sampled_params,
            visibility_config,
            image_config,
            camera_config,
            max_corrections
        )
        
        if corrected_result.is_valid:
            return (True, corrected_pose, corrected_params, corrected_result)
    
    # Validation failed
    return (False, None, None, result)

