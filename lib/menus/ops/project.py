import math
import os

import bpy
from bpy import ops
from bpy.types import Context, Operator
from mathutils import Vector

from ....utils.files import (get_data_directory, get_extension_directory,
                             get_texture_directory, get_ui_directory,
                             load_ini, save_ini, save_json, merge_save_ini, merge_save_json,
                             set_path_reference)
from ...settings import AC_Settings
from ....utils.helpers import is_hidden_name


def format_float(value: float) -> str:
    """Format a float value with consistent formatting (strip trailing zeros)."""
    return f"{value:.6f}".rstrip('0').rstrip('.')


def validate_working_directory(settings: AC_Settings, operator: Operator) -> bool:
    """
    Validate that working directory is set and exists.

    Args:
        settings: AC_Settings instance
        operator: Blender operator (for reporting errors)

    Returns:
        True if valid, False otherwise (operator should return {'CANCELLED'})
    """
    if not settings.working_dir or settings.working_dir == "":
        operator.report({'ERROR'}, "Working directory not set. Please set it in Setup panel first.")
        return False

    if not os.path.isdir(settings.working_dir):
        operator.report({'ERROR'}, f"Working directory does not exist: {settings.working_dir}")
        return False

    # Update the global path reference
    set_path_reference(settings.working_dir)
    return True


def create_gate_pair(context: Context, gate_type: str, name_prefix: str, count: int = None) -> dict:
    """
    Create a pair of gate objects (L and R) at cursor location.

    Args:
        context: Blender context
        gate_type: Type identifier for naming ("TIME", "AB_START", "AB_FINISH")
        name_prefix: Full name prefix (e.g., "AC_TIME", "AC_AB_START")
        count: Gate count number (None for non-numbered gates)

    Returns:
        Dict with 'success': bool, 'objects': list of created object names
    """
    # Store cursor location to restore later
    cursor_location = context.scene.cursor.location.copy()
    created_objects = []

    try:
        # Left gate (offset -5 units on X-axis from cursor)
        context.scene.cursor.location = cursor_location + Vector((-5, 0, 0))
        ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
        gate_L = context.object
        if not gate_L:
            return {'success': False, 'objects': []}

        # Name left gate
        if count is not None:
            gate_L.name = f"{name_prefix}_{count}_L"
        else:
            gate_L.name = f"{name_prefix}_L"
        created_objects.append(gate_L.name)

        # Right gate (offset +5 units on X-axis from cursor)
        context.scene.cursor.location = cursor_location + Vector((5, 0, 0))
        ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
        gate_R = context.object
        if not gate_R:
            # Delete the left gate if the right one fails
            ops.object.select_all(action='DESELECT')
            gate_L.select_set(True)
            ops.object.delete()
            return {'success': False, 'objects': []}

        # Name right gate
        if count is not None:
            gate_R.name = f"{name_prefix}_{count}_R"
        else:
            gate_R.name = f"{name_prefix}_R"
        created_objects.append(gate_R.name)

        return {'success': True, 'objects': created_objects}

    finally:
        # Restore cursor location
        context.scene.cursor.location = cursor_location


def collect_material_data(context=None, visible_only: bool = True) -> list[dict]:
    """
    Collect materials with AC_Material settings.

    Args:
        context: Blender context (required if visible_only=True)
        visible_only: If True, only include materials on visible objects

    Returns:
        List of material info dicts with name, shader, and properties
    """
    import bpy
    from ....utils.helpers import get_visible_materials

    # Get set of visible material names if filtering
    visible_material_names = None
    if visible_only and context:
        visible_material_names = get_visible_materials(context)

    materials_data = []
    for material in bpy.data.materials:
        # Skip materials without node trees or hidden materials
        if not material.node_tree or is_hidden_name(material.name):
            continue

        # Skip unused materials
        if material.users == 0:
            continue

        # Skip materials not on visible objects (if filtering)
        if visible_material_names is not None and material.name not in visible_material_names:
            continue

        # Check if material has AC settings
        if not hasattr(material, 'AC_Material'):
            continue

        ac_mat = material.AC_Material

        # Get shader name
        shader_name = ac_mat.shader_name
        if not shader_name:
            continue

        # Collect shader properties
        material_info = {
            'name': material.name,
            'shader': shader_name,
            'properties': []
        }

        # Add all shader properties
        for prop in ac_mat.shader_properties:
            prop_data = {
                'name': prop.name,
                'type': prop.property_type,
            }

            # Get value based on type
            if prop.property_type == 'float':
                prop_data['value'] = prop.valueA
            elif prop.property_type == 'vec2':
                prop_data['value'] = (prop.valueB[0], prop.valueB[1])
            elif prop.property_type == 'vec3':
                prop_data['value'] = (prop.valueC[0], prop.valueC[1], prop.valueC[2])
            elif prop.property_type == 'vec4':
                prop_data['value'] = (prop.valueD[0], prop.valueD[1], prop.valueD[2], prop.valueD[3])

            material_info['properties'].append(prop_data)

        materials_data.append(material_info)

    return materials_data


def generate_shader_replacement_lines(materials_data: list[dict], include_header: bool = True) -> list[str]:
    """
    Generate shader replacement INI lines for materials.

    Args:
        materials_data: List of material info dicts from collect_material_data()
        include_header: Whether to include the comment header

    Returns:
        List of INI file lines
    """
    lines = []

    if not materials_data:
        return lines

    if include_header:
        lines.append("")
        lines.append("; ==============================================")
        lines.append("; SHADER REPLACEMENTS FOR LIVE MATERIAL EDITING")
        lines.append("; Generated by AC Track Tools")
        lines.append("; ==============================================")
        lines.append("")

    for idx, mat_info in enumerate(materials_data):
        lines.append("[SHADER_REPLACEMENT_...]")
        lines.append(f"MATERIALS = {mat_info['name']}")
        lines.append(f"SHADER = {mat_info['shader']}")

        # Add all shader properties using PROP_... syntax
        for prop in mat_info['properties']:
            if prop['type'] == 'float':
                lines.append(f"PROP_... = {prop['name']}, {format_float(prop['value'])}")
            elif prop['type'] == 'vec2':
                lines.append(f"PROP_... = {prop['name']}, {format_float(prop['value'][0])}, {format_float(prop['value'][1])}")
            elif prop['type'] == 'vec3':
                lines.append(f"PROP_... = {prop['name']}, {format_float(prop['value'][0])}, {format_float(prop['value'][1])}, {format_float(prop['value'][2])}")
            elif prop['type'] == 'vec4':
                lines.append(f"PROP_... = {prop['name']}, {format_float(prop['value'][0])}, {format_float(prop['value'][1])}, {format_float(prop['value'][2])}, {format_float(prop['value'][3])}")

        lines.append("")  # Empty line between sections

    # Add ksTree shader replacement if any ksTree materials exist
    tree_materials = [m for m in materials_data if m['shader'] == 'ksTree']
    if tree_materials:
        lines.append("[SHADER_REPLACEMENT_...]")
        lines.append("MATERIALS = shader:ksTree?")
        lines.append("MATERIAL_FLAG_0 = 1")
        lines.append("")

    return lines


def update_material_config(working_dir: str) -> tuple[bool, str, int]:
    """
    Update only the PROP_... values in existing SHADER_REPLACEMENT sections.
    Does not add or remove sections - only updates property values.

    Args:
        working_dir: Track working directory path

    Returns:
        Tuple of (success, message, updated_count)
    """
    import bpy
    import os
    import re

    if not working_dir or working_dir == "":
        return (False, "Working directory not set", 0)

    ext_dir = os.path.join(working_dir, "extension")
    ext_config_path = os.path.join(ext_dir, "ext_config.ini")

    if not os.path.exists(ext_config_path):
        return (False, "ext_config.ini not found. Use 'Save Extensions' first.", 0)

    # Read existing config
    with open(ext_config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Build a map of material name -> current Blender property values
    material_props = {}
    for material in bpy.data.materials:
        if not hasattr(material, 'AC_Material') or is_hidden_name(material.name):
            continue
        if material.users == 0:
            continue

        ac_mat = material.AC_Material
        if not ac_mat.shader_name:
            continue

        props = {}
        for prop in ac_mat.shader_properties:
            if prop.property_type == 'float':
                props[prop.name] = format_float(prop.valueA)
            elif prop.property_type == 'vec2':
                props[prop.name] = f"{format_float(prop.valueB[0])}, {format_float(prop.valueB[1])}"
            elif prop.property_type == 'vec3':
                props[prop.name] = f"{format_float(prop.valueC[0])}, {format_float(prop.valueC[1])}, {format_float(prop.valueC[2])}"
            elif prop.property_type == 'vec4':
                props[prop.name] = f"{format_float(prop.valueD[0])}, {format_float(prop.valueD[1])}, {format_float(prop.valueD[2])}, {format_float(prop.valueD[3])}"

        material_props[material.name] = props

    # Parse and update the config
    lines = content.split('\n')
    new_lines = []
    current_material = None
    updated_count = 0

    for line in lines:
        stripped = line.strip()

        # Check for MATERIALS = <name> line
        if stripped.startswith('MATERIALS') and '=' in stripped:
            mat_name = stripped.split('=', 1)[1].strip()
            # Only track if it's a specific material (not shader:ksTree? etc)
            if not mat_name.startswith('shader:'):
                current_material = mat_name
            else:
                current_material = None
            new_lines.append(line)
            continue

        # Check for new section - reset current material
        if stripped.startswith('['):
            current_material = None
            new_lines.append(line)
            continue

        # Check for PROP_N line that we should update (e.g., PROP_0, PROP_1, etc.)
        prop_match = re.match(r'^(PROP_\d+)\s*=\s*(.+)$', stripped)
        if prop_match and current_material:
            if current_material in material_props:
                prop_key = prop_match.group(1)  # e.g., "PROP_0"
                parts = prop_match.group(2)     # e.g., "ksAmbient, 0.200000"
                comma_idx = parts.find(',')
                if comma_idx > 0:
                    prop_name = parts[:comma_idx].strip()
                    if prop_name in material_props[current_material]:
                        # Update with new value, preserving original PROP_N key
                        new_value = material_props[current_material][prop_name]
                        new_lines.append(f"{prop_key} = {prop_name}, {new_value}")
                        updated_count += 1
                        continue

        # Keep line unchanged
        new_lines.append(line)

    # Write back
    with open(ext_config_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

    return (True, f"Updated {updated_count} property value(s)", updated_count)


class AC_SaveSettings(Operator):
    """Save the current settings"""
    bl_idname = "ac.save_settings"
    bl_label = "Save Settings"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        settings = context.scene.AC_Settings # type: ignore

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        ui_dir = get_ui_directory()
        track_data = settings.map_track(context)
        save_json(ui_dir + '/ui_track.json', track_data)

        get_texture_directory() # only need to ensure the directory exists
        # TODO: check materials for texture paths and update them to use the texture directory + relocate the textures

        data_dir = get_data_directory()
        surface_data = settings.map_surfaces()
        if 'surface' in list(settings.surface_errors.keys()):
            msg = settings.surface_errors['surface']
            settings.reset_errors()
            self.report({'ERROR'}, msg)
            return { 'CANCELLED' }
        save_ini(data_dir + '/surfaces.ini', surface_data)

        audio_data = settings.map_audio()
        save_ini(data_dir + '/audio_sources.ini', audio_data)

        save_ini(data_dir + '/lighting.ini', settings.map_lighting())

        extension_map: dict = settings.map_extensions()
        if 'extension' not in list(settings.surface_errors.keys()) and len(extension_map.keys()) > 0:
            extension_dir = get_extension_directory()
            save_ini(extension_dir + '/ext_config.ini', extension_map)

        # Note: Layout export (layouts.json, models.ini) has been disabled
        # to avoid creating unnecessary files in the working directory

        print("Settings saved")
        return {'FINISHED'}

class AC_SaveSurfaces(Operator):
    """Save only surfaces.ini (surface physics definitions) - preserves unmanaged sections"""
    bl_idname = "ac.save_surfaces"
    bl_label = "Save Surfaces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        data_dir = get_data_directory()
        surface_data = settings.map_surfaces()

        if 'surface' in list(settings.surface_errors.keys()):
            msg = settings.surface_errors['surface']
            settings.reset_errors()
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        surfaces_path = data_dir + '/surfaces.ini'

        # Get list of sections this operator manages
        # These sections will be completely replaced
        managed_sections = list(surface_data.keys())

        # Use merge save to preserve unmanaged sections (custom user sections)
        merge_save_ini(surfaces_path, surface_data, managed_sections)

        self.report({'INFO'}, f"Saved surfaces.ini ({len(managed_sections)} sections)")
        return {'FINISHED'}

class AC_SaveExtensions(Operator):
    """Save ext_config.ini with all CSP extensions (master exporter).

    This is the primary ext_config.ini writer that exports ALL addon data:
    - INCLUDE (CSP conditions)
    - GRASS_FX
    - RAIN_FX
    - CSP Lights (LIGHTING, LIGHT_*, LIGHT_SERIES_*)
    - Emissive Materials (MATERIAL_ADJUSTMENT_*)
    - Shader Replacements (SHADER_REPLACEMENT_*, includes ksTree flag)
    - Global Extensions (preserved custom sections)

    Note: TREES section is preserved but never written - managed by TreeFX operator.
    """
    bl_idname = "ac.save_extensions"
    bl_label = "Save Extensions"
    bl_options = {'REGISTER', 'UNDO'}

    # Skip sync check for programmatic calls
    skip_sync_check: bpy.props.BoolProperty(
        name="Skip Sync Check",
        description="Skip checking for external modifications to ext_config.ini",
        default=False,
    )

    def invoke(self, context, event):
        """Check for external modifications before exporting."""
        if self.skip_sync_check:
            return self.execute(context)

        from ...configs.ext_config import compare_with_file, get_ext_config_path
        import os

        settings = context.scene.AC_Settings
        filepath = get_ext_config_path(settings)

        # If file doesn't exist, just export
        if not os.path.exists(filepath):
            return self.execute(context)

        # Check for differences
        diff_result = compare_with_file(context)

        # If file has changes not in addon, show sync dialog
        if diff_result["has_differences"]:
            # Check if file has sections that aren't in addon (external additions)
            has_external_changes = False
            for section_name, data in diff_result["sections"].items():
                if data["status"] in ["modified", "removed"]:
                    has_external_changes = True
                    break

            if has_external_changes:
                return bpy.ops.ac.ext_config_sync_dialog('INVOKE_DEFAULT',
                                                          callback_operator="ac.save_extensions")

        # No external changes, proceed with export
        return self.execute(context)

    def execute(self, context):
        from ...configs.ext_config import (
            collect_all_sections,
            get_ext_config_path,
            write_ext_config,
            TREES_SECTION,
        )

        settings = context.scene.AC_Settings

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        # Check for errors
        if 'extension' in list(settings.surface_errors.keys()):
            msg = settings.surface_errors['extension']
            settings.reset_errors()
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}

        # Collect all sections from addon settings
        sections = collect_all_sections(context, include_shader_replacements=True)

        # Get output path
        ext_config_path = get_ext_config_path(settings)

        # Write with consistent ordering, preserving TREES section
        write_ext_config(ext_config_path, sections, preserve_sections=[TREES_SECTION])

        # Report success
        section_count = len(sections)
        self.report({'INFO'}, f"Saved ext_config.ini ({section_count} sections)")
        return {'FINISHED'}

class AC_SaveLighting(Operator):
    """Save only lighting.ini"""
    bl_idname = "ac.save_lighting"
    bl_label = "Save Lighting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        data_dir = get_data_directory()
        save_ini(data_dir + '/lighting.ini', settings.map_lighting())
        self.report({'INFO'}, "Saved lighting.ini")
        return {'FINISHED'}

class AC_SaveAudio(Operator):
    """Save only audio_sources.ini"""
    bl_idname = "ac.save_audio"
    bl_label = "Save Audio"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        data_dir = get_data_directory()
        audio_data = settings.map_audio()
        save_ini(data_dir + '/audio_sources.ini', audio_data)
        self.report({'INFO'}, "Saved audio_sources.ini")
        return {'FINISHED'}

class AC_SaveTrackData(Operator):
    """Save only ui_track.json (track metadata like name, tags, country, etc.) - preserves unmanaged keys"""
    bl_idname = "ac.save_track_data"
    bl_label = "Save Track Data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Validate working directory
        if not validate_working_directory(settings, self):
            return {'CANCELLED'}

        ui_dir = get_ui_directory()
        track_data = settings.map_track(context)

        # Use merge save to preserve unmanaged keys (custom user data)
        merge_save_json(ui_dir + '/ui_track.json', track_data)

        self.report({'INFO'}, "Saved ui_track.json")
        return {'FINISHED'}

class AC_AutofixPreflight(Operator):
    """Attempt to fix common issues"""
    bl_idname = "ac.autofix_preflight"
    bl_label = "Autofix Preflight"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        import bpy

        settings = context.scene.AC_Settings # type: ignore
        settings.track.pitboxes = len(settings.get_pitboxes(context))
        settings.consolidate_logic_gates(context)
        context.scene.unit_settings.system = 'METRIC'
        context.scene.unit_settings.length_unit = 'METERS'
        context.scene.unit_settings.scale_length = 1

        # Remove empty material slots from all mesh objects
        empty_slots_removed = 0
        objects_cleaned = 0
        skipped_objects = []

        for obj in bpy.data.objects:
            # Only process mesh objects
            if obj.type != 'MESH':
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

        if empty_slots_removed > 0:
            self.report({'INFO'}, f"Removed {empty_slots_removed} empty material slot(s) from {objects_cleaned} object(s)")

        if skipped_objects:
            skipped_list = ", ".join(skipped_objects[:3])
            if len(skipped_objects) > 3:
                skipped_list += f" (+{len(skipped_objects) - 3} more)"
            self.report({'WARNING'}, f"Skipped {len(skipped_objects)} object(s) not in view layer: {skipped_list}")

        # Re-run preflight scan to update error status after fixes
        bpy.ops.ac.scan_for_issues()

        return {'FINISHED'}

class AC_AddStart(Operator):
    """Add a new start position"""
    bl_idname = "ac.add_start"
    bl_label = "Add Start"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2), rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
        if context.object:
            ops.object.transform_apply(location=False, rotation=True, scale=False)
        settings = context.scene.AC_Settings # type: ignore
        settings.consolidate_logic_gates(context)
        start_pos = context.object
        if not start_pos:
            return {'CANCELLED'}
        # get next start position
        start_pos.name = f"AC_START_{len(settings.get_starts(context))}"
        return {'FINISHED'}

class AC_AddHotlapStart(Operator):
    """Add a new hotlap start position"""
    bl_idname = "ac.add_hotlap_start"
    bl_label = "Add Hotlap Start"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2), rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
        if context.object:
            ops.object.transform_apply(location=False, rotation=True, scale=False)
        settings = context.scene.AC_Settings # type: ignore
        settings.consolidate_logic_gates(context)
        start_pos = context.object
        if not start_pos:
            return {'CANCELLED'}
        start_pos.name = f"AC_HOTLAP_START_{len(settings.get_hotlap_starts(context))}"
        return {'FINISHED'}

class AC_AddPitbox(Operator):
    """Add a new pitbox"""
    bl_idname = "ac.add_pitbox"
    bl_label = "Add Pitbox"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2), rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
        if context.object:
            ops.object.transform_apply(location=False, rotation=True, scale=False)
        settings = context.scene.AC_Settings # type: ignore
        settings.consolidate_logic_gates(context)
        pitbox = context.object
        if not pitbox:
            return {'CANCELLED'}
        pitbox.name = f"AC_PIT_{len(settings.get_pitboxes(context))}"
        return {'FINISHED'}

class AC_AddTimeGate(Operator):
    """Add a new time gate"""
    bl_idname = "ac.add_time_gate"
    bl_label = "Add Time Gate"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        settings = context.scene.AC_Settings # type: ignore
        settings.consolidate_logic_gates(context)
        count = len(settings.get_time_gates(context)) // 2

        result = create_gate_pair(context, "TIME", "AC_TIME", count)
        return {'FINISHED'} if result['success'] else {'CANCELLED'}

class AC_AddABStartGate(Operator):
    """Add a new AB start gate"""
    bl_idname = "ac.add_ab_start_gate"
    bl_label = "Add AB Start Gate"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        result = create_gate_pair(context, "AB_START", "AC_AB_START")
        return {'FINISHED'} if result['success'] else {'CANCELLED'}

class AC_AddABFinishGate(Operator):
    """Add a new AB finish gate"""
    bl_idname = "ac.add_ab_finish_gate"
    bl_label = "Add AB Finish Gate"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        result = create_gate_pair(context, "AB_FINISH", "AC_AB_FINISH")
        return {'FINISHED'} if result['success'] else {'CANCELLED'}

class AC_AddAudioEmitter(Operator):
    """Add a new audio emitter"""
    bl_idname = "ac.add_audio_emitter"
    bl_label = "Add Audio Emitter"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        settings = context.scene.AC_Settings # type: ignore
        settings.consolidate_logic_gates(context)
        ops.object.empty_add(type='SPHERE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
        audio_emitter = context.object
        if not audio_emitter:
            return {'CANCELLED'}
        audio_emitter.name = f"AC_AUDIO_{len(settings.get_audio_emitters(context)) + 1}"
        return {'FINISHED'}


class AC_AddRaceSetup(Operator):
    """Add all essential race setup objects at once (start, hotlap start, pitbox, time gate, AB gates)"""
    bl_idname = "ac.add_race_setup"
    bl_label = "Add Race Setup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context: Context):
        settings = context.scene.AC_Settings
        created_objects = []

        # Store cursor location to restore later
        cursor_location = context.scene.cursor.location.copy()

        try:
            # 1. Add Race Start (arrow pointing forward)
            ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2),
                                rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
            if context.object:
                ops.object.transform_apply(location=False, rotation=True, scale=False)
                settings.consolidate_logic_gates(context)
                context.object.name = f"AC_START_{len(settings.get_starts(context))}"
                created_objects.append(context.object.name)

            # 2. Add Hotlap Start (slightly offset)
            context.scene.cursor.location = cursor_location + Vector((0, 2.5, 0))  # 2.5 units to the side (50% of 5)
            ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2),
                                rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
            if context.object:
                ops.object.transform_apply(location=False, rotation=True, scale=False)
                settings.consolidate_logic_gates(context)
                context.object.name = f"AC_HOTLAP_START_{len(settings.get_hotlap_starts(context))}"
                created_objects.append(context.object.name)

            # 3. Add Pitbox (offset from start)
            context.scene.cursor.location = cursor_location + Vector((0, -2.5, 0))  # Other side (50% of 5)
            ops.object.empty_add(type='SINGLE_ARROW', scale=(2, 2, 2),
                                rotation=(math.pi * -0.5, 0, 0), align='CURSOR')
            if context.object:
                ops.object.transform_apply(location=False, rotation=True, scale=False)
                settings.consolidate_logic_gates(context)
                context.object.name = f"AC_PIT_{len(settings.get_pitboxes(context))}"
                created_objects.append(context.object.name)

            # 4. Add Time Gate (pair of cubes)
            settings.consolidate_logic_gates(context)
            count = len(settings.get_time_gates(context)) // 2

            # Left gate
            context.scene.cursor.location = cursor_location + Vector((-5, 5, 0))  # 50% of (-10, 10)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            time_gate_L = context.object
            if time_gate_L:
                time_gate_L.name = f"AC_TIME_{count}_L"
                created_objects.append(time_gate_L.name)

            # Right gate
            context.scene.cursor.location = cursor_location + Vector((5, 5, 0))  # 50% of (10, 10)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            time_gate_R = context.object
            if time_gate_R:
                time_gate_R.name = f"AC_TIME_{count}_R"
                created_objects.append(time_gate_R.name)

            # 5. Add AB Start Gate (pair)
            context.scene.cursor.location = cursor_location + Vector((-5, 10, 0))  # 50% of (-10, 20)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            ab_start_L = context.object
            if ab_start_L:
                ab_start_L.name = "AC_AB_START_L"
                created_objects.append(ab_start_L.name)

            context.scene.cursor.location = cursor_location + Vector((5, 10, 0))  # 50% of (10, 20)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            ab_start_R = context.object
            if ab_start_R:
                ab_start_R.name = "AC_AB_START_R"
                created_objects.append(ab_start_R.name)

            # 6. Add AB Finish Gate (pair)
            context.scene.cursor.location = cursor_location + Vector((-5, 15, 0))  # 50% of (-10, 30)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            ab_finish_L = context.object
            if ab_finish_L:
                ab_finish_L.name = "AC_AB_FINISH_L"
                created_objects.append(ab_finish_L.name)

            context.scene.cursor.location = cursor_location + Vector((5, 15, 0))  # 50% of (10, 30)
            ops.object.empty_add(type='CUBE', scale=(2, 2, 2), rotation=(0, 0, 0), align='CURSOR')
            ab_finish_R = context.object
            if ab_finish_R:
                ab_finish_R.name = "AC_AB_FINISH_R"
                created_objects.append(ab_finish_R.name)

            # Report success
            self.report({'INFO'}, f"Created {len(created_objects)} race setup objects")
            return {'FINISHED'}

        finally:
            # Restore cursor location
            context.scene.cursor.location = cursor_location


class AC_ValidateAll(Operator):
    """Validate all materials, auto-detect shaders, and assign texture slots"""
    bl_idname = "ac.validate_all"
    bl_label = "Validate All Materials"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from ...kn5.export_utils import validate_all_materials

        # Call the unified validation function with CSP detection and grass specular fix enabled
        stats = validate_all_materials(context, run_csp_detection=True, fix_grass_specular=True, verbose=True)

        # Build report message
        report_lines = []
        report_lines.append(f"Validated {stats['materials_validated']} material(s)")
        if stats['materials_fixed'] > 0:
            report_lines.append(f"Fixed {stats['materials_fixed']} material(s), added {stats['properties_added']} shader properties")
        if stats['textures_assigned'] > 0:
            report_lines.append(f"Assigned {stats['textures_assigned']} texture slot(s)")
        if stats['materials_upgraded'] > 0:
            report_lines.append(f"Upgraded {stats['materials_upgraded']} shader(s)")
        if stats['grass_specular_fixed'] > 0:
            report_lines.append(f"Set specular=0 for {stats['grass_specular_fixed']} grass material(s)")
        report_lines.append("Auto-detected GrassFX and RainFX materials")

        self.report({'INFO'}, " | ".join(report_lines))

        return {'FINISHED'}


class AC_UpdateMaterialConfig(Operator):
    """Update ext_config.ini with shader replacements for all materials (for live editing in-game)"""
    bl_idname = "ac.update_material_config"
    bl_label = "Update Material Config"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return settings.working_dir and settings.working_dir != ""

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Call the helper function
        success, message, count = update_material_config(settings.working_dir)

        if not success:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

        self.report({'INFO'}, message)
        print(f"✓ Material config updated")
        print(f"  Generated {count} shader replacement sections")

        return {'FINISHED'}


class AC_ScanForIssues(Operator):
    """Run preflight checks and cache results"""
    bl_idname = "ac.scan_for_issues"
    bl_label = "Scan for Issues"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Run preflight checks
        errors = settings.run_preflight(context)

        # Cache results
        settings.preflight_scanned = True
        settings.preflight_error_count = len(errors)
        blocking_errors = [e for e in errors if e["severity"] >= 1]
        settings.preflight_has_blocking_errors = len(blocking_errors) > 0

        # Force UI redraw to update export panel
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # Show results popup
        bpy.ops.ac.show_preflight_errors('INVOKE_DEFAULT')

        return {'FINISHED'}


class AC_ShowPreflightErrors(Operator):
    """Show all preflight errors and warnings"""
    bl_idname = "ac.show_preflight_errors"
    bl_label = "Preflight Checks"
    bl_options = {'REGISTER'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=700)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings

        # Use cached errors (run_preflight was already called by AC_ScanForIssues)
        errors = settings.error

        # Separate by severity
        blocking_errors = [e for e in errors if e["severity"] == 2]
        warnings = [e for e in errors if e["severity"] == 1]
        info = [e for e in errors if e["severity"] == 0]

        # Header
        header = layout.row()
        header.alignment = "CENTER"
        header.scale_y = 1.2

        if len(blocking_errors) == 0 and len(warnings) == 0:
            if len(info) == 0:
                header.label(text="✓ All Checks Passed", icon="CHECKMARK")
            else:
                header.label(text=f"✓ Ready to Export ({len(info)} info)", icon="INFO")
        else:
            total_issues = len(blocking_errors) + len(warnings)
            header.label(text=f"⚠ {total_issues} Issue(s) Found", icon="ERROR")

        layout.separator()

        # Show blocking errors (severity 2)
        if blocking_errors:
            box = layout.box()
            header_row = box.row()
            header_row.label(text=f"Critical Errors ({len(blocking_errors)})", icon="CANCEL")

            for error in blocking_errors:
                error_row = box.row()
                error_row.alert = True
                error_row.scale_y = 0.9

                # Split into label column and message column for better layout
                col = error_row.column()
                col.label(text=f"• {error['message']}", icon="ERROR")

            layout.separator()

        # Show warnings (severity 1)
        if warnings:
            box = layout.box()
            header_row = box.row()
            header_row.label(text=f"Warnings ({len(warnings)})", icon="ERROR")

            for warning in warnings:
                warning_row = box.row()
                warning_row.scale_y = 0.9

                col = warning_row.column()
                col.label(text=f"• {warning['message']}", icon="DOT")

            layout.separator()

        # Show info (severity 0)
        if info:
            box = layout.box()
            header_row = box.row()
            header_row.label(text=f"Information ({len(info)})", icon="INFO")

            for info_item in info:
                info_row = box.row()
                info_row.scale_y = 0.9

                col = info_row.column()
                col.label(text=f"• {info_item['message']}", icon="DOT")

            layout.separator()

        # Footer with autofix button if applicable
        can_fix = len(warnings) > 0
        if can_fix:
            footer = layout.row()
            footer.scale_y = 1.3
            footer.operator("ac.autofix_preflight", text="Attempt to Fix Issues", icon="TOOL_SETTINGS")
