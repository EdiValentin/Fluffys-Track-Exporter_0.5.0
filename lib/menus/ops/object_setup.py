"""Operators for setting up objects with AC-specific configurations."""

import re
import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ...kn5.shader_defaults import get_shader_defaults
from ....utils.helpers import is_hidden_name


def setup_material_with_shader(material, shader_name: str):
    """Configure material with shader-specific settings."""
    ac_mat = material.AC_Material
    defaults = get_shader_defaults(shader_name)

    # Set shader settings
    ac_mat.shader_name = shader_name
    ac_mat.alpha_tested = defaults["alpha_tested"]
    ac_mat.alpha_blend_mode = str(defaults["alpha_blend_mode"])
    ac_mat.depth_mode = str(defaults["depth_mode"])

    # Clear and add shader properties
    ac_mat.shader_properties.clear()
    for prop_data in defaults["properties"]:
        prop = ac_mat.shader_properties.add()
        prop.name = prop_data["name"]
        prop.property_type = prop_data.get("type", "float")

        # Set appropriate value based on type
        if "valueA" in prop_data:
            prop.valueA = prop_data["valueA"]
        if "valueB" in prop_data:
            prop.valueB = prop_data["valueB"]
        if "valueC" in prop_data:
            prop.valueC = prop_data["valueC"]
        if "valueD" in prop_data:
            prop.valueD = prop_data["valueD"]


class AC_SetupAsGrass(Operator):
    """Add selected objects' materials to GrassFX without changing shaders"""

    bl_idname = "ac.setup_as_grass"
    bl_label = "Setup as Grass (GrassFX)"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add materials to GrassFX configuration (preserves existing shader setup)"

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        settings = context.scene.AC_Settings
        grassfx_materials = []
        added_materials = []

        for obj in meshes:
            # Add materials to GrassFX without modifying shader
            for slot in obj.material_slots:
                if slot.material:
                    mat_name = slot.material.name

                    # Track unique materials
                    if mat_name not in grassfx_materials:
                        grassfx_materials.append(mat_name)

                        # Check if material is already in GrassFX list
                        existing_materials = [m.material_name for m in settings.grassfx.materials]
                        if mat_name not in existing_materials:
                            # Add to GrassFX
                            mat_entry = settings.grassfx.materials.add()
                            mat_entry.material_name = mat_name
                            added_materials.append(mat_name)

        # Report results
        if added_materials:
            mats_str = ", ".join(added_materials)
            self.report({'INFO'},
                f"Added {len(added_materials)} material(s) to GrassFX: {mats_str}")
        elif grassfx_materials:
            self.report({'INFO'},
                f"All materials already in GrassFX list")
        else:
            self.report({'WARNING'}, "No materials found on selected objects")

        return {'FINISHED'}


class AC_SetupAsStandard(Operator):
    """Setup selected meshes with ksPerPixel shader"""

    bl_idname = "ac.setup_as_standard"
    bl_label = "Setup as Standard Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        for obj in meshes:
            # Setup materials
            for slot in obj.material_slots:
                if slot.material:
                    setup_material_with_shader(slot.material, "ksPerPixel")

            # Set KN5 object properties
            obj.AC_KN5.cast_shadows = True
            obj.AC_KN5.transparent = False

        self.report({'INFO'}, f"Configured {len(meshes)} object(s) as standard")
        return {'FINISHED'}


class AC_AutoSetupObjects(Operator):
    """Automatically setup objects based on naming patterns"""

    bl_idname = "ac.auto_setup_objects"
    bl_label = "Auto Setup by Name"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Scan object names and auto-configure (grass)"

    def execute(self, context):
        grass_count = 0

        for obj in context.scene.objects:
            if obj.type != 'MESH' or is_hidden_name(obj.name):
                continue

            name_lower = obj.name.lower()

            # Auto-detect grass
            if 'grass' in name_lower:
                context.view_layer.objects.active = obj
                obj.select_set(True)
                bpy.ops.ac.setup_as_grass()
                obj.select_set(False)
                grass_count += 1

        self.report({'INFO'}, f"Auto-configured {grass_count} grass")
        return {'FINISHED'}


class AC_SetupAsTree(Operator):
    """Setup selected objects as AC trees with KSTREE naming and ksTree shader"""

    bl_idname = "ac.setup_as_tree"
    bl_label = "Setup as Tree"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Convert selected objects to AC tree format (KSTREE naming, ksTree shader)"

    group_name: StringProperty(
        name="Group Name",
        description="Name for the tree group (e.g., 'A', 'PINE', 'OAK'). Objects will be named KSTREE_GROUP_[name]_[number]",
        default="A"
    )

    def invoke(self, context, event):
        """Show dialog to enter group name"""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "group_name")
        layout.separator()
        box = layout.box()
        box.scale_y = 0.8
        box.label(text="Objects will be named:", icon='INFO')
        box.label(text=f"KSTREE_GROUP_{self.group_name.upper()}_1, _2, ...", icon='BLANK1')

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not meshes:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}

        # Validate group name (only letters, numbers, underscores)
        group_name = self.group_name.upper().strip()
        if not group_name:
            self.report({'ERROR'}, "Group name cannot be empty")
            return {'CANCELLED'}

        if not re.match(r'^[A-Z0-9_]+$', group_name):
            self.report({'ERROR'}, "Group name can only contain letters, numbers, and underscores")
            return {'CANCELLED'}

        # Find existing KSTREE objects with this group name to continue numbering
        existing_numbers = []
        pattern = rf'^KSTREE_GROUP_{re.escape(group_name)}_(\d+)'
        for obj in bpy.data.objects:
            match = re.match(pattern, obj.name, re.IGNORECASE)
            if match:
                existing_numbers.append(int(match.group(1)))

        next_number = max(existing_numbers, default=0) + 1

        # PERFORMANCE: Track which materials have already been processed
        # to avoid redundant material setup when many objects share materials
        processed_materials = set()

        renamed_count = 0
        material_setup_count = 0

        for obj in meshes:
            # 1. Make single user (required for proper export - no linked/multiuser data)
            # This ensures each tree is independent and won't cause export issues
            if obj.data.users > 1:
                obj.data = obj.data.copy()

            # 2. Rename object to KSTREE_GROUP_[name]_[number]
            new_name = f"KSTREE_GROUP_{group_name}_{next_number}"
            obj.name = new_name
            next_number += 1
            renamed_count += 1

            # 3. Setup materials with ksTree shader (only if not already processed)
            for slot in obj.material_slots:
                if slot.material and slot.material.name not in processed_materials:
                    setup_material_with_shader(slot.material, "ksTree")
                    # Also run texture slot assignment for the material
                    self.assign_texture_slots(slot.material)
                    processed_materials.add(slot.material.name)
                    material_setup_count += 1

            # 4. Set KN5 object properties for trees
            # IMPORTANT: IsTransparent must be FALSE for trees!
            # Using True causes depth/transparency ordering issues
            # The ksTree shader with AlphaTest handles transparency correctly
            obj.AC_KN5.cast_shadows = True  # Trees can cast shadows
            obj.AC_KN5.transparent = False  # Must be False - do NOT use alphablend with trees

        self.report({'INFO'},
            f"Setup {renamed_count} tree(s) in group '{group_name}': "
            f"{material_setup_count} material(s) configured with ksTree shader")
        return {'FINISHED'}

    def assign_texture_slots(self, material):
        """Assign texture slots based on node connections (for ksTree, only txDiffuse is needed)"""
        from ...kn5.shader_defaults import get_texture_slot_from_name

        if not material.node_tree:
            return

        # Find Principled BSDF
        principled_node = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break

        if not principled_node:
            return

        # Trace Base Color socket for txDiffuse
        if 'Base Color' in principled_node.inputs:
            base_color_input = principled_node.inputs['Base Color']
            if base_color_input.is_linked:
                for link in base_color_input.links:
                    self.trace_and_assign_texture(link.from_node, "txDiffuse")

        # Also check Alpha socket
        if 'Alpha' in principled_node.inputs:
            alpha_input = principled_node.inputs['Alpha']
            if alpha_input.is_linked:
                for link in alpha_input.links:
                    self.trace_and_assign_texture(link.from_node, "txDiffuse")

        # Fallback: assign unassigned textures by name pattern
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                if is_hidden_name(node.image.name):
                    continue
                ac_texture = node.AC_Texture
                if not ac_texture.shader_input_name:
                    # Try naming pattern matching
                    slot = get_texture_slot_from_name(node.image.name)
                    if slot:
                        ac_texture.shader_input_name = slot

    def trace_and_assign_texture(self, node, slot_name, visited=None):
        """Recursively trace nodes to find and assign texture slots"""
        if visited is None:
            visited = set()

        if node in visited:
            return
        visited.add(node)

        # If this is a texture node, assign the slot
        if node.type == 'TEX_IMAGE' and node.image:
            if not is_hidden_name(node.image.name):
                ac_texture = node.AC_Texture
                if not ac_texture.shader_input_name or ac_texture.shader_input_name != slot_name:
                    ac_texture.shader_input_name = slot_name

        # Continue tracing through node inputs
        for input_socket in node.inputs:
            if input_socket.is_linked:
                for link in input_socket.links:
                    self.trace_and_assign_texture(link.from_node, slot_name, visited)
