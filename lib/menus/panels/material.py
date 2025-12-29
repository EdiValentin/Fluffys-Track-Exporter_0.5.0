"""Material properties panel for Assetto Corsa KN5 export."""

from bpy.types import Operator, Panel, UIList


class AC_UL_ShaderProperties(UIList):
    """UI List for shader properties."""

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, "name", text="", emboss=False)


class PROPERTIES_PT_AC_Material(Panel):
    """Material properties panel in Properties context."""

    bl_label = "Assetto Corsa"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        material = context.material
        ac_mat = material.AC_Material

        # Shader settings
        row = layout.row(align=True)
        row.prop(ac_mat, "shader_name")
        row.operator("ac.apply_shader_defaults", text="", icon='FILE_REFRESH')
        layout.prop(ac_mat, "alpha_blend_mode")
        layout.prop(ac_mat, "alpha_tested")
        layout.prop(ac_mat, "depth_mode")

        # Shader properties list
        box = layout.box()
        box.label(text="Shader Properties")

        if ac_mat.shader_properties:
            box.template_list(
                "AC_UL_ShaderProperties",
                "",
                ac_mat,
                "shader_properties",
                ac_mat,
                "shader_properties_active",
                rows=3
            )

            # Show active property editor
            if 0 <= ac_mat.shader_properties_active < len(ac_mat.shader_properties):
                active_prop = ac_mat.shader_properties[ac_mat.shader_properties_active]
                col = box.column(align=True)
                col.prop(active_prop, "name")
                col.prop(active_prop, "property_type")
                col.separator()

                # Display appropriate value field based on property type
                prop_type = active_prop.property_type
                if prop_type == "float":
                    col.prop(active_prop, "valueA", text="Value")
                elif prop_type == "vec2":
                    col.prop(active_prop, "valueB", text="Value (X, Y)")
                elif prop_type == "vec3":
                    col.prop(active_prop, "valueC", text="Value (X, Y, Z)")
                elif prop_type == "vec4":
                    col.prop(active_prop, "valueD", text="Value (X, Y, Z, W)")

        # Add/Remove buttons
        row = box.row()
        row.operator("ac.add_shader_property", icon='ADD')
        row.operator("ac.remove_shader_property", icon='REMOVE')


class AC_AddShaderProperty(Operator):
    """Add shader property to material"""

    bl_idname = "ac.add_shader_property"
    bl_label = "Add Shader Property"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Check if there's a material available either from context.material (Properties panel)
        # or from active_material_index (sidebar)
        import bpy
        if getattr(context, 'material', None):
            return True
        settings = context.scene.AC_Settings
        if 0 <= settings.active_material_index < len(bpy.data.materials):
            return True
        return False

    def execute(self, context):
        import bpy
        # Try to get material from context first (Properties panel), then from active_material_index (sidebar)
        material = getattr(context, 'material', None)
        if not material:
            settings = context.scene.AC_Settings
            if 0 <= settings.active_material_index < len(bpy.data.materials):
                material = bpy.data.materials[settings.active_material_index]

        if not material:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        ac_mat = material.AC_Material
        prop = ac_mat.shader_properties.add()
        prop.name = "ksProperty"
        ac_mat.shader_properties_active = len(ac_mat.shader_properties) - 1
        return {'FINISHED'}


class AC_RemoveShaderProperty(Operator):
    """Remove shader property from material"""

    bl_idname = "ac.remove_shader_property"
    bl_label = "Remove Shader Property"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Check if there's a material available either from context.material (Properties panel)
        # or from active_material_index (sidebar)
        import bpy
        if getattr(context, 'material', None):
            return True
        settings = context.scene.AC_Settings
        if 0 <= settings.active_material_index < len(bpy.data.materials):
            return True
        return False

    def execute(self, context):
        import bpy
        # Try to get material from context first (Properties panel), then from active_material_index (sidebar)
        material = getattr(context, 'material', None)
        if not material:
            settings = context.scene.AC_Settings
            if 0 <= settings.active_material_index < len(bpy.data.materials):
                material = bpy.data.materials[settings.active_material_index]

        if not material:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        ac_mat = material.AC_Material
        if 0 <= ac_mat.shader_properties_active < len(ac_mat.shader_properties):
            ac_mat.shader_properties.remove(ac_mat.shader_properties_active)
            ac_mat.shader_properties_active = max(0, ac_mat.shader_properties_active - 1)
        return {'FINISHED'}
