"""
Centralized ext_config.ini management for CSP extensions.

This module provides a unified approach to reading, writing, and updating
the ext_config.ini file with consistent section ordering and smart merging.

Section Order:
1. INCLUDE (required for CSP conditions)
2. GRASS_FX
3. RAIN_FX
4. TREES (managed by TreeFX operator only - never touched here)
5. CSP Lights (LIGHTING, LIGHT_*, LIGHT_SERIES_*)
6. Emissive Materials (MATERIAL_ADJUSTMENT_*)
7. Shader Replacements (SHADER_REPLACEMENT_*, includes ksTree flag)
8. Global Extensions (preserved custom user sections)
"""

import os
import re
from datetime import datetime
from typing import Optional

from ...utils.helpers import is_hidden_name


# =============================================================================
# CONSTANTS
# =============================================================================

# Timestamp format for tracking file modifications
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_PREFIX = "; Last Updated: "

# Section identifiers for ordering
SECTION_ORDER = [
    "INCLUDE",
    "GRASS_FX",
    "RAIN_FX",
    "TREES",  # Never written by save_extensions, only by TreeFX
    "LIGHTING",
    "LIGHT_SERIES_",  # Prefix - matches LIGHT_SERIES_0, LIGHT_SERIES_1, etc.
    "LIGHT_",  # Prefix - matches LIGHT_0, LIGHT_1, etc. (must come after LIGHT_SERIES_)
    "MATERIAL_ADJUSTMENT_",  # Prefix
    "SHADER_REPLACEMENT_",  # Prefix (includes ksTree flag)
]

# Sections that are managed by specific operators and should be preserved
TREES_SECTION = "TREES"  # Managed only by TreeFX operator

# Prefixes for numbered sections
NUMBERED_SECTION_PREFIXES = [
    "LIGHT_SERIES_",
    "LIGHT_",
    "MATERIAL_ADJUSTMENT_",
    "SHADER_REPLACEMENT_",
]

# ALL section names/prefixes that this addon manages
# Used to determine which sections should be replaced (not preserved) on export
ALL_MANAGED_SECTIONS = [
    "INCLUDE",
    "GRASS_FX",
    "RAIN_FX",
    # "TREES" is NOT included - managed only by TreeFX operator
    "LIGHTING",
    "LIGHT_SERIES_",
    "LIGHT_",
    "MATERIAL_ADJUSTMENT_",
    "SHADER_REPLACEMENT_",  # Includes ksTree flag
]

# Separator line pattern (used to detect our generated headers)
SEPARATOR_LINE = "; ============================================================================="

# Section category headers for visual separation
SECTION_CATEGORIES = {
    "INCLUDE": f"{SEPARATOR_LINE}\n; INCLUDES\n{SEPARATOR_LINE}\n",
    "GRASS_FX": f"\n{SEPARATOR_LINE}\n; GRASS FX\n{SEPARATOR_LINE}\n",
    "RAIN_FX": f"\n{SEPARATOR_LINE}\n; RAIN FX\n{SEPARATOR_LINE}\n",
    "TREES": f"\n{SEPARATOR_LINE}\n; TREES\n{SEPARATOR_LINE}\n",
    "LIGHTING": f"\n{SEPARATOR_LINE}\n; CSP LIGHTS\n{SEPARATOR_LINE}\n",
    "MATERIAL_ADJUSTMENT_": f"\n{SEPARATOR_LINE}\n; EMISSIVE MATERIALS\n{SEPARATOR_LINE}\n",
    "SHADER_REPLACEMENT_": f"\n{SEPARATOR_LINE}\n; SHADER REPLACEMENTS\n{SEPARATOR_LINE}\n",
}

# Footer header for user custom sections (always present)
USER_SECTIONS_HEADER = f"\n{SEPARATOR_LINE}\n; USER CUSTOM SECTIONS\n{SEPARATOR_LINE}\n"


# =============================================================================
# PARSING
# =============================================================================

def parse_ext_config(filepath: str) -> dict:
    """
    Parse ext_config.ini into a dictionary of sections.

    Handles auto-indexed sections (e.g., [SHADER_REPLACEMENT_...]) by converting
    them to numbered format (SHADER_REPLACEMENT_0, SHADER_REPLACEMENT_1, etc.)
    for consistent comparison with addon-generated sections.

    Args:
        filepath: Path to ext_config.ini

    Returns:
        Dict of {section_name: {key: value, ...}, ...}
    """
    if not os.path.exists(filepath):
        return {}

    sections = {}
    current_section = None
    # Track counters for auto-indexed section types
    auto_index_counters = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith(';') or line.startswith('#'):
                continue

            # Section header
            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1]

                # Handle auto-indexed sections (e.g., SHADER_REPLACEMENT_...)
                if section_name.endswith('_...'):
                    prefix = section_name[:-3]  # Remove '...'
                    if prefix not in auto_index_counters:
                        auto_index_counters[prefix] = 0
                    section_name = f"{prefix}{auto_index_counters[prefix]}"
                    auto_index_counters[prefix] += 1

                current_section = section_name
                if current_section not in sections:
                    sections[current_section] = {}
                continue

            # Key-value pair
            if current_section and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                sections[current_section][key] = value

    return sections


# =============================================================================
# SECTION ORDERING
# =============================================================================

def get_section_sort_key(section_name: str) -> tuple:
    """
    Get sort key for a section to maintain consistent ordering.

    Returns tuple of (order_index, numeric_suffix) for stable sorting.
    """
    # Check exact matches first
    for i, pattern in enumerate(SECTION_ORDER):
        if section_name == pattern:
            return (i, 0)

    # Check prefix matches for numbered sections
    for i, pattern in enumerate(SECTION_ORDER):
        if pattern.endswith('_') and section_name.startswith(pattern):
            # Extract numeric suffix for sub-ordering
            suffix = section_name[len(pattern):]
            try:
                num = int(suffix)
            except ValueError:
                num = 9999
            return (i, num)

    # Unknown sections go at the end (global extensions)
    return (999, 0)


def sort_sections(sections: dict) -> list:
    """
    Sort section names according to the defined order.

    Args:
        sections: Dict of sections

    Returns:
        List of section names in correct order
    """
    return sorted(sections.keys(), key=get_section_sort_key)


# =============================================================================
# VALUE FORMATTING
# =============================================================================

def format_value(value) -> str:
    """
    Format a value for INI output with consistent formatting.

    Args:
        value: Value to format (str, int, float, bool, tuple, list)

    Returns:
        Formatted string value
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, float):
        # Use reasonable precision, strip trailing zeros
        formatted = f"{value:.6f}".rstrip('0').rstrip('.')
        return formatted
    elif isinstance(value, (tuple, list)):
        # Format each element and join with comma
        return ", ".join(format_value(v) for v in value)
    else:
        return str(value)


# =============================================================================
# WRITING
# =============================================================================

def _is_managed_section(section_name: str, managed_prefixes: list) -> bool:
    """Check if a section name matches any of the managed prefixes."""
    for prefix in managed_prefixes:
        if section_name == prefix or section_name.startswith(prefix):
            return True
    return False


def _is_generated_header_line(line: str) -> bool:
    """Check if a line is one of our generated category headers."""
    stripped = line.strip()
    # Check for separator line
    if stripped.startswith('; ===') and stripped.endswith('==='):
        return True
    # Check for category title lines (e.g., "; INCLUDES", "; GRASS FX", etc.)
    category_titles = [
        "; INCLUDES", "; GRASS FX", "; RAIN FX", "; TREES",
        "; CSP LIGHTS", "; EMISSIVE MATERIALS", "; SHADER REPLACEMENTS",
        "; USER CUSTOM SECTIONS"
    ]
    if stripped in category_titles:
        return True
    return False


def _filter_generated_headers(lines: list) -> list:
    """Filter out our generated category headers from a list of lines."""
    return [line for line in lines if not _is_generated_header_line(line)]


def _is_timestamp_line(line: str) -> bool:
    """Check if a line is our timestamp line."""
    return line.strip().startswith(TIMESTAMP_PREFIX)


def _filter_timestamp(lines: list) -> list:
    """Filter out our timestamp line from a list of lines."""
    return [line for line in lines if not _is_timestamp_line(line)]


def _generate_timestamp_line() -> str:
    """Generate a timestamp line with current date/time."""
    now = datetime.now().strftime(TIMESTAMP_FORMAT)
    return f"{TIMESTAMP_PREFIX}{now}\n"


def read_timestamp(filepath: str) -> Optional[datetime]:
    """
    Read the timestamp from an ext_config.ini file.

    Args:
        filepath: Path to ext_config.ini

    Returns:
        datetime object if timestamp found, None otherwise
    """
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith(TIMESTAMP_PREFIX):
                try:
                    timestamp_str = line.strip()[len(TIMESTAMP_PREFIX):]
                    return datetime.strptime(timestamp_str, TIMESTAMP_FORMAT)
                except ValueError:
                    return None
            # Only check first few lines (timestamp should be at the top)
            if line.strip().startswith('['):
                break
    return None


def _parse_file_structure(filepath: str) -> tuple:
    """
    Parse file into structured sections while preserving raw content.

    Handles auto-indexed sections (e.g., [SHADER_REPLACEMENT_...]) by converting
    them to numbered format for consistent handling.

    Returns:
        Tuple of (header_lines, section_blocks, footer_lines)
        - header_lines: Lines before first section
        - section_blocks: List of (section_name, raw_lines) tuples
        - footer_lines: Lines after last section (text outside any section)
    """
    if not os.path.exists(filepath):
        return [], [], []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header_lines = []
    section_blocks = []
    footer_lines = []
    current_section = None
    current_lines = []
    # Track counters for auto-indexed section types
    auto_index_counters = {}

    for line in lines:
        stripped = line.strip()

        # Check for section header
        if stripped.startswith('[') and stripped.endswith(']'):
            # Save previous section if exists
            if current_section is not None:
                section_blocks.append((current_section, current_lines))
            elif current_lines:
                # These are header lines (before first section)
                header_lines = current_lines

            # Start new section
            section_name = stripped[1:-1]

            # Handle auto-indexed sections (e.g., SHADER_REPLACEMENT_...)
            if section_name.endswith('_...'):
                prefix = section_name[:-3]  # Remove '...'
                if prefix not in auto_index_counters:
                    auto_index_counters[prefix] = 0
                section_name = f"{prefix}{auto_index_counters[prefix]}"
                auto_index_counters[prefix] += 1

            current_section = section_name
            current_lines = [line]
        else:
            current_lines.append(line)

    # Handle remaining content
    if current_section is not None:
        section_blocks.append((current_section, current_lines))
    elif current_lines:
        # File has no sections, all content is header
        header_lines = current_lines

    # Check if there's footer content (lines after last section that aren't part of it)
    # This handles text added at the very end of the file outside any section
    if section_blocks:
        last_name, last_lines = section_blocks[-1]
        # Find where section content ends (last non-empty line that's part of section)
        footer_start = len(last_lines)
        for i in range(len(last_lines) - 1, 0, -1):
            stripped = last_lines[i].strip()
            if stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                if '=' in stripped:
                    footer_start = i + 1
                    break

        # Check if there's actual footer content (non-blank lines after section content)
        potential_footer = last_lines[footer_start:]
        has_footer_content = any(l.strip() and not l.strip().startswith(';')
                                 and not l.strip().startswith('#')
                                 and '=' not in l for l in potential_footer)

        if has_footer_content:
            # Move footer content out of last section
            section_blocks[-1] = (last_name, last_lines[:footer_start])
            footer_lines = potential_footer

    # Filter out our generated category headers and timestamp from preserved content
    # This prevents duplicate headers/timestamps on re-export
    header_lines = _filter_timestamp(_filter_generated_headers(header_lines))
    footer_lines = _filter_generated_headers(footer_lines)

    return header_lines, section_blocks, footer_lines


def _format_section(section_name: str, section_data: dict) -> list:
    """Format a section as a list of lines."""
    # Convert numbered sections to auto-index format for easier user editing
    output_name = section_name
    if re.match(r'^SHADER_REPLACEMENT_\d+$', section_name):
        output_name = "SHADER_REPLACEMENT_..."
    elif re.match(r'^MATERIAL_ADJUSTMENT_\d+$', section_name):
        output_name = "MATERIAL_ADJUSTMENT_..."

    # Note: AC INI format uses KEY=VALUE without spaces around =
    lines = [f"[{output_name}]\n"]
    for key, value in section_data.items():
        formatted_value = format_value(value)
        lines.append(f"{key}={formatted_value}\n")
    lines.append("\n")
    return lines


def _get_category_header(section_name: str) -> Optional[str]:
    """
    Get the category header for a section (if it's the first in its category).

    Returns the header string or None if no header needed.
    """
    # Check exact matches first
    if section_name in SECTION_CATEGORIES:
        return SECTION_CATEGORIES[section_name]

    # Check prefix matches for numbered sections
    for prefix, header in SECTION_CATEGORIES.items():
        if prefix.endswith('_') and section_name.startswith(prefix):
            return header

    return None


def _get_category_key(section_name: str) -> str:
    """Get the category key for a section (for tracking which headers we've written)."""
    # Check prefix matches for numbered sections
    for prefix in SECTION_CATEGORIES.keys():
        if prefix.endswith('_') and section_name.startswith(prefix):
            return prefix

    # Exact match
    return section_name


def write_ext_config(filepath: str, sections: dict,
                     preserve_sections: Optional[list] = None) -> None:
    """
    Write sections to ext_config.ini with consistent ordering.

    Preserves:
    - User comments and text outside managed sections
    - Sections listed in preserve_sections
    - Header content (before first section)
    - Footer content (after last section)

    Args:
        filepath: Output path
        sections: Dict of {section_name: {key: value, ...}, ...}
        preserve_sections: List of section names to preserve from existing file
                          (e.g., ['TREES'] to not overwrite TreeFX data)
    """
    preserve_sections = preserve_sections or []

    # Use ALL managed sections/prefixes - this ensures removed sections are deleted
    # (not accidentally preserved as "unmanaged")
    managed_prefixes = [s for s in ALL_MANAGED_SECTIONS if s not in preserve_sections]

    # Parse existing file structure
    header_lines, section_blocks, footer_lines = _parse_file_structure(filepath)

    # Collect preserved sections from existing file
    preserved_blocks = {}
    unmanaged_blocks = []

    for section_name, raw_lines in section_blocks:
        if section_name in preserve_sections:
            preserved_blocks[section_name] = raw_lines
        elif not _is_managed_section(section_name, managed_prefixes):
            # Unknown section - preserve it (user's custom section)
            unmanaged_blocks.append((section_name, raw_lines))

    # Merge preserved sections into output
    output_sections = dict(sections)

    # Add preserved section names so they appear in sorted output
    for section_name in preserve_sections:
        if section_name in preserved_blocks and section_name not in output_sections:
            output_sections[section_name] = {}  # Placeholder - actual content from preserved_blocks

    # Sort sections for output
    sorted_names = sort_sections(output_sections)

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Build output
    output_lines = []

    # Add timestamp as the very first line
    output_lines.append(_generate_timestamp_line())

    # Add header (preserved comments/text before first section)
    if header_lines:
        output_lines.extend(header_lines)
        # Add blank line after user header before our content
        if not output_lines[-1].endswith('\n\n'):
            output_lines.append('\n')

    # Track which category headers we've written
    written_categories = set()

    # Add managed sections in correct order (with category headers)
    for section_name in sorted_names:
        # Add category header if this is the first section in its category
        category_key = _get_category_key(section_name)
        if category_key not in written_categories:
            header = _get_category_header(section_name)
            if header:
                output_lines.append(header)
            written_categories.add(category_key)

        if section_name in preserve_sections and section_name in preserved_blocks:
            # Write preserved raw content (filter out our generated headers to avoid duplicates)
            filtered_lines = _filter_generated_headers(preserved_blocks[section_name])
            output_lines.extend(filtered_lines)
        else:
            # Write new section data
            section_data = output_sections[section_name]
            output_lines.extend(_format_section(section_name, section_data))

    # Always add USER CUSTOM SECTIONS header at the end
    # This provides a clear place for users to add their own configurations
    output_lines.append(USER_SECTIONS_HEADER)

    # Add any unmanaged sections (user's custom sections)
    for section_name, raw_lines in unmanaged_blocks:
        # Filter out our generated headers from raw content
        filtered_lines = _filter_generated_headers(raw_lines)
        # Strip leading blank lines to prevent accumulation
        while filtered_lines and filtered_lines[0].strip() == '':
            filtered_lines.pop(0)
        output_lines.extend(filtered_lines)

    # Add footer (preserved text after last section)
    # Strip leading blank lines to prevent accumulation
    while footer_lines and footer_lines[0].strip() == '':
        footer_lines.pop(0)
    output_lines.extend(footer_lines)

    # Strip trailing blank lines to prevent accumulation on each save
    while output_lines and output_lines[-1].strip() == '':
        output_lines.pop()
    # Ensure file ends with single newline
    if output_lines and not output_lines[-1].endswith('\n'):
        output_lines[-1] += '\n'

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)


def update_sections(filepath: str, sections: dict,
                    managed_prefixes: list) -> None:
    """
    Update only specific sections in ext_config.ini, preserving everything else.

    This is used by dedicated updaters (lights, emissive) that only want to
    modify their own sections without touching the rest of the file.

    Produces consistent formatted output with category headers (same as write_ext_config).

    Preserves:
    - All sections not matching managed_prefixes
    - User custom sections (unrecognized by addon)
    - Footer content

    Args:
        filepath: Path to ext_config.ini
        sections: Dict of sections to write/update
        managed_prefixes: List of section name prefixes that this update manages
                         (e.g., ['LIGHT_', 'LIGHT_SERIES_', 'LIGHTING'] for lights)
    """
    # Parse existing file structure
    header_lines, section_blocks, footer_lines = _parse_file_structure(filepath)

    # Separate preserved vs managed sections, and identify user custom sections
    preserved_blocks = {}  # Known addon sections to preserve
    unmanaged_blocks = []  # User custom sections (unknown to addon)

    for section_name, raw_lines in section_blocks:
        if not _is_managed_section(section_name, managed_prefixes):
            # Check if it's a known addon section or a user custom section
            if _is_managed_section(section_name, ALL_MANAGED_SECTIONS):
                # Known addon section, preserve it
                preserved_blocks[section_name] = raw_lines
            else:
                # User custom section
                unmanaged_blocks.append((section_name, raw_lines))

    # Combine preserved and new sections
    all_sections = {}

    # Add preserved sections (parse raw content to get section data for sorting)
    for section_name, raw_lines in preserved_blocks.items():
        section_data = {}
        for line in raw_lines:
            stripped = line.strip()
            if '=' in stripped and not stripped.startswith(';') and not stripped.startswith('#'):
                key, _, value = stripped.partition('=')
                section_data[key.strip()] = value.strip()
        all_sections[section_name] = section_data

    # Add new/updated sections
    all_sections.update(sections)

    # Sort all sections
    sorted_names = sort_sections(all_sections)

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Build output
    output_lines = []

    # Add timestamp as the very first line
    output_lines.append(_generate_timestamp_line())

    # Track which category headers we've written
    written_categories = set()

    # Write sections in order (with category headers)
    for section_name in sorted_names:
        # Add category header if this is the first section in its category
        category_key = _get_category_key(section_name)
        if category_key not in written_categories:
            header = _get_category_header(section_name)
            if header:
                output_lines.append(header)
            written_categories.add(category_key)

        if section_name in preserved_blocks:
            # Write preserved raw content (filter out our generated headers to avoid duplicates)
            filtered_lines = _filter_generated_headers(preserved_blocks[section_name])
            # Strip trailing blank lines to prevent accumulation
            while filtered_lines and filtered_lines[-1].strip() == '':
                filtered_lines.pop()
            output_lines.extend(filtered_lines)
            output_lines.append('\n')  # Add single trailing newline
        else:
            # Write new section
            output_lines.extend(_format_section(section_name, sections[section_name]))

    # Always add USER CUSTOM SECTIONS header at the end
    output_lines.append(USER_SECTIONS_HEADER)

    # Add any unmanaged sections (user's custom sections)
    for section_name, raw_lines in unmanaged_blocks:
        # Filter out our generated headers from raw content
        filtered_lines = _filter_generated_headers(raw_lines)
        # Strip leading blank lines to prevent accumulation
        while filtered_lines and filtered_lines[0].strip() == '':
            filtered_lines.pop(0)
        output_lines.extend(filtered_lines)

    # Add footer (preserved text after last section)
    # Strip leading blank lines to prevent accumulation
    while footer_lines and footer_lines[0].strip() == '':
        footer_lines.pop(0)
    output_lines.extend(footer_lines)

    # Strip trailing blank lines to prevent accumulation on each save
    while output_lines and output_lines[-1].strip() == '':
        output_lines.pop()
    # Ensure file ends with single newline
    if output_lines and not output_lines[-1].endswith('\n'):
        output_lines[-1] += '\n'

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def build_include_section() -> dict:
    """Build the INCLUDE section for CSP conditions."""
    return {
        "INCLUDE": "common/conditions.ini"
    }


def collect_all_sections(context, include_shader_replacements: bool = True) -> dict:
    """
    Collect all ext_config sections from addon settings.

    This is the main aggregation function that gathers data from all
    PropertyGroups and builds the complete ext_config structure.

    Args:
        context: Blender context
        include_shader_replacements: Whether to include SHADER_REPLACEMENT sections

    Returns:
        Dict of all sections ready for writing
    """
    settings = context.scene.AC_Settings
    sections = {}

    # 1. INCLUDE section (always present)
    sections["INCLUDE"] = build_include_section()

    # 2. GRASS_FX
    grassfx_dict = settings.grassfx.to_dict()
    if grassfx_dict:
        sections.update(grassfx_dict)

    # 3. RAIN_FX
    rainfx_dict = settings.rainfx.to_dict()
    if rainfx_dict:
        sections["RAIN_FX"] = rainfx_dict

    # 4. TREES - NOT included here, managed by TreeFX operator only

    # 5. CSP LIGHTS
    # Global lighting settings
    sections["LIGHTING"] = settings.lighting.global_lighting.to_dict()

    # Individual lights
    spot_index = 0
    series_index = 0
    for light in settings.lighting.lights:
        if not light.active:
            continue
        light_data = light.to_dict()
        if light.light_type == "SERIES":
            sections[f"LIGHT_SERIES_{series_index}"] = light_data
            series_index += 1
        else:
            sections[f"LIGHT_{spot_index}"] = light_data
            spot_index += 1

    # 7. EMISSIVE MATERIALS
    emissive_light_offset = spot_index  # Continue LIGHT_ numbering for emit_light
    for idx, emissive in enumerate(settings.lighting.emissive_materials):
        if not emissive.active:
            continue

        # MATERIAL_ADJUSTMENT for visual glow
        sections[f"MATERIAL_ADJUSTMENT_{idx}"] = emissive.to_dict()

        # LIGHT_X entries for emit_light enabled emissives
        if emissive.emit_light:
            for light_data in emissive.to_light_dicts():
                sections[f"LIGHT_{emissive_light_offset}"] = light_data
                emissive_light_offset += 1

    # 8. SHADER REPLACEMENTS
    if include_shader_replacements:
        shader_sections = _collect_shader_replacements(context)
        sections.update(shader_sections)

    # 9. GLOBAL EXTENSIONS (custom user sections)
    for extension in settings.global_extensions:
        ext_data = {}
        for item in extension.items:
            ext_data[item.key] = item.value
        if ext_data:
            sections[extension.name] = ext_data

    return sections


def collect_light_sections(context) -> dict:
    """
    Collect only light-related sections for dedicated light updater.

    Returns:
        Dict with LIGHTING, LIGHT_*, LIGHT_SERIES_* sections
    """
    settings = context.scene.AC_Settings
    sections = {}

    # INCLUDE (needed for conditions)
    sections["INCLUDE"] = build_include_section()

    # Global lighting settings
    sections["LIGHTING"] = settings.lighting.global_lighting.to_dict()

    # Individual lights
    spot_index = 0
    series_index = 0
    for light in settings.lighting.lights:
        if not light.active:
            continue
        light_data = light.to_dict()
        if light.light_type == "SERIES":
            sections[f"LIGHT_SERIES_{series_index}"] = light_data
            series_index += 1
        else:
            sections[f"LIGHT_{spot_index}"] = light_data
            spot_index += 1

    return sections


def collect_emissive_sections(context) -> dict:
    """
    Collect only emissive material sections for dedicated emissive updater.

    Returns:
        Dict with MATERIAL_ADJUSTMENT_* sections (and LIGHT_* for emit_light)
    """
    settings = context.scene.AC_Settings
    sections = {}

    # INCLUDE (needed for conditions)
    sections["INCLUDE"] = build_include_section()

    light_index = 0
    for idx, emissive in enumerate(settings.lighting.emissive_materials):
        if not emissive.active:
            continue

        # MATERIAL_ADJUSTMENT for visual glow
        sections[f"MATERIAL_ADJUSTMENT_{idx}"] = emissive.to_dict()

        # LIGHT_X entries for emit_light enabled emissives
        if emissive.emit_light:
            for light_data in emissive.to_light_dicts():
                sections[f"LIGHT_{light_index}"] = light_data
                light_index += 1

    return sections


# =============================================================================
# HELPERS
# =============================================================================

def _collect_shader_replacements(context) -> dict:
    """
    Collect SHADER_REPLACEMENT sections for material property overrides.

    Always adds a global LOD section as SHADER_REPLACEMENT_0 that applies to all meshes.
    Then includes material-specific shader replacements.
    Includes ksTree flag as the final SHADER_REPLACEMENT_N if any ksTree materials exist.
    """
    import bpy
    from ...utils.helpers import get_visible_materials

    sections = {}

    # Always add global LOD settings as the first SHADER_REPLACEMENT_0
    sections["SHADER_REPLACEMENT_0"] = {
        "ACTIVE": 1,
        "MESHES": "?",
        "LOD_IN": 0,
        "LOD_OUT": 500,
    }

    # Start material-specific shader replacements from index 1
    idx = 1
    has_kstree = False

    # Get visible material names to filter by
    visible_material_names = get_visible_materials(context)

    for material in bpy.data.materials:
        # Skip materials without node trees or hidden materials
        if not material.node_tree or is_hidden_name(material.name):
            continue

        # Skip unused materials
        if material.users == 0:
            continue

        # Skip materials not on visible objects
        if material.name not in visible_material_names:
            continue

        # Check if material has AC settings
        if not hasattr(material, 'AC_Material'):
            continue

        ac_mat = material.AC_Material
        shader_name = ac_mat.shader_name
        if not shader_name:
            continue

        # Track if we have any ksTree materials (we'll add the flag at the end)
        if shader_name == "ksTree":
            has_kstree = True
            continue  # Don't create individual shader replacements for ksTree

        # Build section data
        section_data = {
            "MATERIALS": material.name,
            "SHADER": shader_name,
        }

        # Add shader properties
        prop_idx = 0
        for prop in ac_mat.shader_properties:
            if prop.property_type == 'float':
                value = format_value(prop.valueA)
            elif prop.property_type == 'vec2':
                value = f"{format_value(prop.valueB[0])}, {format_value(prop.valueB[1])}"
            elif prop.property_type == 'vec3':
                value = f"{format_value(prop.valueC[0])}, {format_value(prop.valueC[1])}, {format_value(prop.valueC[2])}"
            elif prop.property_type == 'vec4':
                value = f"{format_value(prop.valueD[0])}, {format_value(prop.valueD[1])}, {format_value(prop.valueD[2])}, {format_value(prop.valueD[3])}"
            else:
                continue

            section_data[f"PROP_{prop_idx}"] = f"{prop.name}, {value}"
            prop_idx += 1

        sections[f"SHADER_REPLACEMENT_{idx}"] = section_data
        idx += 1

    # Add ksTree flag as the final SHADER_REPLACEMENT if any ksTree materials exist
    if has_kstree:
        sections[f"SHADER_REPLACEMENT_{idx}"] = {
            "MATERIALS": "shader:ksTree?",
            "MATERIAL_FLAG_0": "1",
            "PROP_0": f"ksAmbient, {format_value(0.18)}",
            "PROP_1": f"ksDiffuse, {format_value(0.1)}",
            "PROP_2": f"ksSpecular, {format_value(0.0)}",
            "PROP_3": f"ksSpecularEXP, {format_value(50.0)}",
        }

    return sections


def get_ext_config_path(settings) -> str:
    """Get the path to ext_config.ini from settings."""
    return os.path.join(settings.working_dir, "extension", "ext_config.ini")


# =============================================================================
# COMPARISON / SYNC
# =============================================================================

def _normalize_value(value) -> str:
    """Normalize a value for comparison (handles formatting differences)."""
    if value is None:
        return ""
    s = str(value).strip()
    # Normalize whitespace around commas
    s = re.sub(r'\s*,\s*', ', ', s)
    # Normalize trailing zeros in floats
    parts = s.split(', ')
    normalized_parts = []
    for part in parts:
        try:
            # Try to parse as float and reformat
            f = float(part)
            # Format consistently
            formatted = f"{f:.6f}".rstrip('0').rstrip('.')
            normalized_parts.append(formatted)
        except ValueError:
            normalized_parts.append(part)
    return ', '.join(normalized_parts)


def _compare_section_values(file_section: dict, addon_section: dict) -> list:
    """
    Compare two section dictionaries and return list of changes.

    Returns:
        List of change dicts: [{"key": str, "file": str, "addon": str}, ...]
    """
    changes = []
    all_keys = set(file_section.keys()) | set(addon_section.keys())

    for key in sorted(all_keys):
        file_val = _normalize_value(file_section.get(key, ""))
        addon_val = _normalize_value(addon_section.get(key, ""))

        if file_val != addon_val:
            changes.append({
                "key": key,
                "file": file_section.get(key, "(not in file)"),
                "addon": addon_section.get(key, "(not in addon)")
            })

    return changes


def compare_with_file(context, include_shader_replacements: bool = True) -> dict:
    """
    Compare current addon state with ext_config.ini file.

    Returns:
        Dict with structure:
        {
            "has_file": bool,           # Whether ext_config.ini exists
            "has_differences": bool,     # Whether any differences were found
            "file_timestamp": datetime,  # Timestamp from file (or None)
            "sections": {
                "SECTION_NAME": {
                    "status": "modified" | "added" | "removed" | "unchanged",
                    "file_values": dict,   # Values from file
                    "addon_values": dict,  # Values from addon
                    "changes": [...]       # List of specific changes
                },
                ...
            }
        }
    """
    settings = context.scene.AC_Settings
    filepath = get_ext_config_path(settings)

    result = {
        "has_file": os.path.exists(filepath),
        "has_differences": False,
        "file_timestamp": None,
        "sections": {}
    }

    # If file doesn't exist, all addon sections are "added"
    if not result["has_file"]:
        addon_sections = collect_all_sections(context, include_shader_replacements)
        for section_name, section_data in addon_sections.items():
            # Skip sections we don't compare (INCLUDE is auto-generated)
            if section_name in ["INCLUDE"]:
                continue
            result["sections"][section_name] = {
                "status": "added",
                "file_values": {},
                "addon_values": dict(section_data),
                "changes": []
            }
        result["has_differences"] = len(result["sections"]) > 0
        return result

    # Read file
    result["file_timestamp"] = read_timestamp(filepath)
    file_sections = parse_ext_config(filepath)
    addon_sections = collect_all_sections(context, include_shader_replacements)

    # Get all section names from both sources (excluding certain auto-generated sections)
    skip_sections = {"INCLUDE", "TREES"}
    file_section_names = {k for k in file_sections.keys() if k not in skip_sections}
    addon_section_names = {k for k in addon_sections.keys() if k not in skip_sections}

    # Also skip user-defined sections (not managed by addon)
    for name in list(file_section_names):
        if not _is_managed_section(name, ALL_MANAGED_SECTIONS):
            file_section_names.discard(name)

    all_section_names = file_section_names | addon_section_names

    for section_name in sorted(all_section_names, key=get_section_sort_key):
        in_file = section_name in file_sections
        in_addon = section_name in addon_sections

        file_data = file_sections.get(section_name, {})
        addon_data = addon_sections.get(section_name, {})

        # Convert addon_data values to strings for comparison
        addon_data_str = {k: format_value(v) for k, v in addon_data.items()}

        if in_file and in_addon:
            changes = _compare_section_values(file_data, addon_data_str)
            status = "modified" if changes else "unchanged"
        elif in_file and not in_addon:
            status = "removed"
            changes = [{"key": k, "file": v, "addon": "(removed)"} for k, v in file_data.items()]
        else:  # in_addon and not in_file
            status = "added"
            changes = [{"key": k, "file": "(new)", "addon": v} for k, v in addon_data_str.items()]

        if status != "unchanged":
            result["has_differences"] = True

        result["sections"][section_name] = {
            "status": status,
            "file_values": file_data,
            "addon_values": addon_data_str,
            "changes": changes
        }

    return result


def get_diff_summary(diff_result: dict) -> str:
    """
    Generate a human-readable summary of differences.

    Args:
        diff_result: Result from compare_with_file()

    Returns:
        Multi-line string summary
    """
    if not diff_result["has_differences"]:
        return "No differences found."

    lines = []

    # Group by status
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

    if modified:
        lines.append(f"Modified sections ({len(modified)}):")
        for name, data in modified:
            lines.append(f"  [{name}]")
            for change in data["changes"][:3]:  # Show first 3 changes
                lines.append(f"    {change['key']}: {change['file']} → {change['addon']}")
            if len(data["changes"]) > 3:
                lines.append(f"    ... and {len(data['changes']) - 3} more")

    if added:
        lines.append(f"New sections ({len(added)}): {', '.join(added[:5])}")
        if len(added) > 5:
            lines.append(f"  ... and {len(added) - 5} more")

    if removed:
        lines.append(f"Removed sections ({len(removed)}): {', '.join(removed[:5])}")
        if len(removed) > 5:
            lines.append(f"  ... and {len(removed) - 5} more")

    return '\n'.join(lines)


def _parse_vector_string(value: str, default: tuple = (0, 0, 0)) -> tuple:
    """
    Parse a comma-separated string into a tuple of floats.

    Args:
        value: String like "0.5, 1.0, 2.0" or already a tuple
        default: Default value if parsing fails

    Returns:
        Tuple of floats
    """
    if isinstance(value, (tuple, list)):
        return tuple(value)
    if not isinstance(value, str):
        return default
    try:
        parts = [float(p.strip()) for p in value.split(',')]
        return tuple(parts)
    except (ValueError, AttributeError):
        return default


def _preprocess_section_data(section_data: dict) -> dict:
    """
    Pre-process section data from parsed INI to convert string vectors to tuples.

    Keys that typically contain vectors:
    - POSITION, OFFSET, DIRECTION, LINE_FROM, LINE_TO
    - DIRECTION_ALTER, DIRECTION_OFFSET
    - BOUNCED_LIGHT_MULT
    - Any VALUE_* that looks like a vector
    """
    vector_keys = {
        "POSITION", "OFFSET", "DIRECTION", "LINE_FROM", "LINE_TO",
        "DIRECTION_ALTER", "DIRECTION_OFFSET", "BOUNCED_LIGHT_MULT"
    }

    result = {}
    for key, value in section_data.items():
        if key in vector_keys and isinstance(value, str) and ',' in value:
            result[key] = _parse_vector_string(value)
        else:
            result[key] = value
    return result


def import_from_file(context) -> tuple[bool, str]:
    """
    Import ext_config.ini values into addon PropertyGroups.

    Updates:
    - GrassFX settings
    - RainFX settings
    - Global lighting settings
    - CSP Lights (replaces entire list)
    - Emissive Materials (replaces entire list)
    - Shader Replacements (updates material AC_Material properties)

    Does NOT import:
    - User-defined sections
    - TREES section

    Args:
        context: Blender context

    Returns:
        Tuple of (success, message)
    """
    import bpy

    settings = context.scene.AC_Settings
    filepath = get_ext_config_path(settings)

    if not os.path.exists(filepath):
        return (False, "ext_config.ini not found")

    sections = parse_ext_config(filepath)

    imported_count = 0
    shader_updated_count = 0

    # 1. Import GRASS_FX
    if "GRASS_FX" in sections:
        settings.grassfx.from_dict(sections["GRASS_FX"])
        imported_count += 1

    # 2. Import RAIN_FX
    if "RAIN_FX" in sections:
        settings.rainfx.from_dict(sections["RAIN_FX"])
        imported_count += 1

    # 3. Import LIGHTING (global settings)
    if "LIGHTING" in sections:
        processed = _preprocess_section_data(sections["LIGHTING"])
        settings.lighting.global_lighting.from_dict(processed)
        imported_count += 1

    # 4. Import LIGHT_N and LIGHT_SERIES_N
    # First, clear existing lights
    settings.lighting.lights.clear()

    # Collect and sort light sections
    light_sections = []
    for section_name, section_data in sections.items():
        if section_name.startswith("LIGHT_SERIES_"):
            try:
                idx = int(section_name[len("LIGHT_SERIES_"):])
                light_sections.append(("series", idx, section_name, section_data))
            except ValueError:
                pass
        elif section_name.startswith("LIGHT_") and not section_name.startswith("LIGHTING"):
            try:
                idx = int(section_name[len("LIGHT_"):])
                light_sections.append(("light", idx, section_name, section_data))
            except ValueError:
                pass

    # Sort and import
    light_sections.sort(key=lambda x: (x[0], x[1]))
    for light_type, idx, section_name, section_data in light_sections:
        light = settings.lighting.lights.add()
        processed = _preprocess_section_data(section_data)
        light.from_dict(processed, is_series=(light_type == "series"))
        imported_count += 1

    # 5. Import MATERIAL_ADJUSTMENT_N (Emissive Materials)
    # First, clear existing
    settings.lighting.emissive_materials.clear()

    # Collect and sort
    emissive_sections = []
    for section_name, section_data in sections.items():
        if section_name.startswith("MATERIAL_ADJUSTMENT_"):
            try:
                idx = int(section_name[len("MATERIAL_ADJUSTMENT_"):])
                emissive_sections.append((idx, section_name, section_data))
            except ValueError:
                pass

    # Sort and import
    emissive_sections.sort(key=lambda x: x[0])
    for idx, section_name, section_data in emissive_sections:
        emissive = settings.lighting.emissive_materials.add()
        emissive.from_dict(section_data)
        imported_count += 1

    # 6. Import SHADER_REPLACEMENT_N (Material shader properties)
    for section_name, section_data in sections.items():
        if not section_name.startswith("SHADER_REPLACEMENT_"):
            continue

        material_name = section_data.get("MATERIALS", "")
        if not material_name:
            continue

        # Find the material in Blender
        material = bpy.data.materials.get(material_name)
        if not material:
            continue

        # Update AC_Material properties
        ac_mat = material.AC_Material

        # Update shader name
        if "SHADER" in section_data:
            ac_mat.shader_name = section_data["SHADER"]

        # Update shader properties
        # First, collect all PROP_N entries
        props_to_import = {}
        for key, value in section_data.items():
            if key.startswith("PROP_") and ',' in value:
                # Parse: "propName, value(s)"
                comma_idx = value.find(',')
                prop_name = value[:comma_idx].strip()
                prop_value = value[comma_idx + 1:].strip()
                props_to_import[prop_name] = prop_value

        # Update existing properties or add new ones
        for prop_name, prop_value_str in props_to_import.items():
            # Find existing property
            existing_prop = None
            for prop in ac_mat.shader_properties:
                if prop.name == prop_name:
                    existing_prop = prop
                    break

            if not existing_prop:
                # Add new property
                existing_prop = ac_mat.shader_properties.add()
                existing_prop.name = prop_name

            # Parse and set value
            values = [v.strip() for v in prop_value_str.split(',')]
            try:
                if len(values) == 1:
                    existing_prop.property_type = 'float'
                    existing_prop.valueA = float(values[0])
                elif len(values) == 2:
                    existing_prop.property_type = 'vec2'
                    existing_prop.valueB = (float(values[0]), float(values[1]))
                elif len(values) == 3:
                    existing_prop.property_type = 'vec3'
                    existing_prop.valueC = (float(values[0]), float(values[1]), float(values[2]))
                elif len(values) >= 4:
                    existing_prop.property_type = 'vec4'
                    existing_prop.valueD = (float(values[0]), float(values[1]),
                                           float(values[2]), float(values[3]))
            except ValueError:
                pass  # Skip properties that can't be parsed

        shader_updated_count += 1

    timestamp = read_timestamp(filepath)
    timestamp_str = timestamp.strftime(TIMESTAMP_FORMAT) if timestamp else "unknown"

    msg_parts = [f"Imported {imported_count} sections"]
    if shader_updated_count > 0:
        msg_parts.append(f"{shader_updated_count} material(s) updated")
    msg_parts.append(f"from file (last updated: {timestamp_str})")

    return (True, ", ".join(msg_parts))
