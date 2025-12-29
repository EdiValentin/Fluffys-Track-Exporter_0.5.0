from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import bpy
from mathutils import Matrix, Quaternion, Vector

if TYPE_CHECKING:
    from bpy.types import Context, Material, ShaderNodeTexImage


def convert_vector3(blender_vec: Vector) -> Vector:
    """
    Convert Blender Z-up vector to Assetto Corsa Y-up coordinate system.

    Blender uses:  X=right, Y=forward, Z=up
    AC uses:       X=right, Y=up,      Z=forward

    Transformation: (X, Y, Z) → (X, Z, -Y)

    Args:
        blender_vec: Blender Vector in Z-up coordinates

    Returns:
        Vector in AC Y-up coordinates
    """
    return Vector((blender_vec[0], blender_vec[2], -blender_vec[1]))


def convert_quaternion(blender_quat: Quaternion) -> Quaternion:
    """
    Convert Blender Z-up quaternion to AC Y-up coordinate system.

    Args:
        blender_quat: Blender Quaternion rotation

    Returns:
        Quaternion in AC Y-up coordinates
    """
    axis, angle = blender_quat.to_axis_angle()
    axis = convert_vector3(axis)
    return Quaternion(axis, angle)


def convert_matrix(blender_matrix: Matrix) -> Matrix:
    """
    Convert Blender Z-up transformation matrix to AC Y-up coordinate system.

    Decomposes into translation, rotation, scale, converts each component,
    then rebuilds the matrix in AC's coordinate system.

    Args:
        blender_matrix: Blender 4x4 transformation matrix

    Returns:
        Matrix in AC Y-up coordinates
    """
    translation, rotation, scale = blender_matrix.decompose()
    translation = convert_vector3(translation)
    rotation = convert_quaternion(rotation)

    mat_loc = Matrix.Translation(translation)
    mat_scale_1 = Matrix.Scale(scale[0], 4, (1, 0, 0))
    mat_scale_2 = Matrix.Scale(scale[2], 4, (0, 1, 0))
    mat_scale_3 = Matrix.Scale(scale[1], 4, (0, 0, 1))
    mat_scale = mat_scale_1 @ mat_scale_2 @ mat_scale_3
    mat_rot = rotation.to_matrix().to_4x4()

    return mat_loc @ mat_rot @ mat_scale


def get_texture_nodes(material: Material) -> list[ShaderNodeTexImage]:
    """
    Get all texture image nodes from a material's node tree.

    Args:
        material: Blender material to extract texture nodes from

    Returns:
        List of ShaderNodeTexImage nodes
    """
    texture_nodes = []
    if material.node_tree:
        for node in material.node_tree.nodes:
            if isinstance(node, bpy.types.ShaderNodeTexImage):
                texture_nodes.append(node)
    return texture_nodes


def get_all_texture_nodes(context: Context) -> list[ShaderNodeTexImage]:
    """
    Get all texture image nodes from all materials in the scene.

    Args:
        context: Blender context

    Returns:
        List of all ShaderNodeTexImage nodes in the scene
    """
    scene_texture_nodes = []
    for obj in context.blend_data.objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            if slot.material:
                scene_texture_nodes.extend(get_texture_nodes(slot.material))
    return scene_texture_nodes


def get_active_material_texture_slot(material: Material) -> ShaderNodeTexImage | None:
    """
    Get the active (visible) texture node from a material.

    Args:
        material: Blender material

    Returns:
        The active texture node, or None if no active texture
    """
    texture_nodes = get_texture_nodes(material)
    for texture_node in texture_nodes:
        if texture_node.show_texture:
            return texture_node
    return None


def is_object_excluded_by_collection(obj, context: Context) -> bool:
    """
    Check if an object should be excluded from export based on visibility settings.

    An object is excluded if:
    1. The object itself has hide_viewport enabled (monitor icon disabled on object)
    2. The object itself has hide_render enabled (camera icon disabled on object)
    3. The object is hidden in the view layer (eye icon disabled on object in outliner)
    4. ALL collections it belongs to are either:
       - Excluded from the view layer (checkbox disabled in outliner)
       - Hidden in the viewport (eye icon disabled on collection)

    Args:
        obj: Blender object to check
        context: Blender context

    Returns:
        True if the object should be excluded from export, False otherwise
    """
    # Check object-level visibility settings first
    if obj.hide_viewport:
        return True

    if obj.hide_render:
        return True

    # Check if object is hidden in the current view layer (eye icon in outliner)
    if obj.hide_get():
        return True

    # Get all collections this object belongs to
    obj_collections = obj.users_collection

    # If object is not in any collection, don't exclude it
    if not obj_collections:
        return False

    # Get the view layer's layer collection for checking exclusion
    view_layer = context.view_layer
    layer_collection = view_layer.layer_collection

    def find_layer_collection(layer_col, collection):
        """Recursively find a layer collection by its collection."""
        if layer_col.collection == collection:
            return layer_col
        for child in layer_col.children:
            result = find_layer_collection(child, collection)
            if result:
                return result
        return None

    # Check each collection the object belongs to
    all_excluded = True
    for collection in obj_collections:
        # Check if collection is hidden in viewport
        if not collection.hide_viewport:
            # Find the layer collection to check exclusion
            layer_col = find_layer_collection(layer_collection, collection)
            if layer_col and not layer_col.exclude:
                # Found at least one visible and non-excluded collection
                all_excluded = False
                break

    return all_excluded


def read_settings(file: str) -> dict:
    """
    Read settings.json from the same directory as the export file.

    Args:
        file: Path to the export file

    Returns:
        Dictionary containing settings, or empty dict if file doesn't exist
    """
    full_path = os.path.abspath(file)
    dir_name = os.path.dirname(full_path)
    settings_path = os.path.join(dir_name, "settings.json")
    if not os.path.exists(settings_path):
        return {}
    with open(settings_path, "r") as f:
        return json.loads(f.read())
