from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import bpy

from .constants import KN5_HEADER, KN5_VERSION
from .kn5_writer import KN5Writer
from .material_writer import MaterialWriter
from .node_writer import NodeWriter
from .texture_writer import TextureWriter
from .utils import get_all_texture_nodes
from ...utils.helpers import is_hidden_name

if TYPE_CHECKING:
    from bpy.types import Context


class KN5Exporter(KN5Writer):
    """
    Main KN5 file exporter.

    Orchestrates writing of header, textures, materials, and scene hierarchy.
    """

    def __init__(self, file, context: Context, warnings: list[str]):
        super().__init__(file)
        self.context = context
        self.warnings = warnings

    def write(self) -> None:
        """Write complete KN5 file: header + textures + materials + nodes."""
        self._write_header()
        self._write_content()

    def _write_header(self) -> None:
        """Write KN5 file signature and version."""
        self.file.write(KN5_HEADER)
        self.write_uint(KN5_VERSION)

    def _write_content(self) -> None:
        """Write textures, materials, and scene hierarchy."""
        texture_writer = TextureWriter(self.file, self.context, self.warnings)
        texture_writer.write()

        # Pass texture name mapping to material writer (for PNG->DDS conversions)
        material_writer = MaterialWriter(
            self.file, self.context, {}, self.warnings,
            texture_name_mapping=texture_writer.texture_name_mapping
        )
        material_writer.write()

        node_writer = NodeWriter(self.file, self.context, {}, self.warnings, material_writer)
        node_writer.write()


def copy_textures_to_working_directory(context: Context, warnings: list[str]) -> None:
    """
    Copy all textures used in the scene to the working directory's texture folder.

    Textures are copied to: working_dir/content/textures/

    Args:
        context: Blender context
        warnings: List to append warning messages to
    """
    # Get working directory from settings
    settings = context.scene.AC_Settings
    if not settings.working_dir:
        warnings.append("No working directory set - skipping texture copy")
        return

    # Create texture directory path
    texture_dir = os.path.join(settings.working_dir, "content", "textures")
    os.makedirs(texture_dir, exist_ok=True)

    # Get all texture nodes used in the scene
    texture_nodes = get_all_texture_nodes(context)

    copied_count = 0
    skipped_count = 0

    for texture_node in texture_nodes:
        # Skip textures starting with "__" (hidden)
        if is_hidden_name(texture_node.name):
            continue

        if not texture_node.image:
            continue

        image = texture_node.image

        # Skip images without file paths (generated/procedural)
        if not image.filepath or image.filepath == "":
            if image.source != 'FILE':
                warnings.append(f"Skipping non-file texture: {image.name}")
                skipped_count += 1
                continue

        # Get absolute path to source image
        source_path = bpy.path.abspath(image.filepath)

        if not os.path.exists(source_path):
            warnings.append(f"Texture file not found: {source_path}")
            skipped_count += 1
            continue

        # Determine destination filename
        # Use the image name with original extension
        dest_filename = image.name
        if not os.path.splitext(dest_filename)[1]:
            # If no extension, use the source file's extension
            _, ext = os.path.splitext(source_path)
            dest_filename += ext

        dest_path = os.path.join(texture_dir, dest_filename)

        # Copy file if it doesn't exist or is different
        try:
            if os.path.exists(dest_path):
                # Check if files are different
                if os.path.getmtime(source_path) > os.path.getmtime(dest_path):
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                # else: file already exists and is up to date
            else:
                shutil.copy2(source_path, dest_path)
                copied_count += 1
        except Exception as e:
            warnings.append(f"Failed to copy texture {image.name}: {e}")
            skipped_count += 1

    if copied_count > 0:
        warnings.append(f"Copied {copied_count} texture(s) to {texture_dir}")
    if skipped_count > 0:
        warnings.append(f"Skipped {skipped_count} texture(s)")


def export_kn5(filepath: str, context: Context, copy_textures: bool = True) -> dict[str, str | list[str]]:
    """
    Export scene to KN5 file.

    Uses atomic write pattern: exports to temporary file first, then replaces
    the target file only on success. This prevents corruption of existing files
    if the export fails.

    Args:
        filepath: Output KN5 file path
        context: Blender context
        copy_textures: If True, copies all used textures to working_dir/content/textures/

    Returns:
        Dictionary with 'status' ('success' or 'error') and 'warnings' list
    """
    warnings: list[str] = []
    output_file = None

    # Create temporary file path - write here first to avoid corrupting existing file
    temp_filepath = filepath + ".tmp"

    try:
        # Write to temporary file
        output_file = open(temp_filepath, "wb")
        exporter = KN5Exporter(output_file, context, warnings)
        exporter.write()
        output_file.close()
        output_file = None

        # Copy textures to working directory after successful export
        if copy_textures:
            copy_textures_to_working_directory(context, warnings)

        # Export succeeded - atomically replace target file
        # Use os.replace() which is atomic on both Windows and Unix
        if os.path.exists(filepath):
            os.replace(temp_filepath, filepath)
        else:
            # No existing file, just rename
            os.rename(temp_filepath, filepath)

        return {"status": "success", "warnings": warnings}

    except Exception as e:
        error_trace = traceback.format_exc()
        warnings.append(f"Export failed: {e}")
        warnings.append(error_trace)

        # Remove temporary file to clean up
        try:
            Path(temp_filepath).unlink(missing_ok=True)
        except OSError:
            pass

        return {"status": "error", "warnings": warnings}

    finally:
        if output_file:
            output_file.close()
