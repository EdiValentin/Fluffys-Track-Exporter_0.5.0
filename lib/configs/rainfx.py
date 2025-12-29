from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup


class AC_RainFX(PropertyGroup):
    """CSP RainFX configuration for track rain effects"""

    enabled: BoolProperty(
        name="Enable RainFX",
        description="Enable Custom Shaders Patch RainFX for this track",
        default=False,
    )

    puddles_materials: StringProperty(
        name="Puddles Materials",
        description="Materials where puddles form (comma-separated). Recommended for road surfaces only. Use ? as wildcard (e.g., ?ROAD?)",
        default="",
    )

    soaking_materials: StringProperty(
        name="Soaking Materials",
        description="Materials that get 70% darker when wet (comma-separated). Good for cloth roofs, track asphalt. Use ? as wildcard",
        default="",
    )

    smooth_materials: StringProperty(
        name="Smooth Materials",
        description="Materials with rain drops on top (comma-separated). Good for glass, cars, smooth metals. Use ? as wildcard",
        default="",
    )

    rough_materials: StringProperty(
        name="Rough Materials",
        description="Materials that get darker but no reflections (comma-separated). Required for grass surfaces. Use ? as wildcard",
        default="",
    )

    lines_materials: StringProperty(
        name="Lines Materials",
        description="Materials for paint lines on track surface (comma-separated). Affects physics (more slippery). Use ? as wildcard",
        default="",
    )

    lines_filter_materials: StringProperty(
        name="Lines Filter Materials",
        description="Filters brighter areas for track lines (comma-separated). Use ? as wildcard",
        default="",
    )

    def to_dict(self) -> dict:
        """Export RainFX settings to ext_config.ini format"""
        if not self.enabled:
            return {}

        data = {}
        if self.puddles_materials:
            data["PUDDLES_MATERIALS"] = self.puddles_materials
        if self.soaking_materials:
            data["SOAKING_MATERIALS"] = self.soaking_materials
        if self.smooth_materials:
            data["SMOOTH_MATERIALS"] = self.smooth_materials
        if self.rough_materials:
            data["ROUGH_MATERIALS"] = self.rough_materials
        if self.lines_materials:
            data["LINES_MATERIALS"] = self.lines_materials
        if self.lines_filter_materials:
            data["LINES_FILTER_MATERIALS"] = self.lines_filter_materials

        return data

    def from_dict(self, data: dict):
        """Load RainFX settings from ext_config.ini"""
        self.enabled = True
        self.puddles_materials = data.get("PUDDLES_MATERIALS", "")
        self.soaking_materials = data.get("SOAKING_MATERIALS", "")
        self.smooth_materials = data.get("SMOOTH_MATERIALS", "")
        self.rough_materials = data.get("ROUGH_MATERIALS", "")
        self.lines_materials = data.get("LINES_MATERIALS", "")
        self.lines_filter_materials = data.get("LINES_FILTER_MATERIALS", "")
