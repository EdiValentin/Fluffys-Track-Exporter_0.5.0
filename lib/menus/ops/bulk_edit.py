"""
Bulk material editing operators for editing multiple materials at once.

Provides a two-step wizard:
1. Select materials to edit
2. Edit common shader properties across all selected materials
"""

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty


class AC_UL_BulkMaterials(bpy.types.UIList):
    """UIList for bulk material selection"""
    bl_idname = "AC_UL_BulkMaterials"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.prop(item, "selected", text="")
        row.label(text=item.name)


class AC_BulkEditSelectMaterials(Operator):
    """Select materials for bulk editing"""
    bl_idname = "ac.bulk_edit_select_materials"
    bl_label = "Bulk Edit Materials"
    bl_description = "Edit shader properties across multiple materials at once"
    bl_options = {'REGISTER', 'UNDO'}

    select_all: BoolProperty(
        name="Select All",
        description="Toggle all materials",
        default=False
    )

    def invoke(self, context, event):
        from ....utils.helpers import get_visible_materials

        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        # Clear and populate material list
        bulk.materials.clear()
        bulk.selected_material_names = ""

        visible_mats = get_visible_materials(context)
        for mat_name in sorted(visible_mats):
            item = bulk.materials.add()
            item.name = mat_name
            item.selected = False

        if not bulk.materials:
            self.report({'WARNING'}, "No visible materials found")
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        # Header with select all toggle
        row = layout.row()
        row.label(text=f"Select Materials ({len(bulk.materials)} available)")
        row.operator("ac.bulk_edit_toggle_all", text="", icon='CHECKBOX_HLT')
        row.operator("ac.bulk_edit_toggle_none", text="", icon='CHECKBOX_DEHLT')

        # Material list
        box = layout.box()
        col = box.column(align=True)

        # Show scrollable list
        for item in bulk.materials:
            row = col.row(align=True)
            row.prop(item, "selected", text="")
            row.label(text=item.name)

        # Selection count
        selected_count = sum(1 for m in bulk.materials if m.selected)
        layout.label(text=f"{selected_count} material(s) selected")

    def execute(self, context):
        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        # Collect selected material names
        selected = [m.name for m in bulk.materials if m.selected]

        if not selected:
            self.report({'WARNING'}, "No materials selected")
            return {'CANCELLED'}

        # Store selected names
        bulk.selected_material_names = "|".join(selected)

        # Launch the property editor
        bpy.ops.ac.bulk_edit_properties('INVOKE_DEFAULT')
        return {'FINISHED'}


class AC_BulkEditToggleAll(Operator):
    """Select all materials"""
    bl_idname = "ac.bulk_edit_toggle_all"
    bl_label = "Select All"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        for item in settings.bulk_edit.materials:
            item.selected = True
        return {'FINISHED'}


class AC_BulkEditToggleNone(Operator):
    """Deselect all materials"""
    bl_idname = "ac.bulk_edit_toggle_none"
    bl_label = "Select None"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        for item in settings.bulk_edit.materials:
            item.selected = False
        return {'FINISHED'}


def find_common_properties(material_names: list) -> dict:
    """
    Find shader properties common to all specified materials.

    Args:
        material_names: List of material names to check

    Returns:
        Dict of property_name -> {type, default_value} for common properties
    """
    import bpy

    if not material_names:
        return {}

    # Build property sets for each material
    property_sets = []
    property_info = {}  # name -> {type, values from first material}

    for mat_name in material_names:
        mat = bpy.data.materials.get(mat_name)
        if not mat or not hasattr(mat, 'AC_Material'):
            continue

        ac_mat = mat.AC_Material
        mat_props = {}

        for prop in ac_mat.shader_properties:
            mat_props[prop.name] = prop.property_type
            # Store info from first material for default values
            if prop.name not in property_info:
                property_info[prop.name] = {
                    'type': prop.property_type,
                    'valueA': prop.valueA,
                    'valueB': tuple(prop.valueB),
                    'valueC': tuple(prop.valueC),
                    'valueD': tuple(prop.valueD),
                }

        property_sets.append(set(mat_props.keys()))

    if not property_sets:
        return {}

    # Find intersection of all property names
    common_names = property_sets[0]
    for prop_set in property_sets[1:]:
        common_names = common_names.intersection(prop_set)

    # Return common properties with their info
    result = {}
    for name in common_names:
        if name in property_info:
            result[name] = property_info[name]

    return result


class AC_BulkEditProperties(Operator):
    """Edit common properties across selected materials"""
    bl_idname = "ac.bulk_edit_properties"
    bl_label = "Edit Common Properties"
    bl_description = "Edit shader properties shared by all selected materials"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        # Get selected material names
        if not bulk.selected_material_names:
            self.report({'ERROR'}, "No materials selected")
            return {'CANCELLED'}

        material_names = bulk.selected_material_names.split("|")

        # Find common properties
        common = find_common_properties(material_names)

        if not common:
            self.report({'WARNING'}, "No common shader properties found among selected materials")
            return {'CANCELLED'}

        # Populate common properties collection
        bulk.common_properties.clear()
        for name, info in sorted(common.items()):
            prop = bulk.common_properties.add()
            prop.name = name
            prop.property_type = info['type']
            prop.valueA = info['valueA']
            prop.valueB = info['valueB']
            prop.valueC = info['valueC']
            prop.valueD = info['valueD']

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        material_names = bulk.selected_material_names.split("|")

        layout.label(text=f"Editing {len(material_names)} materials")
        layout.label(text=f"{len(bulk.common_properties)} common properties found")
        layout.separator()

        # Property editors
        box = layout.box()
        for prop in bulk.common_properties:
            row = box.row(align=True)
            row.label(text=prop.name)

            if prop.property_type == "float":
                row.prop(prop, "valueA", text="")
            elif prop.property_type == "vec2":
                row.prop(prop, "valueB", text="")
            elif prop.property_type == "vec3":
                row.prop(prop, "valueC", text="")
            elif prop.property_type == "vec4":
                row.prop(prop, "valueD", text="")

    def execute(self, context):
        settings = context.scene.AC_Settings
        bulk = settings.bulk_edit

        material_names = bulk.selected_material_names.split("|")
        updated_count = 0

        for mat_name in material_names:
            mat = bpy.data.materials.get(mat_name)
            if not mat or not hasattr(mat, 'AC_Material'):
                continue

            ac_mat = mat.AC_Material

            # Update each common property
            for bulk_prop in bulk.common_properties:
                # Find matching property in material
                for mat_prop in ac_mat.shader_properties:
                    if mat_prop.name == bulk_prop.name:
                        # Copy values based on type
                        if bulk_prop.property_type == "float":
                            mat_prop.valueA = bulk_prop.valueA
                        elif bulk_prop.property_type == "vec2":
                            mat_prop.valueB = bulk_prop.valueB
                        elif bulk_prop.property_type == "vec3":
                            mat_prop.valueC = bulk_prop.valueC
                        elif bulk_prop.property_type == "vec4":
                            mat_prop.valueD = bulk_prop.valueD
                        break

            updated_count += 1

        self.report({'INFO'}, f"Updated {len(bulk.common_properties)} properties on {updated_count} materials")
        return {'FINISHED'}


# Classes to register (PropertyGroups are in lib/configs/bulk_edit.py)
classes = (
    AC_UL_BulkMaterials,
    AC_BulkEditSelectMaterials,
    AC_BulkEditToggleAll,
    AC_BulkEditToggleNone,
    AC_BulkEditProperties,
)
