"""Operators for managing CSP Lights configuration."""

import bpy
import os
import math
from bpy.types import Operator
from bpy.props import IntProperty

from ....utils.helpers import parse_ini_file
from ....utils.constants import DEFAULT_LIGHT_TYPE


# ============================================================================
# SHARED HELPER FUNCTIONS
# ============================================================================

def initialize_new_light(light, light_type=None):
    """
    Initialize a new light with default settings.

    Shared helper to ensure consistent defaults across all light creation operators.

    Args:
        light: AC_Light PropertyGroup to initialize
        light_type: Optional light type override (defaults to DEFAULT_LIGHT_TYPE)
    """
    light.active = True
    light.light_type = light_type or DEFAULT_LIGHT_TYPE
    light.modify_shape = True
    light.modify_color = True


def sync_light_properties_from_blender(ac_light, light_obj):
    """
    Sync AC_Light properties from a Blender light object.

    Consolidates the duplicate _sync_light_properties methods from multiple operators.
    Handles position, direction, color, intensity, spot angle, range, and shadows.

    Args:
        ac_light: AC_Light PropertyGroup to update
        light_obj: Blender light object to sync from
    """
    if light_obj.type != 'LIGHT':
        return

    # IMPORTANT: Sync CSP settings FIRST, before setting any properties
    # that have update callbacks (spot_sharpness, cast_shadows, etc.)
    # Otherwise the callbacks will overwrite the object's AC_CSP values
    ac_light.sync_csp_from_object()

    light_data = light_obj.data

    # Sync position/direction from transform
    ac_light.sync_from_linked_object()

    # Color (Blender 0-1 to CSP 0-1, we store normalized)
    ac_light.color = (light_data.color[0], light_data.color[1], light_data.color[2], 1.0)

    # Intensity - convert Blender Watts to CSP intensity
    # Blender 10W ≈ CSP 0.001, 100W ≈ 0.01, 1000W ≈ 0.1
    ac_light.intensity = light_data.energy / 10000.0

    # Spot angle (Blender radians to CSP degrees)
    if light_data.type == 'SPOT':
        ac_light.spot = int(math.degrees(light_data.spot_size))
        # Blender spot_blend: 0=sharp, 1=soft
        # CSP spot_sharpness: 0=sharp center, 1=uniform
        ac_light.spot_sharpness = light_data.spot_blend

    # Range
    if hasattr(light_data, 'use_custom_distance') and light_data.use_custom_distance:
        ac_light.range = light_data.cutoff_distance

    # Shadows
    ac_light.cast_shadows = light_data.use_shadow
    if light_data.use_shadow:
        ac_light.shadows_static = True

    # Specular
    if hasattr(light_data, 'specular_factor'):
        ac_light.specular_multiplier = light_data.specular_factor * 4.0


def write_ini_with_include_first(filepath, sections):
    """
    Write sections dict to INI file, with INCLUDE section first.

    CSP requires INCLUDE section at the top for conditions.ini.
    Also formats values appropriately (tuples, bools, floats).

    Args:
        filepath: Output path for INI file
        sections: Dict of section_name -> {key: value} mappings
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        # Write INCLUDE section first if it exists (required for conditions)
        if "INCLUDE" in sections:
            f.write("[INCLUDE]\n")
            for key, value in sections["INCLUDE"].items():
                f.write(f"{key} = {value}\n")
            f.write("\n")

        # Write remaining sections
        for section_name, section_data in sections.items():
            if section_name == "INCLUDE":
                continue  # Already written
            f.write(f"[{section_name}]\n")
            for key, value in section_data.items():
                # Format value based on type
                if isinstance(value, tuple):
                    value = ', '.join(str(v) for v in value)
                elif isinstance(value, bool):
                    value = 1 if value else 0
                elif isinstance(value, float):
                    # Round to reasonable precision
                    value = round(value, 4)
                f.write(f"{key} = {value}\n")
            f.write("\n")


def scan_and_sync_lights(context, lighting):
    """
    Scan visible lights and sync with CSP light list.

    Returns tuple of (added_count, removed_count).
    Consolidates duplicate scanning logic from AC_ScanLights and AC_ExportAndUpdateLights.
    """
    from ....utils.helpers import get_visible_lights

    visible_lights = get_visible_lights(context)

    # Build set of currently linked objects
    linked_objects = {light.linked_object for light in lighting.lights if light.linked_object}

    added_count = 0
    removed_count = 0

    # Add new lights not yet in the list
    for obj in visible_lights:
        if obj in linked_objects:
            continue
        ac_light = lighting.lights.add()
        ac_light.linked_object = obj
        ac_light.linked_object_name = obj.name  # Track name to detect deleted objects
        ac_light.use_object_transform = True
        ac_light.description = obj.name
        initialize_new_light(ac_light)
        sync_light_properties_from_blender(ac_light, obj)
        added_count += 1

    # Remove lights whose linked objects no longer exist or were deleted
    scene_objects = set(context.scene.objects)
    scene_object_names = {obj.name for obj in context.scene.objects if obj.type == 'LIGHT'}
    indices_to_remove = []

    for i, light in enumerate(lighting.lights):
        if light.linked_object is not None:
            # Has a linked object reference - check if it's still in the scene
            if light.linked_object not in scene_objects:
                indices_to_remove.append(i)
        else:
            # linked_object is None (object was deleted or never linked)
            # Use linked_object_name or description to identify what it was linked to
            expected_name = light.linked_object_name or light.description
            if expected_name and expected_name in scene_object_names:
                # Object exists - this shouldn't happen, try to re-link
                pass
            elif expected_name:
                # Expected object doesn't exist in scene - was deleted, remove
                indices_to_remove.append(i)
            # If no expected_name, it's manually added - keep it

    # Remove in reverse order to maintain valid indices
    for i in reversed(indices_to_remove):
        lighting.lights.remove(i)
        removed_count += 1

    return added_count, removed_count


# ============================================================================
# LIGHT MANAGEMENT OPERATORS
# ============================================================================


class AC_AddLight(Operator):
    """Add a new light to the CSP lights list"""

    bl_idname = "ac.add_light"
    bl_label = "Add Light"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Add new light
        light = lighting.lights.add()
        light.description = f"Light {len(lighting.lights)}"
        initialize_new_light(light)

        # Set active index to new light
        lighting.active_light_index = len(lighting.lights) - 1

        self.report({'INFO'}, f"Added new light: {light.description}")
        return {'FINISHED'}


class AC_AddLightFromSelection(Operator):
    """Create a CSP light from selected Empty object(s)"""

    bl_idname = "ac.add_light_from_selection"
    bl_label = "Add Light from Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Check if there are selected objects that are empties
        return any(obj.type == 'EMPTY' for obj in context.selected_objects)

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        added_count = 0

        for obj in context.selected_objects:
            if obj.type != 'EMPTY':
                continue

            # Check if this empty is already linked to a light
            already_linked = False
            for existing_light in lighting.lights:
                if existing_light.linked_object == obj:
                    already_linked = True
                    break

            if already_linked:
                self.report({'WARNING'}, f"'{obj.name}' is already linked to a light")
                continue

            # Create new light
            light = lighting.lights.add()
            light.linked_object = obj
            light.linked_object_name = obj.name
            light.use_object_transform = True
            light.description = obj.name
            initialize_new_light(light)

            # Sync initial position/direction from object
            light.sync_from_linked_object()

            # Sync CSP-specific settings from object (for duplicated empties)
            light.sync_csp_from_object()

            added_count += 1

        if added_count > 0:
            lighting.active_light_index = len(lighting.lights) - 1
            self.report({'INFO'}, f"Added {added_count} light(s) from selection")
        else:
            self.report({'WARNING'}, "No valid Empty objects to add")
            return {'CANCELLED'}

        return {'FINISHED'}


class AC_AddLightAtCursor(Operator):
    """Create an Empty at 3D cursor and add it as a CSP light"""

    bl_idname = "ac.add_light_at_cursor"
    bl_label = "Add Light at Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Create empty at cursor
        cursor_loc = context.scene.cursor.location
        bpy.ops.object.empty_add(type='SINGLE_ARROW', location=cursor_loc)
        empty = context.active_object

        # Name it with light prefix
        light_num = len(lighting.lights) + 1
        empty.name = f"AC_Light_{light_num:02d}"

        # Point downward by default (rotate -90 on X)
        empty.rotation_euler = (1.5708, 0, 0)  # 90 degrees in radians

        # Create light entry
        light = lighting.lights.add()
        light.linked_object = empty
        light.linked_object_name = empty.name
        light.use_object_transform = True
        light.description = empty.name
        initialize_new_light(light)

        # Sync position/direction
        light.sync_from_linked_object()

        lighting.active_light_index = len(lighting.lights) - 1

        self.report({'INFO'}, f"Created light '{empty.name}' at cursor")
        return {'FINISHED'}


class AC_RemoveLight(Operator):
    """Remove the selected light from the list"""

    bl_idname = "ac.remove_light"
    bl_label = "Remove Light"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return len(settings.lighting.lights) > 0

    def execute(self, context):
        from ....utils.helpers import is_valid_index, adjust_active_index
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        idx = self.index if self.index >= 0 else lighting.active_light_index

        if is_valid_index(idx, len(lighting.lights)):
            light_name = lighting.lights[idx].description
            lighting.lights.remove(idx)

            # Adjust active index
            lighting.active_light_index = adjust_active_index(lighting.active_light_index, len(lighting.lights))

            self.report({'INFO'}, f"Removed light: {light_name}")
        else:
            self.report({'WARNING'}, "No light selected")
            return {'CANCELLED'}

        return {'FINISHED'}


class AC_ToggleLightShadows(Operator):
    """Toggle cast shadows for the selected light (display is inverted: checked = shadows ON)"""

    bl_idname = "ac.toggle_light_shadows"
    bl_label = "Toggle Cast Shadows"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return 0 <= lighting.active_light_index < len(lighting.lights)

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        light = lighting.lights[lighting.active_light_index]
        light.cast_shadows = not light.cast_shadows
        return {'FINISHED'}


class AC_DuplicateLight(Operator):
    """Duplicate the selected light"""

    bl_idname = "ac.duplicate_light"
    bl_label = "Duplicate Light"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return 0 <= lighting.active_light_index < len(lighting.lights)

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        idx = lighting.active_light_index

        if not (0 <= idx < len(lighting.lights)):
            return {'CANCELLED'}

        source = lighting.lights[idx]

        # Create new light
        new_light = lighting.lights.add()

        # Copy all properties
        for prop in source.bl_rna.properties:
            if not prop.is_readonly and prop.identifier != 'rna_type':
                try:
                    setattr(new_light, prop.identifier, getattr(source, prop.identifier))
                except (AttributeError, TypeError):
                    pass

        # Clear linked object (user should link a new one)
        new_light.linked_object = None
        new_light.description = f"{source.description} (Copy)"

        # Offset position slightly
        pos = list(new_light.position)
        pos[0] += 2.0  # Offset by 2m in X
        new_light.position = tuple(pos)

        lighting.active_light_index = len(lighting.lights) - 1

        self.report({'INFO'}, f"Duplicated light: {new_light.description}")
        return {'FINISHED'}


class AC_SyncLightFromObject(Operator):
    """Sync position and direction from linked object"""

    bl_idname = "ac.sync_light_from_object"
    bl_label = "Sync from Object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        if 0 <= lighting.active_light_index < len(lighting.lights):
            light = lighting.lights[lighting.active_light_index]
            return light.linked_object is not None
        return False

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        light = lighting.lights[lighting.active_light_index]

        light.sync_from_linked_object()

        self.report({'INFO'}, f"Synced '{light.description}' from linked object")
        return {'FINISHED'}


class AC_SyncAllLights(Operator):
    """Sync all lights from their linked objects"""

    bl_idname = "ac.sync_all_lights"
    bl_label = "Sync All Lights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return len(settings.lighting.lights) > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        synced = 0

        for light in lighting.lights:
            if light.linked_object and light.use_object_transform:
                light.sync_from_linked_object()
                synced += 1

        self.report({'INFO'}, f"Synced {synced} light(s)")
        return {'FINISHED'}


class AC_SelectLightObject(Operator):
    """Select the linked object in the viewport"""

    bl_idname = "ac.select_light_object"
    bl_label = "Select Light Object"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(
        name="Light Index",
        description="Index of light to select (-1 for active light)",
        default=-1
    )

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return len(lighting.lights) > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Use specified index or active index
        idx = self.index if self.index >= 0 else lighting.active_light_index

        if not (0 <= idx < len(lighting.lights)):
            self.report({'WARNING'}, "Invalid light index")
            return {'CANCELLED'}

        light = lighting.lights[idx]

        if not light.linked_object:
            self.report({'WARNING'}, "Light has no linked object")
            return {'CANCELLED'}

        # Update active light index to match
        lighting.active_light_index = idx

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Select and make active
        light.linked_object.select_set(True)
        context.view_layer.objects.active = light.linked_object

        self.report({'INFO'}, f"Selected '{light.linked_object.name}'")
        return {'FINISHED'}


class AC_MoveLightUp(Operator):
    """Move light up in the list"""

    bl_idname = "ac.move_light_up"
    bl_label = "Move Light Up"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return lighting.active_light_index > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        idx = lighting.active_light_index

        lighting.lights.move(idx, idx - 1)
        lighting.active_light_index -= 1

        return {'FINISHED'}


class AC_MoveLightDown(Operator):
    """Move light down in the list"""

    bl_idname = "ac.move_light_down"
    bl_label = "Move Light Down"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return lighting.active_light_index < len(lighting.lights) - 1

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        idx = lighting.active_light_index

        lighting.lights.move(idx, idx + 1)
        lighting.active_light_index += 1

        return {'FINISHED'}


class AC_AddBlenderSpotLight(Operator):
    """Create a Blender spot light at cursor and add it as a CSP light"""

    bl_idname = "ac.add_blender_spot_light"
    bl_label = "Add Spot Light at Cursor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Create spot light at cursor
        cursor_loc = context.scene.cursor.location
        bpy.ops.object.light_add(type='SPOT', location=cursor_loc)
        light_obj = context.active_object

        # Name it with light prefix
        light_num = len(lighting.lights) + 1
        light_obj.name = f"AC_SpotLight_{light_num:02d}"

        # Point downward by default (no rotation needed, Blender lights point -Z)
        light_obj.rotation_euler = (0, 0, 0)

        # Set reasonable defaults for the Blender light
        light_data = light_obj.data
        light_data.energy = 100  # Watts
        light_data.color = (1.0, 0.92, 0.83)  # Warm white
        light_data.spot_size = math.radians(120)  # 120 degrees
        light_data.spot_blend = 0.7  # Soft edges
        light_data.use_custom_distance = True
        light_data.cutoff_distance = 40  # 40 meters range
        light_data.use_shadow = False  # Off by default

        # Create AC light entry linked to this light
        ac_light = lighting.lights.add()
        ac_light.linked_object = light_obj
        ac_light.linked_object_name = light_obj.name
        ac_light.use_object_transform = True
        ac_light.description = light_obj.name
        initialize_new_light(ac_light)

        # Sync properties from Blender light
        sync_light_properties_from_blender(ac_light, light_obj)

        lighting.active_light_index = len(lighting.lights) - 1

        self.report({'INFO'}, f"Created spot light '{light_obj.name}' at cursor")
        return {'FINISHED'}


class AC_SyncFromBlenderLight(Operator):
    """Sync CSP light properties from linked Blender light"""

    bl_idname = "ac.sync_from_blender_light"
    bl_label = "Sync from Blender Light"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        if 0 <= lighting.active_light_index < len(lighting.lights):
            light = lighting.lights[lighting.active_light_index]
            return light.linked_object and light.linked_object.type == 'LIGHT'
        return False

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        ac_light = lighting.lights[lighting.active_light_index]
        light_obj = ac_light.linked_object

        if not light_obj or light_obj.type != 'LIGHT':
            self.report({'WARNING'}, "No Blender light linked")
            return {'CANCELLED'}

        sync_light_properties_from_blender(ac_light, light_obj)

        self.report({'INFO'}, f"Synced properties from '{light_obj.name}'")
        return {'FINISHED'}


class AC_AddLightFromBlenderLights(Operator):
    """Create CSP lights from selected Blender light objects"""

    bl_idname = "ac.add_light_from_blender_lights"
    bl_label = "Add from Blender Lights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'LIGHT' for obj in context.selected_objects)

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        added_count = 0

        for obj in context.selected_objects:
            if obj.type != 'LIGHT':
                continue

            # Check if already linked
            already_linked = any(l.linked_object == obj for l in lighting.lights)
            if already_linked:
                self.report({'WARNING'}, f"'{obj.name}' is already linked")
                continue

            # Create AC light
            ac_light = lighting.lights.add()
            ac_light.linked_object = obj
            ac_light.linked_object_name = obj.name
            ac_light.use_object_transform = True
            ac_light.description = obj.name
            initialize_new_light(ac_light)

            # Sync from Blender light
            sync_light_properties_from_blender(ac_light, obj)
            added_count += 1

        if added_count > 0:
            lighting.active_light_index = len(lighting.lights) - 1
            self.report({'INFO'}, f"Added {added_count} light(s) from Blender lights")
        else:
            self.report({'WARNING'}, "No valid Blender lights to add")
            return {'CANCELLED'}

        return {'FINISHED'}


class AC_ScanLights(Operator):
    """Scan viewport for visible lights and sync with CSP light list"""

    bl_idname = "ac.scan_lights"
    bl_label = "Scan Lights"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ....utils.helpers import adjust_active_index
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Use consolidated scanning logic
        added_count, removed_count = scan_and_sync_lights(context, lighting)

        # Update active index
        lighting.active_light_index = adjust_active_index(lighting.active_light_index, len(lighting.lights))

        self.report({'INFO'}, f"Scan complete: +{added_count} added, -{removed_count} removed, {len(lighting.lights)} total")
        return {'FINISHED'}


class AC_SyncAllFromBlender(Operator):
    """Sync all CSP lights from their linked Blender lights"""

    bl_idname = "ac.sync_all_from_blender"
    bl_label = "Sync All from Blender"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return len(settings.lighting.lights) > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        synced = 0

        for ac_light in lighting.lights:
            if not ac_light.linked_object:
                continue

            obj = ac_light.linked_object

            if obj.type == 'LIGHT':
                sync_light_properties_from_blender(ac_light, obj)
            else:
                # Just sync transform for non-light objects
                ac_light.sync_from_linked_object()

            synced += 1

        self.report({'INFO'}, f"Synced {synced} light(s) from Blender")
        return {'FINISHED'}


class AC_ExportAndUpdateLights(Operator):
    """Scan for Blender lights and update light sections in ext_config.ini.

    This operator:
    1. Scans viewport for visible Blender lights
    2. Syncs them with the CSP lights list
    3. Updates only light sections in ext_config.ini

    All other sections (GRASS_FX, RAIN_FX, TREES, etc.) are preserved unchanged.
    """

    bl_idname = "ac.export_and_update_lights"
    bl_label = "Scan & Update Lights"
    bl_options = {'REGISTER'}

    # Skip sync check for programmatic calls
    skip_sync_check: bpy.props.BoolProperty(
        name="Skip Sync Check",
        description="Skip checking for external modifications to ext_config.ini",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return bool(settings.working_dir)

    def invoke(self, context, event):
        """Check for external modifications before updating."""
        if self.skip_sync_check:
            return self.execute(context)

        from ...configs.ext_config import compare_with_file, get_ext_config_path
        import os

        settings = context.scene.AC_Settings
        filepath = get_ext_config_path(settings)

        # If file doesn't exist, just execute
        if not os.path.exists(filepath):
            return self.execute(context)

        # Check for differences
        diff_result = compare_with_file(context)

        # If file has changes not in addon, show sync dialog
        if diff_result["has_differences"]:
            # Check if file has light-related changes
            has_light_changes = False
            for section_name, data in diff_result["sections"].items():
                if section_name.startswith("LIGHT") and data["status"] in ["modified", "removed"]:
                    has_light_changes = True
                    break

            if has_light_changes:
                return bpy.ops.ac.ext_config_sync_dialog('INVOKE_DEFAULT',
                                                          callback_operator="ac.export_and_update_lights")

        # No external changes to lights, proceed
        return self.execute(context)

    def execute(self, context):
        from ....utils.helpers import adjust_active_index
        from ...configs.ext_config import (
            collect_light_sections,
            get_ext_config_path,
            update_sections,
        )

        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Step 1: Scan for visible lights
        added_count, removed_count = scan_and_sync_lights(context, lighting)

        # Update active index
        lighting.active_light_index = adjust_active_index(lighting.active_light_index, len(lighting.lights))

        # Step 2: Collect light sections
        sections = collect_light_sections(context)

        # Step 3: Update only light sections in ext_config.ini
        ext_config_path = get_ext_config_path(settings)
        managed_prefixes = ["INCLUDE", "LIGHTING", "LIGHT_SERIES_", "LIGHT_"]
        update_sections(ext_config_path, sections, managed_prefixes)

        # Report
        light_count = sum(1 for k in sections if k.startswith("LIGHT_") and not k.startswith("LIGHT_SERIES_"))
        series_count = sum(1 for k in sections if k.startswith("LIGHT_SERIES_"))
        total = light_count + series_count

        report_parts = []
        if added_count > 0 or removed_count > 0:
            report_parts.append(f"Scan: +{added_count} -{removed_count}")
        report_parts.append(f"{total} light(s)")

        self.report({'INFO'}, f"Updated ext_config.ini: {', '.join(report_parts)}")
        return {'FINISHED'}


# ============================================================================
# EMISSIVE MATERIAL OPERATORS
# ============================================================================

class AC_AddEmissiveMaterial(Operator):
    """Add emissive material from material selector"""

    bl_idname = "ac.add_emissive_material"
    bl_label = "Add Emissive Material"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return lighting.material_to_add is not None

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        mat = lighting.material_to_add

        if not mat:
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        # Check if this material is already added
        for existing in lighting.emissive_materials:
            if existing.material == mat:
                self.report({'WARNING'}, f"Material '{mat.name}' already added")
                return {'CANCELLED'}

        # Add new emissive material entry
        emissive = lighting.emissive_materials.add()
        emissive.material = mat
        emissive.description = f"{mat.name} glow"
        emissive.active = True

        # Try to get color from material's emission if available
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'EMISSION':
                    if hasattr(node.inputs['Color'], 'default_value'):
                        color = node.inputs['Color'].default_value
                        emissive.emissive_color = (color[0], color[1], color[2])
                    if hasattr(node.inputs['Strength'], 'default_value'):
                        emissive.intensity = min(node.inputs['Strength'].default_value, 10.0)
                    break
                elif node.type == 'BSDF_PRINCIPLED':
                    emission_color = node.inputs.get('Emission Color')
                    if emission_color and hasattr(emission_color, 'default_value'):
                        color = emission_color.default_value
                        emissive.emissive_color = (color[0], color[1], color[2])
                    emission_strength = node.inputs.get('Emission Strength')
                    if emission_strength and hasattr(emission_strength, 'default_value'):
                        strength = emission_strength.default_value
                        if strength > 0:
                            emissive.intensity = min(strength, 10.0)
                    break

        # Set active index to new item
        lighting.active_emissive_index = len(lighting.emissive_materials) - 1

        self.report({'INFO'}, f"Added emissive material: {mat.name}")
        return {'FINISHED'}


class AC_AddEmissiveFromMesh(Operator):
    """Add emissive material using mesh object as filter (MESHES mode)"""

    bl_idname = "ac.add_emissive_from_mesh"
    bl_label = "Add Emissive from Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        obj = context.active_object

        # Check if this mesh is already added
        for existing in lighting.emissive_materials:
            if existing.use_mesh_filter and existing.mesh == obj:
                self.report({'WARNING'}, f"Mesh '{obj.name}' already added")
                return {'CANCELLED'}

        # Add new emissive material entry with mesh filter
        emissive = lighting.emissive_materials.add()
        emissive.mesh = obj
        emissive.use_mesh_filter = True
        emissive.description = f"{obj.name} glow"
        emissive.active = True

        # Also set material if available
        if obj.active_material:
            emissive.material = obj.active_material

        # Set active index to new item
        lighting.active_emissive_index = len(lighting.emissive_materials) - 1

        self.report({'INFO'}, f"Added emissive mesh: {obj.name}")
        return {'FINISHED'}


class AC_RemoveEmissiveMaterial(Operator):
    """Remove the selected emissive material"""

    bl_idname = "ac.remove_emissive_material"
    bl_label = "Remove Emissive Material"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(default=-1)

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return len(settings.lighting.emissive_materials) > 0

    def execute(self, context):
        from ....utils.helpers import is_valid_index, adjust_active_index
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        idx = self.index if self.index >= 0 else lighting.active_emissive_index

        if is_valid_index(idx, len(lighting.emissive_materials)):
            emissive = lighting.emissive_materials[idx]
            name = emissive.description or (emissive.material.name if emissive.material else "Unknown")
            lighting.emissive_materials.remove(idx)

            # Adjust active index
            lighting.active_emissive_index = adjust_active_index(lighting.active_emissive_index, len(lighting.emissive_materials))

            self.report({'INFO'}, f"Removed emissive material: {name}")
        else:
            self.report({'WARNING'}, "No emissive material selected")
            return {'CANCELLED'}

        return {'FINISHED'}


class AC_ToggleEmissiveShadows(Operator):
    """Toggle cast shadows for the selected emissive material (display is inverted: checked = shadows ON)"""

    bl_idname = "ac.toggle_emissive_shadows"
    bl_label = "Toggle Cast Shadows"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return 0 <= lighting.active_emissive_index < len(lighting.emissive_materials)

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        emissive = lighting.emissive_materials[lighting.active_emissive_index]
        emissive.cast_shadows = not emissive.cast_shadows
        return {'FINISHED'}


class AC_ClearEmissiveMaterials(Operator):
    """Remove all emissive materials"""

    bl_idname = "ac.clear_emissive_materials"
    bl_label = "Clear All Emissive Materials"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return len(settings.lighting.emissive_materials) > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        count = len(lighting.emissive_materials)
        lighting.emissive_materials.clear()
        lighting.active_emissive_index = 0

        self.report({'INFO'}, f"Cleared {count} emissive material(s)")
        return {'FINISHED'}


class AC_SelectEmissiveObject(Operator):
    """Select an object using this emissive material in the viewport"""

    bl_idname = "ac.select_emissive_object"
    bl_label = "Select Emissive Object"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(
        name="Emissive Index",
        description="Index of emissive material to select (-1 for active)",
        default=-1
    )

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting
        return len(lighting.emissive_materials) > 0

    def execute(self, context):
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Use specified index or active index
        idx = self.index if self.index >= 0 else lighting.active_emissive_index

        if not (0 <= idx < len(lighting.emissive_materials)):
            self.report({'WARNING'}, "Invalid emissive material index")
            return {'CANCELLED'}

        emissive = lighting.emissive_materials[idx]

        # Update active index to match
        lighting.active_emissive_index = idx

        if not emissive.material:
            self.report({'WARNING'}, "No material set")
            return {'CANCELLED'}

        # Find ALL objects using this material and select them
        from ....utils.helpers import is_hidden_name
        bpy.ops.object.select_all(action='DESELECT')
        selected_objects = []

        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue
            # Skip hidden/template objects
            if is_hidden_name(obj.name):
                continue
            for slot in obj.material_slots:
                if slot.material == emissive.material:
                    obj.select_set(True)
                    selected_objects.append(obj)
                    break  # Only add once per object

        if selected_objects:
            # Set last selected as active
            context.view_layer.objects.active = selected_objects[-1]
            self.report({'INFO'}, f"Selected {len(selected_objects)} object(s) with material '{emissive.material.name}'")
        else:
            self.report({'WARNING'}, f"No objects found using material '{emissive.material.name}'")
            return {'CANCELLED'}

        return {'FINISHED'}
