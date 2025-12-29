"""
Utility modules for AC Track Tools addon.

This package provides shared utilities used across the addon:
- constants: Centralized constants and configuration values
- coordinates: Coordinate system conversion (AC <-> Blender)
- files: File I/O operations (JSON, INI, paths)
- helpers: Common helper functions
- properties: Custom Blender PropertyGroups
"""

from .constants import (
    # Directories
    DATA_DIR,
    UI_DIR,
    # Limits
    MAX_TEXTURE_SIZE,
    MAX_VERTICES_PER_MESH,
    VERTEX_WELD_TOLERANCE,
    # Error limits
    ERROR_PREVIEW_LIMIT,
    OVERSIZED_IMAGE_PREVIEW_LIMIT,
    # Gizmo settings
    GIZMO_SCALE,
    GIZMO_HIGHLIGHT_FACTOR,
    GIZMO_ALPHA_MULTIPLIER,
    # Light defaults
    DEFAULT_LIGHT_TYPE,
    # Precision
    SAVE_PRECISION,
    # Object prefixes
    OBJECT_PREFIXES,
    # Regex patterns
    SURFACE_REGEX,
    SURFACE_OBJECT_REGEX,
    SURFACE_VALID_KEY,
    WALL_REGEX,
    PHYSICS_OBJECT_REGEX,
    AUDIO_SOURCE_REGEX,
    START_CIRCUIT_REGEX,
    START_HOTLAP_REGEX,
    START_AB_L_REGEX,
    START_AB_R_REGEX,
    FINISH_AB_L_REGEX,
    FINISH_AB_R_REGEX,
    PIT_BOX_REGEX,
    AC_TIME_L_REGEX,
    AC_TIME_R_REGEX,
    ASSETTO_CORSA_OBJECTS,
)

from .coordinates import (
    ac_to_blender,
    blender_to_ac,
)

from .helpers import (
    get_objects_by_prefix,
    add_preflight_error,
    parse_ini_file,
    write_ini_file,
    escape_wildcard_pattern,
    convert_to_regex_list,
    format_list_preview,
    clamp,
    safe_get,
    parse_color_string,
    format_color_string,
    is_valid_index,
    adjust_active_index,
    is_hidden_name,
    get_visible_lights,
    get_mesh_objects,
)

from .files import (
    ensure_path_exists,
    set_path_reference,
    get_active_directory,
    get_subdirectory,
    get_ai_directory,
    get_data_directory,
    get_ui_directory,
    get_content_directory,
    get_extension_directory,
    get_sfx_directory,
    get_texture_directory,
    verify_local_file,
    load_json,
    save_json,
    merge_save_json,
    load_ini,
    save_ini,
    merge_save_ini,
    find_maps,
)

__all__ = [
    # Constants
    'DATA_DIR', 'UI_DIR',
    'MAX_TEXTURE_SIZE', 'MAX_VERTICES_PER_MESH', 'VERTEX_WELD_TOLERANCE',
    'ERROR_PREVIEW_LIMIT', 'OVERSIZED_IMAGE_PREVIEW_LIMIT',
    'GIZMO_SCALE', 'GIZMO_HIGHLIGHT_FACTOR', 'GIZMO_ALPHA_MULTIPLIER',
    'DEFAULT_LIGHT_TYPE', 'SAVE_PRECISION', 'OBJECT_PREFIXES',
    # Regex patterns
    'SURFACE_REGEX', 'SURFACE_OBJECT_REGEX', 'SURFACE_VALID_KEY',
    'WALL_REGEX', 'PHYSICS_OBJECT_REGEX', 'AUDIO_SOURCE_REGEX',
    'START_CIRCUIT_REGEX', 'START_HOTLAP_REGEX',
    'START_AB_L_REGEX', 'START_AB_R_REGEX',
    'FINISH_AB_L_REGEX', 'FINISH_AB_R_REGEX',
    'PIT_BOX_REGEX', 'AC_TIME_L_REGEX', 'AC_TIME_R_REGEX',
    'ASSETTO_CORSA_OBJECTS',
    # Coordinates
    'ac_to_blender', 'blender_to_ac',
    # Helpers
    'get_objects_by_prefix', 'add_preflight_error',
    'parse_ini_file', 'write_ini_file',
    'escape_wildcard_pattern', 'convert_to_regex_list',
    'format_list_preview', 'clamp', 'safe_get',
    'parse_color_string', 'format_color_string',
    'is_valid_index', 'adjust_active_index', 'is_hidden_name',
    'get_visible_lights', 'get_mesh_objects',
    # Files
    'ensure_path_exists', 'set_path_reference',
    'get_active_directory', 'get_subdirectory',
    'get_ai_directory', 'get_data_directory', 'get_ui_directory',
    'get_content_directory', 'get_extension_directory',
    'get_sfx_directory', 'get_texture_directory',
    'verify_local_file',
    'load_json', 'save_json', 'merge_save_json',
    'load_ini', 'save_ini', 'merge_save_ini',
    'find_maps',
]
