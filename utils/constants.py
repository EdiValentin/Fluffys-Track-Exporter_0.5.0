# directories
DATA_DIR = 'data/'
UI_DIR = 'ui/'

# Export/Texture limits
MAX_TEXTURE_SIZE = 15000
MAX_VERTICES_PER_MESH = 65536
VERTEX_WELD_TOLERANCE = 0.0001

# Error message limits
ERROR_PREVIEW_LIMIT = 5
OVERSIZED_IMAGE_PREVIEW_LIMIT = 3

# Gizmo settings
GIZMO_SCALE = (4.3, 1.4, 2.3)
GIZMO_HIGHLIGHT_FACTOR = 1.3
GIZMO_ALPHA_MULTIPLIER = 0.3

# Light defaults
DEFAULT_LIGHT_TYPE = "SPOT"

# Precision for saving float values
SAVE_PRECISION = 2

# Object prefixes (single source of truth)
# Note: These prefixes match the old settings.py implementation for backward compatibility.
# Some other parts of the codebase use more specific prefixes with trailing underscores.
OBJECT_PREFIXES = {
    'start': 'AC_START',
    'pitbox': 'AC_PIT',
    'hotlap': 'AC_HOTLAP_START',
    'time_gate': 'AC_TIME',
    'ab_start': 'AC_AB_START',
    'ab_finish': 'AC_AB_FINISH',
    'audio': 'AC_AUDIO',
}

# Surface Regex
SURFACE_REGEX = r"^(\d*)([A-Z\-]+)_?(.*)$"
SURFACE_OBJECT_REGEX = r"^\d*[A-Z\-]+_?(.*)$"
SURFACE_VALID_KEY = r"^[A-Z_-]+$"

# Physics Regex
WALL_REGEX = r"^\d+WALL_(.*)$"
PHYSICS_OBJECT_REGEX = r"^AC_POBJECT_(.*)$"
AUDIO_SOURCE_REGEX = r"^AC_AUDIO_(.*)$"

# Race Logic Regex
START_CIRCUIT_REGEX = r"^AC_START_\d+$"
START_HOTLAP_REGEX = r"^AC_HOTLAP_START_$"
START_AB_L_REGEX = r"^AC_AB_START_L$"
START_AB_R_REGEX = r"^AC_AB_START_R$"
FINISH_AB_L_REGEX = r"^AC_AB_FINISH_L$"
FINISH_AB_R_REGEX = r"^AC_AB_FINISH_R$"
PIT_BOX_REGEX = r"^AC_PIT_\d+$"
AC_TIME_L_REGEX = r"^AC_TIME_\d+_L$"
AC_TIME_R_REGEX = r"^AC_TIME_\d+_R$"

ASSETTO_CORSA_OBJECTS = (
    r"AC_START_\d+",
    r"AC_PIT_\d+",
    r"AC_TIME_\d+_L",
    r"AC_TIME_\d+_R",
    r"AC_HOTLAP_START_\d+",
    r"AC_OPEN_FINISH_R",
    r"AC_OPEN_FINISH_L",
    r"AC_OPEN_START_L",
    r"AC_OPEN_START_R",
    r"AC_AUDIO_.+",
    r"AC_CREW_\d+",
)
