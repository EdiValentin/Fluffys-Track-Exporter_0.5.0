"""
Coordinate system conversion utilities for AC <-> Blender.

Assetto Corsa uses a Y-up right-handed coordinate system:
- X = right
- Y = up
- Z = forward

Blender uses a Z-up right-handed coordinate system:
- X = right
- Y = forward
- Z = up

The conversion transforms are:
- AC to Blender: (x, y, z) -> (x, -z, y)
- Blender to AC: (x, y, z) -> (x, z, -y)
"""

from typing import Tuple

try:
    from mathutils import Vector
    HAS_MATHUTILS = True
except ImportError:
    HAS_MATHUTILS = False


def ac_to_blender(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert AC coordinates (Y-up) to Blender coordinates (Z-up).

    Args:
        x: AC X coordinate (right)
        y: AC Y coordinate (up)
        z: AC Z coordinate (forward)

    Returns:
        Tuple of (x, y, z) in Blender coordinates
    """
    return (x, -z, y)


def blender_to_ac(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert Blender coordinates (Z-up) to AC coordinates (Y-up).

    Args:
        x: Blender X coordinate (right)
        y: Blender Y coordinate (forward)
        z: Blender Z coordinate (up)

    Returns:
        Tuple of (x, y, z) in AC coordinates
    """
    return (x, z, -y)


if HAS_MATHUTILS:
    def ac_to_blender_vector(vec: Vector) -> Vector:
        """
        Convert AC Vector to Blender Vector.

        Args:
            vec: mathutils.Vector in AC coordinates

        Returns:
            mathutils.Vector in Blender coordinates
        """
        return Vector((vec.x, -vec.z, vec.y))


    def blender_to_ac_vector(vec: Vector) -> Vector:
        """
        Convert Blender Vector to AC Vector.

        Args:
            vec: mathutils.Vector in Blender coordinates

        Returns:
            mathutils.Vector in AC coordinates
        """
        return Vector((vec.x, vec.z, -vec.y))


    def convert_vector3(blender_vec: Vector) -> Vector:
        """
        Convert Blender Vector3 to AC coordinates.

        This is the primary conversion function used by the KN5 exporter.
        Converts positions, normals, and tangents from Blender to AC space.

        Args:
            blender_vec: mathutils.Vector in Blender coordinates

        Returns:
            mathutils.Vector in AC coordinates
        """
        return Vector((blender_vec[0], blender_vec[2], -blender_vec[1]))


    def convert_matrix(blender_matrix) -> list:
        """
        Convert Blender 4x4 matrix to AC coordinate system.

        Applies coordinate transform to the matrix translation and rotation.
        Returns row-major list for KN5 binary format.

        Args:
            blender_matrix: Blender Matrix (4x4)

        Returns:
            List of 16 floats in row-major order for AC
        """
        # Extract components
        loc = blender_matrix.to_translation()
        rot = blender_matrix.to_quaternion()
        scale = blender_matrix.to_scale()

        # Convert location
        ac_loc = convert_vector3(loc)

        # Convert rotation (swap Y and Z axes)
        ac_rot = rot.copy()
        ac_rot.y, ac_rot.z = rot.z, -rot.y

        # Reconstruct matrix
        from mathutils import Matrix
        ac_matrix = Matrix.LocRotScale(ac_loc, ac_rot, scale)

        # Return as flat row-major list
        result = []
        for row in ac_matrix:
            result.extend(row)
        return result
