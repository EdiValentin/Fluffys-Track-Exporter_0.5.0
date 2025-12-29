"""
Export utility functions for Smart Export workflow.

Provides modifier refresh and realize/mesh operations for non-destructive export.
Adapted from Link Addon.py.
"""

import bpy
import os
import re
from bpy.types import Operator
from bpy.props import StringProperty
from .utils import is_object_excluded_by_collection
from ...utils.constants import SURFACE_REGEX
from ...utils.helpers import is_hidden_name


# ============================================================================
# MAKE LOCAL UTILITIES
# ============================================================================

def make_all_objects_local(context):
    """
    Make all linked objects in the scene local.

    This is necessary for the export workflow to properly process linked objects
    from external .blend files or library overrides.

    Args:
        context: Blender context

    Returns:
        tuple: (localized_count: int, error_count: int)
    """
    print("\n" + "="*60)
    print("MAKING ALL LINKED OBJECTS LOCAL")
    print("="*60 + "\n")

    localized_count = 0
    error_count = 0

    # Collect all linked objects
    linked_objects = []
    for obj in bpy.data.objects:
        # Skip objects with "__" prefix
        if is_hidden_name(obj.name):
            continue

        # Skip objects in disabled/excluded collections
        if is_object_excluded_by_collection(obj, context):
            continue

        # Check if object is linked
        if obj.library is not None:
            linked_objects.append(obj)
            print(f"  Found linked object: {obj.name} (from {obj.library.filepath})")

    if not linked_objects:
        print("No linked objects found - nothing to localize\n")
        return 0, 0

    print(f"\nFound {len(linked_objects)} linked objects to localize\n")

    # Deselect all first
    try:
        bpy.ops.object.select_all(action='DESELECT')
    except Exception:
        pass  # Selection may fail on certain object types

    # Make each linked object local
    for obj in linked_objects:
        try:
            # Select the object
            obj.select_set(True)
            context.view_layer.objects.active = obj

            # Make it local (with all data)
            bpy.ops.object.make_local(type='ALL')

            print(f"  ✓ Localized: {obj.name}")
            localized_count += 1

            # Deselect for next iteration
            obj.select_set(False)

        except Exception as e:
            print(f"  ✗ Failed to localize {obj.name}: {str(e)}")
            error_count += 1
            # Try to deselect even if it failed
            try:
                obj.select_set(False)
            except Exception:
                pass  # Deselection may fail on certain object types

    # Force view layer update
    context.view_layer.update()

    print("\n" + "="*60)
    print(f"MAKE LOCAL COMPLETE")
    print(f"  Localized: {localized_count}")
    print(f"  Errors:    {error_count}")
    print("="*60 + "\n")

    return localized_count, error_count


def make_everything_local(context):
    """
    Make ALL linked data blocks local (objects, materials, meshes, images, node groups, etc.).

    This comprehensive function ensures that EVERYTHING in the blend file is local,
    not just objects. This is necessary because after realize/mesh operations,
    local objects can still reference linked materials, textures, or other data.

    Args:
        context: Blender context

    Returns:
        dict: Statistics about what was localized
    """
    print("\n" + "="*60)
    print("MAKING EVERYTHING LOCAL (COMPREHENSIVE)")
    print("="*60 + "\n")

    stats = {
        'objects': 0,
        'materials': 0,
        'meshes': 0,
        'images': 0,
        'textures': 0,
        'node_groups': 0,
        'other': 0,
        'errors': 0
    }

    # Helper function to make a data block local
    def make_datablock_local(datablock, datablock_type):
        try:
            if hasattr(datablock, 'library') and datablock.library is not None:
                # Skip hidden/internal data
                if is_hidden_name(datablock.name):
                    return False

                print(f"  Localizing {datablock_type}: {datablock.name} (from {datablock.library.filepath})")

                # Use make_local() method if available
                if hasattr(datablock, 'make_local'):
                    datablock.make_local()
                    return True
                else:
                    print(f"    Warning: {datablock_type} doesn't have make_local() method")
                    return False
            return False
        except Exception as e:
            print(f"    ✗ Error localizing {datablock_type} '{datablock.name}': {str(e)}")
            stats['errors'] += 1
            return False

    # 1. Make all linked OBJECTS local first (this often cascades to data)
    print("1. Localizing Objects...")
    for obj in list(bpy.data.objects):
        if make_datablock_local(obj, "Object"):
            stats['objects'] += 1

    # 2. Make all linked MATERIALS local
    print("\n2. Localizing Materials...")
    for material in list(bpy.data.materials):
        if make_datablock_local(material, "Material"):
            stats['materials'] += 1

    # 3. Make all linked MESHES local
    print("\n3. Localizing Meshes...")
    for mesh in list(bpy.data.meshes):
        if make_datablock_local(mesh, "Mesh"):
            stats['meshes'] += 1

    # 4. Make all linked IMAGES local
    print("\n4. Localizing Images...")
    for image in list(bpy.data.images):
        if make_datablock_local(image, "Image"):
            stats['images'] += 1

    # 5. Make all linked TEXTURES local
    print("\n5. Localizing Textures...")
    for texture in list(bpy.data.textures):
        if make_datablock_local(texture, "Texture"):
            stats['textures'] += 1

    # 6. Make all linked NODE GROUPS local (shader nodes, geometry nodes)
    print("\n6. Localizing Node Groups...")
    for node_group in list(bpy.data.node_groups):
        if make_datablock_local(node_group, "NodeGroup"):
            stats['node_groups'] += 1

    # 7. Make other potentially linked data local
    print("\n7. Localizing Other Data Blocks...")

    # Curves
    for curve in list(bpy.data.curves):
        if make_datablock_local(curve, "Curve"):
            stats['other'] += 1

    # Collections
    for collection in list(bpy.data.collections):
        if make_datablock_local(collection, "Collection"):
            stats['other'] += 1

    # Lights
    for light in list(bpy.data.lights):
        if make_datablock_local(light, "Light"):
            stats['other'] += 1

    # Cameras
    for camera in list(bpy.data.cameras):
        if make_datablock_local(camera, "Camera"):
            stats['other'] += 1

    # Force view layer update
    context.view_layer.update()

    # Print summary
    total_localized = sum([stats[key] for key in stats.keys() if key != 'errors'])

    print("\n" + "="*60)
    print(f"MAKE EVERYTHING LOCAL COMPLETE")
    print(f"  Objects:     {stats['objects']}")
    print(f"  Materials:   {stats['materials']}")
    print(f"  Meshes:      {stats['meshes']}")
    print(f"  Images:      {stats['images']}")
    print(f"  Textures:    {stats['textures']}")
    print(f"  Node Groups: {stats['node_groups']}")
    print(f"  Other:       {stats['other']}")
    print(f"  ---")
    print(f"  Total:       {total_localized}")
    print(f"  Errors:      {stats['errors']}")
    print("="*60 + "\n")

    return stats


# ============================================================================
# MODIFIER REFRESH UTILITIES
# ============================================================================

class KN5_OT_refresh_geonode_pointer(Operator):
    """Internal operator to refresh a geometry node pointer input"""
    bl_idname = "kn5.refresh_geonode_pointer"
    bl_label = "Refresh GeoNode Pointer"
    bl_options = {'INTERNAL'}

    object_name: StringProperty()
    modifier_name: StringProperty()
    socket_id: StringProperty()
    pointer_name: StringProperty()
    pointer_type: StringProperty()  # 'OBJECT' or 'COLLECTION'

    def execute(self, context):
        # Get the object
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}

        # Get the modifier
        mod = obj.modifiers.get(self.modifier_name)
        if not mod or mod.type != 'NODES':
            return {'CANCELLED'}

        # Get the pointer
        if self.pointer_type == 'OBJECT':
            pointer = bpy.data.objects.get(self.pointer_name)
        elif self.pointer_type == 'COLLECTION':
            pointer = bpy.data.collections.get(self.pointer_name)
        else:
            return {'CANCELLED'}

        if not pointer:
            return {'CANCELLED'}

        try:
            # Set to None first
            mod[self.socket_id] = None
            # Set to the actual value
            mod[self.socket_id] = pointer
            # This operator execution should trigger proper updates
        except Exception as e:
            print(f"Error in operator: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


def get_layer_collection_recursive(layer_collection, collection_name):
    """Recursively find a layer collection by name"""
    if layer_collection.collection.name == collection_name:
        return layer_collection
    for child in layer_collection.children:
        result = get_layer_collection_recursive(child, collection_name)
        if result:
            return result
    return None


def refresh_nodegroups_operator(obj, context=None):
    """
    Refresh collection and object pointer inputs in geometry nodes modifiers.
    Uses an operator to properly trigger update callbacks.

    Args:
        obj: Blender object to process
        context: Blender context (required for operator execution)
    """
    if not obj or not hasattr(obj, 'modifiers'):
        return

    if not context:
        print(f"WARNING: No context provided for {obj.name}, skipping refresh")
        return

    print(f"  Refreshing modifiers for: {obj.name}")

    for mod in obj.modifiers:
        if mod.type != 'NODES' or not mod.node_group:
            continue

        ng = mod.node_group

        # Skip if nodegroup is invalid
        if not ng or not hasattr(ng, 'interface'):
            continue

        # Find all pointer inputs that need refreshing
        pointers_to_refresh = []
        try:
            for input_item in ng.interface.items_tree:
                if input_item.item_type == 'SOCKET' and input_item.in_out == 'INPUT':
                    identifier = input_item.identifier

                    try:
                        current_value = mod[identifier]

                        # Only refresh object/collection pointers
                        if isinstance(current_value, (bpy.types.Object, bpy.types.Collection)):
                            pointer_type = 'OBJECT' if isinstance(current_value, bpy.types.Object) else 'COLLECTION'
                            pointers_to_refresh.append({
                                'socket_id': identifier,
                                'pointer_name': current_value.name,
                                'pointer_type': pointer_type
                            })

                    except Exception as e:
                        pass
        except Exception as e:
            pass

        if not pointers_to_refresh:
            continue

        # Refresh all found pointers using the operator
        for pointer_info in pointers_to_refresh:
            try:
                bpy.ops.kn5.refresh_geonode_pointer(
                    object_name=obj.name,
                    modifier_name=mod.name,
                    socket_id=pointer_info['socket_id'],
                    pointer_name=pointer_info['pointer_name'],
                    pointer_type=pointer_info['pointer_type']
                )
            except Exception as e:
                print(f"    Warning: Failed to refresh pointer {pointer_info['socket_id']}: {e}")


def refresh_all_modifiers(context):
    """
    Refresh all geometry node modifiers in the scene.

    Args:
        context: Blender context
    """
    print("\n" + "="*60)
    print("REFRESHING ALL MODIFIERS")
    print("="*60)

    for obj in bpy.data.objects:
        # Skip objects with "__" prefix
        if is_hidden_name(obj.name):
            continue

        # Skip objects in disabled/excluded collections
        if is_object_excluded_by_collection(obj, context):
            continue

        if obj.type == 'MESH' and obj.modifiers:
            refresh_nodegroups_operator(obj, context)

    # Force view layer update
    context.view_layer.update()
    print("Modifier refresh complete\n")


# ============================================================================
# REALIZE & MESH UTILITIES
# ============================================================================

def realize_and_mesh_single(obj, context):
    """
    Enable realize instances on all modifiers and convert single object to mesh.

    Args:
        obj: Blender object to process
        context: Blender context

    Returns:
        tuple: (success: bool, message: str)
    """
    if not obj:
        return False, "No object provided"

    if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
        return False, f"Object type {obj.type} cannot be converted to mesh"

    print(f"  Processing: {obj.name} (type: {obj.type})")

    # Track how many properties we found and enabled
    realize_count = 0

    # Look through all modifiers for realize instance properties
    for mod in obj.modifiers:
        # For geometry nodes modifiers, check the node group inputs
        if mod.type == 'NODES' and mod.node_group:
            ng = mod.node_group

            if ng and hasattr(ng, 'interface'):
                try:
                    # Search for realize-related properties
                    for input_item in ng.interface.items_tree:
                        if input_item.item_type == 'SOCKET' and input_item.in_out == 'INPUT':
                            identifier = input_item.identifier
                            display_name = input_item.name

                            try:
                                current_value = mod[identifier]
                            except Exception:
                                continue  # Skip invalid geometry node configurations

                            # Check BOTH the display name and identifier
                            name_lower = display_name.lower()
                            identifier_lower = identifier.lower()

                            # Look for "realize" OR "instance" in the display name OR identifier
                            if 'realize' in name_lower or 'instance' in name_lower or 'realize' in identifier_lower or 'instance' in identifier_lower:
                                # Check if it's a boolean property
                                if isinstance(current_value, bool):
                                    if not current_value:
                                        try:
                                            mod[identifier] = True
                                            realize_count += 1
                                            print(f"    Enabled: {display_name}")
                                        except Exception as e:
                                            print(f"    Warning: Failed to enable {display_name}: {e}")

                except Exception as e:
                    print(f"    Warning: Error reading modifier interface: {e}")

        # Also check standard modifier properties (for non-GeoNode modifiers)
        if mod.type != 'NODES':
            for prop_name in dir(mod):
                if prop_name.startswith('_'):
                    continue
                name_lower = prop_name.lower()
                if 'realize' in name_lower or 'instance' in name_lower:
                    try:
                        current_value = getattr(mod, prop_name)
                        if isinstance(current_value, bool):
                            if not current_value:
                                setattr(mod, prop_name, True)
                                realize_count += 1
                                print(f"    Enabled: {prop_name}")
                    except Exception:
                        pass  # Modifier property may not exist

    # Force view layer update
    context.view_layer.update()

    if realize_count > 0:
        print(f"    Enabled {realize_count} realize properties")

    # Convert to mesh (applies all modifiers)
    try:
        # Make sure the object is selected and active
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Convert to mesh
        bpy.ops.object.convert(target='MESH')

        print(f"    ✓ Converted to mesh")

        return True, "Success"

    except Exception as e:
        error_msg = f"Failed to convert to mesh: {str(e)}"
        print(f"    ✗ {error_msg}")
        return False, error_msg


def realize_and_mesh_all(context):
    """
    Process all eligible objects in the scene for realize and mesh conversion.

    Eligible objects:
    - MESH objects with modifiers
    - CURVE, SURFACE, FONT, META objects

    Excluded objects:
    - Objects with "__" prefix
    - MESH objects without modifiers

    Args:
        context: Blender context

    Returns:
        tuple: (success_count: int, skip_count: int, error_count: int)
    """
    print("\n" + "="*60)
    print("REALIZE & MESH ALL OBJECTS")
    print("="*60 + "\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    # Collect eligible objects first (to avoid modifying collection during iteration)
    eligible_objects = []

    for obj in list(bpy.data.objects):
        # Skip objects with "__" prefix
        if is_hidden_name(obj.name):
            print(f"Skipping (__ prefix): {obj.name}")
            skip_count += 1
            continue

        # Skip objects in disabled/excluded collections
        if is_object_excluded_by_collection(obj, context):
            print(f"Skipping (collection disabled/excluded): {obj.name}")
            skip_count += 1
            continue

        # Skip objects not in view layer (greyed out in outliner)
        if obj.name not in context.view_layer.objects:
            print(f"Skipping (not in view layer): {obj.name}")
            skip_count += 1
            continue

        # Process CURVE, SURFACE, FONT, META
        if obj.type in {'CURVE', 'SURFACE', 'FONT', 'META'}:
            eligible_objects.append(obj)
        # Process MESH only if it has modifiers
        elif obj.type == 'MESH' and len(obj.modifiers) > 0:
            eligible_objects.append(obj)
        else:
            # Skip MESH without modifiers and other types
            if obj.type == 'MESH':
                print(f"Skipping (mesh, no modifiers): {obj.name}")
            else:
                print(f"Skipping (type {obj.type}): {obj.name}")
            skip_count += 1

    print(f"\nFound {len(eligible_objects)} eligible objects to process\n")

    # Sort objects: process non-road objects first, road objects last
    non_road_objects = []
    road_objects = []

    for obj in eligible_objects:
        # Check if any modifier has "_ROAD" in its name
        has_road_modifier = False
        if hasattr(obj, 'modifiers'):
            for mod in obj.modifiers:
                if "_ROAD" in mod.name:
                    has_road_modifier = True
                    break

        if has_road_modifier:
            road_objects.append(obj)
        else:
            non_road_objects.append(obj)

    print(f"Processing order:")
    print(f"  Non-road objects: {len(non_road_objects)}")
    print(f"  Road objects: {len(road_objects)}")
    print()

    # Process non-road objects first, then road objects
    sorted_objects = non_road_objects + road_objects

    # Process each eligible object
    for obj in sorted_objects:
        try:
            success, message = realize_and_mesh_single(obj, context)
            if success:
                success_count += 1
            else:
                print(f"  Error: {message}")
                error_count += 1
        except Exception as e:
            print(f"  ✗ Unexpected error processing {obj.name}: {str(e)}")
            error_count += 1

    print("\n" + "="*60)
    print(f"REALIZE & MESH COMPLETE")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors:  {error_count}")
    print("="*60 + "\n")

    return success_count, skip_count, error_count


# ============================================================================
# MATERIAL CLEANUP UTILITIES
# ============================================================================

def remove_empty_material_slots(context):
    """
    Remove empty material slots from all mesh objects.

    This ensures all objects have valid material assignments before export.

    Args:
        context: Blender context

    Returns:
        tuple: (empty_slots_removed: int, objects_cleaned: int, skipped_objects: list)
    """
    print("\n" + "="*60)
    print("REMOVING EMPTY MATERIAL SLOTS")
    print("="*60)

    empty_slots_removed = 0
    objects_cleaned = 0
    skipped_objects = []

    for obj in list(bpy.data.objects):
        # Only process mesh objects
        if obj.type != 'MESH':
            continue

        # Skip objects with "__" prefix
        if is_hidden_name(obj.name):
            continue

        # Skip objects in disabled/excluded collections
        if is_object_excluded_by_collection(obj, context):
            continue

        # Skip objects without material slots
        if not obj.material_slots:
            continue

        # Skip objects not in view layer (greyed out in outliner)
        if obj.name not in context.view_layer.objects:
            # Only count if it actually has empty slots
            if any(slot.material is None for slot in obj.material_slots):
                skipped_objects.append(obj.name)
            continue

        # Count empty slots before cleaning
        empty_count_before = sum(1 for slot in obj.material_slots if slot.material is None)

        if empty_count_before > 0:
            print(f"  Cleaning: {obj.name} ({empty_count_before} empty slots)")

            # Remove empty slots by iterating backwards (so indices don't shift)
            # We need to set the object as active to use material_slot_remove
            original_active = context.view_layer.objects.active
            context.view_layer.objects.active = obj

            # Iterate backwards through slots
            for i in range(len(obj.material_slots) - 1, -1, -1):
                if obj.material_slots[i].material is None:
                    obj.active_material_index = i
                    bpy.ops.object.material_slot_remove()
                    empty_slots_removed += 1

            # Restore original active object
            context.view_layer.objects.active = original_active
            objects_cleaned += 1
            print(f"    ✓ Removed {empty_count_before} empty slot(s)")

    # Force view layer update
    context.view_layer.update()

    print("\n" + "="*60)
    print(f"EMPTY MATERIAL SLOTS REMOVED")
    print(f"  Slots removed: {empty_slots_removed}")
    print(f"  Objects cleaned: {objects_cleaned}")
    print(f"  Objects skipped: {len(skipped_objects)}")
    print("="*60 + "\n")

    return empty_slots_removed, objects_cleaned, skipped_objects


def validate_all_materials(context, run_csp_detection=False, fix_grass_specular=False, verbose=True):
    """
    Validate all materials, auto-detect shaders, and assign texture slots.

    This is the unified material validation function used by both the UI operator
    (AC_ValidateAll) and the export workflow. It uses reverse tracing from
    Principled BSDF sockets to find connected textures, with naming pattern
    matching as a fallback for unconnected textures.

    Args:
        context: Blender context
        run_csp_detection: If True, also runs GrassFX and RainFX auto-detection
        fix_grass_specular: If True, sets ksSpecular=0.0 for materials on GRASS surfaces
        verbose: If True, prints detailed progress to console

    Returns:
        dict: Statistics about validation (materials_validated, materials_fixed,
              textures_assigned, materials_upgraded, properties_added)
    """
    if verbose:
        print("\n" + "="*60)
        print("VALIDATING ALL MATERIALS")
        print("="*60)

    # Import required modules
    try:
        from ..menus.ops.material_setup import apply_shader_defaults
        from .shader_defaults import get_shader_defaults, get_texture_slot_from_name
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        return {
            "materials_validated": 0,
            "materials_fixed": 0,
            "textures_assigned": 0,
            "materials_upgraded": 0,
            "properties_added": 0
        }

    # Track validation stats
    stats = {
        "materials_validated": 0,
        "materials_fixed": 0,
        "textures_assigned": 0,
        "materials_upgraded": 0,
        "properties_added": 0,
        "grass_specular_fixed": 0
    }

    def trace_to_image_textures(socket, visited=None):
        """
        Recursively trace backwards from a socket to find all connected Image Texture nodes.

        This handles complex node chains like Image Texture → Color Ramp → Mix → BSDF
        by recursively following all input connections.

        Args:
            socket: Input socket to trace from
            visited: Set of already visited nodes (prevents infinite loops)

        Returns:
            list: Image Texture nodes found in the connection chain
        """
        if visited is None:
            visited = set()

        image_nodes = []

        if not socket.is_linked:
            return image_nodes

        for link in socket.links:
            from_node = link.from_node

            # Avoid infinite loops in node cycles
            if from_node in visited:
                continue
            visited.add(from_node)

            # If we found an Image Texture node, add it
            if from_node.type == 'TEX_IMAGE' and from_node.image:
                # Skip hidden textures
                if not is_hidden_name(from_node.image.name):
                    image_nodes.append(from_node)

            # Continue tracing through this node's inputs
            for input_socket in from_node.inputs:
                image_nodes.extend(trace_to_image_textures(input_socket, visited))

        return image_nodes

    # =========================================================================
    # GRASS SURFACE DETECTION (only when fix_grass_specular=True)
    # =========================================================================
    # Build a set of materials used by GRASS surface objects.
    # These materials should have ksSpecular set to 0.0 (grass shouldn't be shiny)
    # =========================================================================
    grass_materials = set()
    if fix_grass_specular:
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            if is_hidden_name(obj.name):
                continue
            # Check if object name matches GRASS surface pattern
            match = re.match(SURFACE_REGEX, obj.name)
            if match and match.group(2) == 'GRASS':
                # Collect all materials used by this grass object
                for slot in obj.material_slots:
                    if slot.material:
                        grass_materials.add(slot.material.name)

        if grass_materials and verbose:
            print(f"  Detected {len(grass_materials)} grass surface material(s)")

    for material in bpy.data.materials:
        # Skip materials without node trees or hidden materials
        if not material.node_tree or is_hidden_name(material.name):
            continue

        # Skip unused materials
        if material.users == 0:
            continue

        stats["materials_validated"] += 1
        ac_mat = material.AC_Material

        # Find the Principled BSDF node
        principled_node = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break

        # Detect what's connected to determine correct shader
        has_base_color = False
        has_alpha = False
        has_normal = False

        if principled_node:
            # Check Base Color connection
            if principled_node.inputs['Base Color'].is_linked:
                has_base_color = True

            # Check Alpha connection
            if principled_node.inputs['Alpha'].is_linked:
                has_alpha = True

            # Check Normal connection (via Normal Map node)
            if principled_node.inputs['Normal'].is_linked:
                # Trace back to see if there's a Normal Map node
                for link in principled_node.inputs['Normal'].links:
                    if link.from_node.type == 'NORMAL_MAP':
                        has_normal = True
                        break

        # Check if current shader should be protected from auto-upgrade (e.g., ksTree)
        current_shader = ac_mat.shader_name if ac_mat.shader_name else "ksPerPixel"
        current_defaults = get_shader_defaults(current_shader)
        is_protected_shader = current_defaults.get("is_tree_shader", False)

        # Determine appropriate shader based on connections (skip for protected shaders)
        determined_shader = None
        if not is_protected_shader:
            if has_base_color and has_alpha and has_normal:
                determined_shader = "ksPerPixelAT_NM"
            elif has_base_color and has_alpha:
                determined_shader = "ksPerPixelAT"
            elif has_base_color and has_normal:
                determined_shader = "ksPerPixelNM_UVMult"
            elif has_base_color:
                determined_shader = "ksPerPixel"

        # If we determined a shader and it's different from current, update it
        if determined_shader and determined_shader != current_shader:
            if verbose:
                print(f"  Upgrading: {material.name} ({current_shader} → {determined_shader})")
            ac_mat.shader_name = determined_shader
            apply_shader_defaults(material, determined_shader)

            # Set alpha_tested property for AT shaders
            if "AT" in determined_shader:
                ac_mat.alpha_tested = True
                ac_mat.alpha_blend_mode = "0"  # Opaque for alpha test
            else:
                ac_mat.alpha_tested = False

            stats["materials_upgraded"] += 1
            shader_name = determined_shader
        else:
            shader_name = current_shader

        # Ensure shader properties are populated
        existing_props = {prop.name for prop in ac_mat.shader_properties}

        # Get expected properties for this shader
        try:
            defaults = get_shader_defaults(shader_name)
            expected_props = {prop["name"] for prop in defaults.get("properties", [])}

            # Check if properties are missing or incomplete
            missing_props = expected_props - existing_props

            if missing_props or not existing_props:
                # Apply defaults
                apply_shader_defaults(material, shader_name)
                stats["materials_fixed"] += 1
                stats["properties_added"] += len(missing_props)

        except KeyError:
            # Unknown shader - skip
            pass

        # =====================================================================
        # GRASS SURFACE SPECULAR FIX (only when fix_grass_specular=True)
        # =====================================================================
        # Grass surfaces should have specular set to 0.0 (grass shouldn't be shiny)
        # =====================================================================
        if fix_grass_specular and material.name in grass_materials:
            for prop in ac_mat.shader_properties:
                if prop.name == "ksSpecular":
                    if prop.valueA != 0.0:
                        if verbose:
                            print(f"  Setting ksSpecular=0.0 for grass material: {material.name}")
                        prop.valueA = 0.0
                        stats["grass_specular_fixed"] += 1
                    break

        # =====================================================================
        # AUTO-ASSIGN TEXTURE SLOTS
        # =====================================================================
        # Use reverse tracing: start from Principled BSDF sockets and trace
        # backwards to find connected Image Texture nodes. This handles complex
        # node chains (Color Ramp, Mix, etc.) that forward tracing would miss.
        #
        # For unconnected textures, fall back to naming pattern matching.
        # =====================================================================

        # Track which image nodes were assigned via connection tracing
        assigned_image_nodes = set()

        # Process textures connected to the Principled BSDF
        if principled_node:
            # Trace Base Color socket for txDiffuse
            if 'Base Color' in principled_node.inputs:
                for img_node in trace_to_image_textures(principled_node.inputs['Base Color']):
                    assigned_image_nodes.add(img_node)
                    ac_texture = img_node.AC_Texture
                    if ac_texture.shader_input_name != "txDiffuse":
                        ac_texture.shader_input_name = "txDiffuse"
                        stats["textures_assigned"] += 1

            # Trace Alpha socket for txDiffuse (alpha channel)
            if 'Alpha' in principled_node.inputs:
                for img_node in trace_to_image_textures(principled_node.inputs['Alpha']):
                    assigned_image_nodes.add(img_node)
                    ac_texture = img_node.AC_Texture
                    # Only assign if not already assigned to Normal (which takes priority)
                    if ac_texture.shader_input_name not in ("txNormal", "txDiffuse"):
                        ac_texture.shader_input_name = "txDiffuse"
                        stats["textures_assigned"] += 1

            # Trace Emission socket for txEmissive
            if 'Emission Color' in principled_node.inputs:
                for img_node in trace_to_image_textures(principled_node.inputs['Emission Color']):
                    assigned_image_nodes.add(img_node)
                    ac_texture = img_node.AC_Texture
                    if ac_texture.shader_input_name != "txEmissive":
                        ac_texture.shader_input_name = "txEmissive"
                        stats["textures_assigned"] += 1
            elif 'Emission' in principled_node.inputs:
                for img_node in trace_to_image_textures(principled_node.inputs['Emission']):
                    assigned_image_nodes.add(img_node)
                    ac_texture = img_node.AC_Texture
                    if ac_texture.shader_input_name != "txEmissive":
                        ac_texture.shader_input_name = "txEmissive"
                        stats["textures_assigned"] += 1

            # Trace Roughness/Specular/Metallic sockets for txMaps
            for socket_name in ['Roughness', 'Specular', 'Metallic']:
                if socket_name in principled_node.inputs:
                    for img_node in trace_to_image_textures(principled_node.inputs[socket_name]):
                        assigned_image_nodes.add(img_node)
                        ac_texture = img_node.AC_Texture
                        # Don't override txDiffuse or txNormal
                        if ac_texture.shader_input_name not in ("txDiffuse", "txNormal"):
                            if ac_texture.shader_input_name != "txMaps":
                                ac_texture.shader_input_name = "txMaps"
                                stats["textures_assigned"] += 1

            # Trace Normal socket for txNormal
            # Normal input usually connects to a Normal Map node, so we need to trace through that
            if 'Normal' in principled_node.inputs:
                normal_socket = principled_node.inputs['Normal']

                # Look for Normal Map nodes connected to the Normal socket
                if normal_socket.is_linked:
                    for link in normal_socket.links:
                        normal_map_node = link.from_node

                        # If it's a Normal Map node, trace its Color input
                        if normal_map_node.type == 'NORMAL_MAP':
                            if 'Color' in normal_map_node.inputs:
                                for img_node in trace_to_image_textures(normal_map_node.inputs['Color']):
                                    assigned_image_nodes.add(img_node)
                                    ac_texture = img_node.AC_Texture
                                    if ac_texture.shader_input_name != "txNormal":
                                        ac_texture.shader_input_name = "txNormal"
                                        stats["textures_assigned"] += 1

                                        # Set correct color space for normal maps
                                        if img_node.image.colorspace_settings.name != 'Non-Color':
                                            img_node.image.colorspace_settings.name = 'Non-Color'

                        # Also check if an image is connected directly (unusual but possible)
                        elif normal_map_node.type == 'TEX_IMAGE' and normal_map_node.image:
                            if not is_hidden_name(normal_map_node.image.name):
                                assigned_image_nodes.add(normal_map_node)
                                ac_texture = normal_map_node.AC_Texture
                                if ac_texture.shader_input_name != "txNormal":
                                    ac_texture.shader_input_name = "txNormal"
                                    stats["textures_assigned"] += 1

                                    # Set correct color space for normal maps
                                    if normal_map_node.image.colorspace_settings.name != 'Non-Color':
                                        normal_map_node.image.colorspace_settings.name = 'Non-Color'

        # =====================================================================
        # FALLBACK: Naming pattern matching for unconnected textures
        # =====================================================================
        # For image nodes that weren't assigned via connection tracing,
        # try to determine their slot from the image name (e.g., "wall_normal.png")
        # =====================================================================
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                # Skip hidden textures
                if is_hidden_name(node.image.name):
                    continue

                # Skip already assigned nodes
                if node in assigned_image_nodes:
                    continue

                ac_texture = node.AC_Texture
                current_slot = ac_texture.shader_input_name

                # Try naming pattern matching
                new_slot = get_texture_slot_from_name(node.image.name)

                if new_slot:
                    # Set correct color space for normal maps
                    if new_slot == "txNormal":
                        if node.image.colorspace_settings.name != 'Non-Color':
                            node.image.colorspace_settings.name = 'Non-Color'

                    # Update texture slot if different
                    if new_slot != current_slot:
                        ac_texture.shader_input_name = new_slot
                        stats["textures_assigned"] += 1
                        if verbose:
                            print(f"  Pattern match: {node.image.name} → {new_slot}")

    # Force view layer update
    context.view_layer.update()

    # Run CSP feature auto-detection if requested
    if run_csp_detection:
        if verbose:
            print("\nAuto-detecting CSP features...")
        try:
            bpy.ops.ac.auto_detect_grassfx_materials()
            bpy.ops.ac.autodetect_rainfx_materials()
            if verbose:
                print("  ✓ GrassFX and RainFX materials updated")
        except Exception as e:
            print(f"  Warning: Error detecting CSP features: {e}")

    if verbose:
        print("\n" + "="*60)
        print(f"MATERIAL VALIDATION COMPLETE")
        print(f"  Materials validated: {stats['materials_validated']}")
        print(f"  Materials fixed: {stats['materials_fixed']}")
        print(f"  Textures assigned: {stats['textures_assigned']}")
        print(f"  Shaders upgraded: {stats['materials_upgraded']}")
        print(f"  Properties added: {stats['properties_added']}")
        print("="*60 + "\n")

    return stats


# ============================================================================
# FILE MANAGEMENT UTILITIES
# ============================================================================

def get_smart_exports_directory(blend_filepath):
    """
    Get the Smart Exports directory path for a given .blend file.

    Creates the directory if it doesn't exist.

    Args:
        blend_filepath: Path to the .blend file

    Returns:
        str: Path to the Smart Exports directory
    """
    blend_dir = os.path.dirname(blend_filepath)
    smart_exports_dir = os.path.join(blend_dir, "Smart Exports")

    # Create directory if it doesn't exist
    if not os.path.exists(smart_exports_dir):
        os.makedirs(smart_exports_dir)
        print(f"Created Smart Exports directory: {smart_exports_dir}")

    return smart_exports_dir


def get_versioned_filename(base_path, suffix, output_dir=None):
    """
    Generate a versioned filename that doesn't exist yet.

    Args:
        base_path: Path to the current .blend file (e.g., "/path/to/myfile.blend")
        suffix: Suffix to add (e.g., "Original" or "Export")
        output_dir: Optional output directory. If None, uses same directory as base_path.

    Returns:
        str: Versioned filepath (e.g., "/path/to/myfile_Original_001.blend")
    """
    # Split path and extension
    basename = os.path.basename(base_path)
    name, ext = os.path.splitext(basename)

    # Use output_dir if provided, otherwise use same directory as base_path
    directory = output_dir if output_dir else os.path.dirname(base_path)

    # Try without version number first
    new_path = os.path.join(directory, f"{name}_{suffix}{ext}")
    if not os.path.exists(new_path):
        return new_path

    # Generate versioned names
    version = 1
    while True:
        new_path = os.path.join(directory, f"{name}_{suffix}_{version:03d}{ext}")
        if not os.path.exists(new_path):
            return new_path
        version += 1

        # Safety check to prevent infinite loop
        if version > 999:
            raise RuntimeError("Too many versioned files (>999)")


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    KN5_OT_refresh_geonode_pointer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
