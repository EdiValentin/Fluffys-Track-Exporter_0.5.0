"""
Shared utility functions used across multiple modules.

This module provides common helper functions to reduce code duplication
and improve maintainability across the addon.
"""

import re
from typing import List, Optional, Tuple


def get_objects_by_prefix(context, prefix: str) -> list:
    """
    Get all scene objects with names starting with prefix.

    Args:
        context: Blender context
        prefix: String prefix to match object names

    Returns:
        List of objects matching the prefix
    """
    return [obj for obj in context.scene.objects if obj.name.startswith(prefix)]


def add_preflight_error(
    errors: list,
    severity: int,
    message: str,
    code: str
) -> None:
    """
    Add a preflight error to the errors list with standard format.

    Args:
        errors: List to append error to
        severity: 0=info, 1=warning (fixable), 2=error (blocking)
        message: Human-readable error message
        code: Machine-readable error code
    """
    errors.append({
        "severity": severity,
        "message": message,
        "code": code,
    })


def parse_ini_file(filepath: str) -> dict:
    """
    Parse INI file into sections dictionary.

    Simple INI parser that preserves section structure without
    using configparser (useful for preserving comments and ordering).

    Args:
        filepath: Path to INI file

    Returns:
        Dict of section_name -> {key: value} mappings
    """
    sections = {}
    current_section = None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith(';') or line.startswith('#'):
                    continue
                # Section header
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    sections[current_section] = {}
                # Key-value pair
                elif '=' in line and current_section:
                    key, value = line.split('=', 1)
                    sections[current_section][key.strip()] = value.strip()
    except (IOError, UnicodeDecodeError):
        return {}

    return sections


def write_ini_file(filepath: str, sections: dict) -> None:
    """
    Write sections dictionary to INI file.

    Args:
        filepath: Output path for INI file
        sections: Dict of section_name -> {key: value} mappings
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        for section_name, keys in sections.items():
            f.write(f'[{section_name}]\n')
            for key, value in keys.items():
                f.write(f'{key}={value}\n')
            f.write('\n')


def escape_wildcard_pattern(key: str) -> str:
    """
    Convert wildcard pattern to regex-safe string.

    Escapes all regex special characters except '*', which is
    converted to '.*' for wildcard matching.

    Args:
        key: String with optional '*' wildcards

    Returns:
        Regex-safe string with wildcards converted
    """
    wildcard_replacement = "__WILDCARD__"
    key = key.replace("*", wildcard_replacement)
    key = re.escape(key)
    key = key.replace(wildcard_replacement, ".*")
    return key


def convert_to_regex_list(key: str) -> List[re.Pattern]:
    """
    Convert pipe-separated wildcards to compiled regex list.

    Args:
        key: Pipe-separated pattern string (e.g., "ROAD_*|ASPHALT_*")

    Returns:
        List of compiled regex patterns for matching
    """
    matches = []
    for subkey in key.split("|"):
        pattern = f"^{escape_wildcard_pattern(subkey)}$"
        matches.append(re.compile(pattern, re.IGNORECASE))
    return matches


def format_list_preview(items: list, limit: int = 5, separator: str = ", ") -> str:
    """
    Format a list for display with truncation.

    Args:
        items: List of items to format
        limit: Maximum items to show before truncating
        separator: String to join items with

    Returns:
        Formatted string like "item1, item2 (+3 more)"
    """
    if not items:
        return ""

    preview = separator.join(str(item) for item in items[:limit])
    if len(items) > limit:
        preview += f" (+{len(items) - limit} more)"
    return preview


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between min and max bounds.

    Args:
        value: Value to clamp
        min_val: Minimum bound
        max_val: Maximum bound

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))


def safe_get(data: dict, key: str, default=None, cast_type=None):
    """
    Safely get a value from a dictionary with optional type casting.

    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found
        cast_type: Optional type to cast value to (int, float, str, bool)

    Returns:
        Value from dict, default, or casted value
    """
    value = data.get(key, default)
    if value is None or cast_type is None:
        return value

    try:
        if cast_type == bool:
            # Handle various boolean representations
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        return cast_type(value)
    except (ValueError, TypeError):
        return default


def parse_color_string(color_str: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Parse a color string in format "R,G,B,A" where values are 0-255.

    Args:
        color_str: Comma-separated color string

    Returns:
        Tuple of (r, g, b, a) floats normalized to 0-1, or None on error
    """
    try:
        parts = [float(p.strip()) for p in color_str.split(',')]
        if len(parts) < 3:
            return None

        r = parts[0] / 255.0
        g = parts[1] / 255.0
        b = parts[2] / 255.0
        a = parts[3] if len(parts) > 3 else 1.0

        return (
            clamp(r, 0.0, 1.0),
            clamp(g, 0.0, 1.0),
            clamp(b, 0.0, 1.0),
            clamp(a, 0.0, 1.0),
        )
    except (ValueError, IndexError):
        return None


def format_color_string(r: float, g: float, b: float, a: float = 1.0) -> str:
    """
    Format color values (0-1) to AC-style string "R,G,B,A" (0-255).

    Args:
        r, g, b: Color components (0-1)
        a: Alpha component (0-1)

    Returns:
        Formatted color string
    """
    return f"{int(r * 255)},{int(g * 255)},{int(b * 255)},{a}"


def is_valid_index(index: int, collection_length: int) -> bool:
    """Check if index is within valid range for a collection."""
    return 0 <= index < collection_length


def adjust_active_index(active_index: int, collection_length: int) -> int:
    """Adjust active index when collection size changes (e.g., after removal)."""
    if active_index >= collection_length:
        return max(0, collection_length - 1)
    return active_index


def is_hidden_name(name: str) -> bool:
    """Check if name uses hidden/template prefix convention (starts with __)."""
    return name.startswith("__")


def get_visible_lights(context) -> list:
    """Get all visible light objects from the scene."""
    return [obj for obj in context.scene.objects
            if obj.type == 'LIGHT' and not obj.hide_viewport and not obj.hide_get()]


def get_mesh_objects(context, selected_only: bool = True) -> list:
    """Get mesh objects from selection or entire scene."""
    source = context.selected_objects if selected_only else context.scene.objects
    return [obj for obj in source if obj.type == 'MESH']


def is_object_visible(obj, scene) -> bool:
    """
    Check if an object is visible in the viewport.

    Checks:
    - Object is not hidden in viewport (hide_viewport)
    - Object is not hidden via hide_get() (eye icon)
    - Object is in at least one non-excluded collection

    Args:
        obj: Blender object to check
        scene: Scene to check visibility in

    Returns:
        True if object is visible
    """
    import bpy

    # Check object-level visibility
    if obj.hide_viewport or obj.hide_get():
        return False

    # Check if object is in at least one visible (non-excluded) collection
    view_layer = bpy.context.view_layer

    def is_collection_visible(collection_name):
        """Check if collection is visible in the view layer (not excluded)."""
        def check_layer_collection(layer_col):
            if layer_col.collection.name == collection_name:
                return not layer_col.exclude and not layer_col.hide_viewport
            for child in layer_col.children:
                result = check_layer_collection(child)
                if result is not None:
                    return result
            return None

        result = check_layer_collection(view_layer.layer_collection)
        return result if result is not None else False

    # Object must be in at least one visible collection
    for col in obj.users_collection:
        if is_collection_visible(col.name):
            return True

    return False


def get_visible_materials(context) -> set:
    """
    Get materials that are used by visible objects in the scene.

    A material is considered "visible" if:
    1. It is used by at least one object (not orphaned)
    2. That object is visible in the viewport
    3. The object is in a non-excluded collection
    4. The material name doesn't start with "__" (hidden convention)

    Args:
        context: Blender context

    Returns:
        Set of material names that are visible
    """
    import bpy

    visible_materials = set()

    # Build material -> objects mapping
    material_to_objects = {}
    for obj in bpy.data.objects:
        for slot in obj.material_slots:
            if slot.material:
                mat_name = slot.material.name
                if mat_name not in material_to_objects:
                    material_to_objects[mat_name] = []
                material_to_objects[mat_name].append(obj)

    # Check each material
    for mat in bpy.data.materials:
        # Skip hidden materials (__ prefix)
        if mat.name.startswith("__"):
            continue

        # Skip orphaned materials (not used by any object)
        if mat.name not in material_to_objects:
            continue

        # Check if at least one object using this material is visible
        for obj in material_to_objects[mat.name]:
            if is_object_visible(obj, context.scene):
                visible_materials.add(mat.name)
                break

    return visible_materials
