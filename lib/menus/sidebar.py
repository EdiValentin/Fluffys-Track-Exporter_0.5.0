"""
Improved sidebar panels for AC Track Tools with phase-based workflow.
Combines new workflow panels with existing Extra subpanels.
"""

import bpy
import os
from bpy.types import Context, Operator, Panel, UILayout, UIList

from ..settings import AC_Settings
from .panels.material import AC_UL_ShaderProperties

__all__ = [
    # Operators
    'AC_ClearMaterialSearch',
    # UILists
    'AC_UL_Tags',
    'AC_UL_Extensions',
    'AC_UL_SurfaceExtensions',
    'AC_UL_GrassFXMaterials',
    'AC_UL_Materials',
    'AC_UL_Lights',
    'AC_UL_EmissiveMaterials',
    # New panels
    'VIEW3D_PT_AC_Setup',
    'VIEW3D_PT_AC_SurfaceTools',
    'VIEW3D_PT_AC_Surfaces',
    'VIEW3D_PT_AC_Objects',
    'VIEW3D_PT_AC_Export',
    'VIEW3D_PT_AC_TrackImages',
    # Extra parent and subpanels
    'VIEW3D_PT_AC_Sidebar_Extra',
    'VIEW3D_PT_AC_Sidebar_GrassFX',
    'VIEW3D_PT_AC_Sidebar_RainFX',
    'VIEW3D_PT_AC_Sidebar_TreeFX',
    'VIEW3D_PT_AC_Sidebar_AILines',
    'VIEW3D_PT_AC_Sidebar_CSPLights',
    'VIEW3D_PT_AC_Sidebar_EmissiveMaterials',
    # Material editor
    'VIEW3D_PT_AC_MaterialEditor',
    'VIEW3D_PT_AC_MaterialProperties',
    'VIEW3D_PT_AC_ShaderProperties',
]


# ============================================================================
# UILists (unchanged from original)
# ============================================================================

class AC_UL_Tags(UIList):
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.row()
        row.prop(item, "value", text="", emboss=False)
        if active_property == "tags_index":
            delete = row.operator("ac.remove_tag", text="", icon="X")
            delete.index = index
        if active_property == "geotags_index":
            delete = row.operator("ac.remove_geo_tag", text="", icon="X")
            delete.index = index

    def draw_filter(self, context: Context, layout: UILayout):
        pass


class AC_UL_Extensions(UIList):
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.row()
        attr = row.split(factor=0.3)
        attr.prop(item, "key", text="", emboss=False)
        sub = attr.row()
        sub.prop(item, "value", text="", emboss=False)
        delete = row.operator("ac.global_remove_extension_item", text="", icon="X")
        delete.ext_index = int(self.list_id.split("-")[-1])
        delete.item_index = index

    def draw_filter(self, context, layout):
        pass


class AC_UL_SurfaceExtensions(UIList):
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.split(factor=0.3)
        row.prop(item, "key", text="", emboss=False)
        sub = row.row()
        sub.prop(item, "value", text="", emboss=False)
        delete = sub.operator("ac.delete_surface_ext", text="", icon="X")
        delete.extension = data.name
        delete.index = index

    def draw_filter(self, context, layout):
        pass


class AC_UL_GrassFXMaterials(UIList):
    """UIList for GrassFX materials"""
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.row()
        row.label(text=item.material_name, icon="MATSHADERBALL")
        delete = row.operator("ac.remove_grassfx_material", text="", icon="X")
        delete.material_name = item.material_name

    def draw_filter(self, context, layout):
        pass


class AC_UL_Lights(UIList):
    """UIList for CSP Lights"""
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.row(align=True)

        # Active toggle
        row.prop(item, "active", text="", icon="OUTLINER_OB_LIGHT" if item.active else "LIGHT_DATA")

        # Light name/description
        row.prop(item, "description", text="", emboss=False)

        # Select button - selects this light in viewport
        if item.linked_object:
            op = row.operator("ac.select_light_object", text="", icon="RESTRICT_SELECT_OFF", emboss=False)
            op.index = index

        # Remove button
        op = row.operator("ac.remove_light", text="", icon="X", emboss=False)
        op.index = index

    def draw_filter(self, context, layout):
        pass


class AC_UL_EmissiveMaterials(UIList):
    """UIList for CSP Emissive Materials (MATERIAL_ADJUSTMENT sections)"""
    layout_type = "COMPACT"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_property, index
    ):
        row = layout.row(align=True)

        # Active toggle
        row.prop(item, "active", text="", icon="SHADING_RENDERED" if item.active else "SHADING_SOLID")

        # Material name
        if item.material:
            row.label(text=item.material.name, icon="MATERIAL")
        else:
            row.label(text=item.description or "No Material", icon="ERROR")

        # Mesh filter indicator (small icon if mesh filter is active)
        if item.use_mesh_filter and item.mesh:
            row.label(text="", icon="MESH_DATA")

        # Select button - selects objects using this material
        if item.material:
            op = row.operator("ac.select_emissive_object", text="", icon="RESTRICT_SELECT_OFF", emboss=False)
            op.index = index

        # Remove button
        op = row.operator("ac.remove_emissive_material", text="", icon="X", emboss=False)
        op.index = index

    def draw_filter(self, context, layout):
        pass


# ============================================================================
# Base Panel Class
# ============================================================================

class VIEW3D_PT_AC_Sidebar:
    """Base class for all AC sidebar panels"""
    bl_label = "Assetto Corsa Configurator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"


# ============================================================================
# MAIN PANELS (numbered workflow)
# ============================================================================

class VIEW3D_PT_AC_Setup(VIEW3D_PT_AC_Sidebar, Panel):
    """PHASE 1: Setup - Working directory and track metadata"""
    bl_label = "1. Setup"
    bl_idname = "VIEW3D_PT_AC_Setup"
    bl_context = "objectmode"
    bl_order = 0
    bl_options = set()  # Always open

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings
        track = settings.track

        # Working Directory
        box = layout.box()
        box.label(text="Working Directory", icon="FILE_FOLDER")
        box.prop(settings, "working_dir", text="")

        has_working_dir = bool(settings.working_dir)

        # Info
        if not has_working_dir:
            info = box.row()
            info.label(text="Set directory to begin", icon="INFO")
            return  # Don't show rest until directory set

        layout.separator()

        # Track Metadata - Single column layout
        box = layout.box()
        box.label(text="Track Info", icon="WORLD")
        col = box.column(align=True)
        col.prop(track, "name", text="Name")
        col.prop(track, "description", text="Description")
        col.prop(track, "country", text="Country")
        col.prop(track, "city", text="City")
        col.prop(track, "length", text="Length (m)")
        col.prop(track, "width", text="Width (m)")
        col.prop(track, "run", text="Type")

        # Tags (inside box, collapsible)
        col.separator(factor=0.5)
        row = col.row()
        row.prop(
            track,
            "show_tags",
            text="",
            icon="TRIA_DOWN" if track.show_tags else "TRIA_RIGHT",
            emboss=False,
        )
        row.label(text="Tags")
        if track.show_tags:
            tag_col = col.column(align=True)
            tag_col.operator("ac.add_tag", text="New Tag", icon="ADD")
            tag_col.template_list(
                "AC_UL_Tags", "tags", track, "tags", track, "tags_index", rows=2
            )

        # GeoTags (inside box, collapsible)
        col.separator(factor=0.5)
        row = col.row()
        row.prop(
            track,
            "show_geotags",
            text="",
            icon="TRIA_DOWN" if track.show_geotags else "TRIA_RIGHT",
            emboss=False,
        )
        row.label(text="GeoTags")
        if track.show_geotags:
            geotag_col = col.column(align=True)
            geotag_col.operator("ac.add_geo_tag", text="New GeoTag", icon="ADD")
            geotag_col.template_list(
                "AC_UL_Tags", "geotags", track, "geotags", track, "geotags_index", rows=2
            )

        layout.separator()

        # Save Track Data button
        save_row = layout.row()
        save_row.scale_y = 1.2
        save_row.enabled = has_working_dir and bpy.data.is_saved
        save_row.operator("ac.save_track_data", text="Save Track Data (Name, Tags, etc.)", icon="FILE_TEXT")

        layout.separator()


class VIEW3D_PT_AC_SurfaceTools(VIEW3D_PT_AC_Sidebar, Panel):
    """PHASE 3: Surface Tools - Surface assignment, object setup"""
    bl_label = "3. Surface & Object Tools"
    bl_idname = "VIEW3D_PT_AC_SurfaceTools"
    bl_context = "objectmode"
    bl_order = 2
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings

        if not settings.surfaces:
            box = layout.box()
            box.label(text="Initialize Surfaces", icon="INFO")
            box.operator("ac.init_surfaces", text="Initialize Surfaces", icon="ADD")
            return

        # Surface Assignment
        box = layout.box()
        box.label(text="Surface Assignment", icon="MESH_DATA")

        # Show ALL surfaces as buttons
        col = box.column(align=True)

        # Calculate surface groups (this is relatively fast, not like preflight checks)
        surface_groups = settings.get_surface_groups(context)

        for surface in settings.get_surfaces():
            row = col.row(align=True)
            row.scale_y = 1.2
            op = row.operator("ac.assign_surface", text=surface.name)
            op.key = surface.key

        layout.separator()

        # Object Setup section
        box = layout.box()
        box.label(text="Object Setup", icon="OBJECT_DATA")

        col = box.column(align=True)

        # Tree Setup button
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("ac.setup_as_tree", text="Tree")

        # Wall button
        row = col.row(align=True)
        row.scale_y = 1.2
        row.operator("ac.assign_wall", text="Wall")

        # Save Surfaces button
        layout.separator()
        save_row = layout.row()
        save_row.scale_y = 1.2
        save_row.enabled = bool(settings.working_dir) and bpy.data.is_saved
        save_row.operator("ac.save_surfaces", text="Save Surfaces", icon="FILE_TICK")


class VIEW3D_PT_AC_Surfaces(Panel):
    """Surfaces panel - physics surface configuration (subpanel of Surface Tools)"""
    bl_label = "⚙ Surfaces Configuration"
    bl_idname = "VIEW3D_PT_AC_Surfaces"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_SurfaceTools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings

        if not settings.surfaces:
            layout.operator("ac.init_surfaces", text="Initialize Surfaces", icon="ADD")
            return

        # Calculate surface groups (relatively fast operation)
        assigned = settings.get_surface_groups(context)

        active = settings.active_surfaces
        for surface in settings.get_surfaces():
            box = layout.box()
            row = box.row()
            toggle = row.operator(
                "ac.toggle_surface",
                text="",
                icon="TRIA_DOWN" if surface.name in active else "TRIA_RIGHT",
            )
            toggle.target = surface.name
            count = len(assigned.get(surface.key, []))
            row.label(text=f"{surface.name} [{count}]")
            copy_surface = row.operator("ac.add_surface", text="", icon="COPYDOWN")
            copy_surface.copy_from = surface.key
            select_all = row.operator(
                "ac.select_all_surfaces", text="", icon="RESTRICT_SELECT_OFF"
            )
            select_all.surface = surface.key
            if surface.name in active:
                col = box.column(align=True)
                col.enabled = surface.custom
                col.row().prop(surface, "name", text="Name")
                col.row().prop(surface, "key", text="Key")
                if surface.custom:
                    split = col.split(factor=0.5)
                    col_left = split.column(align=True)
                    col_left.label(text="Settings")
                    col_left.row().prop(surface, "is_valid_track", text="Is Valid Track", toggle=True)
                    if surface.is_valid_track:
                        col_left.row().prop(surface, "is_pit_lane", text="Is Pit Lane", toggle=True)
                    else:
                        col_left.row().prop(surface, "black_flag_time", text="Black Flag Time", slider=True)
                    col_left.separator(factor=1.2)
                    col_left.row().prop(surface, "dirt_additive", text="Dirt Additive", slider=True)
                    col_left.separator(factor=2)
                    col_left.label(text="Sound")
                    col_left.row().prop(surface, "wav", text="Wav")
                    col_left.separator(factor=1.2)
                    col_left.row().prop(surface, "wav_pitch", text="Wav Pitch", slider=True)

                    col_right = split.column(align=True)
                    col_right.label(text="Physics")
                    col_right.row().prop(surface, "friction", text="Friction", slider=True)
                    col_right.row().prop(surface, "damping", text="Damping", slider=True)
                    col_right.separator(factor=1.5)
                    col_right.label(text="Feedback")
                    col_right.row().prop(surface, "ff_effect", text="FF Effect")
                    col_right.separator(factor=1.2)
                    col_right.row().prop(surface, "sin_height", text="Sine Height", slider=True)
                    col_right.row().prop(surface, "sin_length", text="Sine Length", slider=True)
                    col_right.separator(factor=1.2)
                    col_right.row().prop(surface, "vibration_gain", text="Vibration Gain", slider=True)
                    col_right.row().prop(surface, "vibration_length", text="Vibration Length", slider=True)

                    # CSP Surface Tweaks
                    box.separator()
                    box.label(text="CSP Surface Tweaks", icon="PREFERENCES")
                    col_left = box.column(align=True)
                    col_left.row().prop(surface, "ext_surface_type", text="Surface Type")
                    col_left.row().prop(surface, "ext_surface_type_modifier", text="Modifier")
                    col_left.separator(factor=1.2)
                    col_left.row().prop(surface, "ext_perlin_noise", text="Use Perlin Noise")
                    if surface.ext_perlin_noise:
                        col_left.row().prop(surface, "ext_perlin_octaves", text="Octaves")
                        col_left.row().prop(surface, "ext_perlin_persistence", text="Persistence", slider=True)

                    box.separator()
                    op = box.row().operator("ac.remove_surface", text="Remove", emboss=True)
                    op.target = surface.key

        col = layout.column(align=True)
        col.separator(factor=1.5)
        row = layout.row(align=True)
        row.operator("ac.add_surface", text="New Surface", icon="ADD")
        row.operator("ac.refresh_surfaces", text="Refresh Defaults", icon="FILE_REFRESH")


class VIEW3D_PT_AC_Objects(VIEW3D_PT_AC_Sidebar, Panel):
    """PHASE 2: Objects - Race setup and object placement"""
    bl_label = "2. Race Objects"
    bl_idname = "VIEW3D_PT_AC_Objects"
    bl_context = "objectmode"
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings

        # Info about cursor placement (moved to top)
        info_box = layout.box()
        info_box.scale_y = 0.8
        info_box.label(text="Objects are placed at 3D cursor", icon="CURSOR")
        info_box.label(text="Position cursor first, then click button", icon="BLANK1")

        layout.separator()

        # Create Objects - Individual object creation
        box = layout.box()
        box.label(text="Create Objects", icon="OBJECT_DATA")

        # Pits & Starts section
        box.label(text="Pits & Starts")
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.add_pitbox", text="Add Pitbox")
        col.operator("ac.add_start", text="Add Start")
        col.operator("ac.add_hotlap_start", text="Add Hotlap Start")

        # Gates section
        box.separator(factor=0.5)
        box.label(text="Gates")
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.add_ab_start_gate", text="Add AB Start")
        col.operator("ac.add_ab_finish_gate", text="Add AB Finish")
        col.operator("ac.add_time_gate", text="Add Time Gate")


class VIEW3D_PT_AC_Sidebar_Extra(VIEW3D_PT_AC_Sidebar, Panel):
    """Parent panel for Extra features (CSP effects, audio, lighting, extensions)"""
    bl_label = "4. Extra"
    bl_idname = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_context = "objectmode"
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass


class VIEW3D_PT_AC_Export(VIEW3D_PT_AC_Sidebar, Panel):
    """PHASE 6: Export - Validation and export"""
    bl_label = "6. Export"
    bl_idname = "VIEW3D_PT_AC_Export"
    bl_context = "objectmode"
    bl_order = 5
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings

        has_working_dir = bool(settings.working_dir)
        is_blend_saved = bpy.data.is_saved
        can_save_or_export = has_working_dir and is_blend_saved

        # Preflight checks - show cached status
        box = layout.box()
        row = box.row()

        # Status label based on cached results
        status_col = row.column()
        if not settings.preflight_scanned:
            status_col.label(text="Not Scanned", icon="QUESTION")
        elif settings.preflight_has_blocking_errors:
            status_col.alert = True
            status_col.label(text=f"{settings.preflight_error_count} Issue(s)", icon="ERROR")
        else:
            if settings.preflight_error_count == 0:
                status_col.label(text="Ready to Export", icon="CHECKMARK")
            else:
                status_col.label(text=f"Ready ({settings.preflight_error_count} info)", icon="INFO")

        # Scan for Issues button
        button_col = row.column()
        button_col.alignment = 'RIGHT'
        button_col.operator("ac.scan_for_issues", text="Scan for Issues", icon="VIEWZOOM")

        # Fix errors button (only show if scanned and has fixable errors)
        if settings.preflight_scanned and settings.preflight_error_count > 0:
            # Check if there are fixable errors (severity 1)
            has_fixable = any(e["severity"] == 1 for e in settings.error)
            if has_fixable:
                fix_col = row.column()
                fix_col.alignment = 'RIGHT'
                fix_col.operator("ac.autofix_preflight", text="Fix", icon="TOOL_SETTINGS")

        layout.separator()

        # ===== SAVE EXT_CONFIG =====
        box = layout.box()
        header_row = box.row()
        header_row.label(text="Save ext_config", icon="DOCUMENTS")

        col = box.column(align=True)
        col.enabled = can_save_or_export
        col.scale_y = 1.1

        # Extensions (CSP)
        col.operator("ac.save_extensions", text="Extensions (CSP)", icon="MODIFIER_ON")

        # Warning if can't export
        if not can_save_or_export:
            layout.separator()
            warning = layout.row()
            warning.alert = True
            warning.scale_y = 0.8
            if not is_blend_saved:
                warning.label(text="Save .blend file first", icon="ERROR")
            elif not has_working_dir:
                warning.label(text="Set working directory first", icon="ERROR")

        # BIG EXPORT BUTTON (moved to bottom)
        layout.separator()
        export_row = layout.row()
        export_row.scale_y = 2.0
        # Enable if basic requirements met (scan will run automatically on click if needed)
        export_row.enabled = can_save_or_export
        export_row.operator("exporter.kn5", text="EXPORT TRACK", icon="EXPORT")


class VIEW3D_PT_AC_TrackImages(Panel):
    """Track Images - Map, outline, and preview generation (subpanel of Export)"""
    bl_label = "Track Images"
    bl_idname = "VIEW3D_PT_AC_TrackImages"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Export"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings

        if not settings.working_dir:
            layout.label(text="Set working directory first", icon="INFO")
            return

        # Experimental notice
        warn_row = layout.row()
        warn_row.alert = True
        warn_row.label(text="Experimental! Avoid using for now!", icon="ERROR")

        # Track Images
        box = layout.box()
        box.label(text="Required Images", icon="IMAGE_DATA")

        # Check which files exist
        map_exists = os.path.exists(os.path.join(settings.working_dir, "map.png"))
        outline_exists = os.path.exists(os.path.join(settings.working_dir, "ui", "outline.png"))
        preview_exists = os.path.exists(os.path.join(settings.working_dir, "ui", "preview.png"))

        # Status checkboxes
        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text="map.png", icon="CHECKMARK" if map_exists else "CHECKBOX_DEHLT")
        row.label(text="outline.png", icon="CHECKMARK" if outline_exists else "CHECKBOX_DEHLT")
        row.label(text="preview.png", icon="CHECKMARK" if preview_exists else "CHECKBOX_DEHLT")

        box.separator(factor=0.5)

        # Generation buttons
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.generate_map", text="Generate Map & Outline", icon="IMAGE_DATA")

        # Preview camera
        preview_cam_exists = "AC_PREVIEW_CAMERA" in context.scene.objects
        if not preview_cam_exists:
            col.operator("ac.create_preview_camera", text="Create Preview Camera", icon="OUTLINER_OB_CAMERA")
        else:
            row = col.row(align=True)
            row.scale_y = 0.8
            row.label(text="Preview Camera Ready", icon="CAMERA_DATA")

        col.operator("ac.generate_preview", text="Generate Preview", icon="RENDER_STILL")

        all_images_done = map_exists and outline_exists and preview_exists
        if all_images_done:
            check_row = box.row()
            check_row.scale_y = 0.8
            check_row.label(text="All images generated", icon="CHECKMARK")


# ============================================================================
# EXTRA SUBPANELS
# ============================================================================

class VIEW3D_PT_AC_Sidebar_CSPLights(Panel):
    """CSP Lights configuration panel"""
    bl_label = "CSP Lights"
    bl_idname = "VIEW3D_PT_AC_Sidebar_CSPLights"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Main actions at top
        row = layout.row(align=True)
        row.scale_y = 1.3
        row.operator("ac.add_blender_spot_light", text="Add Spot Light", icon="ADD")
        row.operator("ac.scan_lights", text="Scan Lights", icon="FILE_REFRESH")

        # Lights list
        layout.template_list(
            "AC_UL_Lights",
            "",
            lighting,
            "lights",
            lighting,
            "active_light_index",
            rows=4,
        )

        # Selected light properties
        if 0 <= lighting.active_light_index < len(lighting.lights):
            light = lighting.lights[lighting.active_light_index]

            # CSP Settings (override Blender light settings for export)
            box = layout.box()
            box.label(text="CSP Export Settings", icon="LIGHT")

            col = box.column(align=True)
            col.prop(light, "range", text="Range")

            # Shadows toggle (inverted display: checked means shadows ON in-game)
            row = col.row(align=True)
            icon = 'CHECKBOX_HLT' if not light.cast_shadows else 'CHECKBOX_DEHLT'
            row.operator("ac.toggle_light_shadows", text="Cast Shadows", icon=icon, depress=not light.cast_shadows)

            # Conditions section
            cond_box = layout.box()
            cond_box.label(text="Condition", icon="TIME")
            col = cond_box.column(align=True)
            col.prop(light, "condition_preset", text="")
            if light.condition_preset == "CUSTOM":
                col.prop(light, "condition", text="Custom")
            if light.use_condition:
                col.prop(light, "condition_offset", text="Offset")

            # Effects section
            fx_box = layout.box()
            fx_box.label(text="Effects", icon="SHADERFX")
            col = fx_box.column(align=True)
            col.prop(light, "volumetric_light", text="Volumetric Light")
            col.prop(light, "long_specular", text="Long Specular")
            col.prop(light, "skip_light_map", text="Skip Light Map")
            col.prop(light, "disable_with_bounced_light", text="Disable with Bounced Light")

        # Bottom actions in a box
        layout.separator()
        export_box = layout.box()
        row = export_box.row(align=True)
        row.scale_y = 1.5
        row.operator("ac.export_and_update_lights", text="Save Lights", icon="FILE_REFRESH")


class VIEW3D_PT_AC_Sidebar_EmissiveMaterials(Panel):
    """Emissive Materials configuration panel (CSP feature)"""
    bl_label = "Emissive Materials (CSP)"
    bl_idname = "VIEW3D_PT_AC_Sidebar_EmissiveMaterials"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        lighting = settings.lighting

        # Material selector and Add button in one row (80/20 split)
        row = layout.row(align=True)
        row.scale_y = 1.3
        split = row.split(factor=0.8, align=True)
        split.prop(lighting, "material_to_add", text="")
        split.operator("ac.add_emissive_material", text="Add", icon="ADD")

        # Emissive materials list
        layout.template_list(
            "AC_UL_EmissiveMaterials",
            "",
            lighting,
            "emissive_materials",
            lighting,
            "active_emissive_index",
            rows=4,
        )

        # Selected emissive material properties
        if 0 <= lighting.active_emissive_index < len(lighting.emissive_materials):
            emissive = lighting.emissive_materials[lighting.active_emissive_index]

            # Cast Light section (first)
            light_box = layout.box()
            header_row = light_box.row()
            header_row.prop(emissive, "emit_light", text="Cast Light", icon="LIGHT")

            if emissive.emit_light:
                col = light_box.column(align=True)

                # Light properties
                row = col.row(align=True)
                row.prop(emissive, "light_intensity", text="Intensity")
                row.prop(emissive, "light_range", text="Range")

                row = col.row(align=True)
                row.prop(emissive, "light_spot", text="Spot")
                row.prop(emissive, "light_spot_sharpness", text="Sharp")

                col.prop(emissive, "light_fade_at", text="Fade At")
                col.prop(emissive, "light_volumetric", text="Volumetric")

                # Shadows toggle (inverted display: checked means shadows ON in-game)
                row = col.row(align=True)
                icon = 'CHECKBOX_HLT' if not emissive.cast_shadows else 'CHECKBOX_DEHLT'
                row.operator("ac.toggle_emissive_shadows", text="Cast Shadows", icon=icon, depress=not emissive.cast_shadows)

            # Glow Mesh Object Settings (second)
            settings_box = layout.box()
            settings_box.label(text="Glow Mesh Object Settings", icon="SHADING_RENDERED")

            col = settings_box.column(align=True)

            # Color and intensity
            row = col.row(align=True)
            row.prop(emissive, "emissive_color", text="")
            row.prop(emissive, "intensity", text="Intensity")

            # Glow effect
            row = col.row(align=True)
            row.prop(emissive, "use_glow_effect", text="Enhanced Glow")

            # Condition section (third)
            cond_box = layout.box()
            cond_box.label(text="Condition", icon="TIME")
            col = cond_box.column(align=True)
            col.prop(emissive, "condition_preset", text="")
            if emissive.condition_preset == "CUSTOM":
                col.prop(emissive, "condition", text="Custom")
            if emissive.use_condition:
                col.prop(emissive, "off_value_mode", text="Off Value")

        # Bottom actions in a box
        layout.separator()
        export_box = layout.box()
        row = export_box.row(align=True)
        row.scale_y = 1.5
        row.operator("ac.save_extensions", text="Save Emissive Materials", icon="EXPORT")


class VIEW3D_PT_AC_Sidebar_GrassFX(Panel):
    """GrassFX configuration panel (CSP feature)"""
    bl_label = "GrassFX (CSP)"
    bl_idname = "VIEW3D_PT_AC_Sidebar_GrassFX"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        grassfx = settings.grassfx

        # Add active material button
        box = layout.box()
        box.label(text="Add Grass Material", icon="ADD")
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.add_grassfx_material", text="Add Active Material", icon="MATERIAL")

        # Info text
        info_row = col.row()
        info_row.scale_y = 0.8
        info_row.label(text="Adds active object's active material", icon="INFO")

        layout.separator()

        # Materials list
        box = layout.box()
        box.label(text="Grass Materials", icon="MATSHADERBALL")
        if grassfx.materials:
            box.template_list(
                "AC_UL_GrassFXMaterials",
                "",
                grassfx,
                "materials",
                grassfx,
                "materials_index",
                rows=4,
            )
        else:
            box.label(text="No materials added", icon="INFO")

        layout.separator()

        # Advanced Settings (collapsible)
        box = layout.box()
        row = box.row()
        row.prop(
            grassfx,
            "show_settings",
            text="",
            icon="TRIA_DOWN" if grassfx.show_settings else "TRIA_RIGHT",
            emboss=False,
        )
        row.label(text="Grass Settings", icon="SETTINGS")

        if grassfx.show_settings:
            # Mask settings
            col = box.column(align=True)
            col.separator(factor=0.5)
            col.label(text="Spawn Mask:", icon="MOD_MASK")
            col.prop(grassfx, "mask_main_threshold", slider=True)
            col.prop(grassfx, "mask_red_threshold", slider=True)
            col.prop(grassfx, "mask_min_luminance", slider=True)
            col.prop(grassfx, "mask_max_luminance", slider=True)

            col.separator()

            # Shape settings
            col.label(text="Grass Shape:", icon="SURFACE_NCURVE")
            col.prop(grassfx, "shape_size", slider=True)
            col.prop(grassfx, "shape_tidy", slider=True)
            col.prop(grassfx, "shape_cut", slider=True)
            col.prop(grassfx, "shape_width", slider=True)


class VIEW3D_PT_AC_Sidebar_RainFX(Panel):
    """RainFX configuration panel (CSP feature)"""
    bl_label = "RainFX (CSP)"
    bl_idname = "VIEW3D_PT_AC_Sidebar_RainFX"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        rainfx = settings.rainfx

        # Enable toggle
        box = layout.box()
        row = box.row()
        row.scale_y = 1.2
        row.prop(rainfx, "enabled", text="Enable RainFX", toggle=True)

        if not rainfx.enabled:
            layout.label(text="Enable to configure rain effects", icon="INFO")
            return

        layout.separator()

        # Auto-detect button
        box = layout.box()
        box.label(text="Material Detection", icon="VIEWZOOM")
        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.autodetect_rainfx_materials", text="Auto-Detect Materials", icon="AUTO")
        col.operator("ac.clear_rainfx_materials", text="Clear All", icon="X")

        layout.separator()

        # Materials configuration
        box = layout.box()
        box.label(text="Material Categories", icon="MATSHADERBALL")

        col = box.column(align=True)

        # Puddles materials
        col.label(text="Puddles (roads only):", icon="MATFLUID")
        col.prop(rainfx, "puddles_materials", text="")
        col.separator(factor=0.5)

        # Soaking materials
        col.label(text="Soaking (gets darker):", icon="MATSHADERBALL")
        col.prop(rainfx, "soaking_materials", text="")
        col.separator(factor=0.5)

        # Smooth materials
        col.label(text="Smooth (rain drops):", icon="MATSPHERE")
        col.prop(rainfx, "smooth_materials", text="")
        col.separator(factor=0.5)

        # Rough materials
        col.label(text="Rough (grass, no reflection):", icon="SURFACE_DATA")
        col.prop(rainfx, "rough_materials", text="")
        col.separator(factor=0.5)

        # Lines materials
        col.label(text="Lines (track markings):", icon="CURVE_PATH")
        col.prop(rainfx, "lines_materials", text="")


class VIEW3D_PT_AC_Sidebar_TreeFX(Panel):
    """TreeFX export panel (CSP feature)"""
    bl_label = "TreeFX (CSP)"
    bl_idname = "VIEW3D_PT_AC_Sidebar_TreeFX"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Tree Export Section
        box = layout.box()
        box.label(text="Tree Export", icon="OUTLINER_OB_POINTCLOUD")

        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("ac.export_tree_list", text="Export Tree List", icon="EXPORT")

        # Info text
        info_box = layout.box()
        info_box.scale_y = 0.8
        info_col = info_box.column(align=True)
        info_col.label(text="Select objects with _TREES modifier", icon="INFO")
        info_col.label(text="Exports instances to trees.txt format", icon="BLANK1")


class VIEW3D_PT_AC_Sidebar_AILines(Panel):
    """AI Line export panel for racing line development"""
    bl_label = "AI Lines"
    bl_idname = "VIEW3D_PT_AC_Sidebar_AILines"
    bl_context = "objectmode"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_Sidebar_Extra"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings

        # Export Section
        box = layout.box()
        box.label(text="Export Fast Lane", icon="EXPORT")
        col = box.column(align=True)
        col.scale_y = 1.2

        # Show export button (disabled if no working dir)
        export_row = col.row()
        export_row.enabled = bool(settings.working_dir)
        export_row.operator("ac.export_ai_line", text="Export fast_lane.ai", icon="FILE")

        if not settings.working_dir:
            col.label(text="Set working directory first", icon="ERROR")

        # Info text
        info_box = layout.box()
        info_box.scale_y = 0.8
        info_col = info_box.column(align=True)
        info_col.label(text="Select an edge mesh to export", icon="INFO")
        info_col.label(text="as fast_lane.ai in track/ai/", icon="BLANK1")
        info_col.separator()
        info_col.label(text="Tip: Use ksEditor to tune AI", icon="INFO")
        info_col.label(text="speed and braking points.", icon="BLANK1")


# ============================================================================
# MATERIAL EDITOR PANEL
# ============================================================================

class AC_ClearMaterialSearch(Operator):
    """Clear material search filter"""
    bl_idname = "ac.clear_material_search"
    bl_label = "Clear Search"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        context.scene.AC_Settings.material_search_query = ""
        return {'FINISHED'}


class AC_ScanMaterials(Operator):
    """Scan scene to find materials on visible objects. This caches the results for better UI performance."""
    bl_idname = "ac.scan_materials"
    bl_label = "Scan Materials"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        from ...utils.helpers import get_visible_materials

        settings = context.scene.AC_Settings

        # Get visible materials using the centralized helper
        visible_materials = get_visible_materials(context)

        # Store as pipe-separated string (use | as separator to handle commas in names)
        settings.material_visibility_cache = "|".join(sorted(visible_materials))

        self.report({'INFO'}, f"Found {len(visible_materials)} visible materials")
        return {'FINISHED'}


class AC_UL_Materials(UIList):
    """UIList for displaying all materials in the blend file."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        material = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Show material name (no icon for performance)
            row = layout.row(align=True)
            row.prop(material, "name", text="", emboss=False)
            # Show user count
            row.label(text=str(material.users), icon='USER' if material.users > 0 else 'ORPHAN_DATA')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(material, "name", text="", emboss=False)

    def filter_items(self, context, data, propname):
        """
        Filter materials by search query and visibility cache.

        If no scan has been done (cache empty), shows all materials.
        Use the "Scan Materials" button to populate the visibility cache.
        """
        materials = getattr(data, propname)
        settings = context.scene.AC_Settings
        search_query = settings.material_search_query.lower().strip()

        # Parse visibility cache (use | as separator)
        cache = settings.material_visibility_cache
        if cache:
            visible_set = set(cache.split("|"))
        else:
            visible_set = None  # No scan done - show all

        flt_flags = []
        flt_neworder = []

        for mat in materials:
            show = True

            # Filter by search query
            if search_query and search_query not in mat.name.lower():
                show = False
            # Filter by visibility cache (if scan has been done)
            elif visible_set is not None and mat.name not in visible_set:
                show = False

            flt_flags.append(self.bitflag_filter_item if show else 0)

        return flt_flags, flt_neworder


class VIEW3D_PT_AC_MaterialEditor(VIEW3D_PT_AC_Sidebar, Panel):
    """Material Editor - Configure Assetto Corsa material properties"""
    bl_label = "5. Material Editor"
    bl_idname = "VIEW3D_PT_AC_MaterialEditor"
    bl_context = "objectmode"
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings: AC_Settings = context.scene.AC_Settings

        has_working_dir = bool(settings.working_dir)
        is_blend_saved = bpy.data.is_saved
        can_save_or_export = has_working_dir and is_blend_saved

        # ===== MATERIAL AUTO-DETECTION =====
        box = layout.box()
        box.label(text="Material Auto-Detection", icon="MODIFIER_ON")

        col = box.column(align=True)

        # Auto-Setup Materials
        validate_row = col.row()
        validate_row.scale_y = 1.2
        validate_row.enabled = can_save_or_export
        validate_row.operator("ac.validate_all", text="Auto-Setup Materials", icon="CHECKMARK")

        layout.separator()

        # Material selector
        box = layout.box()
        box.label(text="Materials", icon="MATERIAL")

        # Get all materials
        materials = bpy.data.materials
        if not materials:
            box.label(text="No materials in scene", icon='INFO')
            return

        # Scan and bulk edit buttons
        row = box.row(align=True)
        row.operator("ac.scan_materials", text="Scan", icon='VIEWZOOM')
        row.operator("ac.bulk_edit_select_materials", text="Batch Edit", icon='PROPERTIES')

        # Search bar
        search_row = box.row(align=True)
        search_row.prop(settings, "material_search_query", text="", icon='SORTALPHA')
        search_row.operator("ac.clear_material_search", text="", icon='X')

        # Material list
        row = box.row()
        row.template_list(
            "AC_UL_Materials",
            "",
            bpy.data,
            "materials",
            settings,
            "active_material_index",
            rows=5
        )

        # Get selected material
        if 0 <= settings.active_material_index < len(materials):
            material = materials[settings.active_material_index]

            # Check if material has AC settings
            if not hasattr(material, 'AC_Material'):
                box.label(text="Material has no AC properties", icon='ERROR')
                return

            # Update Materials button (always visible when material selected)
            layout.separator()
            update_row = layout.row()
            update_row.scale_y = 1.3
            update_row.operator("ac.update_material_config", text="Update Materials", icon="FILE_REFRESH")
        else:
            box.label(text="Select a material", icon='INFO')


class VIEW3D_PT_AC_MaterialProperties(Panel):
    """Material Properties - Shader and blending settings"""
    bl_label = "Properties"
    bl_idname = "VIEW3D_PT_AC_MaterialProperties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_MaterialEditor"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        materials = bpy.data.materials
        if not materials or not (0 <= settings.active_material_index < len(materials)):
            return False
        material = materials[settings.active_material_index]
        return hasattr(material, 'AC_Material')

    def draw_header(self, context):
        settings = context.scene.AC_Settings
        material = bpy.data.materials[settings.active_material_index]
        self.layout.label(text=material.name)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        material = bpy.data.materials[settings.active_material_index]
        ac_mat = material.AC_Material

        # Shader settings
        layout.prop(ac_mat, "shader_name")
        layout.prop(ac_mat, "alpha_blend_mode")
        layout.prop(ac_mat, "depth_mode")
        layout.prop(ac_mat, "alpha_tested")


class VIEW3D_PT_AC_ShaderProperties(Panel):
    """Shader Properties - Custom shader property values"""
    bl_label = "Shader Properties"
    bl_idname = "VIEW3D_PT_AC_ShaderProperties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FTE"
    bl_parent_id = "VIEW3D_PT_AC_MaterialEditor"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        materials = bpy.data.materials
        if not materials or not (0 <= settings.active_material_index < len(materials)):
            return False
        material = materials[settings.active_material_index]
        return hasattr(material, 'AC_Material')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings
        material = bpy.data.materials[settings.active_material_index]
        ac_mat = material.AC_Material

        # Shader properties list
        if ac_mat.shader_properties:
            layout.template_list(
                "AC_UL_ShaderProperties",
                "",
                ac_mat,
                "shader_properties",
                ac_mat,
                "shader_properties_active",
                rows=3
            )

            # Show value editor for selected property
            if 0 <= ac_mat.shader_properties_active < len(ac_mat.shader_properties):
                active_prop = ac_mat.shader_properties[ac_mat.shader_properties_active]
                prop_type = active_prop.property_type

                # Display appropriate value field based on property type
                if prop_type == "float":
                    layout.prop(active_prop, "valueA", text="Value")
                elif prop_type == "vec2":
                    layout.prop(active_prop, "valueB", text="Value")
                elif prop_type == "vec3":
                    layout.prop(active_prop, "valueC", text="Value")
                elif prop_type == "vec4":
                    layout.prop(active_prop, "valueD", text="Value")
        else:
            layout.label(text="No shader properties", icon='INFO')

        # Reset to defaults button
        layout.separator()
        layout.operator("ac.reset_shader_defaults", icon='LOOP_BACK')
