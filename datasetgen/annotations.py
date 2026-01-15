"""
Annotation writing for ring dataset generation.

Handles writing annotations.jsonl with metadata for each rendered image.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from mathutils import Matrix

from datasetgen.config import ImageOutputConfig
from datasetgen.camera_sampling import CameraPose, SampledCameraParameters
from datasetgen.visibility_checks import VisibilityResult
from datasetgen.scene_introspection import RingGeometry


def create_annotation_record(
    image_path: str,
    camera_pose: CameraPose,
    sampled_params: SampledCameraParameters,
    visibility_result: VisibilityResult,
    image_config: ImageOutputConfig,
    ring_radius: float,
    sample_index: int,
    attempts: int
) -> Dict[str, Any]:
    """
    Create a single annotation record for a rendered image.
    
    According to SPEC.md section 9.3, each record must include:
    - Image path (relative)
    - Camera extrinsics (matrix or position + orientation)
    - Camera intrinsics
    - Sampled parameters (yaw, pitch, distance)
    - Visibility metrics (margin used, projected size fraction)
    
    Args:
        image_path: Relative path to the image file
        camera_pose: Camera pose used for rendering
        sampled_params: Sampled camera parameters
        visibility_result: Visibility check results
        image_config: Image output configuration
        ring_radius: Ring bounding sphere radius (R)
        sample_index: Sample index number
        attempts: Number of attempts needed to find valid pose
    
    Returns:
        Dictionary containing the annotation record
    """
    # Convert matrix_world to list of lists for JSON serialization
    matrix_world = camera_pose.to_matrix_world()
    matrix_list = [
        [float(matrix_world[i][j]) for j in range(4)]
        for i in range(4)
    ]
    
    # Build annotation record with stable, deterministic schema
    annotation = {
        "image_path": image_path,
        "camera_extrinsics": {
            "matrix_world": matrix_list,
            "position": {
                "x": float(camera_pose.position.x),
                "y": float(camera_pose.position.y),
                "z": float(camera_pose.position.z)
            },
            "look_at": {
                "x": float(camera_pose.look_at.x),
                "y": float(camera_pose.look_at.y),
                "z": float(camera_pose.look_at.z)
            }
        },
        "camera_intrinsics": {
            "width": image_config.width,
            "height": image_config.height,
            "format": image_config.format
        },
        "sampled_parameters": {
            "yaw": float(sampled_params.yaw),
            "pitch": float(sampled_params.pitch),
            "distance": float(sampled_params.distance),
            "distance_multiplier": float(sampled_params.distance / ring_radius),
            "look_at_jitter": {
                "x": float(sampled_params.look_at_jitter.x),
                "y": float(sampled_params.look_at_jitter.y),
                "z": float(sampled_params.look_at_jitter.z)
            }
        },
        "visibility_metrics": {
            "margin_used": float(visibility_result.margin_used) if visibility_result.margin_used is not None else None,
            "projected_size_fraction": float(visibility_result.projected_size_fraction) if visibility_result.projected_size_fraction is not None else None,
            "projected_bbox": list(visibility_result.projected_bbox) if visibility_result.projected_bbox else None
        },
        "sample_index": sample_index,
        "attempts": attempts
    }
    
    return annotation


def write_annotations_jsonl(
    annotations_path: Path,
    samples: List[Dict[str, Any]],
    image_config: ImageOutputConfig,
    ring_radius: float
) -> int:
    """
    Write annotations.jsonl file with one record per rendered image.
    
    According to SPEC.md section 9.3:
    - One JSON object per line
    - Contains image path, camera extrinsics, camera intrinsics,
      sampled parameters, and visibility metrics
    
    Args:
        annotations_path: Path to output annotations.jsonl file
        samples: List of sample dictionaries, each containing:
            - 'image_path': relative path to image
            - 'pose': CameraPose object
            - 'params': SampledCameraParameters object
            - 'visibility_result': VisibilityResult object
            - 'sample_idx': sample index
            - 'attempts': number of attempts
        image_config: Image output configuration
        ring_radius: Ring bounding sphere radius (R)
    
    Returns:
        Number of annotations written
    
    Raises:
        IOError: If file writing fails
    """
    annotations_path = Path(annotations_path)
    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    
    written_count = 0
    
    with open(annotations_path, 'w') as f:
        for sample in samples:
            # Skip samples that don't have image_path (failed to render)
            if 'image_path' not in sample:
                continue
            
            # Create annotation record
            annotation = create_annotation_record(
                image_path=sample['image_path'],
                camera_pose=sample['pose'],
                sampled_params=sample['params'],
                visibility_result=sample['visibility_result'],
                image_config=image_config,
                ring_radius=ring_radius,
                sample_index=sample['sample_idx'],
                attempts=sample['attempts']
            )
            
            # Write as JSON line (SPEC.md section 9.3)
            f.write(json.dumps(annotation, ensure_ascii=False) + "\n")
            written_count += 1
    
    return written_count


