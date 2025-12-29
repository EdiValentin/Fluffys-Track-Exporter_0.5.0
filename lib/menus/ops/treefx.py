"""Operators for TreeFX export functionality."""

import bpy
import os
from bpy.types import Operator
from bpy.props import StringProperty

from ....utils.files import get_extension_directory, ensure_path_exists, set_path_reference
from ...configs.ext_config import update_sections


class AC_ExportTreeList(Operator):
    """Export tree instances to Assetto Corsa TreeFX format"""

    bl_idname = "ac.export_tree_list"
    bl_label = "Export AC Tree List"
    bl_options = {'REGISTER', 'UNDO'}

    filename: StringProperty(
        name="Filename",
        description="Name of the tree list file (automatically saved to extension/trees/)",
        default="trees.txt"
    )

    def get_socket_value(self, geo_mod, socket_name, default=1.0):
        """Get single float value from socket or return default"""
        try:
            value = geo_mod[socket_name]
            return float(value)
        except (KeyError, TypeError):
            return default

    def ensure_file_extension(self, filepath):
        """Ensure the file has a .txt extension"""
        if not filepath.lower().endswith('.txt'):
            return f"{os.path.splitext(filepath)[0]}.txt"
        return filepath

    def execute(self, context):
        settings = context.scene.AC_Settings

        # Check if working directory is set
        if not settings.working_dir:
            self.report({'ERROR'}, "Working directory not set. Please set it in Setup panel first.")
            return {'CANCELLED'}

        # Ensure path_ref is set to working directory before using file utilities
        set_path_reference(settings.working_dir)

        selected_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objs:
            self.report({'ERROR'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Get extension directory and create trees subfolder
        extension_dir = get_extension_directory()
        trees_dir = ensure_path_exists(extension_dir + '/trees/')

        # Ensure filename has .txt extension
        filename = self.ensure_file_extension(self.filename)

        # Build the full save path
        filepath = os.path.join(trees_dir, filename)

        all_lines = []
        variance_written = False

        for obj in selected_objs:
            # Try to get variance values from _TREES modifier (once)
            if not variance_written:
                geo_mod = next((mod for mod in obj.modifiers
                              if mod.type == 'NODES' and mod.node_group and mod.node_group.name == "_TREES"), None)

                if geo_mod:
                    # Get all variance values as single floats
                    size_min = self.get_socket_value(geo_mod, "Socket_31")
                    size_max = self.get_socket_value(geo_mod, "Socket_39")
                    width_min = self.get_socket_value(geo_mod, "Socket_40")
                    width_max = self.get_socket_value(geo_mod, "Socket_41")
                    angle_min = self.get_socket_value(geo_mod, "Socket_45")
                    angle_max = self.get_socket_value(geo_mod, "Socket_42")
                    bright_min = self.get_socket_value(geo_mod, "Socket_43")
                    bright_max = self.get_socket_value(geo_mod, "Socket_44")

                    # Convert angles from radians to degrees
                    angle_min_deg = round(angle_min * 180 / 3.14159265359)
                    angle_max_deg = round(angle_max * 180 / 3.14159265359)

                    # Add variance headers
                    all_lines.append(f"configure: size variance = {size_min:.1f}, {size_max:.1f}")
                    all_lines.append(f"configure: angle variance = {angle_min_deg}, {angle_max_deg}")
                    all_lines.append(f"configure: width variance = {width_min:.1f}, {width_max:.1f}")
                    all_lines.append("configure: color variance = 1.0, 1.0")
                    all_lines.append(f"configure: brightness variance = {bright_min:.1f}, {bright_max:.1f}")

                    variance_written = True

            # Get evaluated instances
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)

            # Collect all instances
            for dup in depsgraph.object_instances:
                if dup.is_instance and dup.parent and dup.parent.original == obj:
                    inst_obj = dup.instance_object
                    if not inst_obj:
                        continue

                    name = inst_obj.name
                    location = dup.matrix_world.translation
                    # Format: X, Y, -Z (swap Y/Z and flip Z)
                    all_lines.append(
                        f"tree:{name};{location.x:.8f},{location.z:.8f},{-location.y:.8f}"
                    )

        if len(all_lines) <= (5 if variance_written else 0):
            self.report({'ERROR'}, "No instances found in selection")
            return {'CANCELLED'}

        try:
            with open(filepath, "w") as f:
                f.write("\n".join(all_lines))
        except (IOError, OSError, PermissionError) as e:
            self.report({'ERROR'}, f"Failed to write file: {e}")
            return {'CANCELLED'}

        # Update ext_config.ini with TREES section
        try:
            self.update_ext_config(extension_dir, filename)
        except Exception as e:
            self.report({'WARNING'}, f"Tree list exported but failed to update ext_config.ini: {e}")

        tree_count = len(all_lines) - (5 if variance_written else 0)
        self.report({'INFO'}, f"Exported {tree_count} tree instances to {filepath}")
        return {'FINISHED'}

    def update_ext_config(self, extension_dir, filename):
        """
        Update ext_config.ini with TREES section.

        - Scans trees folder for all .txt files
        - Adds new file if not already in config
        - Removes entries for files that no longer exist
        - Preserves other sections
        """
        from ...configs.ext_config import parse_ext_config

        ext_config_path = os.path.join(extension_dir, 'ext_config.ini')
        trees_dir = os.path.join(extension_dir, 'trees')

        # Use backslash for AC path format (how it appears in ext_config)
        new_trees_path = f"trees\\{filename}"

        # Scan trees folder for all existing .txt files
        existing_txt_files = set()
        if os.path.exists(trees_dir):
            for f in os.listdir(trees_dir):
                if f.lower().endswith('.txt'):
                    # Store in AC format (backslash)
                    existing_txt_files.add(f"trees\\{f}")

        # Parse existing ext_config to get current TREES section
        existing_sections = parse_ext_config(ext_config_path)
        existing_trees = existing_sections.get('TREES', {})

        # Collect currently configured LIST entries
        configured_lists = []
        for key, value in existing_trees.items():
            if key.startswith('LIST_'):
                configured_lists.append(value)

        # Build new list of valid tree files:
        # 1. Keep existing entries that still have files
        # 2. Add the newly exported file if not already present
        valid_lists = []

        # First, keep existing entries that have matching files
        for path in configured_lists:
            if path in existing_txt_files:
                valid_lists.append(path)

        # Add the new file if not already in the list
        if new_trees_path not in valid_lists:
            valid_lists.append(new_trees_path)

        # Build TREES section config with numbered LIST entries
        trees_config = {
            'TREES': {
                'ACTIVE': '1',
            }
        }

        for idx, path in enumerate(valid_lists, start=1):
            trees_config['TREES'][f'LIST_{idx}'] = path

        # Use update_sections to properly handle section ordering and preservation
        # Only TREES section will be replaced, all others preserved
        update_sections(ext_config_path, trees_config, managed_prefixes=['TREES'])

    def draw(self, context):
        """Draw the operator dialog"""
        layout = self.layout
        layout.prop(self, "filename")

        # Show full save path
        settings = context.scene.AC_Settings
        if settings.working_dir:
            full_path = os.path.join(settings.working_dir, "extension", "trees", self.filename)
            box = layout.box()
            box.label(text="Save Location:", icon="INFO")
            box.label(text=full_path, icon="BLANK1")

    def invoke(self, context, event):
        # Set default filename based on blend file name
        if not self.filename or self.filename == "trees.txt":
            blend_filepath = context.blend_data.filepath
            if blend_filepath:
                blend_name = os.path.splitext(os.path.basename(blend_filepath))[0]
                self.filename = f"{blend_name}_trees.txt"
            else:
                self.filename = "trees.txt"

        # Show dialog to enter filename
        return context.window_manager.invoke_props_dialog(self)
