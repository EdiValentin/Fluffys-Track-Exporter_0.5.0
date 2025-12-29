"""
Sync operators for ext_config.ini synchronization between Blender and file.

Provides operators to detect, display, and resolve differences between
the addon's current state and the ext_config.ini file on disk.
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, StringProperty

from ...configs.ext_config import (
    compare_with_file,
    get_diff_summary,
    import_from_file,
    get_ext_config_path,
)


class AC_ExtConfigSyncCheck(Operator):
    """Check for differences between addon state and ext_config.ini file"""
    bl_idname = "ac.ext_config_sync_check"
    bl_label = "Check ext_config Sync"
    bl_options = {'REGISTER'}

    action: EnumProperty(
        name="Action",
        items=[
            ('CHECK', "Check", "Just check for differences"),
            ('EXPORT', "Export", "Export from Blender to file"),
            ('IMPORT', "Import", "Import from file to Blender"),
        ],
        default='CHECK',
    )

    callback_operator: StringProperty(
        name="Callback",
        description="Operator to call after sync completes",
        default="",
    )

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return settings.working_dir and settings.working_dir != ""

    def execute(self, context):
        if self.action == 'CHECK':
            return bpy.ops.ac.ext_config_sync_dialog('INVOKE_DEFAULT',
                                                      callback_operator=self.callback_operator)
        elif self.action == 'EXPORT':
            if self.callback_operator:
                try:
                    parts = self.callback_operator.split('.')
                    if len(parts) == 2:
                        getattr(getattr(bpy.ops, parts[0]), parts[1])()
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to run callback: {e}")
                    return {'CANCELLED'}
            else:
                bpy.ops.ac.save_extensions()
            return {'FINISHED'}
        elif self.action == 'IMPORT':
            success, message = import_from_file(context)
            if success:
                self.report({'INFO'}, message)
            else:
                self.report({'ERROR'}, message)
            return {'FINISHED'}

        return {'FINISHED'}


class AC_ExtConfigSyncDialog(Operator):
    """Dialog to resolve sync conflicts between addon and ext_config.ini"""
    bl_idname = "ac.ext_config_sync_dialog"
    bl_label = "ext_config.ini Changed"
    bl_options = {'REGISTER', 'INTERNAL'}

    callback_operator: StringProperty(
        name="Callback",
        description="Operator to call after export completes",
        default="",
    )

    _diff_result = None

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        return settings.working_dir and settings.working_dir != ""

    def invoke(self, context, event):
        self._diff_result = compare_with_file(context)

        # If no differences, just proceed with export
        if not self._diff_result["has_differences"]:
            if self.callback_operator:
                try:
                    parts = self.callback_operator.split('.')
                    if len(parts) == 2:
                        getattr(getattr(bpy.ops, parts[0]), parts[1])()
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to run callback: {e}")
                    return {'CANCELLED'}
            else:
                bpy.ops.ac.save_extensions()
            self.report({'INFO'}, "No differences found. Export complete.")
            return {'FINISHED'}

        # Check addon preferences for sync mode
        addon_prefs = context.preferences.addons[__package__.split('.')[0]].preferences
        sync_mode = addon_prefs.ext_config_sync_mode

        if sync_mode == 'OVERRIDE':
            # Auto-override without dialog
            if self.callback_operator:
                try:
                    parts = self.callback_operator.split('.')
                    if len(parts) == 2:
                        getattr(getattr(bpy.ops, parts[0]), parts[1])()
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to run callback: {e}")
                    return {'CANCELLED'}
            else:
                bpy.ops.ac.save_extensions()
            self.report({'INFO'}, "Exported (auto-override per preferences)")
            return {'FINISHED'}
        elif sync_mode == 'IMPORT':
            # Auto-import without dialog
            success, message = import_from_file(context)
            if success:
                self.report({'INFO'}, message)
                if self.callback_operator:
                    try:
                        parts = self.callback_operator.split('.')
                        if len(parts) == 2:
                            getattr(getattr(bpy.ops, parts[0]), parts[1])()
                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to run callback: {e}")
                        return {'CANCELLED'}
            else:
                self.report({'ERROR'}, message)
                return {'CANCELLED'}
            return {'FINISHED'}

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout

        # Simple header
        row = layout.row()
        row.label(text="External changes detected", icon='ERROR')

        layout.separator()

        # Three buttons in a column
        col = layout.column(align=True)

        op = col.operator("ac.ext_config_view_diff", text="View Details", icon='TEXT')

        col.separator()

        op = col.operator("ac.ext_config_sync_action", text="Override", icon='EXPORT')
        op.action = 'EXPORT'
        op.callback_operator = self.callback_operator

        op = col.operator("ac.ext_config_sync_action", text="Import", icon='IMPORT')
        op.action = 'IMPORT'
        op.callback_operator = self.callback_operator

    def execute(self, context):
        return {'CANCELLED'}


class AC_ExtConfigSyncCancel(Operator):
    """Cancel sync and abort pending operations"""
    bl_idname = "ac.ext_config_sync_cancel"
    bl_label = "Cancel Sync"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        from ...kn5.exporter_ops import _smart_export_pending
        _smart_export_pending["active"] = False
        _smart_export_pending["filepath"] = ""

        self.report({'INFO'}, "Sync cancelled")
        return {'FINISHED'}


class AC_ExtConfigSyncAction(Operator):
    """Execute sync action (export or import)"""
    bl_idname = "ac.ext_config_sync_action"
    bl_label = "Sync Action"
    bl_options = {'REGISTER', 'INTERNAL'}

    action: EnumProperty(
        name="Action",
        items=[
            ('EXPORT', "Export", "Export from Blender to file"),
            ('IMPORT', "Import", "Import from file to Blender"),
        ],
        default='EXPORT',
    )

    callback_operator: StringProperty(
        name="Callback",
        default="",
    )

    def execute(self, context):
        if self.action == 'EXPORT':
            if self.callback_operator:
                try:
                    parts = self.callback_operator.split('.')
                    if len(parts) == 2:
                        getattr(getattr(bpy.ops, parts[0]), parts[1])()
                        self.report({'INFO'}, "Exported from Blender to ext_config.ini")
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to run callback: {e}")
                    return {'CANCELLED'}
            else:
                bpy.ops.ac.save_extensions()
                self.report({'INFO'}, "Exported from Blender to ext_config.ini")

        elif self.action == 'IMPORT':
            success, message = import_from_file(context)
            if success:
                self.report({'INFO'}, message)
                if self.callback_operator:
                    try:
                        parts = self.callback_operator.split('.')
                        if len(parts) == 2:
                            getattr(getattr(bpy.ops, parts[0]), parts[1])()
                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to run callback: {e}")
                        return {'CANCELLED'}
            else:
                self.report({'ERROR'}, message)
                return {'CANCELLED'}

        return {'FINISHED'}


class AC_ExtConfigViewDiff(Operator):
    """View detailed diff between addon state and ext_config.ini"""
    bl_idname = "ac.ext_config_view_diff"
    bl_label = "ext_config.ini Changes"
    bl_options = {'REGISTER', 'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout

        diff_result = compare_with_file(context)

        if not diff_result["has_differences"]:
            layout.label(text="No differences found.", icon='CHECKMARK')
            return

        # Group sections by status
        modified = []
        added = []
        removed = []

        for name, data in diff_result["sections"].items():
            if data["status"] == "modified":
                modified.append((name, data))
            elif data["status"] == "added":
                added.append(name)
            elif data["status"] == "removed":
                removed.append(name)

        # Modified sections - show full values
        if modified:
            box = layout.box()
            box.label(text=f"Modified ({len(modified)})", icon='FILE_REFRESH')
            for name, data in modified:
                section_box = box.box()
                section_box.label(text=f"[{name}]")
                for change in data["changes"]:
                    col = section_box.column(align=True)
                    col.label(text=f"{change['key']}:")
                    # Show full values on separate lines
                    row = col.row()
                    row.label(text="", icon='REMOVE')
                    row.label(text=f"{change['file']}")
                    row = col.row()
                    row.label(text="", icon='ADD')
                    row.label(text=f"{change['addon']}")

        # Added sections (in addon but not in file)
        if added:
            box = layout.box()
            box.label(text=f"New in Addon ({len(added)})", icon='ADD')
            col = box.column(align=True)
            for name in added:
                col.label(text=f"[{name}]")

        # Removed sections (in file but not in addon)
        if removed:
            box = layout.box()
            box.label(text=f"Only in File ({len(removed)})", icon='REMOVE')
            col = box.column(align=True)
            for name in removed:
                col.label(text=f"[{name}]")

    def execute(self, context):
        return {'FINISHED'}


class AC_ImportExtConfig(Operator):
    """Import ext_config.ini values into addon"""
    bl_idname = "ac.import_ext_config"
    bl_label = "Import ext_config.ini"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.AC_Settings
        if not settings.working_dir:
            return False
        import os
        return os.path.exists(get_ext_config_path(settings))

    def execute(self, context):
        success, message = import_from_file(context)
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
