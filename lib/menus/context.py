import re

from bpy.types import Menu, UILayout

from ...utils.constants import SURFACE_VALID_KEY
from ..configs.surface import AC_Surface


class WM_MT_AssignSurface(Menu):
    bl_label = "Assign Surface"
    bl_idname = "WM_MT_AssignSurface"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.AC_Settings # type: ignore
        surface: AC_Surface
        for surface in settings.get_surfaces():
            if not re.match(SURFACE_VALID_KEY, surface.key):
                layout.label(text=f"Invalid surface key: {surface.key}")
                continue
            op = layout.operator("ac.assign_surface", text=surface.name)
            op.key = surface.key
        if len(settings.surfaces) == 0:
            layout.label(text="No surfaces available")

class WM_MT_ObjectSetup(Menu):
    bl_label = "Object Setup"
    bl_idname = "WM_MT_ObjectSetup"

    def draw(self, context):
        layout = self.layout
        layout.operator("ac.setup_as_tree", icon='OUTLINER_OB_MESH')
        layout.operator("ac.setup_as_grass", icon='OUTLINER_OB_GREASEPENCIL')
        layout.operator("ac.setup_as_standard", icon='OBJECT_DATA')

def surface_menu(self, context):
    layout: UILayout = self.layout
    if len(context.selected_objects) == 0: # only show the menu if an object is selected
        return
    objects = [obj for obj in context.selected_objects if obj.type in ('MESH', 'CURVE', 'SURFACE')]
    if len(objects) == 0: # only show the menu if a mesh/curve/surface object is selected
        return
    layout.separator()
    layout.menu("WM_MT_AssignSurface")
    layout.operator("ac.assign_wall")
    layout.operator("ac.assign_phys_prop")
    layout.separator()
    layout.menu("WM_MT_ObjectSetup")
