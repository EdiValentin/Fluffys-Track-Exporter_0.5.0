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


import os
import subprocess
import tempfile

import bpy

from .kn5_writer import KN5Writer
from .utils import get_all_texture_nodes
from ...utils.helpers import is_hidden_name


DDS_HEADER_BYTES = b"DDS"
PNG_HEADER_BYTES = b"\x89PNG"


def get_real_texture_name(image):
    """
    Get the real texture filename, not Blender's indexed name.

    Blender adds numeric suffixes like '.001', '.002' when multiple images
    have the same name. This function returns the actual filename from disk.

    Args:
        image: Blender image object

    Returns:
        The real filename (e.g., 'diffuse.png' instead of 'diffuse.png.001')
    """
    # If image has a valid filepath, use the actual filename from disk
    if image.filepath and image.filepath != "":
        real_filename = os.path.basename(bpy.path.abspath(image.filepath))
        if real_filename:
            return real_filename

    # Fallback to Blender's name (for generated/packed images without filepath)
    return image.name


def get_addon_root():
    """Get the root directory of the addon."""
    # texture_writer.py is in lib/kn5/, so go up 2 levels
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))


def get_texconv_path():
    """Get the path to texconv.exe."""
    addon_root = get_addon_root()
    return os.path.join(addon_root, "texconv.exe")


def is_png_data(image_data):
    """Check if image data is PNG format."""
    return image_data[:4] == PNG_HEADER_BYTES


def is_dds_data(image_data):
    """Check if image data is DDS format."""
    return image_data[:3] == DDS_HEADER_BYTES


def convert_png_to_dds(png_data, image_name, warnings):
    """
    Convert PNG data to DDS using texconv.exe with BC3 compression.

    Args:
        png_data: Raw PNG file bytes
        image_name: Name of the image (for error messages)
        warnings: List to append warnings to

    Returns:
        Tuple of (dds_data, new_name) or (None, None) if conversion failed
    """
    texconv_path = get_texconv_path()

    if not os.path.exists(texconv_path):
        warnings.append(f"texconv.exe not found at {texconv_path} - PNG will not be converted")
        return None, None

    # Create temp directory for conversion
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write PNG to temp file
        png_filename = os.path.splitext(image_name)[0] + ".png"
        png_path = os.path.join(temp_dir, png_filename)

        with open(png_path, "wb") as f:
            f.write(png_data)

        # Run texconv with BC3 compression
        # -f BC3_UNORM: BC3 format (DXT5) - good for textures with alpha
        # -y: Overwrite existing files
        # -o: Output directory
        # -sepalpha: Separate alpha for better quality
        cmd = [
            texconv_path,
            "-f", "BC3_UNORM",
            "-y",
            "-sepalpha",
            "-o", temp_dir,
            png_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # texconv outputs .dds file with same base name
            dds_filename = os.path.splitext(png_filename)[0] + ".dds"
            dds_path = os.path.join(temp_dir, dds_filename)

            if os.path.exists(dds_path):
                with open(dds_path, "rb") as f:
                    dds_data = f.read()

                # New name uses .dds extension
                new_name = os.path.splitext(image_name)[0] + ".dds"
                return dds_data, new_name
            else:
                warnings.append(f"texconv did not create output file for '{image_name}'")
                return None, None

        except subprocess.CalledProcessError as e:
            warnings.append(f"texconv failed for '{image_name}': {e.stderr}")
            return None, None
        except Exception as e:
            warnings.append(f"Error converting '{image_name}' to DDS: {str(e)}")
            return None, None


class TextureWriter(KN5Writer):
    def __init__(self, file, context, warnings):
        super().__init__(file)

        self.available_textures = {}
        self.texture_positions = {}
        self.warnings = warnings
        self.context = context

        # Mapping of original image name -> output texture name (for PNG->DDS conversions)
        self.texture_name_mapping = {}

        # Store processed texture data: name -> (output_name, data_bytes)
        self._processed_textures = {}

        self._fill_available_image_textures()

    def write(self):
        # Process all textures first (convert PNGs to DDS)
        self._process_all_textures()

        # Write texture count
        self.write_int(len(self._processed_textures))

        # Write textures in position order
        for texture_name, _position in sorted(self.texture_positions.items(), key=lambda k: k[1]):
            output_name, image_data = self._processed_textures[texture_name]
            self._write_texture_data(output_name, image_data)

    def _write_texture_data(self, texture_name, image_data):
        """Write a single texture's data to the file."""
        is_active = 1
        self.write_int(is_active)
        self.write_string(texture_name)
        self.write_blob(image_data)

    def _fill_available_image_textures(self):
        self.available_textures = {}
        self.texture_positions = {}
        position = 0

        all_texture_nodes = get_all_texture_nodes(self.context)
        for texture_node in all_texture_nodes:
            if not is_hidden_name(texture_node.name):
                if not texture_node.image:
                    self.warnings.append(f"Ignoring texture node without image '{texture_node.name}'")
                elif not texture_node.image.pixels:
                    self.warnings.append(f"Ignoring texture node without image data '{texture_node.name}'")
                else:
                    self.available_textures[texture_node.image.name] = texture_node
                    self.texture_positions[texture_node.image.name] = position
                    position += 1

    def _process_all_textures(self):
        """Process all textures, converting PNGs to DDS where possible."""
        self._processed_textures = {}
        self.texture_name_mapping = {}

        for blender_name in self.available_textures:
            texture_node = self.available_textures[blender_name]
            output_name, image_data = self._process_texture(texture_node)

            self._processed_textures[blender_name] = (output_name, image_data)

            # Track name mapping: Blender's indexed name -> real output name
            # This handles both:
            # 1. Blender indexing: 'diffuse.png.001' -> 'diffuse.png'
            # 2. PNG to DDS conversion: 'diffuse.png' -> 'diffuse.dds'
            # Combined: 'diffuse.png.001' -> 'diffuse.dds'
            if output_name != blender_name:
                self.texture_name_mapping[blender_name] = output_name

    def _process_texture(self, texture_node):
        """
        Process a single texture, converting PNG to DDS if applicable.

        Uses the real filename from disk, not Blender's indexed name.

        Returns:
            Tuple of (output_name, image_data)
        """
        image = texture_node.image

        # Get real filename (not Blender's indexed name like 'texture.png.001')
        real_name = get_real_texture_name(image)

        # Get the raw image data
        image_data = self._get_raw_image_data(texture_node)

        # Check if it's already DDS - use as-is
        if is_dds_data(image_data):
            return real_name, image_data

        # Check if it's PNG - convert to DDS
        if is_png_data(image_data):
            dds_data, new_name = convert_png_to_dds(image_data, real_name, self.warnings)
            if dds_data is not None:
                self.warnings.append(f"Converted '{real_name}' to DDS ({len(image_data)} → {len(dds_data)} bytes)")
                return new_name, dds_data
            else:
                # Conversion failed, fall back to PNG
                self.warnings.append(f"Using original PNG for '{real_name}' (conversion failed)")
                return real_name, image_data

        # Other formats - use as-is
        return real_name, image_data

    def _get_raw_image_data(self, texture_node):
        """
        Get raw image data from a texture node without packing PNGs into the blend file.

        For external files, reads directly from disk.
        For packed files, returns the packed data.
        """
        image = texture_node.image

        # If image has a valid filepath, read from disk (don't pack into blend)
        if image.filepath and image.filepath != "":
            abs_path = bpy.path.abspath(image.filepath)
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as f:
                    return f.read()

        # If image is already packed, use packed data
        if image.packed_file:
            return image.packed_file.data

        # If image is generated/has pixel data but no file, we need to save it temporarily
        if image.pixels:
            # Save to temp file and read back
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = os.path.join(temp_dir, image.name)
                # Ensure it has an extension
                if not os.path.splitext(temp_path)[1]:
                    temp_path += ".png"

                # Save the image
                original_filepath = image.filepath
                original_format = image.file_format
                try:
                    image.filepath_raw = temp_path
                    image.file_format = 'PNG'
                    image.save()

                    with open(temp_path, "rb") as f:
                        return f.read()
                finally:
                    # Restore original settings
                    image.filepath_raw = original_filepath
                    image.file_format = original_format

        raise RuntimeError(
            f"Cannot get image data for '{image.name}' - no file path, not packed, and no pixel data. "
            f"Please ensure the image file exists or pack it manually."
        )
