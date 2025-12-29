"""
PropertyGroups for bulk material editing.

These are separated from the operators to avoid circular import issues,
since AC_Settings needs to reference AC_BulkEditSettings.
"""

from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)


class AC_BulkMaterialItem(PropertyGroup):
    """Single material entry in bulk edit selection list"""
    name: StringProperty(name="Material Name")
    selected: BoolProperty(name="Selected", default=False)


class AC_BulkPropertyValue(PropertyGroup):
    """Editable property value for bulk editing"""
    name: StringProperty(name="Property Name")
    property_type: StringProperty(name="Type")  # float, vec2, vec3, vec4
    valueA: FloatProperty(name="Value", default=0.0, precision=4)
    valueB: FloatVectorProperty(name="Value", size=2, default=(0.0, 0.0), precision=4)
    valueC: FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0), precision=4)
    valueD: FloatVectorProperty(name="Value", size=4, default=(0.0, 0.0, 0.0, 0.0), precision=4)


class AC_BulkEditSettings(PropertyGroup):
    """Settings for bulk material editing workflow"""
    materials: CollectionProperty(type=AC_BulkMaterialItem)
    materials_index: IntProperty(default=0)
    selected_material_names: StringProperty(
        description="Pipe-separated list of selected material names"
    )
    common_properties: CollectionProperty(type=AC_BulkPropertyValue)
    common_properties_index: IntProperty(default=0)
