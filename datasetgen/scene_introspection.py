"""
Scene introspection for ring dataset generation.

Finds the ring object in the Blender scene and computes its geometric properties.
"""

from typing import Optional, Tuple
import mathutils
import bpy
import bmesh
from mathutils import Vector


class RingGeometry:
    """Geometric properties of the ring object."""
    
    def __init__(
        self,
        center: Vector,
        radius: float,
        bounding_box_world: Tuple[Vector, Vector],  # (min, max) corners
        table_plane_z: float
    ):
        """
        Initialize ring geometry.
        
        Args:
            center: World-space center of the ring (Vector)
            radius: Bounding sphere radius (float)
            bounding_box_world: World-space bounding box as (min, max) corners
            table_plane_z: Z coordinate of the table plane (min_z of bounding box)
        """
        self.center = center
        self.radius = radius
        self.bounding_box_world = bounding_box_world
        self.table_plane_z = table_plane_z
    
    def __repr__(self) -> str:
        return (
            f"RingGeometry(center={self.center}, radius={self.radius:.4f}, "
            f"table_plane_z={self.table_plane_z:.4f})"
        )


def find_ring_object(ring_object_name: str) -> Optional[bpy.types.Object]:
    """
    Find the ring object in the scene.
    
    According to SPEC.md section 3, the ring object can be:
    - A mesh object, OR
    - An empty whose children contain the renderable mesh(es)
    
    Args:
        ring_object_name: Name of the ring object to find
    
    Returns:
        The ring object if found, None otherwise
    """
    # First, try to find object by exact name
    if ring_object_name in bpy.data.objects:
        obj = bpy.data.objects[ring_object_name]
        return obj
    
    # If not found, search case-insensitively (but prefer exact match)
    for obj in bpy.data.objects:
        if obj.name == ring_object_name or obj.name.lower() == ring_object_name.lower():
            return obj
    
    return None


def get_all_mesh_objects(obj: bpy.types.Object) -> list[bpy.types.Object]:
    """
    Get all mesh objects from an object and its children.
    
    Handles the case where the ring object is an empty with children.
    
    Args:
        obj: The root object (may be empty or mesh)
    
    Returns:
        List of all mesh objects (including the object itself if it's a mesh)
    """
    mesh_objects = []
    
    # If the object itself is a mesh, include it
    if obj.type == 'MESH':
        mesh_objects.append(obj)
    
    # Recursively collect all child mesh objects
    def collect_children(parent_obj):
        for child in parent_obj.children:
            if child.type == 'MESH':
                mesh_objects.append(child)
            collect_children(child)
    
    collect_children(obj)
    
    return mesh_objects


def compute_world_space_bounding_box(obj: bpy.types.Object) -> Tuple[Vector, Vector]:
    """
    Compute world-space bounding box for an object and all its children.
    
    Args:
        obj: The root object
    
    Returns:
        Tuple of (min_corner, max_corner) in world space
    """
    mesh_objects = get_all_mesh_objects(obj)
    
    if not mesh_objects:
        raise ValueError(
            f"Object '{obj.name}' has no mesh geometry. "
            "Ring object must be a mesh or empty with mesh children."
        )
    
    # Initialize with first vertex
    first_obj = mesh_objects[0]
    # Get world matrix
    world_matrix = first_obj.matrix_world
    
    # Get mesh data (may need to be evaluated in edit mode)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    first_eval = first_obj.evaluated_get(depsgraph)
    first_mesh = first_eval.to_mesh()
    
    if not first_mesh.vertices:
        first_eval.to_mesh_clear()
        raise ValueError(f"Object '{first_obj.name}' has no vertices.")
    
    # Transform first vertex to world space
    first_vert_world = world_matrix @ first_mesh.vertices[0].co
    min_corner = Vector(first_vert_world)
    max_corner = Vector(first_vert_world)
    
    first_eval.to_mesh_clear()
    
    # Process all mesh objects
    for mesh_obj in mesh_objects:
        world_matrix = mesh_obj.matrix_world
        
        # Get evaluated mesh (handles modifiers)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = mesh_obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        
        # Transform all vertices to world space
        for vertex in mesh.vertices:
            vert_world = world_matrix @ vertex.co
            min_corner.x = min(min_corner.x, vert_world.x)
            min_corner.y = min(min_corner.y, vert_world.y)
            min_corner.z = min(min_corner.z, vert_world.z)
            max_corner.x = max(max_corner.x, vert_world.x)
            max_corner.y = max(max_corner.y, vert_world.y)
            max_corner.z = max(max_corner.z, vert_world.z)
        
        eval_obj.to_mesh_clear()
    
    return (min_corner, max_corner)


def compute_bounding_sphere_radius(bounding_box_min: Vector, bounding_box_max: Vector) -> float:
    """
    Compute bounding sphere radius from bounding box.
    
    The radius is half the diagonal of the bounding box.
    
    Args:
        bounding_box_min: Minimum corner of bounding box
        bounding_box_max: Maximum corner of bounding box
    
    Returns:
        Radius of the bounding sphere
    """
    diagonal = bounding_box_max - bounding_box_min
    radius = diagonal.length / 2.0
    return radius


def compute_ring_center(bounding_box_min: Vector, bounding_box_max: Vector) -> Vector:
    """
    Compute center point of the bounding box.
    
    Args:
        bounding_box_min: Minimum corner of bounding box
        bounding_box_max: Maximum corner of bounding box
    
    Returns:
        Center point as Vector
    """
    center = (bounding_box_min + bounding_box_max) / 2.0
    return center


def introspect_ring(ring_object_name: str) -> RingGeometry:
    """
    Find the ring object and compute its geometric properties.
    
    According to SPEC.md:
    - Section 3: Find object named "ring" (mesh or empty with children)
    - Section 4: table_plane_z = min_z of ring world-space bounding box
    - Section 5.2: R = ring bounding sphere radius
    
    Args:
        ring_object_name: Name of the ring object to find
    
    Returns:
        RingGeometry object with all computed properties
    
    Raises:
        RuntimeError: If ring object is not found (fails loudly per SPEC.md section 3)
        ValueError: If ring object has no geometry
    """
    # Find the ring object
    ring_obj = find_ring_object(ring_object_name)
    
    if ring_obj is None:
        # Fail loudly with clear error message (SPEC.md section 3)
        available_objects = [obj.name for obj in bpy.data.objects]
        raise RuntimeError(
            f"Ring object '{ring_object_name}' not found in scene!\n"
            f"Available objects: {', '.join(available_objects) if available_objects else '(none)'}\n"
            f"The ring object must exist and be named '{ring_object_name}'."
        )
    
    # Compute world-space bounding box
    try:
        bbox_min, bbox_max = compute_world_space_bounding_box(ring_obj)
    except ValueError as e:
        raise ValueError(
            f"Failed to compute bounding box for ring object '{ring_object_name}': {e}"
        )
    
    # Compute center (midpoint of bounding box)
    center = compute_ring_center(bbox_min, bbox_max)
    
    # Compute bounding sphere radius R (SPEC.md section 5.2)
    radius = compute_bounding_sphere_radius(bbox_min, bbox_max)
    
    # Compute table plane Z (SPEC.md section 4)
    # table_plane_z = min_z of ring world-space bounding box
    table_plane_z = bbox_min.z
    
    return RingGeometry(
        center=center,
        radius=radius,
        bounding_box_world=(bbox_min, bbox_max),
        table_plane_z=table_plane_z
    )

