from bpy.ops import object
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator


# Base classes for tag operations to reduce duplication
class TagOperatorBase:
    """Base functionality for tag/geotag operations"""

    # Subclasses must define collection_name ('tags' or 'geotags')
    collection_name = None

    def get_collection(self, context):
        """Get the tag collection from track settings"""
        settings = context.scene.AC_Settings # type: ignore
        return getattr(settings.track, self.collection_name)


class AddTagBase(TagOperatorBase, Operator):
    """Base class for adding tags"""
    bl_options = {'REGISTER'}
    tag: StringProperty(
        name="Tag",
        default="New Tag",
    )

    def execute(self, context):
        collection = self.get_collection(context)
        tag = collection.add()
        tag.value = self.tag
        return {'FINISHED'}


class RemoveTagBase(TagOperatorBase, Operator):
    """Base class for removing tags"""
    bl_options = {'REGISTER'}
    index: IntProperty(
        name="Index",
        default=-1,
    )

    def execute(self, context):
        collection = self.get_collection(context)
        if self.index >= 0 and self.index < len(collection):
            collection.remove(self.index)
        return {'FINISHED'}


class ToggleTagBase(TagOperatorBase, Operator):
    """Base class for toggling tag visibility"""
    bl_options = {'REGISTER'}
    target: StringProperty(
        name="Target",
        default="",
    )

    # Subclasses must define toggle_property ('show_tags' or 'show_geotags')
    toggle_property = None

    def execute(self, context):
        settings = context.scene.AC_Settings # type: ignore
        current_value = getattr(settings.track, self.toggle_property)
        setattr(settings.track, self.toggle_property, not current_value)
        return {'FINISHED'}


# Concrete operator implementations for tags
class AC_AddTag(AddTagBase):
    """Add tag to track"""
    bl_idname = "ac.add_tag"
    bl_label = "Add Tag"
    collection_name = "tags"


class AC_RemoveTag(RemoveTagBase):
    """Remove tag from track"""
    bl_idname = "ac.remove_tag"
    bl_label = "Remove Tag"
    collection_name = "tags"


class AC_ToggleTag(ToggleTagBase):
    """Toggle tag"""
    bl_idname = "ac.toggle_tag"
    bl_label = "Toggle Tag"
    collection_name = "tags"
    toggle_property = "show_tags"


# Concrete operator implementations for geotags
class AC_AddGeoTag(AddTagBase):
    """Add geotag to track"""
    bl_idname = "ac.add_geo_tag"
    bl_label = "Add GeoTag"
    collection_name = "geotags"


class AC_RemoveGeoTag(RemoveTagBase):
    """Remove geotag from track"""
    bl_idname = "ac.remove_geo_tag"
    bl_label = "Remove GeoTag"
    collection_name = "geotags"


class AC_ToggleGeoTag(ToggleTagBase):
    """Toggle geotag"""
    bl_idname = "ac.toggle_geo_tag"
    bl_label = "Toggle GeoTag"
    collection_name = "geotags"
    toggle_property = "show_geotags"

class AC_SelectByName(Operator):
    """Select object by name"""
    bl_idname = "ac.select_by_name"
    bl_label = "Select By Name"
    bl_options = {'REGISTER'}
    name: StringProperty(
        name="Name",
        default="",
    )
    def execute(self, context):
        ob = context.scene.objects.get(self.name)
        if ob:
            object.select_all(action='DESELECT')
            ob.select_set(True)
            context.view_layer.objects.active = ob
        return {'FINISHED'}
