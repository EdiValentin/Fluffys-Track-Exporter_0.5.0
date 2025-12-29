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


import traceback
import os
import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from .utils import read_settings
from .kn5_writer import KN5Writer
from .texture_writer import TextureWriter
from .material_writer import MaterialWriter
from .node_writer import NodeWriter
from .constants import KN5_HEADER
from .export_utils import (
    make_all_objects_local,
    refresh_all_modifiers,
    realize_and_mesh_all,
    remove_empty_material_slots,
    validate_all_materials,
    get_versioned_filename,
    get_smart_exports_directory
)
from .utils import is_object_excluded_by_collection
from ...utils.helpers import is_hidden_name


# Temporary storage for Smart Export state when sync dialog is shown
_smart_export_pending = {
    "filepath": "",
    "active": False
}


class AC_ContinueSmartExport(bpy.types.Operator):
    """Continue Smart Export after ext_config sync resolution"""
    bl_idname = "ac.continue_smart_export"
    bl_label = "Continue Smart Export"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global _smart_export_pending

        if not _smart_export_pending["active"]:
            self.report({'ERROR'}, "No pending Smart Export")
            return {'CANCELLED'}

        filepath = _smart_export_pending["filepath"]
        _smart_export_pending["active"] = False
        _smart_export_pending["filepath"] = ""

        if not filepath:
            self.report({'ERROR'}, "No export filepath set")
            return {'CANCELLED'}

        # Call the export operator with sync check skipped
        return bpy.ops.exporter.kn5(
            'EXEC_DEFAULT',
            filepath=filepath,
            export_mode='SMART',
            show_export_dialog=False,
            skip_ext_config_sync=True
        )


class ReportOperator(bpy.types.Operator):
    bl_idname = "kn5.report_message"
    bl_label = "Export report"

    is_error: BoolProperty()
    title: StringProperty()
    message: StringProperty()

    def execute(self, context):
        if self.is_error:
            self.report({'WARNING'}, self.message)
        else:
            self.report({'INFO'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return context.window_manager.invoke_popup(self, width=600)

    def draw(self, context):
        if self.is_error:
            self.layout.alert = True
        row = self.layout.row()
        row.alignment = "CENTER"
        row.label(text=self.title)
        for line in self.message.splitlines():
            row = self.layout.row()
            line = line.replace("\t", " " * 4)
            row.label(text=line)
        row = self.layout.row()
        row.operator("kn5.report_clipboard").content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    bl_idname = "kn5.report_clipboard"
    bl_label = "Copy to clipboard"

    content: StringProperty()

    def execute(self, context):
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {'FINISHED'}


class KN5FileWriter(KN5Writer):
    def __init__(self, file, context, settings, warnings):
        super().__init__(file)

        self.context = context
        self.settings = settings
        self.warnings = warnings

        self.file_version = 5

    def write(self):
        self._write_header()
        self._write_content()

    def _write_header(self):
        self.file.write(KN5_HEADER)
        self.write_uint(self.file_version)

    def _write_content(self):
        texture_writer = TextureWriter(self.file, self.context, self.warnings)
        texture_writer.write()

        # Pass texture name mapping to material writer (for PNG->DDS conversions)
        material_writer = MaterialWriter(
            self.file, self.context, self.settings, self.warnings,
            texture_name_mapping=texture_writer.texture_name_mapping
        )
        material_writer.write()

        node_writer = NodeWriter(self.file, self.context, self.settings, self.warnings, material_writer)
        node_writer.write()


class ExportKN5(bpy.types.Operator, ExportHelper):
    bl_idname = "exporter.kn5"
    bl_label = "Export KN5"
    bl_description = "Export KN5"

    filename_ext = ".kn5"

    # Export mode selection
    export_mode: EnumProperty(
        name="Export Mode",
        description="Choose export workflow",
        items=[
            ('SMART', "Smart Export (Recommended)",
             "Creates backup, makes objects local, realizes modifiers/curves, cleans materials, validates shaders, returns to editable scene"),
            ('DIRECT', "Direct Export",
             "Current workflow - no file duplication"),
        ],
        default='SMART'
    )

    # Internal flag to control dialog flow
    show_export_dialog: BoolProperty(
        default=True,
        options={'HIDDEN'}
    )

    # Skip ext_config sync check (used when continuing after sync dialog)
    skip_ext_config_sync: BoolProperty(
        name="Skip Sync Check",
        description="Skip checking for external modifications to ext_config.ini",
        default=False,
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        """Check preflight status, then show export mode dialog, then file browser."""
        settings = context.scene.AC_Settings

        # Check if scan has been run
        if not settings.preflight_scanned:
            # Run scan automatically
            bpy.ops.ac.scan_for_issues('INVOKE_DEFAULT')
            return {'CANCELLED'}  # Cancel this export attempt, user can try again after reviewing issues

        # Check if there are blocking errors
        if settings.preflight_has_blocking_errors:
            # Show issues popup
            bpy.ops.ac.show_preflight_errors('INVOKE_DEFAULT')
            return {'CANCELLED'}  # Block export

        # All checks passed, proceed with export
        # Reset dialog flag
        self.show_export_dialog = True

        # Show export mode selection dialog first
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        """Draw the export mode selection dialog or file browser."""
        if self.show_export_dialog:
            # Draw export mode selection dialog
            layout = self.layout
            layout.label(text="Select Export Mode:", icon='EXPORT')
            layout.separator()

            # Export mode selection
            box = layout.box()
            box.prop(self, "export_mode", expand=True)

            layout.separator()

            # Show description based on selection
            box = layout.box()
            if self.export_mode == 'SMART':
                box.label(text="Smart Export:", icon='INFO')
                box.label(text="  • Creates 'Smart Exports' folder next to .blend file")
                box.label(text="  • Saves export copy (_Export.blend) there")
                box.label(text="  • Makes all linked objects local")
                box.label(text="  • Auto-realizes modifiers and converts curves")
                box.label(text="  • Removes empty material slots")
                box.label(text="  • Validates materials and assigns texture slots")
                box.label(text="  • Returns you to working file")
            else:
                box.label(text="Direct Export:", icon='INFO')
                box.label(text="  • Uses current export workflow")
                box.label(text="  • No file duplication")
                box.label(text="  • Exports scene as-is")

    def execute(self, context):
        """Execute export based on selected mode."""
        # If we just finished the mode selection dialog, proceed to file browser
        if self.show_export_dialog:
            self.show_export_dialog = False

            # Set default filename and directory from working directory
            settings = context.scene.AC_Settings
            if settings.working_dir:
                track_name = os.path.basename(os.path.normpath(settings.working_dir))
                self.filepath = os.path.join(settings.working_dir, track_name + self.filename_ext)
            else:
                self.filepath = "track" + self.filename_ext

            # Now invoke the file browser (ExportHelper standard flow)
            return ExportHelper.invoke(self, context, None)

        # Execute the appropriate export workflow
        if self.export_mode == 'SMART':
            return self._execute_smart_export(context)
        else:
            return self._execute_direct_export(context)

    def _execute_direct_export(self, context):
        """Execute the current/direct export workflow (Option 2)."""
        return self._perform_kn5_export(context)

    def _execute_smart_export(self, context):
        """Execute the Smart Export workflow (Option 1)."""
        global _smart_export_pending

        # Check for ext_config.ini changes FIRST, before any other operations
        if not self.skip_ext_config_sync:
            from ..configs.ext_config import compare_with_file, get_ext_config_path, import_from_file

            settings = context.scene.AC_Settings
            filepath = get_ext_config_path(settings)

            # Get addon preferences for sync mode
            addon_prefs = context.preferences.addons[__package__.split('.')[0]].preferences
            sync_mode = addon_prefs.ext_config_sync_mode

            # Only check if file exists and working directory is set
            if settings.working_dir and os.path.exists(filepath):
                diff_result = compare_with_file(context)

                if diff_result["has_differences"]:
                    # Check if file has sections that differ from addon
                    has_external_changes = False
                    for section_name, data in diff_result["sections"].items():
                        if data["status"] in ["modified", "removed"]:
                            has_external_changes = True
                            break

                    if has_external_changes:
                        # Handle based on preference
                        if sync_mode == 'OVERRIDE':
                            # Skip dialog, just proceed with export (will override file)
                            print("\n" + "="*60)
                            print("EXT_CONFIG SYNC: AUTO-OVERRIDE")
                            print("="*60)
                            print("External changes detected - overriding (per preferences)")
                            print("="*60 + "\n")
                        elif sync_mode == 'IMPORT':
                            # Import from file first, then proceed
                            print("\n" + "="*60)
                            print("EXT_CONFIG SYNC: AUTO-IMPORT")
                            print("="*60)
                            print("External changes detected - importing (per preferences)")
                            print("="*60 + "\n")
                            success, message = import_from_file(context)
                            if not success:
                                self.report({'ERROR'}, f"Failed to import ext_config.ini: {message}")
                                return {'CANCELLED'}
                        else:
                            # ASK mode - show dialog
                            # Store state for callback
                            _smart_export_pending["filepath"] = self.filepath
                            _smart_export_pending["active"] = True

                            print("\n" + "="*60)
                            print("EXT_CONFIG SYNC CHECK")
                            print("="*60)
                            print("External changes detected in ext_config.ini")
                            print("Showing sync dialog before proceeding...")
                            print("="*60 + "\n")

                            # Show sync dialog with callback to continue export
                            return bpy.ops.ac.ext_config_sync_dialog(
                                'INVOKE_DEFAULT',
                                callback_operator="ac.continue_smart_export"
                            )

        print("\n" + "="*60)
        print("SMART EXPORT STARTED")
        print("="*60 + "\n")

        # Check if file is saved
        if not bpy.data.filepath:
            self.report({'ERROR'}, "File must be saved before using Smart Export")
            print("ERROR: File is not saved (untitled.blend)\n")
            return {'CANCELLED'}

        original_filepath = bpy.data.filepath
        print(f"Working file: {original_filepath}")

        try:
            # Step 1: Save current file (capture any unsaved changes)
            print("\n[1/10] Saving working file...")
            bpy.ops.wm.save_mainfile()
            print("✓ Working file saved")

            # Step 2: Create export copy (_Export.blend) in Smart Exports folder
            print("\n[2/10] Creating export copy in Smart Exports folder...")
            try:
                # Get or create the Smart Exports directory
                smart_exports_dir = get_smart_exports_directory(original_filepath)
                export_filepath = get_versioned_filename(original_filepath, "Export", output_dir=smart_exports_dir)
                print(f"Export file path: {export_filepath}")
                bpy.ops.wm.save_as_mainfile(filepath=export_filepath)
                print(f"✓ Export copy created: {os.path.basename(export_filepath)}")
                print(f"  Location: {smart_exports_dir}")
            except PermissionError:
                self.report({'ERROR'}, "Permission denied - cannot write export file")
                print("ERROR: Permission denied when creating export file\n")
                return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Failed to create export file: {str(e)}")
                print(f"ERROR: {str(e)}\n")
                return {'CANCELLED'}

            # Step 3: Make all linked objects local (first pass)
            print("\n[3/10] Making all linked data local (first pass)...")
            try:
                # Ensure we're in object mode
                if context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                # Select all objects
                bpy.ops.object.select_all(action='SELECT')

                # Run make_local with type='ALL' to make everything local
                # This is the native Blender operator (same as F3 > Make Local)
                bpy.ops.object.make_local(type='ALL')

                print("✓ Made all linked data local (objects, materials, meshes, etc.)")

                # Deselect all after operation
                bpy.ops.object.select_all(action='DESELECT')
            except Exception as e:
                print(f"Warning: Error making data local: {str(e)}")
                # Continue anyway - not critical
                # Try to deselect even if it failed
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                except Exception:
                    pass  # Deselection may fail

            # Step 4: Refresh all modifiers
            print("\n[4/10] Refreshing modifiers...")
            try:
                refresh_all_modifiers(context)
                print("✓ Modifiers refreshed")
            except Exception as e:
                print(f"Warning: Error refreshing modifiers: {str(e)}")
                # Continue anyway - not critical

            # Step 5: Realize & mesh all eligible objects
            print("\n[5/10] Realizing and meshing objects...")
            try:
                success_count, skip_count, error_count = realize_and_mesh_all(context)
                print(f"✓ Realize complete: {success_count} success, {skip_count} skipped, {error_count} errors")

                if error_count > 0:
                    self.report({'WARNING'}, f"Some objects failed to realize ({error_count} errors)")
            except Exception as e:
                self.report({'ERROR'}, f"Critical error during realize: {str(e)}")
                print(f"ERROR: {str(e)}\n")
                # Try to recover by opening original file
                try:
                    bpy.ops.wm.open_mainfile(filepath=original_filepath)
                    print(f"Recovered by opening: {os.path.basename(original_filepath)}")
                except Exception:
                    pass  # File may not exist or be inaccessible
                return {'CANCELLED'}

            # Force scene and context updates after realize/mesh operations
            print("Updating scene and depsgraph...")
            context.view_layer.update()
            bpy.context.evaluated_depsgraph_get().update()
            print("✓ Scene updated")

            # Step 6: Remove empty material slots
            print("\n[6/10] Removing empty material slots...")
            try:
                empty_slots_removed, objects_cleaned, skipped_objects = remove_empty_material_slots(context)
                if empty_slots_removed > 0:
                    print(f"✓ Removed {empty_slots_removed} empty material slot(s) from {objects_cleaned} object(s)")
                else:
                    print("✓ No empty material slots found")

                if skipped_objects:
                    print(f"Warning: Skipped {len(skipped_objects)} object(s) not in view layer")
            except Exception as e:
                print(f"Warning: Error removing empty material slots: {str(e)}")
                # Continue anyway - not critical

            # Step 7: Make everything local again (second pass)
            print("\n[7/10] Making everything local (second pass)...")
            try:
                # After realize/mesh operations, new objects and data may have been created
                # that reference linked data. Run make_local again to ensure everything is local.

                # Ensure we're in object mode
                if context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                # Select all objects
                bpy.ops.object.select_all(action='SELECT')

                # Run make_local with type='ALL' (native Blender operator)
                # This includes objects, materials, meshes, textures, node groups, etc.
                bpy.ops.object.make_local(type='ALL')

                print("✓ Made all data blocks local (objects, materials, meshes, textures, etc.)")

                # Deselect all after operation
                bpy.ops.object.select_all(action='DESELECT')
            except Exception as e:
                print(f"Warning: Error making everything local: {str(e)}")
                print(f"  You may need to manually make data local in the export file")
                # Continue anyway - not critical
                # Try to deselect even if it failed
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                except Exception:
                    pass  # Deselection may fail

            # Step 7b: Remove empty material slots (again)
            print("\n[7b/10] Removing empty material slots (second pass)...")
            try:
                empty_slots_removed, objects_cleaned, skipped_objects = remove_empty_material_slots(context)
                if empty_slots_removed > 0:
                    print(f"✓ Removed {empty_slots_removed} empty material slot(s) from {objects_cleaned} object(s)")
                else:
                    print("✓ No empty material slots found")

                if skipped_objects:
                    print(f"Warning: Skipped {len(skipped_objects)} object(s) not in view layer")
            except Exception as e:
                print(f"Warning: Error removing empty material slots: {str(e)}")
                # Continue anyway - not critical

            # Step 8: Validate all materials and update CSP configs
            print("\n[8/10] Validating all materials and CSP configs...")
            try:
                # Unified validation with CSP detection (GrassFX, RainFX)
                stats = validate_all_materials(context, run_csp_detection=True)
                print(f"✓ Validated {stats['materials_validated']} materials")
                if stats['materials_upgraded'] > 0:
                    print(f"  Upgraded {stats['materials_upgraded']} shader(s)")
                if stats['textures_assigned'] > 0:
                    print(f"  Assigned {stats['textures_assigned']} texture slot(s)")
                if stats['materials_fixed'] > 0:
                    print(f"  Fixed {stats['materials_fixed']} material(s)")
            except Exception as e:
                print(f"Warning: Error validating materials: {str(e)}")
                # Continue anyway - not critical

            # Step 9: Perform KN5 export
            print("\n[9/10] Exporting KN5...")
            result = self._perform_kn5_export(context)

            if result != {'FINISHED'}:
                print("ERROR: KN5 export failed\n")
                # Try to recover by opening original file
                try:
                    bpy.ops.wm.open_mainfile(filepath=original_filepath)
                    print(f"Recovered by opening: {os.path.basename(original_filepath)}")
                except Exception:
                    pass  # File may not exist or be inaccessible
                return result

            print("✓ KN5 export complete")

            # Save the export file
            print("Saving export file...")
            try:
                bpy.ops.wm.save_mainfile()
                print(f"✓ Export file saved: {os.path.basename(export_filepath)}")
            except Exception as e:
                print(f"Warning: Could not save export file: {str(e)}")
                # Not critical - continue

            # Step 10: Save track data and extensions
            print("\n[10/10] Saving track data and ext_config.ini...")
            try:
                # Quick re-validation (no CSP detection needed, already done in step 8)
                validate_all_materials(context, run_csp_detection=False, verbose=False)

                # Get settings and ensure path reference is set
                settings = context.scene.AC_Settings
                from ...utils.files import set_path_reference, get_ui_directory, merge_save_json
                set_path_reference(settings.working_dir)

                # Count pitboxes directly from the scene
                pitbox_count = len(settings.get_pitboxes(context))
                print(f"  Detected {pitbox_count} pitbox(es) in scene")

                # Update the stored pitbox count
                if settings.track.pitboxes != pitbox_count:
                    print(f"  Adjusting pitbox count: {settings.track.pitboxes} → {pitbox_count}")
                    settings.track.pitboxes = pitbox_count

                # Build track data dict with correct pitbox count
                track_data = settings.track.to_dict()
                track_data["pitboxes"] = pitbox_count  # Ensure we use the counted value

                # Save track data directly (not via operator to avoid context issues)
                ui_dir = get_ui_directory()
                merge_save_json(os.path.join(ui_dir, 'ui_track.json'), track_data)
                print(f"✓ Saved ui_track.json (pitboxes: {pitbox_count})")

                # Save all extensions to ext_config.ini
                bpy.ops.ac.save_extensions()
                print("✓ Saved ext_config.ini (all extensions)")
            except Exception as e:
                print(f"Warning: Error saving track data/extensions: {str(e)}")
                import traceback
                traceback.print_exc()
                # Continue anyway - not critical

            # Return to working file
            print("\nReturning to working file...")
            try:
                bpy.ops.wm.open_mainfile(filepath=original_filepath)
                print(f"✓ Returned to: {os.path.basename(original_filepath)}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to open working file: {str(e)}")
                print(f"ERROR: Failed to open working file: {str(e)}\n")
                return {'CANCELLED'}

            print("\n" + "="*60)
            print("SMART EXPORT COMPLETED SUCCESSFULLY")
            print(f"  KN5: {os.path.basename(self.filepath)}")
            print(f"  Export blend: {os.path.basename(export_filepath)}")
            print(f"  Smart Exports folder: {smart_exports_dir}")
            print(f"  Working file: {os.path.basename(original_filepath)}")
            print("="*60 + "\n")

            self.report({'INFO'}, f"Smart Export complete - export files saved to Smart Exports folder")
            return {'FINISHED'}

        except Exception as e:
            error = traceback.format_exc()
            print("\n=== SMART EXPORT ERROR ===")
            print(error)
            print("==========================\n")
            self.report({'ERROR'}, f"Smart Export failed: {str(e)}")
            return {'CANCELLED'}

    def _perform_kn5_export(self, context):
        """Perform the actual KN5 export (used by both workflows)."""
        warnings = []

        # Track objects that need to be renamed with "__" prefix
        renamed_objects = []

        try:
            # Note: texture_writer handles all image sources directly:
            # - Files on disk: reads directly (no packing needed)
            # - Already packed: uses packed data
            # - Generated images: saves to temp file and reads
            # No pre-packing step needed - this prevents blend file bloat

            # Before export: Collect objects that need prefixing
            objects_to_prefix = []
            for obj in list(bpy.data.objects):
                # Skip objects in disabled/excluded collections
                if is_object_excluded_by_collection(obj, context):
                    continue

                should_prefix = False

                # Check if it's a curve object
                if obj.type == 'CURVE':
                    should_prefix = True
                # Check if it's a mesh without materials
                elif obj.type == 'MESH':
                    if not obj.data.materials or len(obj.data.materials) == 0:
                        should_prefix = True
                    # Also check if all material slots are empty
                    elif all(slot.material is None for slot in obj.material_slots):
                        should_prefix = True

                # Add to list if needs prefix (and not already prefixed)
                if should_prefix and not is_hidden_name(obj.name):
                    objects_to_prefix.append(obj)

            # Apply prefixes
            for obj in objects_to_prefix:
                try:
                    original_name = obj.name
                    obj.name = "__" + original_name
                    renamed_objects.append((obj, original_name))
                except AttributeError:
                    # Skip objects with read-only names
                    warnings.append(f"Could not rename object '{obj.name}' (read-only)")
                    continue

            # Perform the export
            output_file = open(self.filepath, "wb")
            try:
                settings = read_settings(self.filepath)
                kn5_writer = KN5FileWriter(output_file, context, settings, warnings)
                kn5_writer.write()

                # Print warnings to console
                if warnings:
                    print("\n=== KN5 Export Warnings ===")
                    for warning in warnings:
                        print(f"  - {warning}")
                    print("===========================\n")

                # Simple success popup
                self.report({'INFO'}, f"KN5 exported successfully: {os.path.basename(self.filepath)}")

            finally:
                if output_file is not None:
                    output_file.close()
        except Exception as e:
            error = traceback.format_exc()

            # Print full error to console
            print("\n=== KN5 Export Error ===")
            print(error)
            if warnings:
                print("\nWarnings before error:")
                for warning in warnings:
                    print(f"  - {warning}")
            print("========================\n")

            try:
                # Remove output file so we can't crash the engine with a broken file
                os.remove(self.filepath)
            except OSError:
                pass

            # Simple error popup
            self.report({'ERROR'}, f"KN5 export failed: {e}")
            return {'CANCELLED'}

        finally:
            # After export: Restore original names
            for obj, original_name in renamed_objects:
                try:
                    obj.name = original_name
                except (AttributeError, ReferenceError):
                    # Object might have been deleted or is no longer accessible
                    pass

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ExportKN5.bl_idname, text="Assetto Corsa (.kn5)")
