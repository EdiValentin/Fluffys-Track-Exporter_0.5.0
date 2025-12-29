"""
Shader default configurations for Assetto Corsa materials.

Each shader has specific material properties and texture requirements.
Property types:
- 'float': Single scalar value (uses valueA)
- 'vec2': 2-component vector (uses valueB)
- 'vec3': 3-component vector (uses valueC)
- 'vec4': 4-component vector (uses valueD)

Note: Most AC shader properties (ksAmbient, ksDiffuse, ksSpecular) are float multipliers,
not color values. The color comes from the texture itself.
"""

# Texture naming patterns for auto-assignment (case-insensitive)
# Priority: Core textures are checked first, then detail/layer textures
# Patterns are checked in order - more specific patterns should come before generic ones
TEXTURE_NAMING_PATTERNS = {
    # Core textures (high priority)
    "txDiffuse": [
        # Standard PBR naming
        "diffuse", "albedo", "basecolor", "base_color", "color", "col",
        # Shortened versions
        "diff", "alb", "bc", "d",
        # Substance Painter/Designer
        "_diffuse", "_albedo", "_basecolor",
        # Suffix versions
        "_d", "_diff", "_color", "_col",
        # Quixel/Megascans style
        "_albedo", "_basecolor",
    ],

    "txNormal": [
        # Standard naming
        "normal", "normals", "normalmap", "normal_map",
        # OpenGL vs DirectX
        "normal_gl", "normal_dx", "normalgl", "normaldx",
        # Shortened versions
        "nrm", "norm", "nml", "n",
        # Suffix versions
        "_normal", "_normals", "_nrm", "_norm", "_n",
        # Height-to-normal (sometimes used)
        "bump", "_bump",
    ],

    "txMaps": [
        # Combined maps (typical for AC)
        "maps", "packed", "mask", "composite",
        # Specular workflow
        "specular", "spec", "sp", "s",
        "reflection", "reflect", "refl",
        # Roughness/Glossiness
        "roughness", "rough", "r",
        "glossiness", "gloss", "g",
        # Metallic/Metalness
        "metallic", "metalness", "metal", "met", "m",
        # AO (often packed in maps)
        "ao", "ambient", "occlusion", "ambientocclusion",
        # Suffix versions
        "_specular", "_spec", "_roughness", "_rough",
        "_metallic", "_metal", "_ao",
    ],

    "txEmissive": [
        # Standard naming
        "emissive", "emission", "emit", "glow",
        # Light-related
        "light", "lighting", "illumination", "illum",
        # Self-illumination
        "selfillum", "self_illum", "si",
        # Shortened
        "emi", "em", "e",
        # Suffix versions
        "_emissive", "_emission", "_emit", "_glow", "_light",
    ],

    # Detail & layer textures (lower priority)
    "txDetail": [
        "detail", "details", "detailmap", "detail_map",
        "tile", "tiling", "tileable",
        "micro", "microdetail",
        "_detail", "_tile", "_d",
    ],

}

# Define priority order for texture matching
TEXTURE_PRIORITY_ORDER = [
    # Core textures first
    "txDiffuse", "txNormal", "txMaps", "txEmissive",
    # Detail textures next
    "txDetail",
]


def get_texture_slot_from_name(texture_name: str) -> str | None:
    """
    Determine texture slot from texture name using pattern matching.

    Single-letter patterns (d, n, s, etc.) only match as suffixes with separators
    to avoid false positives (e.g., "_d", "_n.png", "texture-r.png", etc.)

    Args:
        texture_name: Image name (case-insensitive matching)

    Returns:
        Texture slot name (e.g., 'txDiffuse') or None if no match
    """
    import re

    name_lower = texture_name.lower()
    # Remove file extension for cleaner matching
    name_without_ext = name_lower.rsplit('.', 1)[0] if '.' in name_lower else name_lower

    # Check patterns in priority order
    for slot_name in TEXTURE_PRIORITY_ORDER:
        patterns = TEXTURE_NAMING_PATTERNS.get(slot_name, [])
        for pattern in patterns:
            pattern_lower = pattern.lower()

            # Single-letter patterns require separators to avoid false positives
            if len(pattern_lower) == 1:
                # Match pattern only with separators: _X, -X at end
                # Examples: "texture_d", "normal_n", "albedo-r"
                # Will NOT match: "road", "ground", "sand" (letter is part of word)
                regex = rf'[_\-]{re.escape(pattern_lower)}$'
                if re.search(regex, name_without_ext):
                    return slot_name
            else:
                # Multi-character patterns use simple substring matching
                if pattern_lower in name_lower:
                    return slot_name

    return None


SHADER_DEFAULTS = {
    "ksPerPixel": {
        "description": "Standard per-pixel shader for most objects",
        "properties": [
            {"name": "ksAmbient", "type": "float", "valueA": 0.18},  # Ambient lighting multiplier
            {"name": "ksDiffuse", "type": "float", "valueA": 0.10},  # Diffuse lighting multiplier
            {"name": "ksSpecular", "type": "float", "valueA": 0.0},  # Must be zero for no reflections
            {"name": "ksSpecularEXP", "type": "float", "valueA": 50.0},  # Specular sharpness
        ],
        "required_textures": ["txDiffuse"],
        "optional_textures": [],
        "alpha_tested": False,
        "alpha_blend_mode": 0,  # Opaque
        "depth_mode": 0,  # DepthNormal
    },

    "ksPerPixelAT": {
        "description": "Alpha-tested shader for cutout transparency (fences, signs, foliage)",
        "properties": [
            {"name": "ksAmbient", "type": "float", "valueA": 0.18},
            {"name": "ksDiffuse", "type": "float", "valueA": 0.10},
            {"name": "ksSpecular", "type": "float", "valueA": 0.0},
            {"name": "ksAlphaRef", "type": "float", "valueA": 0.5},  # 50% alpha cutoff
        ],
        "required_textures": ["txDiffuse"],  # Must have alpha channel
        "optional_textures": [],
        "alpha_tested": True,
        "alpha_blend_mode": 0,
        "depth_mode": 0,
    },

    "ksPerPixelNM_UVMult": {
        "description": "Per-pixel shader with normal mapping and UV multiplier control for different normal/diffuse tiling",
        "properties": [
            {"name": "ksAmbient", "type": "float", "valueA": 0.18},
            {"name": "ksDiffuse", "type": "float", "valueA": 0.10},
            {"name": "ksSpecular", "type": "float", "valueA": 0.15},  # Enable specular highlights
            {"name": "ksSpecularEXP", "type": "float", "valueA": 50.0},
            {"name": "diffuseMult", "type": "float", "valueA": 0.0},  # UV multiplier for diffuse (formula: UV * (1 + value), so 0 = no change)
            {"name": "normalMult", "type": "float", "valueA": 0.0},  # UV multiplier for normal (formula: UV * (1 + value), so 0 = no change)
        ],
        "required_textures": ["txDiffuse", "txNormal"],
        "optional_textures": [],
        "alpha_tested": False,
        "alpha_blend_mode": 0,
        "depth_mode": 0,
    },

    "ksPerPixelAT_NM": {
        "description": "Alpha-tested shader with normal mapping for detailed transparent objects",
        "properties": [
            {"name": "ksAmbient", "type": "float", "valueA": 0.18},
            {"name": "ksDiffuse", "type": "float", "valueA": 0.10},
            {"name": "ksSpecular", "type": "float", "valueA": 0.15},
            {"name": "ksSpecularEXP", "type": "float", "valueA": 50.0},
            {"name": "ksAlphaRef", "type": "float", "valueA": 0.5},  # 50% alpha cutoff
        ],
        "required_textures": ["txDiffuse", "txNormal"],
        "optional_textures": [],
        "alpha_tested": True,
        "alpha_blend_mode": 0,
        "depth_mode": 0,
    },

    "ksTree": {
        "description": "Tree shader for 2D/Y-trees with automatic normals and no self-shadow",
        "properties": [
            {"name": "ksAmbient", "type": "float", "valueA": 0.18},
            {"name": "ksDiffuse", "type": "float", "valueA": 0.10},
            {"name": "ksSpecular", "type": "float", "valueA": 0.0},  # No specular for trees
            {"name": "ksSpecularEXP", "type": "float", "valueA": 1.0},
            {"name": "ksEmissive", "type": "vec3", "valueC": (0.0, 0.0, 0.0)},
            {"name": "ksAlphaRef", "type": "float", "valueA": 0.5},  # Alpha cutoff threshold
        ],
        "required_textures": ["txDiffuse"],  # Must have alpha channel for transparency
        "optional_textures": [],
        "alpha_tested": True,
        "alpha_blend_mode": 0,  # eAlphaTest (mandatory for trees)
        "depth_mode": 0,  # eDepthNormal
        "is_tree_shader": True,  # Flag to prevent auto-upgrade in validate_all_materials
    },
}


def get_shader_list(self, context):
    """Get list of available shaders for EnumProperty."""
    return [(name, name, defaults.get("description", "")) for name, defaults in SHADER_DEFAULTS.items()]


def get_shader_defaults(shader_name: str) -> dict:
    """Get default configuration for a shader."""
    return SHADER_DEFAULTS.get(shader_name, SHADER_DEFAULTS["ksPerPixel"])


def get_required_textures(shader_name: str) -> list[str]:
    """Get list of required textures for a shader."""
    defaults = get_shader_defaults(shader_name)
    return defaults.get("required_textures", [])


def get_optional_textures(shader_name: str) -> list[str]:
    """Get list of optional textures for a shader."""
    defaults = get_shader_defaults(shader_name)
    return defaults.get("optional_textures", [])


def get_all_texture_slots(shader_name: str) -> list[str]:
    """Get all texture slots (required + optional) for a shader."""
    defaults = get_shader_defaults(shader_name)
    return defaults.get("required_textures", []) + defaults.get("optional_textures", [])
