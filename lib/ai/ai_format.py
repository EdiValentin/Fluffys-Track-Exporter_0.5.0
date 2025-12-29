"""
AI Line file format specification and parsing for Assetto Corsa.

Binary format (.ai files):
- Little-endian byte order throughout
- Header: 16 bytes (4x int32)
- Ideal line: N points of 20 bytes each (4 floats + 1 int)
- Detail data: N points of 72 bytes each (18 floats)

Coordinate system:
- AC uses: X=right, Y=up, Z=forward (right-handed, Y-up)
- Blender uses: X=right, Y=forward, Z=up (right-handed, Z-up)
- Conversion: AC(x,y,z) -> Blender(x,-z,y)
"""

import struct
from dataclasses import dataclass, field
from typing import List, Tuple

from ...utils.coordinates import ac_to_blender, blender_to_ac


# Format constants
AI_HEADER_SIZE = 16  # 4 int32s
AI_IDEAL_POINT_SIZE = 20  # 4 floats + 1 int
AI_DETAIL_POINT_SIZE = 72  # 18 floats


@dataclass
class AIPoint:
    """A point on the ideal racing line."""
    x: float = 0.0
    y: float = 0.0  # Height in AC coordinates
    z: float = 0.0
    distance: float = 0.0  # Distance from start
    id: int = 0


@dataclass
class AIDetailPoint:
    """Extended data for each point on the racing line."""
    unknown: float = 0.0  # Index 0
    speed: float = 100.0  # Index 1 - Target speed in km/h
    gas: float = 1.0  # Index 2 - Throttle input 0-1
    brake: float = 0.0  # Index 3 - Brake input 0-1
    obsolete_lat_g: float = 0.0  # Index 4 - Deprecated
    radius: float = 1000.0  # Index 5 - Corner radius
    wall_left: float = 5.0  # Index 6 - Distance to left wall
    wall_right: float = 5.0  # Index 7 - Distance to right wall
    camber: float = 0.0  # Index 8 - Track camber angle
    direction: float = 0.0  # Index 9 - Heading angle in radians
    normal_x: float = 0.0  # Index 10
    normal_y: float = 1.0  # Index 11
    normal_z: float = 0.0  # Index 12
    length: float = 0.0  # Index 13 - Segment length
    forward_x: float = 0.0  # Index 14
    forward_y: float = 0.0  # Index 15
    forward_z: float = 1.0  # Index 16
    tag: float = 0.0  # Index 17 - Surface tag


@dataclass
class AILineData:
    """Complete AI line data from a .ai file."""
    header_version: int = 0
    point_count: int = 0
    unknown1: int = 0
    unknown2: int = 0
    ideal_points: List[AIPoint] = field(default_factory=list)
    detail_points: List[AIDetailPoint] = field(default_factory=list)


def read_ai_file(filepath: str) -> AILineData:
    """
    Read an Assetto Corsa AI line file.

    Args:
        filepath: Path to .ai file

    Returns:
        AILineData containing all parsed data
    """
    import os

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"AI file not found: {filepath}")

    filesize = os.stat(filepath).st_size
    data = AILineData()

    with open(filepath, "rb") as f:
        # Read header (16 bytes, little-endian)
        header_bytes = f.read(AI_HEADER_SIZE)
        if len(header_bytes) < AI_HEADER_SIZE:
            raise ValueError("Invalid AI file: header too short")

        data.header_version, data.point_count, data.unknown1, data.unknown2 = struct.unpack(
            "<4i", header_bytes
        )

        # Read ideal line points
        for i in range(data.point_count):
            point_bytes = f.read(AI_IDEAL_POINT_SIZE)
            if len(point_bytes) < AI_IDEAL_POINT_SIZE:
                print(f"Warning: Ideal line data truncated at point {i}/{data.point_count}")
                break

            x, y, z, dist, point_id = struct.unpack("<4fi", point_bytes)

            data.ideal_points.append(AIPoint(x=x, y=y, z=z, distance=dist, id=point_id))

        # Read detail data (starts after all ideal points)
        for i in range(data.point_count):
            detail_bytes = f.read(AI_DETAIL_POINT_SIZE)
            if len(detail_bytes) < AI_DETAIL_POINT_SIZE:
                print(f"Warning: Detail data truncated at point {i}/{data.point_count}")
                break

            values = struct.unpack("<18f", detail_bytes)
            data.detail_points.append(AIDetailPoint(
                unknown=values[0],
                speed=values[1],
                gas=values[2],
                brake=values[3],
                obsolete_lat_g=values[4],
                radius=values[5],
                wall_left=values[6],
                wall_right=values[7],
                camber=values[8],
                direction=values[9],
                normal_x=values[10],
                normal_y=values[11],
                normal_z=values[12],
                length=values[13],
                forward_x=values[14],
                forward_y=values[15],
                forward_z=values[16],
                tag=values[17],
            ))

    return data


def write_ai_file(filepath: str, data: AILineData) -> None:
    """
    Write an Assetto Corsa AI line file.

    Args:
        filepath: Output path for .ai file
        data: AILineData to write
    """
    # Magic number: encodes point count in first detail record
    # This is how AC expects the count to be embedded in the data
    POINT_COUNT_MAGIC = 1.40129846432481e-45

    point_count = len(data.ideal_points)

    with open(filepath, "wb") as f:
        # Write header (little-endian)
        f.write(struct.pack("<4i",
            data.header_version,
            point_count,
            data.unknown1,
            data.unknown2
        ))

        # Write ideal line points
        for point in data.ideal_points:
            f.write(struct.pack("<4fi", point.x, point.y, point.z, point.distance, point.id))

        # Write detail data
        for i, detail in enumerate(data.detail_points):
            # First point has magic value encoding point count
            unknown_value = POINT_COUNT_MAGIC * point_count if i == 0 else detail.unknown

            f.write(struct.pack("<18f",
                unknown_value,
                detail.speed,
                detail.gas,
                detail.brake,
                detail.obsolete_lat_g,
                detail.radius,
                detail.wall_left,
                detail.wall_right,
                detail.camber,
                detail.direction,
                detail.normal_x,
                detail.normal_y,
                detail.normal_z,
                detail.length,
                detail.forward_x,
                detail.forward_y,
                detail.forward_z,
                detail.tag,
            ))


# Re-export coordinate conversion functions for backward compatibility
def ac_to_blender_coords(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert AC coordinates to Blender coordinates.

    AC: X=right, Y=up, Z=forward
    Blender: X=right, Y=forward, Z=up

    Transform: (x, y, z) -> (x, -z, y)
    """
    return ac_to_blender(x, y, z)


def blender_to_ac_coords(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert Blender coordinates to AC coordinates.

    Blender: X=right, Y=forward, Z=up
    AC: X=right, Y=up, Z=forward

    Transform: (x, y, z) -> (x, z, -y)
    """
    return blender_to_ac(x, y, z)
