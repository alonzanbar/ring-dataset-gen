#!/usr/bin/env python3
"""
Ring dataset generation script for Blender.

This script runs in headless Blender mode to generate a dataset of RGB images
with camera-only randomization.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import datasetgen modules
# Use absolute path to avoid issues
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Debug: Print paths (will only show if script actually runs)
try:
    print(f"Python executable: {sys.executable}", file=sys.stderr)
    print(f"Project root: {project_root}", file=sys.stderr)
    print(f"Script path: {Path(__file__).absolute()}", file=sys.stderr)
except:
    pass

try:
    from datasetgen.config import parse_cli_args, create_config_from_args, write_run_config, get_blender_version
    from datasetgen.scene_introspection import introspect_ring
    from datasetgen.camera_sampling import sample_camera_pose
    from datasetgen.visibility_checks import validate_with_auto_correction, RejectionReason
    from datasetgen.render_pipeline import render_still
    from datasetgen.annotations import write_annotations_jsonl
except ImportError as e:
    print(f"Error importing module: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    # Try to continue with minimal functionality
    try:
        import bpy
        print("Blender bpy module is available", file=sys.stderr)
    except ImportError:
        print("Blender bpy module not available", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point for the dataset generation script."""
    try:
        # Parse command-line arguments
        args = parse_cli_args()
        
        # Create configuration from args (loads JSON defaults, then applies CLI overrides)
        config = create_config_from_args(args)
        
        # Get mode from args
        mode = args.mode if hasattr(args, 'mode') else "validate"
        
        # Get Blender version
        try:
            import bpy
            config.blender_version = bpy.app.version_string
            print(f"Blender version detected: {config.blender_version}")
        except ImportError:
            config.blender_version = get_blender_version()
            print("Blender bpy module not available")
        
        # Print configuration summary
        print("=" * 60)
        print("Ring Dataset Generation")
        print("=" * 60)
        print(f"Mode: {mode}")
        print(f"Ring object name: {config.ring_object_name}")
        print(f"Number of images: {config.num_images}")
        print(f"Output directory: {config.output_dir}")
        print(f"Seed: {config.seed}")
        print(f"Blender version: {config.blender_version}")
        print(f"Image size: {config.image_output.width}x{config.image_output.height}")
        print(f"Camera pitch range: {config.camera.pitch_min}° - {config.camera.pitch_max}°")
        print(f"Camera distance range: {config.camera.distance_min_multiplier}x - {config.camera.distance_max_multiplier}x")
        print("=" * 60)
        print()
        
        # Create output directory structure
        output_dir = Path(config.output_dir)
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Write run configuration
        run_config_path = output_dir / "run_config.json"
        write_run_config(config, run_config_path)
        
        print(f"Output directory created: {output_dir}")
        print(f"Images directory: {images_dir}")
        print()
        
        # Scene introspection: Find and analyze the ring object
        print("Analyzing scene...")
        try:
            ring_geom = introspect_ring(config.ring_object_name)
            print(f"✓ Found ring object: '{config.ring_object_name}'")
            print(f"  Center: ({ring_geom.center.x:.4f}, {ring_geom.center.y:.4f}, {ring_geom.center.z:.4f})")
            print(f"  Bounding sphere radius (R): {ring_geom.radius:.4f}")
            print(f"  Table plane Z: {ring_geom.table_plane_z:.4f}")
            bbox_min, bbox_max = ring_geom.bounding_box_world
            print(f"  Bounding box min: ({bbox_min.x:.4f}, {bbox_min.y:.4f}, {bbox_min.z:.4f})")
            print(f"  Bounding box max: ({bbox_max.x:.4f}, {bbox_max.y:.4f}, {bbox_max.z:.4f})")
            print()
        except RuntimeError as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"✗ Error during scene introspection: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
        
        # Initialize random number generator for reproducibility
        import random
        from collections import defaultdict
        rng = random.Random(config.seed) if config.seed is not None else random.Random()
        
        # Track rejection reasons for diagnostics (SPEC.md section 8)
        rejection_counts = defaultdict(int)
        valid_samples = []
        total_attempts = 0
        
        print(f"Generating {config.num_images} samples...")
        print(f"Max attempts per sample: {config.sampling.max_attempts_per_sample}")
        print()
        
        sample_idx = 0
        while len(valid_samples) < config.num_images:
            # Prevent infinite loop (SPEC.md section 8)
            if total_attempts > config.num_images * config.sampling.max_attempts_per_sample * 2:
                print(f"✗ Error: Too many attempts ({total_attempts}). Stopping to prevent infinite loop.", file=sys.stderr)
                break
            
            # Attempt to find a valid camera pose for this sample
            attempts_for_sample = 0
            found_valid = False
            
            for attempt in range(config.sampling.max_attempts_per_sample):
                total_attempts += 1
                attempts_for_sample += 1
                
                try:
                    # Sample a camera pose (SPEC.md section 5)
                    camera_pose, sampled_params = sample_camera_pose(ring_geom, config.camera, rng)
                    
                    # Store initial sampled values to detect auto-correction
                    initial_yaw = sampled_params.yaw
                    initial_pitch = sampled_params.pitch
                    initial_distance = sampled_params.distance / ring_geom.radius
                    
                    # Validate visibility with auto-correction (SPEC.md section 7)
                    is_valid, final_pose, final_params, visibility_result = validate_with_auto_correction(
                        ring_geom,
                        camera_pose,
                        sampled_params,
                        config.visibility,
                        config.image_output,
                        config.camera,
                        enable_auto_correction=True,
                        max_corrections=5
                    )
                    
                    if is_valid:
                        # Valid pose found!
                        sample_data = {
                            'sample_idx': sample_idx,
                            'pose': final_pose,
                            'params': final_params,
                            'visibility_result': visibility_result,
                            'attempts': attempts_for_sample
                        }
                        valid_samples.append(sample_data)
                        found_valid = True
                        
                        # Check if auto-correction was applied (compare initial vs final)
                        corrected = (abs(final_params.yaw - initial_yaw) > 0.1 or 
                                   abs(final_params.pitch - initial_pitch) > 0.1 or
                                   abs(final_params.distance/ring_geom.radius - initial_distance) > 0.01)
                        
                        # Log all valid samples with details
                        if corrected:
                            print(f"  Sample {sample_idx}: ✓ Valid after {attempts_for_sample} attempt(s) (auto-corrected)")
                            print(f"    Initial: yaw={initial_yaw:.2f}°, pitch={initial_pitch:.2f}°, dist={initial_distance:.2f}×R")
                            print(f"    Final:   yaw={final_params.yaw:.2f}°, pitch={final_params.pitch:.2f}°, dist={final_params.distance/ring_geom.radius:.2f}×R")
                        else:
                            print(f"  Sample {sample_idx}: ✓ Valid after {attempts_for_sample} attempt(s) | yaw={initial_yaw:.2f}°, pitch={initial_pitch:.2f}°, dist={initial_distance:.2f}×R")
                        
                        # In render mode: render the image and record annotation
                        if mode == "render":
                            try:
                                # Generate image filename (SPEC.md section 9.2: deterministic naming)
                                image_filename = f"{sample_idx:06d}.png"
                                image_path = images_dir / image_filename
                                
                                # Render the image
                                print(f"    Rendering to: {image_filename}")
                                rendered_path = render_still(
                                    output_filepath=image_path,
                                    camera_pose=final_pose,
                                    image_config=config.image_output,
                                    use_gpu=True
                                )
                                
                                # Store image path in sample data
                                sample_data['image_path'] = str(image_path.relative_to(output_dir))
                                sample_data['image_filename'] = image_filename
                                
                                print(f"    ✓ Rendered: {image_filename}")
                            except Exception as e:
                                print(f"    ✗ Render failed: {e}", file=sys.stderr)
                                # Remove from valid samples if render failed
                                valid_samples.pop()
                                found_valid = False
                                continue
                        
                        break
                    else:
                        # Track rejection reason (SPEC.md section 8)
                        if config.sampling.track_rejection_reasons:
                            rejection_counts[visibility_result.rejection_reason] += 1
                        
                        # Log rejection details
                        rejection_msg = f"  Sample {sample_idx}, attempt {attempts_for_sample}: ✗ {visibility_result.rejection_reason.value}"
                        
                        # Add detailed rejection information
                        if visibility_result.rejection_reason == RejectionReason.TOO_SMALL:
                            if visibility_result.projected_size_fraction is not None:
                                rejection_msg += f" (size: {visibility_result.projected_size_fraction:.4f} = {visibility_result.projected_size_fraction*100:.2f}%, need: {config.visibility.min_projected_size_fraction*100:.0f}%)"
                                rejection_msg += f" | distance: {sampled_params.distance / ring_geom.radius:.2f}×R"
                        
                        elif visibility_result.rejection_reason == RejectionReason.TOO_LARGE:
                            if visibility_result.projected_size_fraction is not None:
                                rejection_msg += f" (size: {visibility_result.projected_size_fraction:.4f} = {visibility_result.projected_size_fraction*100:.2f}%, max: {config.visibility.max_projected_size_fraction*100:.0f}%)"
                        
                        elif visibility_result.rejection_reason == RejectionReason.CROPPED:
                            if visibility_result.margin_used is not None:
                                rejection_msg += f" (margin: {visibility_result.margin_used:.4f} = {visibility_result.margin_used*100:.2f}%, need: {config.visibility.edge_margin_fraction*100:.0f}%)"
                            if visibility_result.projected_bbox is not None:
                                min_x, min_y, max_x, max_y = visibility_result.projected_bbox
                                rejection_msg += f" | bbox: [{min_x:.3f}, {min_y:.3f}] to [{max_x:.3f}, {max_y:.3f}]"
                        
                        elif visibility_result.rejection_reason == RejectionReason.BELOW_TABLE_PLANE:
                            rejection_msg += f" | camera Z: {camera_pose.position.z:.4f}, table Z: {ring_geom.table_plane_z:.4f}"
                        
                        print(rejection_msg)
                
                except Exception as e:
                    print(f"✗ Error during sample {sample_idx}, attempt {attempts_for_sample}: {e}", file=sys.stderr)
                    if config.sampling.track_rejection_reasons:
                        rejection_counts[RejectionReason.INVALID_PROJECTION] += 1
            
            if found_valid:
                sample_idx += 1
                if sample_idx % 10 == 0 or sample_idx == config.num_images:
                    print(f"Progress: {sample_idx}/{config.num_images} valid samples found (total attempts: {total_attempts})")
            else:
                # Failed to find valid pose after max attempts
                if config.sampling.track_rejection_reasons:
                    # Count the last rejection reason
                    rejection_counts[visibility_result.rejection_reason] += 1
                print(f"⚠ Sample {sample_idx}: Failed to find valid pose after {attempts_for_sample} attempts")
                print(f"  Last rejection: {visibility_result.rejection_reason.value}")
                if visibility_result.projected_size_fraction is not None:
                    print(f"  Last projected size: {visibility_result.projected_size_fraction:.4f}")
        
        print()
        print("=" * 60)
        print(f"Sampling Complete")
        print("=" * 60)
        print(f"Valid samples generated: {len(valid_samples)}/{config.num_images}")
        print(f"Total attempts: {total_attempts}")
        if total_attempts > 0:
            success_rate = (len(valid_samples) / total_attempts) * 100
            print(f"Success rate: {success_rate:.2f}%")
            rejection_rate = ((total_attempts - len(valid_samples)) / total_attempts) * 100
            print(f"Rejection rate: {rejection_rate:.2f}%")
        
        # Print rejection statistics (SPEC.md section 8)
        if config.sampling.track_rejection_reasons and rejection_counts:
            print("\nRejection statistics:")
            total_rejections = sum(rejection_counts.values())
            for reason, count in sorted(rejection_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_rejections * 100) if total_rejections > 0 else 0
                print(f"  {reason.value}: {count} ({percentage:.1f}%)")
        print("=" * 60)
        print()
        
        if len(valid_samples) == 0:
            print("✗ Error: No valid samples generated!", file=sys.stderr)
            return 1
        
        # In render mode: write annotations.jsonl (SPEC.md section 9.3)
        if mode == "render":
            annotations_path = output_dir / "annotations.jsonl"
            print(f"\nWriting annotations to: {annotations_path}")
            
            try:
                written_count = write_annotations_jsonl(
                    annotations_path=annotations_path,
                    samples=valid_samples,
                    image_config=config.image_output,
                    ring_radius=ring_geom.radius
                )
                print(f"✓ Wrote {written_count} annotations")
            except Exception as e:
                print(f"✗ Error writing annotations: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        
        # Display sample from valid poses
        if len(valid_samples) > 0:
            sample = valid_samples[0]
            print(f"\nExample valid sample:")
            print(f"  Sample index: {sample['sample_idx']}")
            print(f"  Attempts needed: {sample['attempts']}")
            print(f"  Yaw: {sample['params'].yaw:.2f}°, Pitch: {sample['params'].pitch:.2f}°")
            print(f"  Distance: {sample['params'].distance / ring_geom.radius:.2f}×R")
            print(f"  Margin used: {sample['visibility_result'].margin_used:.4f}")
            print(f"  Projected size: {sample['visibility_result'].projected_size_fraction:.4f}")
            if mode == "render" and 'image_path' in sample:
                print(f"  Image: {sample['image_path']}")
            print()
        
        # Print completion message
        if mode == "validate":
            print("Validation complete (no rendering performed)")
        else:
            rendered_count = len([s for s in valid_samples if 'image_path' in s])
            print(f"Dataset generation complete: {rendered_count} images rendered")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
