"""
AI Line tools for Assetto Corsa track development.

This module provides export functionality for AI line files (.ai format)
used by Assetto Corsa for AI racing lines.

File types:
- fast_lane.ai: Main racing line for AI cars (auto-exported to track/ai/)

The .ai format contains:
- Header: version info and point count
- Ideal line data: 3D positions + distance + ID per point
- Detail data: 18 floats per point (speed, gas, brake, lateral grip,
  radius, wall distances, camber, direction, normals, forward vectors, tags)
"""

from .ai_format import (
    AI_HEADER_SIZE,
    AI_IDEAL_POINT_SIZE,
    AI_DETAIL_POINT_SIZE,
    AIPoint,
    AIDetailPoint,
    write_ai_file,
)
from .ai_ops import (
    AC_ExportAILine,
)

__all__ = [
    # Format
    'AI_HEADER_SIZE',
    'AI_IDEAL_POINT_SIZE',
    'AI_DETAIL_POINT_SIZE',
    'AIPoint',
    'AIDetailPoint',
    'write_ai_file',
    # Operators
    'AC_ExportAILine',
]
