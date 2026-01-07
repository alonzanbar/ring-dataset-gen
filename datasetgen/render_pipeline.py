"""
Render pipeline for ring dataset generation.

Handles RGB rendering with configurable settings.
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to path to allow imports when run directly from Blender
# This MUST happen before any datasetgen imports
# This is needed because Blender's Python doesn't know about the project structure
try:
    # Try to determine project root from this file's location
    current_file = Path(__file__).absolute()
    project_root = current_file.parent.parent.absolute()
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
except (NameError, AttributeError, Exception) as e:
    # If __file__ is not available, we can't determine the path
    # This might happen in some Blender contexts, but should be rare
    import os
    # Try alternative: use current working directory
    try:
        cwd = Path(os.getcwd()).absolute()
        if str(cwd) not in sys.path:
            sys.path.insert(0, str(cwd))
    except:
        pass

# Now we can import Blender modules and project modules
import bpy
from mathutils import Matrix

from datasetgen.config import ImageOutputConfig
from datasetgen.camera_sampling import CameraPose


def configure_render_settings(
    image_config: ImageOutputConfig,
    render_engine: str = "CYCLES",
    use_gpu: bool = True
) -> None:
    """
    Configure Blender render settings for RGB image output.
    
    According to SPEC.md:
    - Section 9.2: RGB images only, PNG format
    - Section 9.2: Deterministic naming (000000.png, etc.)
    - Section 10: Headless execution (no UI state)
    
    Args:
        image_config: Image output configuration (width, height, format)
        render_engine: Render engine to use (default: "CYCLES")
        use_gpu: Whether to attempt GPU rendering (default: True, falls back to CPU if unavailable)
    """
    scene = bpy.context.scene
    
    # Set render engine
    scene.render.engine = render_engine
    
    # Set resolution
    scene.render.resolution_x = image_config.width
    scene.render.resolution_y = image_config.height
    
    # Set resolution percentage to 100% (no scaling)
    scene.render.resolution_percentage = 100
    
    # Configure output format (PNG for RGB)
    scene.render.image_settings.file_format = image_config.format
    
    # PNG settings for RGB
    if image_config.format == "PNG":
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.color_depth = "8"  # 8-bit RGB
        scene.render.image_settings.compression = 15  # PNG compression (0-100, 15 is good balance)
    
    # Disable transparency/alpha for RGB-only output
    scene.render.film_transparent = False
    
    # Set output color space to sRGB (standard for RGB images)
    scene.view_settings.view_transform = "Standard"
    scene.sequencer_colorspace_settings.name = "sRGB"
    
    # Optimize CYCLES for speed without sacrificing quality
    if render_engine == "CYCLES":
        # Try to use GPU for faster rendering (much faster than CPU)
        if use_gpu:
            try:
                # Enable Cycles addon preferences
                prefs = bpy.context.preferences
                cycles_addon = prefs.addons.get("cycles")
                
                if cycles_addon:
                    cycles_prefs = cycles_addon.preferences
                    # Refresh devices to detect available GPUs
                    cycles_prefs.refresh_devices()
                    
                    # Try to find and enable a GPU device
                    gpu_enabled = False
                    for device in cycles_prefs.devices:
                        # Prefer Metal on macOS, CUDA/OPTIX on Linux/Windows
                        if device.type in ["METAL", "CUDA", "OPTIX", "HIP", "OPENCL"]:
                            device.use = True
                            gpu_enabled = True
                            print(f"Using GPU: {device.name} ({device.type})")
                            break
                    
                    if gpu_enabled:
                        scene.cycles.device = "GPU"
                    else:
                        scene.cycles.device = "CPU"
                        print("No GPU found, using CPU")
                else:
                    scene.cycles.device = "CPU"
                    print("Cycles addon not available, using CPU")
            except Exception as e:
                # Fallback to CPU if GPU setup fails
                scene.cycles.device = "CPU"
                print(f"GPU setup failed ({e}), using CPU")
        else:
            scene.cycles.device = "CPU"
            print("Using CPU rendering")
        
        # Optimize tile size for better performance
        # Larger tiles for GPU, smaller for CPU
        # Note: In Blender 3.0+, tile settings are in cycles properties
        if scene.cycles.device == "GPU":
            # GPU benefits from larger tiles
            if hasattr(scene.cycles, 'tile_size'):
                scene.cycles.tile_size = 256
            elif hasattr(scene.render, 'tile_x'):
                scene.render.tile_x = 256
                scene.render.tile_y = 256
        else:
            # CPU benefits from smaller tiles
            if hasattr(scene.cycles, 'tile_size'):
                scene.cycles.tile_size = 64
            elif hasattr(scene.render, 'tile_x'):
                scene.render.tile_x = 64
                scene.render.tile_y = 64
        
        # Use adaptive sampling for better quality/speed balance
        # This maintains quality while potentially reducing render time
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.01  # Good quality threshold
        
        # Enable denoising for cleaner results (can use fewer samples)
        scene.cycles.use_denoising = True
        
        # Optimize light tree for faster rendering (Blender 3.5+)
        if hasattr(scene.cycles, 'use_light_tree'):
            scene.cycles.use_light_tree = True
        
        # Use persistent data to speed up multiple renders
        scene.render.use_persistent_data = True


def set_camera_pose(
    camera_pose: CameraPose,
    camera_object: Optional[bpy.types.Object] = None
) -> bpy.types.Object:
    """
    Set camera pose in the scene.
    
    According to SPEC.md:
    - Section 5: Camera pose is randomized (position, orientation)
    - Section 6: Camera looks at ring center with jitter
    
    Args:
        camera_pose: Camera pose to apply
        camera_object: Camera object to update (defaults to active camera or creates one)
    
    Returns:
        The camera object that was updated
    """
    # Get or create camera object
    if camera_object is None:
        if bpy.context.scene.camera is None:
            # Create camera if none exists
            bpy.ops.object.camera_add()
            camera_object = bpy.context.active_object
            # Set as scene camera
            bpy.context.scene.camera = camera_object
        else:
            camera_object = bpy.context.scene.camera
    
    # Ensure camera object is active
    bpy.context.view_layer.objects.active = camera_object
    
    # Set camera matrix_world from pose
    camera_object.matrix_world = camera_pose.to_matrix_world()
    
    return camera_object


def render_still(
    output_filepath: Path,
    camera_pose: CameraPose,
    image_config: ImageOutputConfig,
    camera_object: Optional[bpy.types.Object] = None,
    render_engine: str = "CYCLES",
    use_gpu: bool = True
) -> Path:
    """
    Render a still image with the given camera pose.
    
    According to SPEC.md:
    - Section 9.2: RGB images only, PNG format
    - Section 9.2: Deterministic file paths
    - Section 10: Headless execution
    
    Args:
        output_filepath: Path where the rendered image will be saved
        camera_pose: Camera pose to use for rendering
        image_config: Image output configuration (width, height, format)
        camera_object: Camera object to use (defaults to active camera or creates one)
        render_engine: Render engine to use (default: "CYCLES")
        use_gpu: Whether to attempt GPU rendering (default: True, falls back to CPU)
    
    Returns:
        Path to the rendered image file
    
    Raises:
        RuntimeError: If rendering fails
    """
    # Configure render settings with optimizations
    configure_render_settings(image_config, render_engine, use_gpu=use_gpu)
    
    # Set camera pose
    camera_obj = set_camera_pose(camera_pose, camera_object)
    
    # Ensure output directory exists
    output_filepath = Path(output_filepath)
    output_filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Set output filepath in Blender
    # Blender expects absolute path for headless rendering
    abs_output_path = str(output_filepath.absolute())
    device = bpy.context.scene.cycles.device if render_engine == "CYCLES" else "N/A"
    print(f"Rendering to: {abs_output_path}")
    print(f"Device: {device}, Engine: {render_engine}")
    bpy.context.scene.render.filepath = abs_output_path
    
    # Render the image
    try:
        import time
        start_time = time.time()
        bpy.ops.render.render(write_still=True)
        elapsed = time.time() - start_time
        print(f"Render completed in {elapsed:.2f} seconds")
    except Exception as e:
        raise RuntimeError(f"Failed to render image to {output_filepath}: {e}") from e
    
    # Verify file was created
    if not output_filepath.exists():
        raise RuntimeError(f"Rendered image file not found at {output_filepath}")
    
    return output_filepath


def test_render_pipeline(
    output_filepath: Optional[Path] = None,
    test_ring_geometry: Optional[object] = None
) -> bool:
    """
    Test the render pipeline with a simple test scene.
    
    This function can be called from within Blender to test rendering functionality.
    It creates a simple test camera pose and renders an image.
    
    Args:
        output_filepath: Optional path for test output (defaults to output/test_render.png)
        test_ring_geometry: Optional RingGeometry object to use for camera positioning.
                          If None, creates a simple test pose looking at origin.
    
    Returns:
        True if test passed, False otherwise
    
    Example usage in Blender:
        from datasetgen.render_pipeline import test_render_pipeline
        test_render_pipeline(Path("output/test_render.png"))
    """
    try:
        from mathutils import Vector, Matrix
        from datasetgen.scene_introspection import introspect_ring
        
        # Default output path
        if output_filepath is None:
            output_filepath = Path("output/test_render.png")
        
        # Create test image config
        image_config = ImageOutputConfig(width=640, height=480, format="PNG")
        
        # Create test camera pose
        if test_ring_geometry is not None:
            # Use ring geometry if provided
            ring_geom = test_ring_geometry
            # Create a simple test pose: camera at (0, -5, 3) looking at ring center
            camera_position = Vector((0, -5, 3))
            look_at_point = ring_geom.center
        else:
            # Simple test pose looking at origin
            camera_position = Vector((0, -5, 3))
            look_at_point = Vector((0, 0, 0))
        
        # Compute camera orientation
        forward = (look_at_point - camera_position).normalized()
        world_up = Vector((0, 0, 1))
        right = forward.cross(world_up).normalized()
        up = right.cross(forward).normalized()
        
        # Build rotation matrix
        rotation_matrix = Matrix((
            (right.x, up.x, -forward.x),
            (right.y, up.y, -forward.y),
            (right.z, up.z, -forward.z)
        ))
        
        # Create camera pose
        test_pose = CameraPose(
            position=camera_position,
            rotation_matrix=rotation_matrix,
            look_at=look_at_point,
            up=up
        )
        
        print(f"Testing render pipeline...")
        print(f"  Output: {output_filepath}")
        print(f"  Resolution: {image_config.width}x{image_config.height}")
        print(f"  Camera position: ({camera_position.x:.2f}, {camera_position.y:.2f}, {camera_position.z:.2f})")
        print(f"  Look at: ({look_at_point.x:.2f}, {look_at_point.y:.2f}, {look_at_point.z:.2f})")
        
        # Test render
        rendered_path = render_still(
            output_filepath=output_filepath,
            camera_pose=test_pose,
            image_config=image_config,
            render_engine="CYCLES"
        )
        
        # Verify output
        if rendered_path.exists():
            file_size = rendered_path.stat().st_size
            print(f"✓ Test passed! Rendered image: {rendered_path}")
            print(f"  File size: {file_size} bytes")
            return True
        else:
            print(f"✗ Test failed: Output file not found at {rendered_path}")
            return False
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # This can be run from Blender's Python console or as a script
    # Usage: blender -b scene.blend -P datasetgen/render_pipeline.py
    print("=" * 60)
    print("Render Pipeline Test")
    print("=" * 60)
    
    # Try to use ring geometry if available
    try:
        from datasetgen.scene_introspection import introspect_ring
        ring_geom = introspect_ring("ring")
        print(f"Found ring object, using it for test")
        success = test_render_pipeline(
            output_filepath=Path("output/test_render.png"),
            test_ring_geometry=ring_geom
        )
    except RuntimeError:
        print("No ring object found, using simple test pose")
        success = test_render_pipeline(
            output_filepath=Path("output/test_render.png"),
            test_ring_geometry=None
        )
    
    if success:
        print("=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
    else:
        print("=" * 60)
        print("Test failed!")
        print("=" * 60)
        exit(1)
