from ...utils.constants import MAX_VERTICES_PER_MESH

KN5_HEADER = b"sc6969"
KN5_VERSION = 5

# MAX_VERTICES_PER_MESH is imported from utils.constants for single source of truth

MATERIAL_BLEND_MODES = {
    "Opaque": 0,
    "AlphaBlend": 1,
    "AlphaToCoverage": 2,
}

MATERIAL_DEPTH_MODES = {
    "DepthNormal": 0,
    "DepthNoWrite": 1,
    "DepthOff": 2,
}

NODE_TYPES = {
    "Node": 1,
    "Mesh": 2,
    "SkinnedMesh": 3,
}

# Binary format constants
MESH_CHILD_COUNT = 0  # Mesh nodes cannot have children
DEFAULT_MATERIAL_ID = 0  # Default material index when none assigned
