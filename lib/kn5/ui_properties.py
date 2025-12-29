# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2014  Thomas Hagnhofer


import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from .constants import MATERIAL_BLEND_MODES, MATERIAL_DEPTH_MODES


def convert_dict_to_blender_enum(dictionary: dict):
    items = []
    for key in dictionary:
        val = str(dictionary[key])
        items.append((val, key, val))
    return items


# ===== OBJECT PROPERTIES =====

class NodeProperties(bpy.types.PropertyGroup):
    lodIn: FloatProperty(
        name="LOD In",
        min=0.0,
        unit="LENGTH",
        subtype="DISTANCE",
        description="Nearest distance to the object until it disappears")
    lodOut: FloatProperty(
        name="LOD Out",
        min=0.0,
        unit="LENGTH",
        subtype="DISTANCE",
        description="Farthest distance to the object until it disappears")
    layer: IntProperty(
        name="Layer",
        default=0,
        description="Unknown behaviour")
    castShadows: BoolProperty(
        name="Cast Shadows",
        default=True)
    visible: BoolProperty(
        name="Visible",
        default=True,
        description="Unknown behaviour")
    transparent: BoolProperty(
        name="Transparent",
        default=False)
    renderable: BoolProperty(
        name="Renderable",
        default=True,
        description="Toggles if the object should be rendered or not")


class KN5_PT_NodePanel(bpy.types.Panel):
    bl_label = "Assetto Corsa"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type in ["MESH", "CURVE"]

    def draw(self, context):
        ac_obj = context.object.AC_KN5
        self.layout.prop(ac_obj, "renderable")
        self.layout.prop(ac_obj, "cast_shadows")
        self.layout.prop(ac_obj, "transparent")
        self.layout.prop(ac_obj, "lod_in")
        self.layout.prop(ac_obj, "lod_out")
        self.layout.prop(ac_obj, "visible")


# ===== MATERIAL PROPERTIES =====

class MaterialProperties(bpy.types.PropertyGroup):
    shaderName: StringProperty(
        name="Shader Name",
        default="ksPerPixel")
    alphaBlendMode: EnumProperty(
        name="Alpha Blend Mode",
        items=convert_dict_to_blender_enum(MATERIAL_BLEND_MODES),
        default=str(MATERIAL_BLEND_MODES["Opaque"]))
    alphaTested: BoolProperty(
        name="Alpha Tested",
        default=False)
    depthMode: EnumProperty(
        name="Depth Mode",
        items=convert_dict_to_blender_enum(MATERIAL_DEPTH_MODES),
        default=str(MATERIAL_DEPTH_MODES["DepthNormal"]))


# ===== TEXTURE PROPERTIES =====

class TextureProperties(bpy.types.PropertyGroup):
    shaderInputName: StringProperty(
        name="Shader Input Name",
        default="txDiffuse",
        description="Name of the shader input slot the texture should be assigned to")


class KN5_PT_TexturePanel(bpy.types.Panel):
    bl_label = "Assetto Corsa"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Assetto Corsa"

    @classmethod
    def poll(cls, context):
        if len(context.selected_nodes) == 1:
            return isinstance(context.selected_nodes[0], bpy.types.ShaderNodeTexImage)
        return False

    def draw(self, context):
        ac_node = context.selected_nodes[0].AC_Texture
        self.layout.prop(ac_node, "shader_input_name")
