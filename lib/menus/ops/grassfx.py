"""Operators for managing GrassFX configuration."""

import bpy
from bpy.types import Operator
from ....utils.helpers import is_hidden_name


class AC_AddGrassFXMaterial(Operator):
    """Add selected material to GrassFX configuration"""

    bl_idname = "ac.add_grassfx_material"
    bl_label = "Add Material to GrassFX"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.active_material

    def execute(self, context):
        material = context.active_object.active_material
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Check if material is already in list
        existing_materials = [m.material_name for m in grassfx.materials]
        if material.name in existing_materials:
            self.report({'WARNING'}, f"Material '{material.name}' is already in GrassFX list")
            return {'CANCELLED'}

        # Add material
        mat_entry = grassfx.materials.add()
        mat_entry.material_name = material.name

        self.report({'INFO'}, f"Added '{material.name}' to GrassFX")
        return {'FINISHED'}


class AC_RemoveGrassFXMaterial(Operator):
    """Remove material from GrassFX configuration"""

    bl_idname = "ac.remove_grassfx_material"
    bl_label = "Remove Material from GrassFX"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Find and remove material
        for i, mat in enumerate(grassfx.materials):
            if mat.material_name == self.material_name:
                grassfx.materials.remove(i)
                self.report({'INFO'}, f"Removed '{self.material_name}' from GrassFX")
                return {'FINISHED'}

        self.report({'WARNING'}, f"Material '{self.material_name}' not found in GrassFX list")
        return {'CANCELLED'}


class AC_ClearGrassFXMaterials(Operator):
    """Clear all materials from GrassFX configuration"""

    bl_idname = "ac.clear_grassfx_materials"
    bl_label = "Clear All GrassFX Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        count = len(settings.grassfx.materials)
        settings.grassfx.materials.clear()

        self.report({'INFO'}, f"Cleared {count} material(s) from GrassFX")
        return {'FINISHED'}


class AC_AutoDetectGrassFXMaterials(Operator):
    """Automatically detect and add all ksGrass materials to GrassFX"""

    bl_idname = "ac.auto_detect_grassfx_materials"
    bl_label = "Auto-Detect Grass Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Get existing materials
        existing_materials = set(m.material_name for m in grassfx.materials)

        # Find all materials with ksGrass shader
        found_materials = []
        for mat in bpy.data.materials:
            if is_hidden_name(mat.name):
                continue
            if hasattr(mat, 'AC_Material') and mat.AC_Material.shader_name == "ksGrass":
                if mat.name not in existing_materials:
                    mat_entry = grassfx.materials.add()
                    mat_entry.material_name = mat.name
                    found_materials.append(mat.name)

        if found_materials:
            self.report({'INFO'}, f"Added {len(found_materials)} grass material(s) to GrassFX")
        else:
            self.report({'INFO'}, "No new ksGrass materials found")

        return {'FINISHED'}


class AC_AddOccludingMaterial(Operator):
    """Manually add material to occluding materials list (usually auto-populated)"""

    bl_idname = "ac.add_occluding_material"
    bl_label = "Add Occluding Material"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Manually add material to occluding list (auto-populated on export)"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.active_material

    def execute(self, context):
        material = context.active_object.active_material
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Check if material is already in list
        existing_materials = [m.material_name for m in grassfx.occluding_materials]
        if material.name in existing_materials:
            self.report({'WARNING'}, f"Material '{material.name}' is already in occluding list")
            return {'CANCELLED'}

        # Add material
        mat_entry = grassfx.occluding_materials.add()
        mat_entry.material_name = material.name

        self.report({'INFO'}, f"Added '{material.name}' as occluding material")
        return {'FINISHED'}


class AC_RemoveOccludingMaterial(Operator):
    """Remove material from occluding list"""

    bl_idname = "ac.remove_occluding_material"
    bl_label = "Remove Occluding Material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Find and remove material
        for i, mat in enumerate(grassfx.occluding_materials):
            if mat.material_name == self.material_name:
                grassfx.occluding_materials.remove(i)
                self.report({'INFO'}, f"Removed '{self.material_name}' from occluding materials")
                return {'FINISHED'}

        self.report({'WARNING'}, f"Material '{self.material_name}' not found in occluding list")
        return {'CANCELLED'}


class AC_ClearOccludingMaterials(Operator):
    """Clear all occluding materials"""

    bl_idname = "ac.clear_occluding_materials"
    bl_label = "Clear All Occluding Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.AC_Settings
        count = len(settings.grassfx.occluding_materials)
        settings.grassfx.occluding_materials.clear()

        self.report({'INFO'}, f"Cleared {count} occluding material(s)")
        return {'FINISHED'}
