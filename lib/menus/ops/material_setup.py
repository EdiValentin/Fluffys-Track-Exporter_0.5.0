"""Material setup operators for automatic texture slot assignment."""

import bpy
from bpy.types import Operator

from ...kn5.shader_defaults import get_shader_defaults, get_texture_slot_from_name
from ....utils.helpers import is_hidden_name


def apply_shader_defaults(material, shader_name: str):
    """
    Apply default shader properties for a given shader.

    This function reads the shader definitions from shader_defaults.py and creates
    the appropriate AC_ShaderProperty entries with correct types and values.
    """
    defaults = get_shader_defaults(shader_name)
    ac_mat = material.AC_Material

    # Only add properties if they don't already exist
    existing_props = {prop.name for prop in ac_mat.shader_properties}

    for prop_def in defaults.get("properties", []):
        prop_name = prop_def["name"]
        if prop_name not in existing_props:
            new_prop = ac_mat.shader_properties.add()
            new_prop.name = prop_name

            # Set property type (default to 'float' if not specified)
            prop_type = prop_def.get("type", "float")
            new_prop.property_type = prop_type

            # Set appropriate value based on type
            if "valueA" in prop_def:
                new_prop.valueA = prop_def["valueA"]
            if "valueB" in prop_def:
                new_prop.valueB = prop_def["valueB"]
            if "valueC" in prop_def:
                # valueC is used for colors (RGB) or 3-component vectors
                new_prop.valueC = prop_def["valueC"]
            if "valueD" in prop_def:
                new_prop.valueD = prop_def["valueD"]


class AC_AutoAssignTextureSlots(Operator):
    """Automatically assign AC texture slots based on node connections and naming patterns"""
    bl_idname = "ac.auto_assign_texture_slots"
    bl_label = "Auto-Assign Texture Slots"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        materials_processed = 0
        textures_assigned = 0
        materials_upgraded = 0
        unassigned_textures = []

        # Process all materials in the scene
        for material in bpy.data.materials:
            if not material.node_tree or is_hidden_name(material.name):
                continue

            # Check if material is used in the scene
            if material.users == 0:
                continue

            # Find the Principled BSDF node (most common shader node)
            principled_node = None
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                    break

            if not principled_node:
                continue

            materials_processed += 1
            material_changed = False
            has_normal_map = False
            has_maps_texture = False

            # Check all texture nodes and their connections
            for node in material.node_tree.nodes:
                if node.type != 'TEX_IMAGE' or not node.image:
                    continue

                # Skip hidden textures
                if is_hidden_name(node.image.name):
                    continue

                ac_texture = node.AC_Texture
                current_slot = ac_texture.shader_input_name
                new_slot = None
                assignment_method = None  # Track how slot was assigned

                # PRIORITY 1: Check node connections to Principled BSDF (most reliable)
                for output in node.outputs:
                    for link in output.links:
                        to_node = link.to_node
                        socket_name = link.to_socket.name

                        # Check if connected to Principled BSDF
                        if to_node == principled_node:
                            if socket_name in ('Base Color', 'Color'):
                                new_slot = "txDiffuse"
                                assignment_method = "connected to Base Color"
                                break
                            elif socket_name in ('Emission', 'Emission Color', 'Emission Strength'):
                                new_slot = "txEmissive"
                                assignment_method = "connected to Emission"
                                break
                            elif socket_name in ('Roughness',):
                                if current_slot not in ("txDiffuse", "txNormal", "txEmissive"):
                                    new_slot = "txMaps"
                                    assignment_method = "connected to Roughness"
                            elif socket_name in ('Specular', 'Specular IOR Level'):
                                if current_slot not in ("txDiffuse", "txNormal", "txEmissive"):
                                    new_slot = "txMaps"
                                    assignment_method = "connected to Specular"
                            elif socket_name in ('Metallic',):
                                if current_slot not in ("txDiffuse", "txNormal", "txEmissive"):
                                    new_slot = "txMaps"
                                    assignment_method = "connected to Metallic"

                        # Check for Normal Map node connection
                        elif to_node.type == 'NORMAL_MAP':
                            new_slot = "txNormal"
                            assignment_method = "connected to Normal Map node"
                            has_normal_map = True
                            break

                        # Check for ColorRamp or MixRGB nodes (detail/mask textures)
                        elif to_node.type in ('VALTORGB', 'MIX_RGB', 'MIX'):
                            # These might be detail or mask textures
                            # Use naming pattern matching for these
                            pass

                    if new_slot and assignment_method:  # Break outer loop if we found a connection
                        break

                # PRIORITY 2: If no connection-based assignment, use naming pattern matching
                if not new_slot:
                    new_slot = get_texture_slot_from_name(node.image.name)
                    if new_slot:
                        assignment_method = "pattern match"

                # PRIORITY 3: Set correct color space for normal maps
                if new_slot == "txNormal" and node.image:
                    if node.image.colorspace_settings.name != 'Non-Color':
                        node.image.colorspace_settings.name = 'Non-Color'

                # Track if we have maps texture
                if new_slot == "txMaps":
                    has_maps_texture = True

                # Update texture slot if determined and different
                if new_slot and new_slot != current_slot:
                    ac_texture.shader_input_name = new_slot
                    textures_assigned += 1
                    material_changed = True
                    self.report({'INFO'}, f"  {material.name}: {node.image.name} → {new_slot} ({assignment_method})")
                elif not new_slot and not current_slot:
                    # Track unassigned textures for warning
                    unassigned_textures.append((material.name, node.image.name))

            # If material has normal map but uses basic shader, upgrade to appropriate NM shader
            if (has_normal_map or has_maps_texture) and material_changed:
                ac_mat = material.AC_Material
                if ac_mat.shader_name == "ksPerPixel":
                    ac_mat.shader_name = "ksPerPixelNM_UVMult"
                    apply_shader_defaults(material, "ksPerPixelNM_UVMult")
                    materials_upgraded += 1
                    self.report({'INFO'}, f"  {material.name}: Upgraded to ksPerPixelNM_UVMult")
                elif ac_mat.shader_name == "ksPerPixelAT":
                    ac_mat.shader_name = "ksPerPixelAT_NM"
                    apply_shader_defaults(material, "ksPerPixelAT_NM")
                    materials_upgraded += 1
                    self.report({'INFO'}, f"  {material.name}: Upgraded to ksPerPixelAT_NM")

        # Report unassigned textures as warnings
        if unassigned_textures:
            self.report({'WARNING'}, f"{len(unassigned_textures)} texture(s) could not be auto-assigned:")
            for mat_name, tex_name in unassigned_textures[:5]:  # Limit to first 5
                self.report({'WARNING'}, f"  {mat_name}: {tex_name} - assign manually")
            if len(unassigned_textures) > 5:
                self.report({'WARNING'}, f"  ... and {len(unassigned_textures) - 5} more")

        # Final report
        if textures_assigned > 0:
            upgrade_msg = f"Upgraded {materials_upgraded} shader(s)" if materials_upgraded > 0 else ""
            self.report({'INFO'},
                f"Assigned {textures_assigned} texture slot(s) across {materials_processed} material(s). {upgrade_msg}")
        else:
            self.report({'INFO'}, f"Processed {materials_processed} material(s). No texture slot changes needed.")

        return {'FINISHED'}


class AC_SetupNormalMap(Operator):
    """Setup normal map for active material (auto-detect or create)"""
    bl_idname = "ac.setup_normal_map"
    bl_label = "Setup Normal Map"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.active_material

    def execute(self, context):
        material = context.active_object.active_material

        if not material.node_tree:
            self.report({'ERROR'}, "Material has no node tree")
            return {'CANCELLED'}

        # Find Principled BSDF
        principled = None
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        if not principled:
            self.report({'ERROR'}, "Material has no Principled BSDF node")
            return {'CANCELLED'}

        # Check if normal map already exists
        normal_map_node = None
        for link in principled.inputs['Normal'].links:
            if link.from_node.type == 'NORMAL_MAP':
                normal_map_node = link.from_node
                break

        # Find or create Normal Map node
        if not normal_map_node:
            normal_map_node = material.node_tree.nodes.new('ShaderNodeNormalMap')
            normal_map_node.location = (principled.location.x - 400, principled.location.y - 200)
            material.node_tree.links.new(normal_map_node.outputs['Normal'], principled.inputs['Normal'])
            self.report({'INFO'}, "Created Normal Map node")

        # Check if texture is already connected
        texture_node = None
        if normal_map_node.inputs['Color'].links:
            connected_node = normal_map_node.inputs['Color'].links[0].from_node
            if connected_node.type == 'TEX_IMAGE':
                texture_node = connected_node

        # If no texture connected, look for normal map texture in material
        if not texture_node:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    # Check if filename suggests it's a normal map
                    name_lower = node.image.name.lower()
                    if any(keyword in name_lower for keyword in ['normal', 'nrm', '_n.', '_n_']):
                        texture_node = node
                        break

        # Create or connect texture node
        if texture_node:
            # Connect if not already connected
            if not normal_map_node.inputs['Color'].links:
                material.node_tree.links.new(texture_node.outputs['Color'], normal_map_node.inputs['Color'])

            # Set AC texture slot
            texture_node.AC_Texture.shader_input_name = "txNormal"

            # Set correct color space
            texture_node.image.colorspace_settings.name = 'Non-Color'

            self.report({'INFO'}, f"Setup normal map: {texture_node.image.name} → txNormal")
        else:
            texture_node = material.node_tree.nodes.new('ShaderNodeTexImage')
            texture_node.location = (normal_map_node.location.x - 300, normal_map_node.location.y)
            texture_node.label = "Normal Map (txNormal)"
            material.node_tree.links.new(texture_node.outputs['Color'], normal_map_node.inputs['Color'])
            texture_node.AC_Texture.shader_input_name = "txNormal"

            self.report({'WARNING'}, "Created empty normal map texture node - assign an image")

        # Upgrade shader if needed
        ac_mat = material.AC_Material
        if ac_mat.shader_name == "ksPerPixel":
            ac_mat.shader_name = "ksPerPixelNM_UVMult"
            apply_shader_defaults(material, "ksPerPixelNM_UVMult")
            self.report({'INFO'}, "Upgraded material shader to ksPerPixelNM_UVMult with default properties")
        elif not ac_mat.shader_properties:
            # If no properties exist for current shader, apply defaults
            apply_shader_defaults(material, ac_mat.shader_name)
            self.report({'INFO'}, f"Applied default properties for {ac_mat.shader_name}")

        return {'FINISHED'}


class AC_ApplyShaderDefaults(Operator):
    """Apply default shader properties for current shader"""
    bl_idname = "ac.apply_shader_defaults"
    bl_label = "Apply Shader Defaults"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Works from either Properties panel or sidebar Material Editor
        if context.active_object and context.active_object.active_material:
            return True
        # Check sidebar material selector
        settings = context.scene.AC_Settings
        return 0 <= settings.active_material_index < len(bpy.data.materials)

    def execute(self, context):
        import bpy
        # Try to get material from active object first (Properties panel), then from active_material_index (sidebar)
        material = None
        if context.active_object and context.active_object.active_material:
            material = context.active_object.active_material
        else:
            settings = context.scene.AC_Settings
            if 0 <= settings.active_material_index < len(bpy.data.materials):
                material = bpy.data.materials[settings.active_material_index]

        if not material:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        ac_mat = material.AC_Material

        # Get current shader name
        shader_name = ac_mat.shader_name

        # Apply defaults
        apply_shader_defaults(material, shader_name)

        self.report({'INFO'}, f"Applied default properties for {shader_name}")
        return {'FINISHED'}


class AC_ResetShaderDefaults(Operator):
    """Reset shader properties to defaults (clears all and applies fresh defaults)"""
    bl_idname = "ac.reset_shader_defaults"
    bl_label = "Reset to Defaults"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Works from either Properties panel or sidebar Material Editor
        if context.active_object and context.active_object.active_material:
            return True
        # Check sidebar material selector
        settings = context.scene.AC_Settings
        return 0 <= settings.active_material_index < len(bpy.data.materials)

    def execute(self, context):
        import bpy
        # Try to get material from active object first (Properties panel), then from active_material_index (sidebar)
        material = None
        if context.active_object and context.active_object.active_material:
            material = context.active_object.active_material
        else:
            settings = context.scene.AC_Settings
            if 0 <= settings.active_material_index < len(bpy.data.materials):
                material = bpy.data.materials[settings.active_material_index]

        if not material:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        ac_mat = material.AC_Material

        # Clear all existing shader properties
        ac_mat.shader_properties.clear()
        ac_mat.shader_properties_active = -1

        # Get current shader name and apply fresh defaults
        shader_name = ac_mat.shader_name
        apply_shader_defaults(material, shader_name)

        self.report({'INFO'}, f"Reset properties to {shader_name} defaults")
        return {'FINISHED'}
