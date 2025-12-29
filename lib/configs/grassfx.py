"""GrassFX configuration for Custom Shaders Patch (CSP)."""

import bpy
from bpy.props import BoolProperty, CollectionProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from ...utils.helpers import is_hidden_name


class AC_GrassFXMaterial(PropertyGroup):
    """Individual grass material entry for GRASS_FX section."""

    material_name: StringProperty(
        name="Material Name",
        description="Name of the material to spawn grass on",
        default="",
    )


class AC_GrassFXOccludingMaterial(PropertyGroup):
    """Individual occluding material entry - prevents grass spawning on surfaces with this material."""

    material_name: StringProperty(
        name="Material Name",
        description="Name of the material that blocks grass spawning",
        default="",
    )


class AC_GrassFX(PropertyGroup):
    """GrassFX configuration for CSP."""

    materials: CollectionProperty(
        type=AC_GrassFXMaterial,
        name="Grass Materials",
        description="List of materials to spawn grass on",
    )

    materials_index: IntProperty(
        name="Active Material Index",
        description="Index of the currently selected grass material",
        default=0,
    )

    occluding_materials: CollectionProperty(
        type=AC_GrassFXOccludingMaterial,
        name="Occluding Materials",
        description="List of materials that prevent grass from spawning (auto-populated on export)",
    )

    # Mask settings
    mask_main_threshold: FloatProperty(
        name="Green Saturation",
        description="Green saturation level required for grass spawning",
        default=0.5,
        min=0.0,
        max=1.0,
    )

    mask_red_threshold: FloatProperty(
        name="Color Offset",
        description="Color offset tolerance for grass spawning",
        default=0.05,
        min=0.0,
        max=1.0,
    )

    mask_min_luminance: FloatProperty(
        name="Min Brightness",
        description="Minimum surface brightness for grass spawning",
        default=0.02,
        min=0.0,
        max=1.0,
    )

    mask_max_luminance: FloatProperty(
        name="Max Brightness",
        description="Maximum surface brightness for grass spawning",
        default=0.35,
        min=0.0,
        max=1.0,
    )

    # Shape settings
    shape_size: FloatProperty(
        name="Size",
        description="Overall grass size/density",
        default=1.0,
        min=0.0,
        max=5.0,
    )

    shape_tidy: FloatProperty(
        name="Uniformity",
        description="Grass uniformity (0=random, 1=uniform)",
        default=0.0,
        min=0.0,
        max=1.0,
    )

    shape_cut: FloatProperty(
        name="Trim Level",
        description="How trimmed the grass appears (0=wild, 1=mowed)",
        default=0.0,
        min=0.0,
        max=1.0,
    )

    shape_width: FloatProperty(
        name="Width",
        description="Grass width relative to height",
        default=1.0,
        min=0.0,
        max=2.0,
    )

    show_settings: BoolProperty(
        name="Show Settings",
        description="Show/hide advanced grass settings",
        default=False,
    )

    def to_dict(self) -> dict:
        """Convert GrassFX settings to dictionary for INI export.

        Automatically populates OCCLUDING_MATERIALS with all scene materials
        that are NOT in the grass materials list.
        """
        if not self.materials:
            return {}

        # Build comma-separated list of grass material names
        grass_material_names = [mat.material_name for mat in self.materials]
        grass_materials_str = ", ".join(grass_material_names)

        # Auto-detect occluding materials (all scene materials except grass materials)
        occluding_materials = []
        import bpy
        for mat in bpy.data.materials:
            # Skip hidden/excluded materials
            if is_hidden_name(mat.name):
                continue
            # Skip grass materials
            if mat.name in grass_material_names:
                continue
            # Check if material is actually used in the scene
            if mat.users > 0:
                occluding_materials.append(mat.name)

        result = {
            "GRASS_FX": {
                "GRASS_MATERIALS": grass_materials_str,
                "MASK_MAIN_THRESHOLD": str(self.mask_main_threshold),
                "MASK_RED_THRESHOLD": str(self.mask_red_threshold),
                "MASK_MIN_LUMINANCE": str(self.mask_min_luminance),
                "MASK_MAX_LUMINANCE": str(self.mask_max_luminance),
                "SHAPE_SIZE": str(self.shape_size),
                "SHAPE_TIDY": str(self.shape_tidy),
                "SHAPE_CUT": str(self.shape_cut),
                "SHAPE_WIDTH": str(self.shape_width),
            }
        }

        # Add occluding materials if any were found
        if occluding_materials:
            result["GRASS_FX"]["OCCLUDING_MATERIALS"] = ", ".join(occluding_materials)

        return result

    def from_dict(self, data: dict):
        """Load GrassFX settings from dictionary."""
        # Parse grass material list
        if "GRASS_MATERIALS" in data:
            self.materials.clear()
            materials_str = data["GRASS_MATERIALS"]
            if materials_str:
                for mat_name in materials_str.split(","):
                    mat_name = mat_name.strip()
                    if mat_name:
                        mat_entry = self.materials.add()
                        mat_entry.material_name = mat_name

        # Parse occluding materials (auto-populated on export, stored for reference)
        self.occluding_materials.clear()
        if "OCCLUDING_MATERIALS" in data:
            materials_str = data["OCCLUDING_MATERIALS"]
            if materials_str:
                for mat_name in materials_str.split(","):
                    mat_name = mat_name.strip()
                    if mat_name:
                        mat_entry = self.occluding_materials.add()
                        mat_entry.material_name = mat_name

        # Load settings with fallbacks
        if "MASK_MAIN_THRESHOLD" in data:
            self.mask_main_threshold = float(data["MASK_MAIN_THRESHOLD"])
        if "MASK_RED_THRESHOLD" in data:
            self.mask_red_threshold = float(data["MASK_RED_THRESHOLD"])
        if "MASK_MIN_LUMINANCE" in data:
            self.mask_min_luminance = float(data["MASK_MIN_LUMINANCE"])
        if "MASK_MAX_LUMINANCE" in data:
            self.mask_max_luminance = float(data["MASK_MAX_LUMINANCE"])
        if "SHAPE_SIZE" in data:
            self.shape_size = float(data["SHAPE_SIZE"])
        if "SHAPE_TIDY" in data:
            self.shape_tidy = float(data["SHAPE_TIDY"])
        if "SHAPE_CUT" in data:
            self.shape_cut = float(data["SHAPE_CUT"])
        if "SHAPE_WIDTH" in data:
            self.shape_width = float(data["SHAPE_WIDTH"])
