import configparser
import json
import os

from bpy import path

##
##  Directory Management
##
path_ref = ""
def ensure_path_exists(loc: str):
    # Normalize path to use os-specific separators
    normalized_loc = os.path.normpath(loc)

    # Check if path ends in a file (has extension)
    if os.path.basename(normalized_loc) and '.' in os.path.basename(normalized_loc):
        # It's a file path, ensure the directory exists
        dir_path = os.path.dirname(normalized_loc)
        if dir_path:  # Only create if directory path is not empty
            os.makedirs(dir_path, exist_ok=True)
    else:
        # It's a directory path, create it
        if normalized_loc:  # Only create if path is not empty
            os.makedirs(normalized_loc, exist_ok=True)

    return normalized_loc

def set_path_reference(new_path: str):
    global path_ref
    path_ref = new_path

def get_active_directory():
    abs_path = path.abspath(path_ref)
    return os.path.realpath(abs_path)

def get_subdirectory(*subdirs: str) -> str:
    """
    Get a subdirectory path under the active directory.

    Args:
        *subdirs: One or more subdirectory names to join

    Returns:
        Full path to the subdirectory (created if needed)
    """
    base = get_active_directory()
    for subdir in subdirs:
        base = os.path.join(base, subdir)
    return ensure_path_exists(base)


def get_ai_directory():
    return get_subdirectory('ai')


def get_data_directory():
    return get_subdirectory('data')


def get_ui_directory():
    return get_subdirectory('ui')


def get_content_directory():
    return get_subdirectory('content')


def get_extension_directory():
    return get_subdirectory('extension')


def get_sfx_directory():
    return get_subdirectory('content', 'sfx')


def get_texture_directory():
    return get_subdirectory('content', 'texture')

##
## Import File
##

def verify_local_file(file_path: str, folder: str):
    if not file_path or not os.path.exists(file_path):
        return None
    if file_path.startswith(get_active_directory()):
        return file_path
    if not os.path.exists(file_path):
        return None
    # Use os.path.basename for cross-platform compatibility
    filename = os.path.basename(file_path)
    target_file = ensure_path_exists(os.path.join(get_active_directory(), folder, filename))
    if not os.path.exists(target_file):
        return None
    return target_file

##
##  JSON Files
##
def load_json(filename: str):
    normalized_file = ensure_path_exists(filename)
    try:
        with open(normalized_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_json(filename: str, data):
    normalized_file = ensure_path_exists(filename)
    with open(normalized_file, 'w') as file:
        json.dump(data, file)

def merge_save_json(filename: str, new_data: dict):
    """Save JSON with merge - preserves existing keys not in new_data"""
    normalized_file = ensure_path_exists(filename)

    # Load existing data
    existing_data = load_json(normalized_file)
    if existing_data is None:
        existing_data = {}

    # Deep merge: update existing with new data
    def deep_merge(base: dict, update: dict) -> dict:
        """Recursively merge update into base"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    merged_data = deep_merge(existing_data, new_data)

    # Save merged data
    with open(normalized_file, 'w') as file:
        json.dump(merged_data, file, indent=2)

##
##  INI Files
##
def load_ini(filename: str):
    config = configparser.ConfigParser(allow_no_value=True, strict=False)
    config.optionxform = str  # Preserve case for option names (keys)
    try:
        config.read(filename)
        return config
    except (FileNotFoundError, configparser.Error):
        return None

def save_ini(filename: str, config: dict):
    parser = configparser.ConfigParser()
    parser.optionxform = str  # Preserve case for option names (keys)
    parser.read_dict(config)
    normalized_file = ensure_path_exists(filename)
    with open(normalized_file, 'w') as configfile:
        parser.write(configfile, False)

def merge_save_ini(filename: str, new_config: dict, managed_sections: list = None):
    """
    Save INI with merge - preserves existing sections as raw text (including duplicate keys).

    Args:
        filename: Path to INI file
        new_config: New configuration data (dict of sections)
        managed_sections: List of section names that should be completely replaced.
                         If None, all sections in new_config are updated/added.
                         Sections not in this list are preserved as raw text from existing file.
    """
    normalized_file = ensure_path_exists(filename)

    # Read existing file as raw text to preserve duplicate keys, comments, formatting
    preserved_sections = {}  # section_name -> list of raw lines (including section header)

    if os.path.exists(normalized_file):
        with open(normalized_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse into sections preserving raw text
        lines = content.split('\n')
        current_section = None
        current_lines = []

        for line in lines:
            stripped = line.strip()
            # Check for section header
            if stripped.startswith('[') and stripped.endswith(']'):
                # Save previous section
                if current_section is not None:
                    preserved_sections[current_section] = current_lines
                # Start new section
                current_section = stripped[1:-1]
                current_lines = [line]
            elif current_section is not None:
                current_lines.append(line)

        # Save last section
        if current_section is not None:
            preserved_sections[current_section] = current_lines

    # Determine which sections to keep as raw text
    sections_to_preserve_raw = {}
    if managed_sections is not None:
        for section_name, section_lines in preserved_sections.items():
            if section_name not in managed_sections:
                sections_to_preserve_raw[section_name] = section_lines

    # Build output
    output_lines = []

    # Write new/managed sections first
    # Note: AC INI format uses KEY=VALUE without spaces around =
    for section_name, section_data in new_config.items():
        output_lines.append(f"[{section_name}]")
        for key, value in section_data.items():
            output_lines.append(f"{key}={value}")
        output_lines.append("")

    # Write preserved raw sections
    for section_name, section_lines in sections_to_preserve_raw.items():
        # Remove trailing empty lines from section
        while section_lines and not section_lines[-1].strip():
            section_lines.pop()
        output_lines.extend(section_lines)
        output_lines.append("")

    # Write to file
    with open(normalized_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

def find_maps():
    main_dir = get_active_directory()
    ui_dir = get_ui_directory()
    result = {}
    map_path = os.path.join(main_dir, 'map.png')
    outline_path = os.path.join(ui_dir, 'outline.png')
    preview_path = os.path.join(ui_dir, 'preview.png')
    result['map'] = map_path if os.path.exists(map_path) else None
    result['outline'] = outline_path if os.path.exists(outline_path) else None
    result['preview'] = preview_path if os.path.exists(preview_path) else None
    return result
