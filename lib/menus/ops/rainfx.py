import re

import bpy
from bpy.types import Operator
from ....utils.helpers import is_hidden_name


class AC_AutoDetectRainFXMaterials(Operator):
    """Automatically detect and categorize materials for RainFX based on naming patterns"""

    bl_idname = "ac.autodetect_rainfx_materials"
    bl_label = "Auto-Detect Materials"
    bl_description = "Scan scene materials and automatically suggest RainFX categories based on naming patterns"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.AC_Settings
        rainfx = settings.rainfx

        # Material categorization patterns
        puddles_patterns = [
            r"(?i).*road.*",
            r"(?i).*asphalt.*",
            r"(?i).*tarmac.*",
            r"(?i).*track.*",
        ]

        soaking_patterns = [
            r"(?i).*road.*",
            r"(?i).*asphalt.*",
            r"(?i).*tarmac.*",
            r"(?i).*track.*",
            r"(?i).*curb.*",
            r"(?i).*kerb.*",
            r"(?i).*cloth.*",
            r"(?i).*fabric.*",
        ]

        smooth_patterns = [
            r"(?i).*glass.*",
            r"(?i).*metal.*",
            r"(?i).*chrome.*",
            r"(?i).*car.*",
            r"(?i).*window.*",
            r"(?i).*mirror.*",
        ]

        rough_patterns = [
            r"(?i).*grass.*",
            r"(?i).*tree.*",
            r"(?i).*vegetation.*",
            r"(?i).*foliage.*",
            r"(?i).*bush.*",
            r"(?i).*leaves.*",
            r"(?i).*ground.*",
            r"(?i).*dirt.*",
            r"(?i).*sand.*",
            r"(?i).*gravel.*",
        ]

        lines_patterns = [
            r"(?i).*line.*",
            r"(?i).*paint.*",
            r"(?i).*stripe.*",
            r"(?i).*marking.*",
            r"(?i).*white.*line.*",
            r"(?i).*yellow.*line.*",
        ]

        # Collect materials from scene objects (not hidden)
        scene_materials = set()
        for obj in context.scene.objects:
            if is_hidden_name(obj.name):
                continue
            if hasattr(obj, "material_slots"):
                for slot in obj.material_slots:
                    if slot.material and not is_hidden_name(slot.material.name):
                        scene_materials.add(slot.material)

        # Categorize materials
        categorized = {
            "puddles": set(),
            "soaking": set(),
            "smooth": set(),
            "rough": set(),
            "lines": set(),
        }

        for material in scene_materials:
            mat_name = material.name

            # Check each category
            for pattern in puddles_patterns:
                if re.match(pattern, mat_name):
                    categorized["puddles"].add(mat_name)
                    break

            for pattern in soaking_patterns:
                if re.match(pattern, mat_name):
                    categorized["soaking"].add(mat_name)
                    break

            for pattern in smooth_patterns:
                if re.match(pattern, mat_name):
                    categorized["smooth"].add(mat_name)
                    break

            for pattern in rough_patterns:
                if re.match(pattern, mat_name):
                    categorized["rough"].add(mat_name)
                    break

            for pattern in lines_patterns:
                if re.match(pattern, mat_name):
                    categorized["lines"].add(mat_name)
                    break

        # Merge auto-detected materials with existing user input (don't overwrite!)
        def merge_materials(existing: str, detected: set) -> str:
            """Merge detected materials with existing ones, preserving user input"""
            # Parse existing materials
            existing_set = set()
            if existing.strip():
                existing_set = {mat.strip() for mat in existing.split(",") if mat.strip()}

            # Merge with detected materials
            merged = existing_set | detected

            # Return sorted comma-separated list
            return ", ".join(sorted(merged)) if merged else existing

        # Update RainFX settings by merging (not replacing)
        if categorized["puddles"]:
            rainfx.puddles_materials = merge_materials(rainfx.puddles_materials, categorized["puddles"])

        if categorized["soaking"]:
            rainfx.soaking_materials = merge_materials(rainfx.soaking_materials, categorized["soaking"])

        if categorized["smooth"]:
            rainfx.smooth_materials = merge_materials(rainfx.smooth_materials, categorized["smooth"])

        if categorized["rough"]:
            rainfx.rough_materials = merge_materials(rainfx.rough_materials, categorized["rough"])

        if categorized["lines"]:
            rainfx.lines_materials = merge_materials(rainfx.lines_materials, categorized["lines"])

        # Report results
        total_detected = sum(len(v) for v in categorized.values())
        if total_detected == 0:
            self.report(
                {"WARNING"},
                "No materials detected for RainFX. Try renaming materials with keywords like 'road', 'grass', 'glass', etc.",
            )
        else:
            self.report(
                {"INFO"},
                f"Detected {total_detected} materials across {sum(1 for v in categorized.values() if v)} categories",
            )

        return {"FINISHED"}


class AC_ClearRainFXMaterials(Operator):
    """Clear all RainFX material assignments"""

    bl_idname = "ac.clear_rainfx_materials"
    bl_label = "Clear All Materials"
    bl_description = "Clear all RainFX material assignments"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.AC_Settings
        rainfx = settings.rainfx

        rainfx.puddles_materials = ""
        rainfx.soaking_materials = ""
        rainfx.smooth_materials = ""
        rainfx.rough_materials = ""
        rainfx.lines_materials = ""
        rainfx.lines_filter_materials = ""

        self.report({"INFO"}, "Cleared all RainFX material assignments")
        return {"FINISHED"}


class AC_ToggleRainFX(Operator):
    """Toggle RainFX on/off"""

    bl_idname = "ac.toggle_rainfx"
    bl_label = "Toggle RainFX"
    bl_description = "Enable or disable RainFX for this track"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.AC_Settings
        rainfx = settings.rainfx
        rainfx.enabled = not rainfx.enabled

        status = "enabled" if rainfx.enabled else "disabled"
        self.report({"INFO"}, f"RainFX {status}")
        return {"FINISHED"}
