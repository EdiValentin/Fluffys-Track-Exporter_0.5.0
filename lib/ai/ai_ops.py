"""
Blender operators for AI line export.

Export writes selection to fast_lane.ai in the track's ai folder.
"""

import os
import math
from typing import List, Tuple

import bpy
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatProperty,
)
from mathutils import Vector

from .ai_format import (
    AIPoint,
    AIDetailPoint,
    AILineData,
    write_ai_file,
    blender_to_ac_coords,
)
from ...utils.files import get_ai_directory, set_path_reference


class AC_ExportAILine(Operator):
    """Export selected mesh to track/ai/fast_lane.ai"""

    bl_idname = "ac.export_ai_line"
    bl_label = "Export Fast Lane"
    bl_description = "Export selected edge mesh as fast_lane.ai in the track's ai folder"
    bl_options = {"REGISTER", "UNDO"}

    # Export options
    scale: FloatProperty(
        name="Scale",
        description="Scale factor (divide by this value, e.g., use 1.0 if scene is in meters)",
        default=1.0,
        min=0.001,
        max=1000.0,
    )

    default_wall_distance: FloatProperty(
        name="Default Wall Distance",
        description="Default distance to track walls in meters",
        default=5.0,
        min=0.1,
        max=100.0,
    )

    @classmethod
    def poll(cls, context):
        # Need at least one selected mesh object and a working directory set
        if not context.selected_objects:
            return False
        if not any(obj.type == "MESH" for obj in context.selected_objects):
            return False
        # Check if working directory is set
        if not hasattr(context.scene, 'AC_Settings'):
            return False
        return bool(context.scene.AC_Settings.working_dir)

    def execute(self, context):
        # Get working directory and set it for file utilities
        settings = context.scene.AC_Settings
        if not settings.working_dir:
            self.report({"ERROR"}, "Working directory not set. Please set it in the Setup panel.")
            return {"CANCELLED"}

        set_path_reference(settings.working_dir)
        # Find the ideal line mesh (first selected mesh, or one with "ideal" in name)
        ideal_obj = None
        for obj in context.selected_objects:
            if obj.type == "MESH":
                if "ideal" in obj.name.lower():
                    ideal_obj = obj
                    break
                elif ideal_obj is None:
                    ideal_obj = obj

        if ideal_obj is None:
            self.report({"ERROR"}, "No mesh selected for export")
            return {"CANCELLED"}

        # Get mesh data
        mesh = ideal_obj.data

        if len(mesh.vertices) < 2:
            self.report({"ERROR"}, "Mesh must have at least 2 vertices")
            return {"CANCELLED"}

        # Build vertex chain following edges
        # Create edge map
        edge_map = {}
        for edge in mesh.edges:
            v1, v2 = edge.vertices[0], edge.vertices[1]
            if v1 not in edge_map:
                edge_map[v1] = []
            if v2 not in edge_map:
                edge_map[v2] = []
            edge_map[v1].append(v2)
            edge_map[v2].append(v1)

        # Find start vertex (one with only one edge connection, or vertex 0 for loops)
        start_vertex = 0
        for v_idx, connections in edge_map.items():
            if len(connections) == 1:
                start_vertex = v_idx
                break

        # Walk the edge chain
        ordered_vertices = [start_vertex]
        visited = {start_vertex}

        current = start_vertex
        while True:
            neighbors = edge_map.get(current, [])
            next_vertex = None
            for n in neighbors:
                if n not in visited:
                    next_vertex = n
                    break

            if next_vertex is None:
                break

            ordered_vertices.append(next_vertex)
            visited.add(next_vertex)
            current = next_vertex

        # Convert vertices to AI data
        ai_data = AILineData()
        ai_data.header_version = 7  # Standard AC version
        ai_data.unknown1 = 0
        ai_data.unknown2 = 0

        total_distance = 0.0
        prev_pos = None

        for i, v_idx in enumerate(ordered_vertices):
            vertex = mesh.vertices[v_idx]

            # Transform to world space
            world_pos = ideal_obj.matrix_world @ vertex.co

            # Convert to AC coordinates
            ax, ay, az = blender_to_ac_coords(
                world_pos.x / self.scale,
                world_pos.y / self.scale,
                world_pos.z / self.scale,
            )

            # Calculate distance
            if prev_pos is not None:
                dx = ax - prev_pos[0]
                dy = ay - prev_pos[1]
                dz = az - prev_pos[2]
                total_distance += math.sqrt(dx * dx + dy * dy + dz * dz)

            ai_data.ideal_points.append(AIPoint(
                x=ax,
                y=ay,
                z=az,
                distance=total_distance,
                id=i,
            ))

            # AC expects a "basic" AI line with mostly zeros
            # The actual AI parameters (speed, gas, brake, etc.) are computed
            # by AC/ksEditor when the track is processed
            # Only wall distances should be set
            ai_data.detail_points.append(AIDetailPoint(
                unknown=0.0,  # First point will get magic value in write_ai_file
                speed=0.0,
                gas=0.0,
                brake=0.0,
                obsolete_lat_g=0.0,
                radius=0.0,
                wall_left=self.default_wall_distance,
                wall_right=self.default_wall_distance,
                camber=0.0,
                direction=0.0,
                normal_x=0.0,
                normal_y=0.0,
                normal_z=0.0,
                length=0.0,
                forward_x=0.0,
                forward_y=0.0,
                forward_z=0.0,
                tag=0.0,
            ))

            prev_pos = (ax, ay, az)

        # Get the ai directory (creates it if needed)
        ai_dir = get_ai_directory()
        filepath = os.path.join(ai_dir, "fast_lane.ai")

        # Write file
        try:
            write_ai_file(filepath, ai_data)
            self.report(
                {"INFO"},
                f"Exported {len(ai_data.ideal_points)} points to {filepath}"
            )
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {str(e)}")
            return {"CANCELLED"}


def register():
    # No menu entries needed - export is done from the sidebar panel
    pass


def unregister():
    # No menu entries to remove
    pass
