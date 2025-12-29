import re

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, IntProperty, PointerProperty, StringProperty)
from bpy.types import Object, PropertyGroup

from ..utils.constants import MAX_TEXTURE_SIZE, OBJECT_PREFIXES, SURFACE_VALID_KEY
from ..utils.files import find_maps, get_active_directory, set_path_reference
from ..utils.helpers import format_list_preview, get_objects_by_prefix, is_hidden_name
from ..utils.properties import ExtensionCollection
from .kn5.utils import is_object_excluded_by_collection
from .configs.audio_source import AC_AudioSource
from .configs.grassfx import AC_GrassFX
from .configs.lighting import AC_Lighting
from .configs.rainfx import AC_RainFX
from .configs.surface import AC_Surface
from .configs.track import AC_Track
from .configs.bulk_edit import AC_BulkEditSettings


class ExportSettings(PropertyGroup):
    export_format: EnumProperty(
        name="Export Format",
        description="Choose export format for track",
        items=[
            ("FBX", "FBX", "Export to FBX format for external tools"),
            ("KN5", "KN5", "Export to KN5 format (native AC format, recommended)"),
        ],
        default="KN5",
    )
    # Legacy property for compatibility
    use_kn5: BoolProperty(
        name="Export KN5",
        description="Export directly to KN5 format instead of FBX (deprecated - use export_format)",
        default=True,
        options={'HIDDEN'},
    )
    scale: FloatProperty(
        name="Global Scale",
        description="Scale to apply to exported track",
        default=1.0,
        min=0.0,
        soft_max=1.0,
        max=5.0,
    )
    forward: EnumProperty(
        name="Forward Vector",
        description="Forward vector for exported track",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="-Z",
    )
    up: EnumProperty(
        name="Up Vector",
        description="Up vector for exported track",
        items=(
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ),
        default="Y",
    )
    unit_scale: BoolProperty(
        name="Apply Unit Scale",
        description="Apply the scene's unit scale to the exported track",
        default=True,
    )
    space_transform: BoolProperty(
        name="Use Space Transform",
        description="Apply the scene's space transform to the exported track",
        default=True,
    )
    mesh_modifiers: BoolProperty(
        name="Use Mesh Modifiers",
        description="Apply mesh modifiers to the exported track",
        default=True,
    )
    scale_options: EnumProperty(
        name="Apply Scalings",
        description="How to apply custom and units scalings in generated FBX file "
        "(Blender uses FBX scale to detect units on import, "
        "but many other applications do not handle the same way)",
        default="FBX_SCALE_UNITS",
        items=(
            (
                "FBX_SCALE_NONE",
                "All Local",
                "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0",
            ),
            (
                "FBX_SCALE_UNITS",
                "FBX Units Scale",
                "Apply custom scaling to each object transformation, and units scaling to FBX scale",
            ),
            (
                "FBX_SCALE_CUSTOM",
                "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and units scaling to each object transformation",
            ),
            (
                "FBX_SCALE_ALL",
                "FBX All",
                "Apply custom scaling and units scaling to FBX scale",
            ),
        ),
    )
    batch_mode: EnumProperty(
        name="Batch Mode",
        default="OFF",
        items=(
            ("OFF", "Off", "Active scene to file"),
            ("SCENE", "Scene", "Each scene as a file"),
            (
                "COLLECTION",
                "Collection",
                "Each collection (data-block ones) as a file, does not include content of children collections",
            ),
            (
                "SCENE_COLLECTION",
                "Scene Collections",
                "Each collection (including master, non-data-block ones) of each scene as a file, "
                "including content from children collections",
            ),
            (
                "ACTIVE_SCENE_COLLECTION",
                "Active Scene Collections",
                "Each collection (including master, non-data-block one) of the active scene as a file, "
                "including content from children collections",
            ),
        ),
    )
    copy_textures: BoolProperty(
        name="Copy Textures to Track Folder",
        description="Copy all used textures to working_dir/content/textures/ after export",
        default=False,
    )


class KN5_MeshSettings(PropertyGroup):
    """KN5-specific settings for mesh objects"""
    lod_in: FloatProperty(
        name="LOD In",
        description="Distance where mesh becomes visible (meters)",
        default=0.0,
        min=0.0,
        max=10000.0,
    )
    lod_out: FloatProperty(
        name="LOD Out",
        description="Distance where mesh becomes invisible (meters). 0 = no distance culling.",
        default=0.0,
        min=0.0,
        max=10000.0,
    )
    cast_shadows: BoolProperty(
        name="Cast Shadows",
        description="Whether this mesh casts shadows in AC",
        default=True,
    )
    visible: BoolProperty(
        name="Visible",
        description="Whether this mesh is visible in AC",
        default=True,
    )
    renderable: BoolProperty(
        name="Renderable",
        description="Whether this mesh is rendered in AC",
        default=True,
    )
    transparent: BoolProperty(
        name="Transparent",
        description="Whether this mesh uses transparency",
        default=False,
    )


class AC_Settings(PropertyGroup):
    working_dir: StringProperty(
        name="Working Directory",
        description="Directory to save and load files",
        default="",
        subtype="DIR_PATH",
        update=lambda s, _: s.update_directory(s.working_dir),
    )

    export_settings: PointerProperty(
        type=ExportSettings,
        name="Export Settings",
    )
    track: PointerProperty(
        type=AC_Track,
        name="Track",
    )
    surfaces: CollectionProperty(
        type=AC_Surface,
        name="Track Surfaces",
    )
    surface_ext: CollectionProperty(
        type=ExtensionCollection,
        name="Surface Extensions",
        description="Unsupported extension to save/load",
    )
    global_extensions: CollectionProperty(
        type=ExtensionCollection,
        name="Global Extensions",
        description="Unsupported extension to save/load",
    )
    audio_sources: CollectionProperty(
        type=AC_AudioSource,
        name="Audio Sources",
    )
    lighting: PointerProperty(
        type=AC_Lighting,
        name="Lighting",
    )
    grassfx: PointerProperty(
        type=AC_GrassFX,
        name="GrassFX Settings",
    )
    rainfx: PointerProperty(
        type=AC_RainFX,
        name="RainFX Settings",
    )
    bulk_edit: PointerProperty(
        type=AC_BulkEditSettings,
        name="Bulk Edit Settings",
    )

    # Preflight scan caching
    preflight_scanned: BoolProperty(
        name="Preflight Scanned",
        description="Whether preflight checks have been run (session-only cache)",
        default=False,
    )
    preflight_has_blocking_errors: BoolProperty(
        name="Has Blocking Errors",
        description="Whether the last scan found blocking errors",
        default=False,
    )
    preflight_error_count: IntProperty(
        name="Error Count",
        description="Number of issues found in last scan",
        default=0,
    )
    active_material_index: IntProperty(
        name="Active Material",
        description="Currently selected material in Material Editor panel",
        default=0,
        min=0,
    )
    material_search_query: StringProperty(
        name="Search",
        description="Filter materials by name",
        default="",
    )
    # Cache for visible materials (populated by scan operator)
    # Format: comma-separated material names, empty = not scanned yet
    material_visibility_cache: StringProperty(
        name="Material Visibility Cache",
        description="Cached list of visible material names (internal)",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    error: list[dict] = []
    surface_errors: dict = {}
    active_surfaces: list[str] = []
    default_surfaces: dict = {
        "SURFACE_ROAD": {"KEY": "ROAD", "NAME": "Road", "FRICTION": 1, "CUSTOM": False},
        "SURFACE_KERB": {
            "KEY": "KERB",
            "NAME": "Kerb",
            "FRICTION": 0.92,
            "WAV": "kerb.wav",
            "WAV_PITCH": 1.3,
            "FF_EFFECT": 1,
            "VIBRATION_GAIN": 1.0,
            "VIBRATION_LENGTH": 1.5,
            "CUSTOM": False,
        },
        "SURFACE_GRASS": {
            "KEY": "GRASS",
            "NAME": "Grass",
            "FRICTION": 0.6,
            "WAV": "grass.wav",
            "WAV_PITCH": 0,
            "DIRT_ADDITIVE": 1,
            "IS_VALID_TRACK": False,
            "SIN_HEIGHT": 0.03,
            "SIN_LENGTH": 0.5,
            "VIBRATION_GAIN": 0.2,
            "VIBRATION_LENGTH": 0.6,
            "CUSTOM": False,
        },
        "SURFACE_SAND": {
            "KEY": "SAND",
            "NAME": "Sand",
            "FRICTION": 0.8,
            "DAMPING": 0.1,
            "WAV": "sand.wav",
            "WAV_PITCH": 0,
            "FF_EFFECT": 0,
            "DIRT_ADDITIVE": 1,
            "IS_VALID_TRACK": False,
            "SIN_HEIGHT": 0.04,
            "SIN_LENGTH": 0.5,
            "VIBRATION_GAIN": 0.2,
            "VIBRATION_LENGTH": 0.3,
            "CUSTOM": False,
        },
        "SURFACE_GRAVEL": {
            "KEY": "GRAVEL",
            "NAME": "Gravel",
            "FRICTION": 0.75,
            "DAMPING": 0.05,
            "WAV": "gravel.wav",
            "WAV_PITCH": 1.0,
            "FF_EFFECT": 2,
            "DIRT_ADDITIVE": 0.5,
            "IS_VALID_TRACK": False,
            "SIN_HEIGHT": 0.02,
            "SIN_LENGTH": 1.5,
            "VIBRATION_GAIN": 0.15,
            "VIBRATION_LENGTH": 0.5,
            # CSP Surface Tweaks
            "_EXT_SURFACE_TYPE": "GRAVEL",
            "_EXT_SURFACE_TYPE_MODIFIER": "LOOSE",
            "CUSTOM": True,  # Export to surfaces.ini with CSP extensions
        },
    }

    def reset_errors(self):
        self.error.clear()

    def get_surface_groups(
        self, context, key: str | None = None, ex_key: str | None = None
    ) -> list[Object] | dict[str, Object]:
        # dict of lists surface keys
        groups = {}
        for surface in self.surfaces:
            if surface.key not in groups:
                groups[surface.key] = []
        groups["WALL"] = []

        # if key is provided, only return objects from the scene matching the key
        for surfaceKey in groups:
            objects = [obj for obj in context.scene.objects if obj.type in ("MESH", "CURVE", "SURFACE")]
            for obj in objects:
                match = re.match(rf"^\d*{surfaceKey}.*$", obj.name)
                if match:
                    groups[surfaceKey].append(obj)

        if key:
            return groups.get(key, [])
        if ex_key:
            groups.pop(ex_key)
            return [obj for sublist in groups.values() for obj in sublist]
        return groups

    def get_walls(self, context) -> list[Object]:
        return self.get_surface_groups(context, "WALL")  # type: ignore

    def get_nonwalls(self, context) -> list[Object]:
        return self.get_surface_groups(context, ex_key="WALL")  # type: ignore

    def check_copy_names(self, context):
        # detect any AC objects with names ending in .001, .002, etc.
        # Returns: tuple (has_errors: bool, duplicate_names: list[str])
        obs = [obj for obj in context.scene.objects if obj.name.startswith("AC_")]
        duplicate_names = []
        for ob in obs:
            if re.match(r".*\.\d+$", ob.name):
                duplicate_names.append(ob.name)
        return (len(duplicate_names) > 0, duplicate_names)

    # return a list of {severity: int, message: str} objects
    # severity: 0 = info (non-blocking), 1 = warning (blocking, fixable), 2 = error (blocking, unfixable)
    def run_preflight(self, context) -> list:
        self.error.clear()

        # Check working directory first
        if not self.working_dir or self.working_dir == "":
            self.error.append(
                {"severity": 2, "message": "No working directory set", "code": "NO_WORKING_DIR"}
            )

        if not context.preferences.addons.get("io_scene_fbx"):
            self.error.append(
                {"severity": 2, "message": "FBX Exporter not enabled", "code": "NO_FBX"}
            )

        # Check for start positions and pitboxes
        start_count = len(self.get_starts(context))
        pitbox_count = len(self.get_pitboxes(context))

        if start_count == 0:
            self.error.append(
                {"severity": 2, "message": "No start positions defined", "code": "NO_STARTS"}
            )
        if pitbox_count == 0:
            self.error.append(
                {"severity": 2, "message": "No pitboxes defined", "code": "NO_PITBOXES"}
            )

        if start_count > 0 and pitbox_count > 0 and start_count != pitbox_count:
            self.error.append(
                {
                    "severity": 2,
                    "message": "Pitbox <-> Race Start mismatch",
                    "code": "PITBOX_START_MISMATCH",
                }
            )
        if pitbox_count != self.track.pitboxes:
            self.error.append(
                {
                    "severity": 1,
                    "message": "Pitbox count mismatch",
                    "code": "PITBOX_COUNT_MISMATCH",
                }
            )
        if not self.get_nonwalls(context):
            self.error.append(
                {
                    "severity": 0,
                    "message": "No track surfaces assigned",
                    "code": "NO_SURFACES",
                }
            )
        has_duplicates, duplicate_names = self.check_copy_names(context)
        if has_duplicates:
            dup_list = format_list_preview(duplicate_names, limit=5)
            self.error.append(
                {
                    "severity": 1,
                    "message": f"Track objects with duplicate suffixes (.001, .002): {dup_list}",
                    "code": "DUPLICATE_NAMES",
                }
            )
        if context.scene.unit_settings.system != "METRIC":
            self.error.append(
                {
                    "severity": 1,
                    "message": "Scene units are not set to Metric",
                    "code": "IMPERIAL_UNITS",
                }
            )
        if context.scene.unit_settings.length_unit != "METERS":
            self.error.append(
                {
                    "severity": 1,
                    "message": "Scene units are not set to Meters",
                    "code": "INVALID_UNITS",
                }
            )
        if context.scene.unit_settings.scale_length != 1:
            self.error.append(
                {
                    "severity": 1,
                    "message": "Scene scale is not set to 1",
                    "code": "INVALID_UNIT_SCALE",
                }
            )

        # KN5-specific checks
        if self.export_settings.export_format == "KN5":
            self._run_kn5_preflight_checks(context)

        # Check for missing map files (only if working directory is set)
        # These are now optional - severity 0 (info) means they won't block export
        if self.working_dir and self.working_dir != "":
            if self.working_dir != get_active_directory():
                set_path_reference(self.working_dir)
            map_files = find_maps()
            if not map_files["map"]:
                self.error.append(
                    {
                        "severity": 0,
                        "message": 'No map file found "./map.png" (optional)',
                        "code": "NO_MAP",
                    }
                )
            if not map_files["outline"]:
                self.error.append(
                    {
                        "severity": 0,
                        "message": 'No outline file found "./ui/outline.png" (optional)',
                        "code": "NO_OUTLINE",
                    }
                )
            if not map_files["preview"]:
                self.error.append(
                    {
                        "severity": 0,
                        "message": 'No preview file found "./ui/preview.png" (optional)',
                        "code": "NO_PREVIEW",
                    }
                )

        return self.error

    def _is_object_excluded(self, obj, context) -> bool:
        """Check if object should be excluded from preflight checks (same as export visibility)."""
        # Skip objects starting with "__" (templates/examples)
        if is_hidden_name(obj.name):
            return True
        # Use the same visibility check as the exporter
        return is_object_excluded_by_collection(obj, context)

    def _get_scene_materials(self, context):
        """Get all materials used by visible objects in the active scene."""
        materials = set()
        for obj in context.scene.objects:
            # Skip excluded objects (hidden, in hidden collections, etc.)
            if self._is_object_excluded(obj, context):
                continue
            if hasattr(obj, 'material_slots'):
                for slot in obj.material_slots:
                    if slot.material and not is_hidden_name(slot.material.name):
                        materials.add(slot.material)
        return materials

    def _run_kn5_preflight_checks(self, context):
        """KN5-specific validation checks."""
        # Check for empty material slots
        empty_slot_count = 0
        objects_with_empty_slots = []
        for obj in context.scene.objects:
            if obj.type != "MESH":
                continue
            if self._is_object_excluded(obj, context):
                continue

            if obj.material_slots:
                obj_empty_count = sum(1 for slot in obj.material_slots if slot.material is None)
                if obj_empty_count > 0:
                    empty_slot_count += obj_empty_count
                    objects_with_empty_slots.append(obj.name)

        if empty_slot_count > 0:
            obj_list = format_list_preview(objects_with_empty_slots, limit=5)
            self.error.append({
                "severity": 1,
                "message": f"Found {empty_slot_count} empty material slot(s): {obj_list}",
                "code": "KN5_EMPTY_MATERIAL_SLOTS",
            })

        # Check vertex counts
        for obj in context.scene.objects:
            if obj.type != "MESH":
                continue
            if self._is_object_excluded(obj, context):
                continue

            mesh_data = obj.to_mesh()
            try:
                vert_count = len(mesh_data.vertices)
                if vert_count > 65536:
                    self.error.append({
                        "severity": 0,  # Changed from 2 to 0 - show warning but allow export
                        "message": f"Mesh '{obj.name}' has {vert_count:,} vertices (max 65,536) - export may fail",
                        "code": "KN5_VERTEX_LIMIT",
                    })
            finally:
                obj.to_mesh_clear()

        # Check for procedural textures (only in materials used by scene objects)
        procedural_types = {
            'TEX_NOISE', 'TEX_GRADIENT', 'TEX_VORONOI', 'TEX_MAGIC',
            'TEX_WAVE', 'TEX_MUSGRAVE', 'TEX_CHECKER', 'TEX_BRICK'
        }
        procedural_nodes = []
        scene_materials = self._get_scene_materials(context)
        for mat in scene_materials:
            if not mat.node_tree:
                continue
            for node in mat.node_tree.nodes:
                if node.type in procedural_types:
                    procedural_nodes.append((mat.name, node.name))

        if procedural_nodes:
            # Get unique material names
            mat_names = list(set(mat_name for mat_name, node_name in procedural_nodes))
            mat_list = format_list_preview(mat_names, limit=5)
            self.error.append({
                "severity": 2,
                "message": f"Procedural textures not supported - replace with images: {mat_list}",
                "code": "KN5_PROCEDURAL_TEXTURES",
            })

        # Check for materials without node trees (only in scene)
        for mat in scene_materials:
            if not mat.node_tree:
                self.error.append({
                    "severity": 0,
                    "message": f"Material '{mat.name}' has no node tree - will use default shader",
                    "code": "KN5_NO_NODES",
                })

        # Check for objects with no materials
        for obj in context.scene.objects:
            if obj.type not in ("MESH", "CURVE", "SURFACE"):
                continue
            if self._is_object_excluded(obj, context):
                continue
            # Skip grass scatter system objects
            if obj.name.startswith("GRASS_"):
                continue
            # Skip template/example objects
            name_lower = obj.name.lower()
            if "_profile" in name_lower or "_example" in name_lower or "collider" in name_lower:
                continue

            # For curves/surfaces, check if they have modifiers that generate geometry
            # (Array, Geometry Nodes, etc.) - these will inherit materials from instances
            if obj.type in ("CURVE", "SURFACE"):
                has_geometry_modifiers = any(
                    mod.type in ("ARRAY", "NODES", "MIRROR", "SOLIDIFY")
                    for mod in obj.modifiers
                )
                if has_geometry_modifiers:
                    continue

            if not obj.material_slots:
                self.error.append({
                    "severity": 0,
                    "message": f"Object '{obj.name}' has no material assigned",
                    "code": "KN5_NO_MATERIAL",
                })
            else:
                for i, slot in enumerate(obj.material_slots):
                    if not slot.material:
                        self.error.append({
                            "severity": 0,
                            "message": f"Object '{obj.name}' has empty material slot {i}",
                            "code": "KN5_EMPTY_SLOT",
                        })

        # Check for mesh objects with children (KN5 limitation)
        for obj in context.scene.objects:
            if obj.type != "MESH":
                continue
            if self._is_object_excluded(obj, context):
                continue
            # Only count visible children
            children = [child for child in obj.children if not self._is_object_excluded(child, context)]
            if children:
                self.error.append({
                    "severity": 2,
                    "message": f"Mesh '{obj.name}' has {len(children)} child(ren) - KN5 meshes cannot have children",
                    "code": "KN5_MESH_CHILDREN",
                })

        # Check for oversized image textures (>15000x15000)
        oversized_images = []
        for image in bpy.data.images:
            # Skip generated/temporary images
            if is_hidden_name(image.name) or not image.name:
                continue

            # Check resolution
            if image.size[0] > MAX_TEXTURE_SIZE or image.size[1] > MAX_TEXTURE_SIZE:
                oversized_images.append({
                    "name": image.name,
                    "width": image.size[0],
                    "height": image.size[1]
                })

        if oversized_images:
            # Create warning message with image details
            img_details = [
                f"{img['name']} ({img['width']}x{img['height']}px)"
                for img in oversized_images
            ]
            img_list = format_list_preview(img_details, limit=3)

            self.error.append({
                "severity": 1,
                "message": f"Found {len(oversized_images)} image(s) larger than {MAX_TEXTURE_SIZE}x{MAX_TEXTURE_SIZE}px: {img_list}",
                "code": "KN5_OVERSIZED_TEXTURES",
            })

    def update_directory(self, path: str):
        if path == "":
            return
        if path == "//":
            self.working_dir = bpy.path.abspath(path)
            return
        print(f"Updating working directory to {path}")
        set_path_reference(path)

    def get_surfaces(self) -> list[AC_Surface]:
        out_surfaces = {}
        for surface in self.surfaces:
            out_surfaces[surface.key] = surface
        return list(out_surfaces.values())

    def map_surfaces(self) -> dict:
        surface_map = {}

        # only save custom surfaces
        custom_surfaces = [surface for surface in self.surfaces if surface.custom]
        for i, surface in enumerate(custom_surfaces):
            # validity check
            if not re.match(SURFACE_VALID_KEY, surface.key):
                self.surface_errors["surface"] = (
                    f"Surface {surface.name} assigned invalid key: {surface.key}"
                )

            surface_map[f"SURFACE_{i}"] = surface.to_dict()

        for extension in self.surface_ext:
            surface_map[extension.name] = {}
            for item in extension.items:
                surface_map[extension.name][item.key] = item.value
        return surface_map

    def load_surfaces(self, surface_map: dict):
        self.surfaces.clear()
        self.surface_ext.clear()
        # Track which surface KEYs we've already loaded to prevent duplicates
        loaded_keys = set()

        for surface in {**self.default_surfaces, **surface_map}.items():
            section_name = surface[0]
            section_data = surface[1]

            if section_name.startswith("DEFAULT"):
                continue

            # Check if this is a surface definition (has KEY field) or an extension
            # Sections with KEY field are surfaces, even if name doesn't start with SURFACE_
            is_surface = section_name.startswith("SURFACE_") or "KEY" in section_data

            if not is_surface:
                # This is a true extension (no KEY field)
                extension = self.surface_ext.add()
                extension.name = section_name
                for key, value in section_data.items():
                    pair = extension.items.add()
                    pair.key = key
                    pair.value = f"{value}"
                continue

            # This is a surface definition
            # Skip if we already loaded a surface with this KEY (prevent duplicates)
            surface_key = section_data.get("KEY", section_name)
            if surface_key in loaded_keys:
                continue
            loaded_keys.add(surface_key)

            new_surface = self.surfaces.add()
            new_surface.from_dict(
                section_data, section_data["CUSTOM"] if "CUSTOM" in section_data else True
            )

    def map_track(self, context) -> dict:
        track_info = self.track.to_dict()
        track_info.update(
            {
                "pitboxes": len(self.get_pitboxes(context)),
            }
        )
        return track_info

    def load_track(self, track: dict):
        self.track.from_dict(track)

    def map_lighting(self) -> dict:
        return self.lighting.to_dict()

    def load_lighting(self, lighting: dict):
        for section in lighting.items():
            if section[0] == "DEFAULT":
                continue
            self.lighting.from_dict(section[1])

    def map_audio(self) -> dict:
        audio_map = {}
        for audio in self.audio_sources:
            mapped = audio.to_dict()
            audio_map[mapped["NAME"]] = mapped
            audio_map[mapped["NAME"]].pop("NAME")
        return audio_map

    def load_audio(self, audio_map: dict):
        self.audio_sources.clear()
        for audio in audio_map.items():
            if audio[0].startswith("DEFAULT"):
                continue
            if not audio[0]:
                continue
            new_audio = self.audio_sources.add()
            audio[1]["NAME"] = audio[0]
            new_audio.from_dict(audio[1])
            pointer_name = audio[1]["NODE"] if "NODE" in audio[1] else audio[1]["NAME"]
            # find the object in the scene by name and assign it to the audio source
            new_audio.node_pointer = bpy.data.objects.get(pointer_name)

    # extensions are stored in a single config file, but should be organized by group within the UI.
    # each config section should get mapped to the proper config group when loaded, then saved back to the same file
    def map_extensions(self) -> dict:
        extension_map = {}
        for extension in self.global_extensions:
            extension_map[extension.name] = {}
            for item in extension.items:
                extension_map[extension.name][item.key] = item.value

        extension_map["LIGHTING"] = self.lighting.global_lighting.to_dict()

        # Add individual light sections
        spot_index = 0
        series_index = 0
        for light in self.lighting.lights:
            if not light.active:
                continue
            light_data = light.to_dict()
            if light.light_type == "SERIES":
                extension_map[f"LIGHT_SERIES_{series_index}"] = light_data
                series_index += 1
            else:
                extension_map[f"LIGHT_{spot_index}"] = light_data
                spot_index += 1

        # Add GRASS_FX section if enabled
        grassfx_dict = self.grassfx.to_dict()
        if grassfx_dict:
            extension_map.update(grassfx_dict)

        # Add RAIN_FX section if enabled
        rainfx_dict = self.rainfx.to_dict()
        if rainfx_dict:
            extension_map["RAIN_FX"] = rainfx_dict

        return extension_map

    def load_extensions(self, extension_map: dict):
        for extension in extension_map.items():
            if extension[0].startswith("DEFAULT") or not extension[0]:
                continue

            if extension[0] == "LIGHTING":  # global light settings
                self.lighting.global_lighting.from_dict(extension[1])
                continue

            if extension[0] == "GRASS_FX":  # CSP GrassFX settings
                self.grassfx.from_dict(extension[1])
                continue

            if extension[0] == "RAIN_FX":  # CSP RainFX settings
                self.rainfx.from_dict(extension[1])
                continue

            # Individual light sections
            if extension[0].startswith("LIGHT_SERIES_"):
                self.lighting.light_from_dict(extension[1], is_series=True)
                continue

            if extension[0].startswith("LIGHT_") and not extension[0].startswith("LIGHT_SERIES"):
                self.lighting.light_from_dict(extension[1], is_series=False)
                continue

            ext_group = self.global_extensions.add()
            ext_group.name = extension[0]
            for item in extension[1].items():
                new_item = ext_group.items.add()
                new_item.key = item[0]
                new_item.value = item[1]

    def get_starts(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['start'])

    def get_pitboxes(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['pitbox'])

    def get_hotlap_starts(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['hotlap'])

    def get_time_gates(self, context, pairs=False) -> list[Object] | list[list[Object]]:
        gates = get_objects_by_prefix(context, OBJECT_PREFIXES['time_gate'])
        if not pairs:
            return gates
        l_gates = [gate for gate in gates if gate.name.endswith("_L")]
        r_gates = [gate for gate in gates if gate.name.endswith("_R")]

        grouped_gates = []
        for gate in l_gates:
            match = re.match(r"^AC_TIME_(\d+)_L$", gate.name)
            if match:
                matching_r_gates = [g for g in r_gates if g.name == f"AC_TIME_{match.group(1)}_R"]
                if matching_r_gates:
                    grouped_gates.append([gate, matching_r_gates[0]])
        return grouped_gates

    def get_ab_start_gates(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['ab_start'])

    def get_ab_finish_gates(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['ab_finish'])

    def get_audio_emitters(self, context) -> list[Object]:
        return get_objects_by_prefix(context, OBJECT_PREFIXES['audio'])

    def consolidate_logic_gates(self, context):
        starts = self.get_starts(context)
        hotlap_starts = self.get_hotlap_starts(context)
        time_gates = self.get_time_gates(context)
        pitboxes = self.get_pitboxes(context)

        for i, gate in enumerate(starts):
            gate.name = f"AC_START_{i}"
        for i, gate in enumerate(hotlap_starts):
            gate.name = f"AC_HOTLAP_START_{i}"
        l_times = [gate for gate in time_gates if gate.name.endswith("_L")]
        r_times = [gate for gate in time_gates if gate.name.endswith("_R")]
        for i, gate in enumerate(l_times):
            gate.name = f"AC_TIME_{i}_L"
        for i, gate in enumerate(r_times):
            gate.name = f"AC_TIME_{i}_R"
        for i, box in enumerate(pitboxes):
            box.name = f"AC_PIT_{i}"


def get_settings() -> AC_Settings:
    return bpy.context.scene.AC_Settings  # type: ignore
