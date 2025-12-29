"""Material PropertyGroups for KN5 export."""

from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, FloatVectorProperty, IntProperty,
                       StringProperty)
from bpy.types import PropertyGroup

from ...kn5.shader_defaults import get_shader_list


class AC_ShaderProperty(PropertyGroup):
    """Shader property with up to 4 component values."""

    name: StringProperty(
        name="Property Name",
        description="Shader property name (e.g., ksDiffuse, ksAmbient)",
        default="ksDiffuse",
    )
    property_type: EnumProperty(
        name="Property Type",
        description="Type of shader property (determines which value field to use)",
        items=[
            ("float", "Float", "Single scalar value (valueA)"),
            ("vec2", "Vector2", "2-component vector (valueB)"),
            ("vec3", "Vector3", "3-component vector (valueC)"),
            ("vec4", "Vector4", "4-component vector (valueD)"),
        ],
        default="float",
    )
    valueA: FloatProperty(
        name="Value A",
        description="Single float value (used when property_type='float')",
        default=0.0,
        min=0.0,
        max=1000.0,
        soft_min=0.0,
        soft_max=100.0,
    )
    valueB: FloatVectorProperty(
        name="Value B",
        description="2-component vector (used when property_type='vec2')",
        size=2,
        default=(0.0, 0.0),
    )
    valueC: FloatVectorProperty(
        name="Value C",
        description="3-component vector (used when property_type='vec3')",
        size=3,
        default=(0.0, 0.0, 0.0),
    )
    valueD: FloatVectorProperty(
        name="Value D",
        description="4-component vector (used when property_type='vec4')",
        size=4,
        default=(0.0, 0.0, 0.0, 0.0),
    )


class AC_MaterialSettings(PropertyGroup):
    """Assetto Corsa material settings for KN5 export."""

    shader_name: EnumProperty(
        name="Shader",
        description="AC shader to use for this material",
        items=get_shader_list,
        default=0,
    )
    alpha_blend_mode: EnumProperty(
        name="Alpha Blend Mode",
        description="How to handle alpha blending",
        items=[
            ("0", "Opaque", "No transparency"),
            ("1", "Alpha Blend", "Standard alpha blending"),
            ("2", "Alpha to Coverage", "MSAA-based transparency"),
        ],
        default="0",
    )
    alpha_tested: BoolProperty(
        name="Alpha Tested",
        description="Enable alpha testing (cutout transparency)",
        default=False,
    )
    depth_mode: EnumProperty(
        name="Depth Mode",
        description="Depth buffer write mode",
        items=[
            ("0", "Depth Normal", "Normal depth writing"),
            ("1", "Depth No Write", "Read depth but don't write"),
            ("2", "Depth Off", "No depth testing"),
        ],
        default="0",
    )
    shader_properties: CollectionProperty(
        type=AC_ShaderProperty,
        name="Shader Properties",
        description="Material shader properties (ksDiffuse, ksAmbient, etc.)",
    )
    shader_properties_active: IntProperty(
        name="Active Shader Property",
        description="Active property in the list",
        default=-1,
    )
