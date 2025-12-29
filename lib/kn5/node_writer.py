# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2014  Thomas Hagnhofer


import os
import re
import math
import bmesh
from mathutils import Matrix, Vector
from .utils import (
    convert_matrix,
    convert_vector3,
    get_active_material_texture_slot,
    is_object_excluded_by_collection,
)
from .kn5_writer import KN5Writer
from .constants import NODE_TYPES, MAX_VERTICES_PER_MESH, MESH_CHILD_COUNT, DEFAULT_MATERIAL_ID
from ...utils.constants import ASSETTO_CORSA_OBJECTS, VERTEX_WELD_TOLERANCE
from ...utils.helpers import is_hidden_name
from ...utils.helpers import convert_to_regex_list


NODES = "nodes"

# Pattern to match KSTREE_GROUP_[name]_[number] naming convention
# Groups: (1) group name, (2) instance number
KSTREE_GROUP_PATTERN = re.compile(r'^KSTREE_GROUP_([A-Z0-9_]+)_(\d+)$', re.IGNORECASE)

NODE_SETTINGS = (
    "lodIn",
    "lodOut",
    "layer",
    "castShadows",
    "visible",
    "transparent",
    "renderable",
)


class NodeWriter(KN5Writer):
    def __init__(self, file, context, settings, warnings, material_writer):
        super().__init__(file)

        self.context = context
        self.settings = settings
        self.warnings = warnings
        self.material_writer = material_writer
        self.scene = self.context.scene
        self.node_settings = []
        self.ac_objects = []
        self._init_assetto_corsa_objects()
        self._init_node_settings()

    def _init_node_settings(self):
        self.node_settings = []
        if NODES in self.settings:
            for node_key in self.settings[NODES]:
                self.node_settings.append(NodeSettings(self.settings, node_key))

    def _init_assetto_corsa_objects(self):
        for obj_name in ASSETTO_CORSA_OBJECTS:
            self.ac_objects.append(re.compile(f"^{obj_name}$"))

    def _is_ac_object(self, name):
        for regex in self.ac_objects:
            if regex.match(name):
                return True
        return False

    def _is_tree_shader(self, material):
        """Check if a material uses ksTree shader."""
        if material and hasattr(material, 'AC_Material'):
            return material.AC_Material.shader_name == "ksTree"
        return False

    def _calculate_tree_normal(self, vertex_pos, vertex_normal, mesh_center_y):
        """
        Calculate foliage-style normal for tree vertices.

        ksTree shader expects normals that point predominantly upward to simulate
        foliage receiving light from above. The normal is biased upward while
        preserving some of the original horizontal direction for natural shading.

        Based on ksEditor output analysis:
        - Top vertices (near tree top): mostly straight up (0, 1, 0)
        - Lower vertices: blend of upward + outward direction
        - Average Y component should be ~0.6-0.9 (mostly upward)

        Args:
            vertex_pos: Vertex position in AC coordinates (Y-up)
            vertex_normal: Original geometric normal
            mesh_center_y: Y coordinate of mesh center (for height-based blending)

        Returns:
            Normalized (x, y, z) normal tuple pointing predominantly upward
        """
        # Height factor: vertices higher in the tree get more upward normals
        # Normalize height relative to mesh center
        height_above_center = vertex_pos[1] - mesh_center_y

        # Blend factor: higher = more upward, lower = more original direction
        # Clamp between 0.5 and 1.0 to always have strong upward bias
        height_factor = min(1.0, max(0.5, 0.7 + height_above_center * 0.1))

        # Start with mostly upward normal
        up_vector = (0.0, 1.0, 0.0)

        # Blend with horizontal component of original normal for variation
        # This gives natural-looking shading variation across the tree
        orig_horiz_len = math.sqrt(vertex_normal[0]**2 + vertex_normal[2]**2)

        if orig_horiz_len > 0.001:
            # Normalize horizontal component
            horiz_x = vertex_normal[0] / orig_horiz_len
            horiz_z = vertex_normal[2] / orig_horiz_len

            # Blend: mostly up, with small horizontal component
            horiz_weight = (1.0 - height_factor) * 0.5
            nx = horiz_x * horiz_weight
            ny = height_factor + (1.0 - height_factor) * 0.5
            nz = horiz_z * horiz_weight
        else:
            # If original normal was straight up/down, just use up
            nx, ny, nz = 0.0, 1.0, 0.0

        # Normalize the result
        length = math.sqrt(nx*nx + ny*ny + nz*nz)
        if length > 0.001:
            nx, ny, nz = nx/length, ny/length, nz/length
        else:
            nx, ny, nz = 0.0, 1.0, 0.0

        return (nx, ny, nz)

    def _get_kstree_group_name(self, obj_name):
        """
        Extract the KSTREE group name from an object name.
        Returns the group name (e.g., 'Test' from 'KSTREE_GROUP_Test_1') or None if not a kstree object.
        Preserves original case for consistent naming with child objects.
        """
        match = KSTREE_GROUP_PATTERN.match(obj_name)
        if match:
            return match.group(1)  # Preserve original case
        return None

    def _collect_and_group_objects(self):
        """
        Collect all top-level objects and group KSTREE objects by their group name.
        Returns: (regular_objects, kstree_groups)
            - regular_objects: list of non-kstree top-level objects
            - kstree_groups: dict mapping group_name -> (original_case_name, list of objects)

        Uses case-insensitive grouping but preserves original case for container naming.
        """
        regular_objects = []
        kstree_groups = {}  # key: lowercase group name, value: (original_case, [objects])

        for obj in self.context.blend_data.objects:
            # Skip objects with parents (they're handled by their parent)
            if obj.parent:
                continue
            # Skip hidden/excluded objects
            if is_hidden_name(obj.name):
                continue
            if is_object_excluded_by_collection(obj, self.context):
                continue

            group_name = self._get_kstree_group_name(obj.name)
            if group_name:
                # Use lowercase key for case-insensitive grouping
                group_key = group_name.lower()
                if group_key not in kstree_groups:
                    # Store original case from first object found
                    kstree_groups[group_key] = (group_name, [])
                kstree_groups[group_key][1].append(obj)
            else:
                regular_objects.append(obj)

        # Sort regular objects by children count (original behavior)
        regular_objects.sort(key=lambda k: len(k.children))

        # Sort objects within each kstree group by name for consistent ordering
        for group_key in kstree_groups:
            kstree_groups[group_key][1].sort(key=lambda k: k.name)

        return regular_objects, kstree_groups

    def _write_kstree_group(self, group_name, objects):
        """
        Write a KSTREE group as a single merged mesh node.

        ksEditor merges all tree instances into one mesh for performance.
        This matches that behavior: all KSTREE_GROUP_[name]_N objects become
        a single mesh named [name] with combined geometry.

        Tree normals are overridden to point upward for proper foliage shading.
        """
        # Filter to mesh objects only
        mesh_objects = [obj for obj in objects if obj.type == "MESH"]
        if not mesh_objects:
            return

        # Collect all geometry from all tree instances
        all_vertices = []
        all_indices = []
        material_id = None
        node_properties = None

        # First pass: collect all geometry and find mesh center for normal calculation
        all_positions_y = []

        for obj in mesh_objects:
            mesh_data = self._extract_tree_mesh_data(obj)
            if mesh_data:
                for verts, indices, mat_id in mesh_data:
                    # Track material (should be same for all trees in group)
                    if material_id is None:
                        material_id = mat_id
                    if node_properties is None:
                        node_properties = NodeProperties(obj)

                    # Collect Y positions for center calculation
                    for v in verts:
                        all_positions_y.append(v.co[1])

        # Calculate mesh center Y for normal calculation
        if all_positions_y:
            mesh_center_y = sum(all_positions_y) / len(all_positions_y)
        else:
            mesh_center_y = 0.0

        # Second pass: merge geometry with tree normal override
        for obj in mesh_objects:
            mesh_data = self._extract_tree_mesh_data(obj)
            if mesh_data:
                for verts, indices, mat_id in mesh_data:
                    # Offset indices for merged mesh
                    index_offset = len(all_vertices)

                    # Add vertices with tree normal override
                    for v in verts:
                        # Calculate foliage-style upward normal
                        tree_normal = self._calculate_tree_normal(
                            v.co, v.normal, mesh_center_y
                        )
                        # Create new vertex with overridden normal
                        new_vertex = UvVertex(v.co, tree_normal, v.uv, v.tangent)
                        all_vertices.append(new_vertex)

                    # Add offset indices
                    for idx in indices:
                        all_indices.append(idx + index_offset)

        if not all_vertices:
            return

        # Check vertex limit
        if len(all_vertices) > MAX_VERTICES_PER_MESH:
            self.warnings.append(
                f"KSTREE group '{group_name}' has {len(all_vertices)} vertices, "
                f"exceeding limit of {MAX_VERTICES_PER_MESH}. Consider splitting into multiple groups."
            )
            # Still try to write, but it may fail

        # Write as single mesh node with just the group name (not KSTREE_GROUP_name)
        # This matches ksEditor behavior
        self._write_node_class("Mesh")
        self.write_string(group_name)
        self.write_uint(MESH_CHILD_COUNT)  # No children for mesh nodes
        self.write_bool(True)  # active

        # Mesh properties
        if node_properties:
            self.write_bool(node_properties.castShadows)
            self.write_bool(node_properties.visible)
            self.write_bool(node_properties.transparent)
        else:
            self.write_bool(True)   # castShadows
            self.write_bool(True)   # visible
            self.write_bool(False)  # transparent

        # Write vertices
        self.write_uint(len(all_vertices))
        for vertex in all_vertices:
            self.write_vector3(vertex.co)
            self.write_vector3(vertex.normal)
            self.write_vector2(vertex.uv)
            self.write_vector3(vertex.tangent)

        # Write indices
        self.write_uint(len(all_indices))
        for i in all_indices:
            self.write_ushort(i)

        # Material
        if material_id is not None:
            self.write_uint(material_id)
        else:
            self.warnings.append(f"No material for KSTREE group '{group_name}'")
            self.write_uint(DEFAULT_MATERIAL_ID)

        # LOD and layer
        if node_properties:
            self.write_uint(node_properties.layer)
            self.write_float(node_properties.lodIn)
            self.write_float(node_properties.lodOut)
        else:
            self.write_uint(0)    # layer
            self.write_float(0.0) # lodIn
            self.write_float(0.0) # lodOut

        # Bounding sphere
        self._write_bounding_sphere(all_vertices)

        # Renderable flag
        if node_properties:
            self.write_bool(node_properties.renderable)
        else:
            self.write_bool(True)

    def _extract_tree_mesh_data(self, obj):
        """
        Extract mesh data from a tree object for merging.

        Returns list of (vertices, indices, material_id) tuples.
        Similar to _split_object_by_materials but returns raw data for merging.
        """
        result = []
        mesh_copy = obj.to_mesh()

        bm = bmesh.new()
        bm.from_mesh(mesh_copy)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=VERTEX_WELD_TOLERANCE)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(mesh_copy)
        bm.free()

        try:
            mesh_copy.calc_loop_triangles()

            has_uvs = len(mesh_copy.uv_layers) > 0
            if has_uvs:
                try:
                    mesh_copy.calc_tangents()
                except RuntimeError:
                    has_uvs = False

            mesh_vertices = mesh_copy.vertices[:]
            mesh_loops = mesh_copy.loops[:]
            mesh_triangles = mesh_copy.loop_triangles[:]
            uv_layer = mesh_copy.uv_layers.active if has_uvs else None
            matrix = obj.matrix_world

            if not mesh_copy.materials:
                return result

            used_materials = set([triangle.material_index for triangle in mesh_triangles])
            for material_index in used_materials:
                if not mesh_copy.materials[material_index]:
                    continue
                material = mesh_copy.materials[material_index]
                material_name = material.name
                if is_hidden_name(material_name):
                    continue

                vertices = {}
                indices = []
                for triangle in mesh_triangles:
                    if material_index != triangle.material_index:
                        continue
                    face_indices = []
                    for loop_index in triangle.loops:
                        loop = mesh_loops[loop_index]
                        local_position = matrix @ mesh_vertices[loop.vertex_index].co
                        converted_position = convert_vector3(local_position)
                        converted_normal = convert_vector3(loop.normal)
                        uv = (0, 0)
                        if uv_layer:
                            uv = uv_layer.data[loop_index].uv
                            uv = (uv[0], -uv[1])

                        tangent = convert_vector3(loop.tangent) if has_uvs else (1.0, 0.0, 0.0)
                        vertex = UvVertex(converted_position, converted_normal, uv, tangent)
                        if vertex not in vertices:
                            new_index = len(vertices)
                            vertices[vertex] = new_index
                        face_indices.append(vertices[vertex])

                    indices.extend((face_indices[1], face_indices[2], face_indices[0]))

                vertices_list = [v for v, index in sorted(vertices.items(), key=lambda k: k[1])]
                material_id = self.material_writer.material_positions.get(material_name)
                if material_id is not None:
                    result.append((vertices_list, indices, material_id))
        finally:
            obj.to_mesh_clear()

        return result

    def write(self):
        # Collect and categorize all top-level objects
        regular_objects, kstree_groups = self._collect_and_group_objects()

        # Calculate total children: regular objects + kstree group containers
        total_children = len(regular_objects) + len(kstree_groups)

        # Write root node with correct child count
        node_data = {
            "name": "BlenderFile",
            "childCount": total_children,
            "active": True,
            "transform": Matrix(),
        }
        self._write_base_node_data(node_data)

        # Write KSTREE group containers first (grouped trees)
        # kstree_groups values are tuples: (original_case_name, objects_list)
        for group_key in sorted(kstree_groups.keys()):
            original_name, objects = kstree_groups[group_key]
            self._write_kstree_group(original_name, objects)

        # Write regular (non-kstree) objects
        for obj in regular_objects:
            self._write_object(obj)

    def _write_object(self, obj):
        if not is_hidden_name(obj.name):
            if obj.type == "MESH":
                if obj.children:
                    raise Exception(f"A mesh cannot contain children ('{obj.name}')")
                self._write_mesh_node(obj)
            else:
                self._write_base_node(obj, obj.name)
            for child in obj.children:
                # Skip children in disabled/excluded collections
                if not is_object_excluded_by_collection(child, self.context):
                    self._write_object(child)

    def _any_child_is_mesh(self, obj):
        for child in obj.children:
            if child.type in ["MESH", "CURVE"] or self._any_child_is_mesh(child):
                return True
        return False

    def _write_base_node(self, obj, node_name):
        node_data = {}
        matrix = None
        num_children = 0
        if not obj:
            matrix = Matrix()
            for obj in self.context.blend_data.objects:
                if not obj.parent and not is_hidden_name(obj.name):
                    # Skip objects in disabled/excluded collections
                    if not is_object_excluded_by_collection(obj, self.context):
                        num_children += 1
        else:
            if not self._is_ac_object(obj.name) and not self._any_child_is_mesh(obj):
                msg = f"Unknown logical object '{obj.name}' might prevent other objects from loading.{os.linesep}"
                msg += "\tRename it to '__{obj.name}' if you do not want to export it."
                self.warnings.append(msg)
            matrix = convert_matrix(obj.matrix_local)
            for child in obj.children:
                if not is_hidden_name(child.name):
                    # Skip objects in disabled/excluded collections
                    if not is_object_excluded_by_collection(child, self.context):
                        num_children += 1

        node_data["name"] = node_name
        node_data["childCount"] = num_children
        node_data["active"] = True
        node_data["transform"] = matrix
        self._write_base_node_data(node_data)

    def _write_base_node_data(self, node_data):
        self._write_node_class("Node")
        self.write_string(node_data["name"])
        self.write_uint(node_data["childCount"])
        self.write_bool(node_data["active"])
        self.write_matrix(node_data["transform"])

    def _write_mesh_node(self, obj):
        divided_meshes = self._split_object_by_materials(obj)
        divided_meshes = self._split_meshes_for_vertex_limit(divided_meshes)
        if obj.parent or len(divided_meshes) > 1:
            node_data = {}
            node_data["name"] = obj.name
            node_data["childCount"] = len(divided_meshes)
            node_data["active"] = True
            transform_matrix = Matrix()
            if obj.parent:
                transform_matrix = convert_matrix(obj.parent.matrix_world.inverted())
            node_data["transform"] = transform_matrix
            self._write_base_node_data(node_data)
        node_properties = NodeProperties(obj)
        for node_setting in self.node_settings:
            node_setting.apply_settings_to_node(node_properties)
        for mesh in divided_meshes:
            self._write_mesh(obj, mesh, node_properties)

    def _write_node_class(self, node_class):
        self.write_uint(NODE_TYPES[node_class])

    def _write_mesh(self, obj, mesh, node_properties):
        self._write_node_class("Mesh")
        self.write_string(obj.name)
        self.write_uint(MESH_CHILD_COUNT)  # Child count, none allowed for mesh nodes
        is_active = True
        self.write_bool(is_active)
        self.write_bool(node_properties.castShadows)
        self.write_bool(node_properties.visible)
        self.write_bool(node_properties.transparent)
        if len(mesh.vertices) > MAX_VERTICES_PER_MESH:
            raise Exception(f"Only {MAX_VERTICES_PER_MESH} vertices per mesh allowed. ('{obj.name}')")
        self.write_uint(len(mesh.vertices))
        for vertex in mesh.vertices:
            self.write_vector3(vertex.co)
            self.write_vector3(vertex.normal)
            self.write_vector2(vertex.uv)
            self.write_vector3(vertex.tangent)
        self.write_uint(len(mesh.indices))
        for i in mesh.indices:
            self.write_ushort(i)
        if mesh.material_id is None:
            self.warnings.append(f"No material to mesh '{obj.name}' assigned")
            self.write_uint(DEFAULT_MATERIAL_ID)
        else:
            self.write_uint(mesh.material_id)
        self.write_uint(node_properties.layer) #Layer
        self.write_float(node_properties.lodIn) #LOD In
        self.write_float(node_properties.lodOut) #LOD Out
        self._write_bounding_sphere(mesh.vertices)
        self.write_bool(node_properties.renderable) #isRenderable

    def _write_bounding_sphere(self, vertices):
        max_x = float('-inf')
        max_y = float('-inf')
        max_z = float('-inf')
        min_x = float('inf')
        min_y = float('inf')
        min_z = float('inf')
        for vertex in vertices:
            co = vertex.co
            if co[0] > max_x:
                max_x = co[0]
            if co[0] < min_x:
                min_x = co[0]
            if co[1] > max_y:
                max_y = co[1]
            if co[1] < min_y:
                min_y = co[1]
            if co[2] > max_z:
                max_z = co[2]
            if co[2] < min_z:
                min_z = co[2]

        sphere_center = [
            min_x + (max_x - min_x) / 2,
            min_y + (max_y - min_y) / 2,
            min_z + (max_z - min_z) / 2
        ]
        # Calculate actual radius as max distance from center to any vertex
        sphere_radius = 0.0
        for vertex in vertices:
            co = vertex.co
            dx = co[0] - sphere_center[0]
            dy = co[1] - sphere_center[1]
            dz = co[2] - sphere_center[2]
            dist = (dx * dx + dy * dy + dz * dz) ** 0.5
            if dist > sphere_radius:
                sphere_radius = dist
        self.write_vector3(sphere_center)
        self.write_float(sphere_radius)

    def _split_object_by_materials(self, obj):
        meshes = []
        mesh_copy = obj.to_mesh()

        bm = bmesh.new()
        bm.from_mesh(mesh_copy)
        # Weld vertices that are very close together (matches ksEditor behavior)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=VERTEX_WELD_TOLERANCE)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(mesh_copy)
        bm.free()

        try:
            mesh_copy.calc_loop_triangles()

            # Only calculate tangents if UV maps exist (needed for normal maps)
            has_uvs = len(mesh_copy.uv_layers) > 0
            if has_uvs:
                try:
                    mesh_copy.calc_tangents()
                except RuntimeError:
                    # Tangent calculation failed, likely due to invalid UV data
                    has_uvs = False

            mesh_vertices = mesh_copy.vertices[:]
            mesh_loops = mesh_copy.loops[:]
            mesh_triangles = mesh_copy.loop_triangles[:]
            uv_layer = mesh_copy.uv_layers.active if has_uvs else None
            matrix = obj.matrix_world

            if not mesh_copy.materials:
                raise Exception(f"Object '{obj.name}' has no material assigned")

            used_materials = set([triangle.material_index for triangle in mesh_triangles])
            for material_index in used_materials:
                if not mesh_copy.materials[material_index]:
                    raise Exception(f"Material slot {material_index} for object '{obj.name}' has no material assigned")
                material_name = mesh_copy.materials[material_index].name
                if is_hidden_name(material_name):
                    raise Exception(f"Material '{material_name}' is ignored but is used by object '{obj.name}'")

                vertices = {}
                indices = []
                for triangle in mesh_triangles:
                    if material_index != triangle.material_index:
                        continue
                    vertex_index_for_face = 0
                    face_indices = []
                    for loop_index in triangle.loops:
                        loop = mesh_loops[loop_index]
                        local_position = matrix @ mesh_vertices[loop.vertex_index].co
                        converted_position = convert_vector3(local_position)
                        converted_normal = convert_vector3(loop.normal)
                        uv = (0, 0)
                        if uv_layer:
                            uv = uv_layer.data[loop_index].uv
                            uv = (uv[0], -uv[1])
                        else:
                            uv = self._calculate_uvs(obj, mesh_copy, material_index, local_position)

                        # Use calculated tangent if available, otherwise use default
                        # Tangent must be converted to AC coordinate system like position/normal
                        tangent = convert_vector3(loop.tangent) if has_uvs else (1.0, 0.0, 0.0)
                        vertex = UvVertex(converted_position, converted_normal, uv, tangent)
                        if vertex not in vertices:
                            new_index = len(vertices)
                            vertices[vertex] = new_index
                        face_indices.append(vertices[vertex])
                        vertex_index_for_face += 1
                    indices.extend((face_indices[1], face_indices[2], face_indices[0]))
                    if len(face_indices) == 4:
                        indices.extend((face_indices[2], face_indices[3], face_indices[0]))
                vertices = [v for v, index in sorted(vertices.items(), key=lambda k: k[1])]
                material_id = self.material_writer.material_positions[material_name]
                meshes.append(Mesh(material_id, vertices, indices))
        finally:
            obj.to_mesh_clear()
        return meshes

    def _split_meshes_for_vertex_limit(self, divided_meshes):
        new_meshes = []
        limit = MAX_VERTICES_PER_MESH
        for mesh in divided_meshes:
            if len(mesh.vertices) > limit:
                start_index = 0
                while start_index < len(mesh.indices):
                    vertex_index_mapping = {}
                    new_indices = []
                    for i in range(start_index, len(mesh.indices), 3):
                        start_index += 3
                        face = mesh.indices[i:i+3]
                        for face_index in face:
                            if not face_index in vertex_index_mapping:
                                new_index = len(vertex_index_mapping)
                                vertex_index_mapping[face_index] = new_index
                            new_indices.append(vertex_index_mapping[face_index])
                        if len(vertex_index_mapping) >= limit-3:
                            break
                    verts = [mesh.vertices[v] for v, index in sorted(vertex_index_mapping.items(), key=lambda k: k[1])]
                    new_meshes.append(Mesh(mesh.material_id, verts, new_indices))
            else:
                new_meshes.append(mesh)
        return new_meshes

    def _calculate_uvs(self, obj, mesh, material_id, co):
        size = obj.dimensions
        x = co[0] / size[0]
        y = co[1] / size[1]
        mat = mesh.materials[material_id]
        texture_node = get_active_material_texture_slot(mat)
        if texture_node:
            x *= texture_node.texture_mapping.scale[0]
            y *= texture_node.texture_mapping.scale[1]
            x += texture_node.texture_mapping.translation[0]
            y += texture_node.texture_mapping.translation[1]
        return (x, y)


class NodeProperties:
    def __init__(self, node):
        ac_node = node.AC_KN5
        self.name = node.name
        self.lodIn = ac_node.lod_in
        self.lodOut = ac_node.lod_out
        self.layer = 0  # AC_KN5 doesn't have layer property
        self.castShadows = ac_node.cast_shadows
        self.visible = ac_node.visible
        self.transparent = ac_node.transparent
        self.renderable = ac_node.renderable


class NodeSettings:
    def __init__(self, settings, node_settings_key):
        self._settings = settings
        self._node_settings_key = node_settings_key
        self._node_name_matches = convert_to_regex_list(node_settings_key)

    def apply_settings_to_node(self, node):
        if not self._does_node_name_match(node.name):
            return
        for setting in NODE_SETTINGS:
            setting_val = self._get_node_setting(setting)
            if setting_val is not None:
                setattr(node, setting, setting_val)

    def _does_node_name_match(self, node_name):
        for regex in self._node_name_matches:
            if regex.match(node_name):
                return True
        return False

    def _get_node_setting(self, setting):
        if setting in self._settings[NODES][self._node_settings_key]:
            return self._settings[NODES][self._node_settings_key][setting]
        return None


class UvVertex:
    """
    Represents a unique vertex with position, normal, UV, and tangent data.

    Uses epsilon-based comparison to merge vertices that are effectively identical
    but have tiny floating-point differences from mesh processing. This reduces
    vertex count without affecting visual quality.

    Deduplication is based on position, normal, and UV only - NOT tangent.
    Tangents can vary slightly per-face even at the same vertex, and ksEditor
    does not appear to use tangent for vertex deduplication.

    The epsilon (1e-5) is chosen to:
    - Catch floating-point calculation noise from Blender
    - Preserve intentional differences (UV seams, hard edges)
    - Be well within 32-bit float precision (~7 significant digits)
    """

    # Epsilon for floating-point comparison
    # 1e-5 catches FP noise but preserves intentional differences
    EPSILON = 1e-5

    # Quantization factor for hashing (inverse of epsilon)
    # Vertices that compare equal must hash to the same bucket
    QUANT = 1e5

    def __init__(self, co, normal, uv, tangent):
        self.co = co
        self.normal = normal
        self.uv = uv
        self.tangent = tangent
        self._hash = None

    def _quantize(self, value):
        """Quantize a float to grid for consistent hashing."""
        return round(value * self.QUANT)

    def __hash__(self):
        """
        Hash using quantized values to ensure vertices that compare equal
        also hash to the same bucket. Only uses position, normal, UV (not tangent).
        """
        if self._hash is None:
            self._hash = hash((
                self._quantize(self.co[0]),
                self._quantize(self.co[1]),
                self._quantize(self.co[2]),
                self._quantize(self.normal[0]),
                self._quantize(self.normal[1]),
                self._quantize(self.normal[2]),
                self._quantize(self.uv[0]),
                self._quantize(self.uv[1]),
            ))
        return self._hash

    def _approx_equal(self, a, b):
        """Check if two floats are approximately equal within epsilon."""
        return abs(a - b) < self.EPSILON

    def __eq__(self, other):
        """
        Compare vertices using epsilon tolerance.

        Position, normal, and UV must match within epsilon to be considered equal.
        Tangent is NOT compared - it varies per-face and the first tangent
        encountered is used for merged vertices (matches ksEditor behavior).
        """
        # Position check
        if not (self._approx_equal(self.co[0], other.co[0]) and
                self._approx_equal(self.co[1], other.co[1]) and
                self._approx_equal(self.co[2], other.co[2])):
            return False

        # Normal check (preserves hard edges)
        if not (self._approx_equal(self.normal[0], other.normal[0]) and
                self._approx_equal(self.normal[1], other.normal[1]) and
                self._approx_equal(self.normal[2], other.normal[2])):
            return False

        # UV check (preserves texture seams)
        if not (self._approx_equal(self.uv[0], other.uv[0]) and
                self._approx_equal(self.uv[1], other.uv[1])):
            return False

        return True


class Mesh:
    def __init__(self, material_id, vertices, indices):
        self.material_id = material_id
        self.vertices = vertices
        self.indices = indices
