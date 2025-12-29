import bpy
import math
from bpy.types import Gizmo, GizmoGroup, Object, Operator
from mathutils import Matrix, Vector, Euler

from ..settings import AC_Settings
from ...utils.constants import GIZMO_SCALE, GIZMO_HIGHLIGHT_FACTOR, GIZMO_ALPHA_MULTIPLIER

# Map object prefixes to gizmo configuration
GIZMO_TYPE_MAP = {
    'AC_PIT_': {
        'class': 'AC_GizmoPitbox',
        'pref_show': 'show_pitboxes',
        'pref_color': 'pitbox_color'
    },
    'AC_START_': {
        'class': 'AC_GizmoStartPos',
        'pref_show': 'show_start',
        'pref_color': 'start_color'
    },
    'AC_HOTLAP_START_': {
        'class': 'AC_GizmoStartPos',
        'pref_show': 'show_hotlap_start',
        'pref_color': 'hotlap_start_color'
    },
}


class AC_SelectGizmoObject(Operator):
    """Select the object associated with this gizmo"""
    bl_idname = "ac.select_gizmo_object"
    bl_label = "Select Object"
    bl_options = {'INTERNAL'}

    object_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        ob = context.scene.objects.get(self.object_name)
        if ob:
            # Deselect all other objects first
            for obj in context.selected_objects:
                obj.select_set(False)
            # Select and make active
            ob.select_set(True)
            context.view_layer.objects.active = ob
        return {'FINISHED'}


class AC_GizmoPitbox(Gizmo):
    bl_idname = "AC_GizmoPitbox"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    ob_name: str

    def setup(self):
        if not hasattr(self, "shape"):
            # Pitbox: box with X on ground + "PIT" text on front vertical wall
            # Floor is at Y=-1, box is square from X=-1 to X=1, Z=-1 to Z=1
            self.shape = self.new_custom_shape('TRIS',
            [
                # Box outline on ground (Y=-1 plane)
                # Front edge (Z=1)
                (-1, -1, 1), (1, -1, 1), (1, -1, 1.05),
                (-1, -1, 1), (1, -1, 1.05), (-1, -1, 1.05),
                # Back edge (Z=-1)
                (-1, -1, -1), (1, -1, -1), (1, -1, -0.95),
                (-1, -1, -1), (1, -1, -0.95), (-1, -1, -0.95),
                # Left edge (X=-1)
                (-1, -1, -1), (-1, -1, 1), (-1, -1, 1.05),
                (-1, -1, -1), (-1, -1, 1.05), (-1, -1, -0.95),
                # Right edge (X=1)
                (1, -1, -1), (1, -1, 1), (1, -1, 1.05),
                (1, -1, -1), (1, -1, 1.05), (1, -1, -0.95),

                # X inside box on ground (Y=-1 plane)
                # Diagonal 1: top-left to bottom-right (this one was working)
                (-0.85, -1, 0.85), (-0.75, -1, 0.85), (0.85, -1, -0.85),
                (-0.75, -1, 0.85), (0.85, -1, -0.75), (0.85, -1, -0.85),

                # Diagonal 2: top-right to bottom-left (mirror the pattern)
                (0.85, -1, 0.85), (0.75, -1, 0.85), (-0.85, -1, -0.85),
                (0.75, -1, 0.85), (-0.85, -1, -0.75), (-0.85, -1, -0.85),

                # Short vertical walls on left and right sides (Y=-1 to Y=-0.7, extending front to back)
                # Left wall (X=-1, Z=-1 to Z=1, short height Y=-1 to Y=-0.9)
                (-1, -1, -1), (-1, -0.9, -1), (-1, -0.9, 1),
                (-1, -1, -1), (-1, -0.9, 1), (-1, -1, 1),
                # Right wall (X=1, Z=-1 to Z=1, short height Y=-1 to Y=-0.9)
                (1, -1, -1), (1, -0.9, -1), (1, -0.9, 1),
                (1, -1, -1), (1, -0.9, 1), (1, -1, 1),

                # "PIT" text on front vertical wall (Z=1, Y=-1 to Y=-0.7, using X and Y)
                # P - vertical bar (left side, full height)
                (-0.7, -1, 1), (-0.6, -1, 1), (-0.6, -0.7, 1),
                (-0.7, -1, 1), (-0.6, -0.7, 1), (-0.7, -0.7, 1),
                # P - top horizontal (connecting to top of vertical bar)
                (-0.6, -0.75, 1), (-0.3, -0.75, 1), (-0.3, -0.7, 1),
                (-0.6, -0.75, 1), (-0.3, -0.7, 1), (-0.6, -0.7, 1),
                # P - middle horizontal (closing the loop)
                (-0.6, -0.85, 1), (-0.3, -0.85, 1), (-0.3, -0.8, 1),
                (-0.6, -0.85, 1), (-0.3, -0.8, 1), (-0.6, -0.8, 1),
                # P - right vertical segment (only from middle to top, forming the loop)
                (-0.3, -0.85, 1), (-0.2, -0.85, 1), (-0.2, -0.7, 1),
                (-0.3, -0.85, 1), (-0.2, -0.7, 1), (-0.3, -0.7, 1),

                # I - vertical bar
                (-0.05, -1, 1), (0.05, -1, 1), (0.05, -0.7, 1),
                (-0.05, -1, 1), (0.05, -0.7, 1), (-0.05, -0.7, 1),

                # T - top horizontal
                (0.2, -0.75, 1), (0.7, -0.75, 1), (0.7, -0.7, 1),
                (0.2, -0.75, 1), (0.7, -0.7, 1), (0.2, -0.7, 1),
                # T - vertical bar
                (0.4, -1, 1), (0.5, -1, 1), (0.5, -0.7, 1),
                (0.4, -1, 1), (0.5, -0.7, 1), (0.4, -0.7, 1),
            ])
            self.scale = GIZMO_SCALE
            self.use_draw_scale = False
            self.use_draw_modal = True
            self.use_select_background = True

    def draw(self, context):
        from gpu.state import blend_set
        blend_set('ALPHA')
        self.draw_custom_shape(self.shape)
        blend_set('NONE')

    def draw_select(self, context, select_id): # type: ignore
        self.draw_custom_shape(self.shape, select_id=select_id)

    def update(self, mat_location, mat_rotation):
        mat_t = Matrix.Translation(mat_location)
        mat_r = mat_rotation.to_matrix().to_4x4()
        self.matrix_basis = mat_t @ mat_r


class AC_GizmoStartPos(Gizmo):
    bl_idname = "AC_GizmoStartPos"
    bl_target_properties = (
        {"id": "offset", "type": 'FLOAT', "array_length": 1},
    )

    ob_name: str

    def setup(self):
        if not hasattr(self, "shape"):
            # Wide, short U-shape with floor marking and vertical walls
            # Floor is at Y=-1, vertical walls from Y=-0.7 to Y=-0.5
            # U-shape extends in Z direction, front at Z=1
            self.shape = self.new_custom_shape('TRIS',
            [
                # Floor markings on Y=-1 plane

                # Left floor bar (X=-1 side, Z=0.7 to Z=1)
                (-1, -1, 0.7), (-0.85, -1, 0.7), (-0.85, -1, 1),
                (-1, -1, 0.7), (-0.85, -1, 1), (-1, -1, 1),

                # Right floor bar (X=1 side, Z=0.7 to Z=1)
                (0.85, -1, 0.7), (1, -1, 0.7), (1, -1, 1),
                (0.85, -1, 0.7), (1, -1, 1), (0.85, -1, 1),

                # Front floor bar (connecting left and right at Z=1)
                (-0.85, -1, 1), (0.85, -1, 1), (0.85, -1, 0.85),
                (-0.85, -1, 1), (0.85, -1, 0.85), (-0.85, -1, 0.85),

                # Short vertical walls (Y=-1 to Y=-0.9, same height as pitbox)

                # Left vertical wall (X=-1, Z=0.7 to Z=1)
                (-1, -1, 0.7), (-1, -0.9, 0.7), (-1, -0.9, 1),
                (-1, -1, 0.7), (-1, -0.9, 1), (-1, -1, 1),

                # Right vertical wall (X=1, Z=0.7 to Z=1)
                (1, -1, 0.7), (1, -0.9, 0.7), (1, -0.9, 1),
                (1, -1, 0.7), (1, -0.9, 1), (1, -1, 1),

                # Front vertical wall (Z=1, X=-1 to X=1, Y=-1 to Y=-0.9)
                (-1, -1, 1), (1, -1, 1), (1, -0.9, 1),
                (-1, -1, 1), (1, -0.9, 1), (-1, -0.9, 1),
            ])
            self.scale = GIZMO_SCALE
            self.use_draw_scale = False
            self.use_draw_modal = True
            self.use_select_background = True

    def draw(self, context):
        from gpu.state import blend_set
        blend_set('ALPHA')
        self.draw_custom_shape(self.shape)
        blend_set('NONE')

    def draw_select(self, context, select_id): # type: ignore
        self.draw_custom_shape(self.shape, select_id=select_id)

    def update(self, mat_location, mat_rotation):
        mat_t = Matrix.Translation(mat_location)
        mat_r = mat_rotation.to_matrix().to_4x4()
        self.matrix_basis = mat_t @ mat_r


class AC_GizmoGate(Gizmo):
    bl_idname = "AC_GizmoGate"

    pos_start: tuple[float, float, float]
    pos_end: tuple[float, float, float]
    def setup(self):
        if not hasattr(self, "shape"):
            self.shape = self.new_custom_shape('LINES', [(-1, 0, 0), (1, 0, 0)])
            self.scale = 1, 1, 1
            self.use_draw_scale = False
            self.use_draw_modal = True

    def update_shape(self):
        up_vector = Vector((0, 0, 0.5))
        down_vector = Vector((0, 0, -0.5))

        self.shape = self.new_custom_shape('LINES',
            [
                self.pos_start, self.pos_end,
                self.pos_start + down_vector, self.pos_end + down_vector,
                self.pos_start + up_vector, self.pos_end + up_vector,
            ])

    def draw(self, context):
        self.draw_custom_shape(self.shape)

    def draw_select(self, context, select_id): # type: ignore
        self.draw_custom_shape(self.shape, select_id=select_id)

    def update(self, loc_start, loc_end):
        self.pos_start = loc_start
        self.pos_end = loc_end
        self.update_shape()


class AC_GizmoGroup(GizmoGroup):
    bl_idname = "AC_GizmoGroup"
    bl_label = "AC Track Gizmo Group"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', '3D', 'SHOW_MODAL_ALL', 'DEPTH_3D'}

    @classmethod
    def poll(cls, context): # type: ignore
        return (context.scene.objects)

    @staticmethod
    def _compute_gizmo_matrix(obj):
        """Compute the matrix for a gizmo based on object location and rotation.

        Applies a compensating +90° X rotation to flatten gizmo on ground,
        then applies the object's Z rotation (heading).
        """
        loc = obj.location.copy()
        rot = obj.matrix_world.to_euler('XYZ')
        compensating_rot = Euler((math.pi * 0.5, 0, rot.z), 'XYZ')
        mat_t = Matrix.Translation(loc)
        mat_r = compensating_rot.to_matrix().to_4x4()
        return mat_t @ mat_r


    def setup(self, context):
        prefs = context.preferences.addons[__package__.split('.')[0]].preferences # type: ignore
        self.gizmos.clear()
        obs = context.scene.objects

        for ob in obs:
            if ob.type == 'EMPTY':
                # Check each prefix in the gizmo type map
                for prefix, config in GIZMO_TYPE_MAP.items():
                    if ob.name.startswith(prefix):
                        # Create gizmo of the appropriate class
                        gb = self.gizmos.new(config['class'])

                        # Set matrix based on object location and rotation
                        gb.matrix_basis = self._compute_gizmo_matrix(ob)

                        # Configure gizmo properties
                        gb.ob_name = ob.name

                        # Set target operator for click selection
                        op = gb.target_set_operator("ac.select_gizmo_object")
                        op.object_name = ob.name

                        # Get color from preferences
                        color = getattr(prefs, config['pref_color'])
                        show = getattr(prefs, config['pref_show'])

                        # Set visibility and colors
                        gb.hide = not ob.visible_get() or not show
                        gb.color = color[:3]
                        gb.alpha = color[3] * GIZMO_ALPHA_MULTIPLIER
                        gb.color_highlight = tuple(min(c * GIZMO_HIGHLIGHT_FACTOR, 1.0) for c in color[:3])
                        gb.alpha_highlight = color[3]

                        # Only process first matching prefix
                        break

    def refresh(self, context):
        prefs = context.preferences.addons[__package__.split('.')[0]].preferences # type: ignore

        # Get current valid objects
        valid_object_names = set()
        for ob in context.scene.objects:
            if ob.type == 'EMPTY':
                for prefix in GIZMO_TYPE_MAP.keys():
                    if ob.name.startswith(prefix):
                        valid_object_names.add(ob.name)
                        break

        # Identify gizmos to remove (stale gizmos whose objects no longer exist)
        gizmos_to_remove = []
        existing_gizmo_object_names = set()

        for g in self.gizmos:
            if g.bl_idname in ['AC_GizmoPitbox', 'AC_GizmoStartPos']:
                if hasattr(g, 'ob_name'):
                    if g.ob_name not in valid_object_names:
                        # Object was deleted - mark gizmo for removal
                        gizmos_to_remove.append(g)
                    else:
                        existing_gizmo_object_names.add(g.ob_name)
            elif g.bl_idname == 'AC_GizmoGate':
                # Gate gizmos are always recreated, mark for removal
                gizmos_to_remove.append(g)

        # Remove stale gizmos
        for g in gizmos_to_remove:
            self.gizmos.remove(g)

        # Check if we need to add new gizmos (for new objects)
        new_objects = valid_object_names - existing_gizmo_object_names
        if new_objects:
            # Need to add gizmos for new objects - rebuild all to be safe
            self.setup(context)
            return

        # Update existing gizmos
        for g in self.gizmos:
            if not hasattr(g, 'ob_name'):
                continue

            ob = context.scene.objects.get(g.ob_name)
            if not ob:
                # This shouldn't happen after cleanup, but hide just in case
                g.hide = True
                continue

            # Update visibility based on object type
            if ob.name.startswith('AC_PIT_'):
                g.hide = not ob.visible_get() or not prefs.show_pitboxes
            elif ob.name.startswith('AC_START_'):
                g.hide = not ob.visible_get() or not prefs.show_start
            elif ob.name.startswith('AC_HOTLAP_START_'):
                g.hide = not ob.visible_get() or not prefs.show_hotlap_start

            # Update gizmo position and rotation
            g.matrix_basis = self._compute_gizmo_matrix(ob)

        settings: AC_Settings = context.scene.AC_Settings # type: ignore
        time_gates: list[list[Object]] = settings.get_time_gates(context, True) # type: ignore
        for gate in time_gates:
            if len(gate) != 2:
                continue
            g = self.gizmos.new("AC_GizmoGate")
            g.hide = not gate[0].visible_get() or not gate[1].visible_get() or not prefs.show_time_gates
            g.color = prefs.time_gate_color[:3]
            g.alpha = prefs.time_gate_color[3] * GIZMO_ALPHA_MULTIPLIER
            g.color_highlight = prefs.time_gate_color[:3]
            g.alpha_highlight = prefs.time_gate_color[3]
            g.update(gate[0].location, gate[1].location)

        ab_start_gates = settings.get_ab_start_gates(context)
        if len(ab_start_gates) % 2 == 0 and len(ab_start_gates) > 0:
            g = self.gizmos.new("AC_GizmoGate")
            g.hide = not ab_start_gates[0].visible_get() or not ab_start_gates[1].visible_get() or not prefs.show_ab_start
            g.color = prefs.ab_start_color[:3]
            g.alpha = prefs.ab_start_color[3] * GIZMO_ALPHA_MULTIPLIER
            g.color_highlight = prefs.ab_start_color[:3]
            g.alpha_highlight = prefs.ab_start_color[3]
            g.update(ab_start_gates[0].location, ab_start_gates[1].location)

        ab_finish_gates = settings.get_ab_finish_gates(context)
        if len(ab_finish_gates) % 2 == 0 and len(ab_finish_gates) > 0:
            g = self.gizmos.new("AC_GizmoGate")
            g.hide = not ab_finish_gates[0].visible_get() or not ab_finish_gates[1].visible_get() or not prefs.show_ab_finish
            g.color = prefs.ab_finish_color[:3]
            g.alpha = prefs.ab_finish_color[3] * GIZMO_ALPHA_MULTIPLIER
            g.color_highlight = prefs.ab_finish_color[:3]
            g.alpha_highlight = prefs.ab_finish_color[3]
            g.update(ab_finish_gates[0].location, ab_finish_gates[1].location)
