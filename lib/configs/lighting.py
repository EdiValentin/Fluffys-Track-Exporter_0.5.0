from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, FloatVectorProperty, IntProperty,
                       PointerProperty, StringProperty)
import mathutils
from bpy.types import Material, Object, PropertyGroup

from ...utils.helpers import is_hidden_name


# CSP Condition Presets - built-in conditions from common/conditions.ini
CONDITION_PRESETS = [
    ("NONE", "None", "No condition - always active"),
    ("", "", "", "DISABLE", 1),  # Separator
    # Time-based (most common)
    ("NIGHT_SMOOTH", "Night (Smooth)", "Activates at dusk with gradual fade (most common)"),
    ("NIGHT_SHARP", "Night (Sharp)", "Activates at dusk with instant on/off"),
    ("ALWAYS_ON", "Always On", "Constant activation"),
    ("ALL_DAYS", "All Days", "Always on with optimized day/night intensity curve"),
    ("", "", "", "DISABLE", 5),  # Separator
    # Early activation (tunnels/interiors)
    ("SMOOTH_SUN_A", "Early Night (Smooth)", "Activates 5° above horizon - for tunnels/interiors"),
    ("SHARP_SUN_A", "Early Night (Sharp)", "Activates 5° above horizon with instant response"),
    ("", "", "", "DISABLE", 8),  # Separator
    # Flashing/Effects
    ("HAZARDS", "Hazards (4Hz)", "4Hz synced flashing - warning lights, beacons"),
    ("FLAME_FLICKERING", "Flame Flickering", "5Hz irregular flickering - fire, candles, torches"),
    ("", "", "", "DISABLE", 11),  # Separator
    # Heating simulation
    ("NIGHT_SMOOTH_HEATING", "Night + Heating", "Gradual warm-up effect"),
    ("NIGHT_SLOW_HEATING", "Night + Slow Heating", "Very slow warm-up (like sodium lamps)"),
    ("", "", "", "DISABLE", 14),  # Separator
    # Racing/Seasonal
    ("RACING_FLAG", "Racing Flag", "Changes based on race flag state"),
    ("SEASON_SUMMER_NORTH", "Summer (North)", "Peak intensity in summer months"),
    ("SEASON_WINTER_NORTH", "Winter (North)", "Peak intensity in winter months"),
    ("", "", "", "DISABLE", 18),  # Separator
    ("CUSTOM", "Custom...", "Enter a custom condition string"),
]

# Condition presets for emissive materials (MATERIAL_ADJUSTMENT)
# Some conditions cause glow to stop working, so we exclude them here
EMISSIVE_CONDITION_PRESETS = [
    ("NONE", "None", "No condition - always active"),
    ("", "", "", "DISABLE", 1),  # Separator
    # Time-based (sharp transitions only - smooth ones break glow)
    ("NIGHT_SHARP", "Night (Sharp)", "Activates at dusk with instant on/off"),
    ("ALWAYS_ON", "Always On", "Constant activation"),
    ("", "", "", "DISABLE", 4),  # Separator
    # Early activation (tunnels/interiors)
    ("SHARP_SUN_A", "Early Night (Sharp)", "Activates 5° above horizon with instant response"),
    ("", "", "", "DISABLE", 6),  # Separator
    # Heating simulation
    ("NIGHT_SMOOTH_HEATING", "Night + Heating", "Gradual warm-up effect"),
    ("NIGHT_SLOW_HEATING", "Night + Slow Heating", "Very slow warm-up (like sodium lamps)"),
    ("", "", "", "DISABLE", 9),  # Separator
    # Racing/Seasonal
    ("RACING_FLAG", "Racing Flag", "Changes based on race flag state"),
    ("SEASON_SUMMER_NORTH", "Summer (North)", "Peak intensity in summer months"),
    ("SEASON_WINTER_NORTH", "Winter (North)", "Peak intensity in winter months"),
    ("", "", "", "DISABLE", 13),  # Separator
    ("CUSTOM", "Custom...", "Enter a custom condition string"),
]


def update_condition_preset(self, context):
    """Update the condition string when preset changes"""
    if self.condition_preset == "NONE":
        self.use_condition = False
        self.condition = ""
    elif self.condition_preset == "CUSTOM":
        self.use_condition = True
        # Keep existing condition string for custom
    elif self.condition_preset:
        self.use_condition = True
        self.condition = self.condition_preset
    # Sync to linked object if this is an AC_Light
    if hasattr(self, 'sync_csp_to_object'):
        self.sync_csp_to_object()


class AC_CSPLightSettings(PropertyGroup):
    """CSP-specific light settings stored on Blender objects.

    These properties are attached to bpy.types.Object so they persist
    when duplicating lights in Blender. The addon syncs these with
    AC_Light entries when scanning/exporting.
    """

    # Shape settings (not available on native Blender lights)
    spot_sharpness: FloatProperty(
        name="Spot Sharpness",
        description="Sharpness of spotlight edge (0=sharp, 1=soft)",
        default=0.3,
        min=0,
        max=1
    )
    range_gradient_offset: FloatProperty(
        name="Range Gradient Offset",
        description="Light fade out starting distance",
        default=0.2,
        min=0,
        max=1
    )

    # Performance settings
    fade_at: IntProperty(
        name="Fade At",
        description="Distance where brightness has 50% intensity",
        default=400,
        min=0,
        max=1000
    )
    fade_smooth: IntProperty(
        name="Fade Smooth",
        description="Fade out smoothness",
        default=50,
        min=0,
        max=100
    )

    # Color settings (CSP-specific)
    specular_multiplier: FloatProperty(
        name="Specular Multiplier",
        description="Specular multiplier",
        default=0,
        min=0,
        max=4
    )
    single_frequency: BoolProperty(
        name="Single Frequency",
        description="Use single frequency for light",
        default=False
    )
    diffuse_concentration: FloatProperty(
        name="Diffuse Concentration",
        description="Diffuse concentration",
        default=0.88,
        min=0,
        max=1
    )

    # Condition settings
    condition_preset: EnumProperty(
        name="Condition Preset",
        description="Select a built-in CSP condition",
        items=CONDITION_PRESETS,
        default="NONE"
    )
    use_condition: BoolProperty(
        name="Use Condition",
        description="Enable condition trigger",
        default=False
    )
    condition: StringProperty(
        name="Condition",
        description="Condition trigger to control brightness and color",
        default=""
    )
    condition_offset: StringProperty(
        name="Condition Offset",
        description="Offset condition flashing",
        default=""
    )

    # Extras
    volumetric_light: BoolProperty(
        name="Volumetric Light",
        description="Enable volumetric light (expensive)",
        default=False
    )
    long_specular: BoolProperty(
        name="Long Specular",
        description="Enable long specular (wet look, cannot cast shadows)",
        default=False
    )
    skip_light_map: BoolProperty(
        name="Skip Light Map",
        description="Exclude light from bounced lighting FX",
        default=False
    )
    disable_with_bounced_light: BoolProperty(
        name="Disable With Bounced Light",
        description="Disable light when bounced light is enabled",
        default=False
    )

    # Shadow settings
    cast_shadows: BoolProperty(
        name="Shadows",
        description="Cast shadows",
        default=False
    )
    shadows_static: BoolProperty(
        name="Shadows Static",
        description="Static shadows",
        default=True
    )
    shadows_half_res: BoolProperty(
        name="Shadows Half Res",
        description="Half resolution shadows",
        default=False
    )
    shadows_spot_angle: IntProperty(
        name="Shadows Spot Angle",
        description="Shadow spotlight angle",
        default=0,
        min=0,
        max=180
    )
    shadows_range: FloatProperty(
        name="Shadows Range",
        description="Shadow casting distance",
        default=0,
        min=0,
        max=1000
    )
    shadows_boost: FloatProperty(
        name="Shadows Boost",
        description="Shadow boost",
        default=0,
        min=0,
        max=4
    )
    shadows_clip_plane: FloatProperty(
        name="Shadows Clip Plane",
        description="Shadow clip plane distance",
        default=0.5,
        min=0,
        max=100
    )
    shadows_clip_sphere: FloatProperty(
        name="Shadows Clip Sphere",
        description="Shadow clip sphere radius",
        default=0.5,
        min=0,
        max=100
    )
    shadows_exp_factor: IntProperty(
        name="Shadow Exp Factor",
        description="Shadow exponent factor",
        default=20,
        min=0,
        max=100
    )
    shadows_extra_blur: BoolProperty(
        name="Shadow Extra Blur",
        description="Shadow extra blur",
        default=False
    )


class AC_SunSettings(PropertyGroup):
    sun_pitch_angle: IntProperty(
        name="Sun Pitch Angle",
        description="The pitch angle of the sun (sunrise <-> noon)",
        default=45,
        min=0,
        max=180
    )

    sun_heading_angle: IntProperty(
        name="Sun Heading Angle",
        description="The heading angle of the sun (cardinal direction)",
        default=0,
        min=-180,
        max=180
    )

class AC_GlobalLighting(PropertyGroup):
    enable_trees_lighting: BoolProperty(
        name="Enable Trees Lighting",
        description="If all your trees are not very close to a track, you can improve performance a lot by disabling trees lighting completely",
        default=True
    )

    use_track_ambient_ground_mult: BoolProperty(
        name="Use Track Ambient Ground Multiplier",
        description="Override default ambient ground lighting (affects surfaces facing down)",
        default=False
    )
    track_ambient_ground_mult: FloatProperty(
        name="Track Ambient Ground Multiplier",
        description="Allows to redefine ambient multiplier for surfaces facing down",
        default=0.5,
        min=0,
        max=1
    )

    use_multipliers: BoolProperty(
        name="Use Multipliers",
        default=False
    )
    lit_mult: FloatProperty(
        name="Lit Multiplier",
        description="Multiplier for dynamic lights affecting the track",
        default=1,
        min=0,
        max=4
    )

    specular_mult: FloatProperty(
        name="Specular Multiplier",
        description="Multiplier for speculars",
        default=1,
        min=0,
        max=4
    )

    car_lights_lit_mult: FloatProperty(
        name="Car Lights Lit Multiplier",
        description="Multiplier for dynamic lights affecting cars on the track",
        default=1,
        min=0,
        max=4
    )

    use_bounced_light_mult: BoolProperty(
        name="Use Bounced Light Multiplier",
        default=False
    )
    bounced_light_mult: FloatVectorProperty(
        name="Bounced Light Multiplier",
        description="Multiplier for bouncing light (set to 0 if track is black, for example)",
        default=(1, 1, 1, 1),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    use_terrain_shadows_threshold: BoolProperty(
        name="Use Terrain Shadows Threshold",
        default=False
    )
    terrain_shadows_threshold: FloatProperty(
        name="Terrain Shadows Threshold",
        description="Terrain shadows threshold",
        default=0,
        min=0,
        max=1
    )

    def from_dict(self, data: dict):
        self.enable_trees_lighting = data.get("ENABLE_TREES_LIGHTING", 0) == 1
        self.use_track_ambient_ground_mult = "TRACK_AMBIENT_GROUND_MULT" in data
        self.track_ambient_ground_mult = float(data.get("TRACK_AMBIENT_GROUND_MULT", 0.5))
        self.use_multipliers = "LIT_MULT" in data
        self.lit_mult = float(data.get("LIT_MULT", 1))
        self.specular_mult = float(data.get("SPECULAR_MULT", 1))
        self.car_lights_lit_mult = float(data.get("CAR_LIGHTS_LIT_MULT", 1))
        self.use_bounced_light_mult = "BOUNCED_LIGHT_MULT" in data
        self.bounced_light_mult = data.get("BOUNCED_LIGHT_MULT", (1, 1, 1, 1))
        self.use_terrain_shadows_threshold = "TERRAIN_SHADOWS_THRESHOLD" in data
        self.terrain_shadows_threshold = float(data.get("TERRAIN_SHADOWS_THRESHOLD", 0))

    def to_dict(self) -> dict:
        data = {}
        data["ENABLE_TREES_LIGHTING"] = 1 if self.enable_trees_lighting else 0
        if self.use_track_ambient_ground_mult:
            data["TRACK_AMBIENT_GROUND_MULT"] = self.track_ambient_ground_mult
        if self.use_multipliers:
            data["LIT_MULT"] = self.lit_mult
            data["SPECULAR_MULT"] = self.specular_mult
            data["CAR_LIGHTS_LIT_MULT"] = self.car_lights_lit_mult
        if self.use_bounced_light_mult:
            data["BOUNCED_LIGHT_MULT"] = self.bounced_light_mult
        if self.use_terrain_shadows_threshold:
            data["TERRAIN_SHADOWS_THRESHOLD"] = self.terrain_shadows_threshold
        return data


class AC_MeshList(PropertyGroup):
    mesh: PointerProperty(
        name="Mesh",
        description="Mesh object to use as light source",
        type=Object
    )

class AC_MaterialList(PropertyGroup):
    material: PointerProperty(
        name="Material",
        description="Material to use as light source",
        type=Material
    )

class AC_PositionList(PropertyGroup):
    position: FloatVectorProperty(
        name="Position",
        description="Light position",
        default=(0, 0, 0),
        subtype="XYZ"
    )

class AC_DirectionList(PropertyGroup):
    direction: FloatVectorProperty(
        name="Direction",
        description="Light direction",
        default=(0, -1, 0),
        subtype="DIRECTION"
    )


class AC_EmissiveMaterial(PropertyGroup):
    """Configuration for CSP emissive material adjustment (MATERIAL_ADJUSTMENT_X sections)"""
    active: BoolProperty(
        name="Active",
        description="Enable this emissive material",
        default=True
    )
    description: StringProperty(
        name="Description",
        description="Description for this emissive configuration",
        default=""
    )
    material: PointerProperty(
        name="Material",
        description="Target material to make emissive",
        type=Material
    )
    use_mesh_filter: BoolProperty(
        name="Filter by Mesh",
        description="Only apply to specific mesh objects (uses MESHES instead of MATERIALS)",
        default=False
    )
    mesh: PointerProperty(
        name="Mesh",
        description="Target mesh object (optional, filters which objects get the emissive effect)",
        type=Object
    )
    # Emissive color and intensity
    emissive_color: FloatVectorProperty(
        name="Emissive Color",
        description="Color of the emissive glow (RGB)",
        default=(1.0, 0.82, 0.7),  # Warm white
        min=0.0,
        max=1.0,
        size=3,
        subtype='COLOR'
    )
    intensity: FloatProperty(
        name="Intensity",
        description="Emissive intensity (typical values: 0.1-2.0)",
        default=0.5,
        min=0.0,
        max=10.0,
        precision=2
    )
    # Glow effect (ksAlphaRef trick)
    use_glow_effect: BoolProperty(
        name="Enhanced Glow",
        description="Enable enhanced glow effect using ksAlphaRef (makes it more 'glowy')",
        default=True
    )
    glow_amount: FloatProperty(
        name="Glow Amount",
        description="Glow intensity (negative values create bloom effect, -193 is common)",
        default=-193.0,
        min=-500.0,
        max=0.0
    )
    # Condition for time-based activation
    condition_preset: EnumProperty(
        name="Condition Preset",
        description="Select a built-in CSP condition or choose Custom for manual entry",
        items=CONDITION_PRESETS,
        default="NONE",
        update=update_condition_preset
    )
    use_condition: BoolProperty(
        name="Use Condition",
        description="Enable time-based condition (e.g., only at night). When disabled, emissive glows all the time.",
        default=False
    )
    condition: StringProperty(
        name="Condition",
        description="CSP condition trigger (e.g., NIGHT_SMOOTH, NIGHT, HEADLIGHTS)",
        default="NIGHT_SMOOTH"
    )
    # Off value mode
    off_value_mode: EnumProperty(
        name="Off Value",
        description="What value to use when condition is not met",
        items=[
            ("ORIGINAL", "Original", "Use original material value"),
            ("OFF", "Off", "Turn emissive off completely (black)"),
        ],
        default="ORIGINAL"
    )

    # Light emission settings (creates LIGHT_SERIES for actual illumination)
    emit_light: BoolProperty(
        name="Emit Light",
        description="Also emit actual light that illuminates surroundings (creates LIGHT_SERIES entry)",
        default=False
    )
    light_range: FloatProperty(
        name="Range",
        description="How far the light reaches in meters",
        default=40.0,
        min=1.0,
        max=500.0
    )
    light_spot: IntProperty(
        name="Spot Angle",
        description="Light cone angle in degrees (180 = omnidirectional)",
        default=100,
        min=0,
        max=180
    )
    light_spot_sharpness: FloatProperty(
        name="Sharpness",
        description="How sharp the light cone edge is (0=sharp, 1=soft)",
        default=0.0,
        min=0.0,
        max=1.0
    )
    light_intensity: FloatProperty(
        name="Light Intensity",
        description="Brightness of the emitted light (typical: 0.01-0.1)",
        default=0.01,
        min=0.001,
        max=1.0,
        precision=3
    )
    light_direction: FloatVectorProperty(
        name="Direction",
        description="Light direction (0,-1,0 = downward)",
        default=(0.0, -1.0, 0.0),
        size=3,
        subtype='DIRECTION'
    )
    light_offset: FloatVectorProperty(
        name="Offset",
        description="Offset from mesh pivot point",
        default=(0.0, 0.0, 0.0),
        size=3,
        subtype='TRANSLATION'
    )
    light_fade_at: FloatProperty(
        name="Fade Distance",
        description="Distance at which light starts to fade out",
        default=200.0,
        min=10.0,
        max=1000.0
    )
    light_volumetric: BoolProperty(
        name="Volumetric",
        description="Enable volumetric light effect (expensive, use sparingly)",
        default=False
    )
    cast_shadows: BoolProperty(
        name="Cast Shadows",
        description="Light casts shadows (SHADOWS=0 disables shadows for this light)",
        default=False
    )

    def to_dict(self) -> dict:
        """Export to CSP ext_config.ini MATERIAL_ADJUSTMENT format"""
        data = {
            "ACTIVE": 1 if self.active else 0,
        }

        if self.description:
            data["DESCRIPTION"] = self.description

        # Target: either MESHES or MATERIALS
        if self.use_mesh_filter and self.mesh:
            data["MESHES"] = self.mesh.name
        elif self.material:
            data["MATERIALS"] = self.material.name

        # ksEmissive property
        r = int(self.emissive_color[0] * 255)
        g = int(self.emissive_color[1] * 255)
        b = int(self.emissive_color[2] * 255)
        data["KEY_0"] = "ksEmissive"
        data["VALUE_0"] = f"{r}, {g}, {b}, {self.intensity}"

        if self.use_condition:
            if self.off_value_mode == "ORIGINAL":
                data["VALUE_0_OFF"] = "ORIGINAL"
            else:
                data["VALUE_0_OFF"] = "0, 0, 0"

        # Glow effect (ksAlphaRef)
        if self.use_glow_effect:
            data["KEY_1"] = "ksAlphaRef"
            data["VALUE_1"] = str(int(self.glow_amount))
            if self.use_condition:
                if self.off_value_mode == "ORIGINAL":
                    data["VALUE_1_OFF"] = "ORIGINAL"
                else:
                    data["VALUE_1_OFF"] = "0"

        # Condition
        if self.use_condition and self.condition:
            data["CONDITION"] = self.condition

        return data

    def to_light_dicts(self) -> list:
        """Export to CSP ext_config.ini LIGHT_X format for actual light emission.

        Returns a list of dicts, one per mesh. Using individual LIGHT_X sections
        (instead of LIGHT_SERIES with multiple MESHES) ensures each light is
        placed at its mesh's origin rather than averaged between meshes.
        """
        import bpy

        if not self.emit_light:
            return []

        # Collect mesh names
        mesh_names = []

        if self.mesh:
            # Explicit mesh specified - use it
            mesh_names.append(self.mesh.name)
        elif self.material:
            # No mesh specified - find all meshes using this material
            for obj in bpy.data.objects:
                if obj.type != 'MESH':
                    continue
                # Skip hidden/template objects
                if is_hidden_name(obj.name):
                    continue
                # Check if object uses this material
                for slot in obj.material_slots:
                    if slot.material == self.material:
                        mesh_names.append(obj.name)
                        break  # Only add once per object

        if not mesh_names:
            return []

        # Build color string: R, G, B, intensity
        r = int(self.emissive_color[0] * 255)
        g = int(self.emissive_color[1] * 255)
        b = int(self.emissive_color[2] * 255)
        color_str = f"{r}, {g}, {b}, {self.light_intensity}"

        # Build base light data (shared by all lights)
        base_data = {
            "ACTIVE": 1 if self.active else 0,
            "COLOR": color_str,
            "DIRECTION": f"{self.light_direction[0]}, {self.light_direction[1]}, {self.light_direction[2]}",
            "SPOT": self.light_spot,
            "SPOT_SHARPNESS": round(self.light_spot_sharpness, 2),
            "RANGE": round(self.light_range, 1),
            "RANGE_GRADIENT_OFFSET": 0.2,
            "FADE_AT": int(self.light_fade_at),
            "FADE_SMOOTH": 50,
        }

        # Add offset if non-zero
        if self.light_offset != (0, 0, 0):
            base_data["OFFSET"] = f"{self.light_offset[0]}, {self.light_offset[1]}, {self.light_offset[2]}"

        # Add condition if enabled
        if self.use_condition and self.condition:
            base_data["CONDITION"] = self.condition

        # Add volumetric if enabled
        if self.light_volumetric:
            base_data["VOLUMETRIC_LIGHT"] = 1

        # Add shadows if enabled
        if self.cast_shadows:
            base_data["SHADOWS"] = 1

        # Create individual light entry for each mesh
        light_dicts = []
        for mesh_name in mesh_names:
            light_data = base_data.copy()
            light_data["MESH"] = mesh_name
            if self.description:
                light_data["DESCRIPTION"] = f"{self.description} - {mesh_name}"
            light_dicts.append(light_data)

        return light_dicts

    def from_dict(self, data: dict):
        """Load from CSP ext_config.ini MATERIAL_ADJUSTMENT format"""
        self.active = data.get("ACTIVE", 1) == 1
        self.description = data.get("DESCRIPTION", "")

        # Determine target type
        if "MESHES" in data:
            self.use_mesh_filter = True
            mesh_name = data["MESHES"]
            if mesh_name:
                import bpy
                self.mesh = bpy.data.objects.get(mesh_name)
        else:
            self.use_mesh_filter = False
            if "MATERIALS" in data:
                mat_name = data["MATERIALS"]
                if mat_name:
                    import bpy
                    self.material = bpy.data.materials.get(mat_name)

        # Parse ksEmissive value
        if "VALUE_0" in data and data.get("KEY_0") == "ksEmissive":
            value_str = data["VALUE_0"]
            if value_str != "ORIGINAL":
                parts = [p.strip() for p in value_str.split(",")]
                if len(parts) >= 4:
                    self.emissive_color = (
                        float(parts[0]) / 255.0,
                        float(parts[1]) / 255.0,
                        float(parts[2]) / 255.0
                    )
                    self.intensity = float(parts[3])

        # Check for glow effect
        if "KEY_1" in data and data.get("KEY_1") == "ksAlphaRef":
            self.use_glow_effect = True
            try:
                self.glow_amount = float(data.get("VALUE_1", -193))
            except ValueError:
                self.glow_amount = -193.0
        else:
            self.use_glow_effect = False

        # Condition
        if "CONDITION" in data:
            self.use_condition = True
            self.condition = data["CONDITION"]
        else:
            self.use_condition = False

        # Off value mode
        if "VALUE_0_OFF" in data:
            if data["VALUE_0_OFF"] == "ORIGINAL":
                self.off_value_mode = "ORIGINAL"
            else:
                self.off_value_mode = "OFF"


def update_csp_setting(self, context):
    """Update callback for CSP-specific properties.

    Syncs the changed setting to the linked object's AC_CSP property
    so it persists when the object is duplicated in Blender.
    """
    if hasattr(self, 'sync_csp_to_object'):
        self.sync_csp_to_object()


class AC_Light(PropertyGroup):
    expand: BoolProperty(
        name="Expand",
        default=False
    )
    active: BoolProperty(
        name="Active",
        default=True
    )
    description: StringProperty(
        name="Description",
        default=""
    )

    # Linked object support for Empty-based workflow
    linked_object: PointerProperty(
        name="Linked Object",
        description="Empty object to use for position and direction",
        type=Object
    )
    linked_object_name: StringProperty(
        name="Linked Object Name",
        description="Name of the linked object (used to detect deleted objects)",
        default=""
    )
    use_object_transform: BoolProperty(
        name="Use Object Transform",
        description="Use linked object's position and rotation for light placement",
        default=True
    )

    light_type: EnumProperty(
        name="Light Type",
        items=[
            ("SPOT", "Spot", "Spotlight source"),
            ("MESH", "Mesh", "Mesh light source"),
            ("LINE", "Line", "Line light source"),
            ("SERIES", "Series", "Series light source")
        ],
        default="SPOT"
    )
    mesh: PointerProperty(
        name="Mesh",
        description="Mesh object to use as light source",
        type=Object
    )
    # if mesh is None, name is 'position', else name this to 'offset' on export/import
    # reset to (0, 0, 0) when mesh is set/removed
    position: FloatVectorProperty(
        name="Position",
        description="Light position",
        default=(0, 0, 0),
        subtype="XYZ"
    )
    # default direction is down: 0, -1, 0
    direction: FloatVectorProperty(
        name="Direction",
        description="Light direction",
        default=(0, -1, 0),
        subtype="DIRECTION"
    )
    direction_mode: EnumProperty(
        name="Direction Mode",
        description="Direction mode",
        items=[
            ("NORMAL", "Normal", "Use normal direction"),
            ("FIXED", "Fixed", "Use fixed direction")
        ],
    )
    direction_alter: FloatVectorProperty(
        name="Direction Alter",
        description="Light direction alter",
        default=(0, 0, 0),
        subtype='DIRECTION'
    )
    direction_offset: FloatVectorProperty(
        name="Direction Offset",
        description="Light direction offset",
        default=(0, 0, 0),
        subtype='DIRECTION'
    )

    # line settings
    line_from: FloatVectorProperty(
        name="Line From",
        description="Line light source start position",
        default=(0, 0, 0),
    )
    color_from: FloatVectorProperty(
        name="Color From",
        description="Line light source start color",
        default=(1, 1, 1, 1), # TODO: verify output: expects #RRGGBB, INT
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )
    line_from_helper: PointerProperty(
        name="Line From Helper",
        description="Line light source start helper",
        type=Object
    )
    line_to: FloatVectorProperty(
        name="Line To",
        description="Line light source end position",
        default=(0, 0, 0),
    )
    color_to: FloatVectorProperty(
        name="Color To",
        description="Line light source end color",
        default=(1, 1, 1, 1),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )
    line_to_helper: PointerProperty(
        name="Line To Helper",
        description="Line light source end helper",
        type=Object
    )

    meshes: CollectionProperty(
        name="Meshes",
        description="List of meshes to use as light source",
        type=AC_MeshList
    )
    materials: CollectionProperty(
        name="Materials",
        description="List of materials to use as light source",
        type=AC_MaterialList
    )
    positions: CollectionProperty(
        type=AC_PositionList,
        name="Positions",
        description="List of light positions"
    )
    directions: CollectionProperty(
        type=AC_DirectionList,
        name="Directions",
        description="List of light directions"
    )

    # shape settings
    modify_shape: BoolProperty(
        name="Modify Shape",
        description="Enable to modify shape",
        default=True
    )
    spot: IntProperty(
        name="Spot",
        description="Spotlight angle",
        default=120,
        min=0,
        max=180
    )
    spot_sharpness: FloatProperty(
        name="Spot Sharpness",
        description="Sharpness of spotlight edge",
        default=0.3,
        precision=3,
        min=0,
        max=1,
        update=update_csp_setting
    )
    range: FloatProperty(
        name="Range",
        description="Light casting distance in meters",
        default=40,
        min=0,
        max=1000
    )
    range_gradient_offset: FloatProperty(
        name="Range Gradient Offset",
        description="light fade out starting distance",
        default=0.2,
        min=0,
        max=1,
        update=update_csp_setting
    )

    # performance settings
    fade_at: IntProperty(
        name="Fade At",
        description="Initial fade out distance where brightness has 50% intensity",
        default=400,
        min=0,
        max=1000,
        update=update_csp_setting
    )
    fade_smooth: IntProperty(
        name="Fade Smooth",
        description="Fade out smoothness",
        default=50,
        min=0,
        max=100,
        update=update_csp_setting
    )


    # color settings
    modify_color: BoolProperty(
        name="Modify Color",
        description="Enable to modify color",
        default=True
    )
    color: FloatVectorProperty(
        name="Color",
        description="Light color (RGB) - use Intensity for brightness",
        default=(1, 0.92, 0.83, 1),  # Warm white, full intensity placeholder
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )
    intensity: FloatProperty(
        name="Intensity",
        description="Light intensity/brightness (typical values: 0.01-0.1)",
        default=0.05,
        min=0.001,
        max=5.0,
        precision=3
    )
    specular_multiplier: FloatProperty(
        name="Specular Multiplier",
        description="Specular multiplier",
        default=0,
        min=0,
        max=4,
        update=update_csp_setting
    )
    single_frequency: BoolProperty(
        name="Single Frequency",
        description="Use single frequency for light",
        default=False,
        update=update_csp_setting
    )
    diffuse_concentration: FloatProperty(
        name="Diffuse Concentration",
        description="Diffuse concentration",
        default=0.88,
        precision=3,
        min=0,
        max=1,
        update=update_csp_setting
    )

    # condition settings, to be implemented with global definitions later
    condition_preset: EnumProperty(
        name="Condition Preset",
        description="Select a built-in CSP condition or choose Custom for manual entry",
        items=CONDITION_PRESETS,
        default="NONE",
        update=update_condition_preset
    )
    use_condition: BoolProperty(
        name="Use Condition",
        description="Enable condition trigger",
        default=False,
        update=update_csp_setting
    )
    condition: StringProperty(
        name="Condition",
        description="Condition trigger to control brightness and color",
        default="",
        update=update_csp_setting
    )
    condition_offset: StringProperty(
        name="Condition Offset",
        description="(optional) offset condition flashing",
        default="",
        update=update_csp_setting
    )

    # extras
    volumetric_light: BoolProperty(
        name="Volumetric Light",
        description="Enable volumetric light (expensive)",
        default=False,
        update=update_csp_setting
    )
    long_specular: BoolProperty(
        name="Long Specular",
        description="Enable long specular (used to create wet look, cannot cast shadows)",
        default=False,
        update=update_csp_setting
    )
    skip_light_map: BoolProperty(
        name="Skip Light Map",
        description="Enable this to exclude light from contributing to bounced lighting FX",
        default=False,
        update=update_csp_setting
    )
    disable_with_bounced_light: BoolProperty(
        name="Disable With Bounced Light",
        description="Disable light when bounced light is enabled",
        default=False,
        update=update_csp_setting
    )

    # shadow settings
    cast_shadows: BoolProperty(
        name="Shadows",
        description="Cast shadows",
        default=False,
        update=update_csp_setting
    )
    shadows_static: BoolProperty(
        name="Shadows Static",
        description="Static shadows",
        default=True,
        update=update_csp_setting
    )
    shadows_half_res: BoolProperty(
        name="Shadows Half Res",
        description="Half resolution shadows",
        default=False,
        update=update_csp_setting
    )
    shadows_spot_angle: IntProperty(
        name="Shadows Spot Angle",
        description="Shadow spotlight angle",
        default=0, # 0 to unset the value
        min=0,
        max=180,
        update=update_csp_setting
    )
    shadows_range: FloatProperty(
        name="Shadows Range",
        description="Shadow casting distance",
        default=0, # 0 to unset the value
        min=0,
        max=1000,
        update=update_csp_setting
    )
    shadows_dir: FloatVectorProperty(
        name="Shadows Direction",
        description="Shadow direction",
        default=(0, 0, 0), # 0 to unset the value
        min=-1,
        max=1,
        size=3,
        subtype="DIRECTION"
    )
    shadows_offset: FloatVectorProperty(
        name="Shadows Offset",
        description="Shadow offset position (limited to 5m)",
        default=(0, 0, 0), # 0 to unset the value
        precision=3,
        min=-5,
        max=5,
        size=3,
        subtype="TRANSLATION"
    )
    shadows_boost: FloatProperty(
        name="Shadows Boost",
        description="Shadow boost",
        default=0, # 0 to unset the value
        min=0,
        max=4,
        update=update_csp_setting
    )
    shadows_clip_plane: FloatProperty(
        name="Shadows Clip Plane",
        description="Shadow clip plane distance",
        default=0.5, # 0.5 to unset the value
        min=0,
        max=100,
        update=update_csp_setting
    )
    shadows_clip_sphere: FloatProperty(
        name="Shadows Clip Sphere",
        description="Shadow clip sphere radius",
        default=0.5, # 0.5 to unset the value
        min=0,
        max=100,
        update=update_csp_setting
    )
    shadows_exp_factor: IntProperty(
        name="Shadow Exp Factor",
        description="Shadow exponent factor",
        default=20,
        min=0,
        max=100,
        update=update_csp_setting
    )
    shadows_extra_blur: BoolProperty(
        name="Shadow Extra Blur",
        description="Shadow extra blur",
        default=False,
        update=update_csp_setting
    )

    def from_dict(self, data: dict, is_series: bool = False):
        self.active = data.get("ACTIVE", 1) == 1
        self.description = data.get("DESCRIPTION", "")
        if "LINKED_OBJECT" in data:
            import bpy
            self.linked_object_name = data["LINKED_OBJECT"]
            self.linked_object = bpy.data.objects.get(data["LINKED_OBJECT"])
        if not is_series:
            self.mesh = data.get("MESH", None)
            position = data.get("POSITION", (0, 0, 0))
            offset = data.get("OFFSET", (0, 0, 0))
            self.position = offset if self.mesh else position
            if "LINE_FROM" in data:
                self.light_type = "LINE"
                self.line_from = data["LINE_FROM"]
                self.line_to = data["LINE_TO"]
            elif "MESH" in data:
                self.light_type = "MESH"
                # TODO: bind mesh passed from settings
            else:
                self.light_type = "SPOT"
            direction = data.get("DIRECTION", (0, -1, 0))
            self.direction = (-direction[0], -direction[1], -direction[2])
        else:
            self.light_type = "SERIES"
            self.meshes.clear()
            self.materials.clear()
            self.positions.clear()
            self.directions.clear()
            self.direction_mode = 'NORMAL' if data.get('DIRECTION', 'NORMAL') == 'NORMAL' else 'FIXED'
            direction = data.get('DIRECTION', (0, -1, 0))
            self.direction = (-direction[0], -direction[1], -direction[2])
            self.direction_alter = data.get('DIRECTION_ALTER', (0, 0, 0))
            self.direction_offset = data.get('DIRECTION_OFFSET', (0, 0, 0))
            if "MESHES" in data:
                # TODO: bind mesh passed from settings
                pass
            elif "MATERIALS" in data:
                for material_name in data["MATERIALS"]:
                    # TODO: bind material passed from settings
                    pass
            else:
                for property in data:
                    if property.startswith("POSITION_"):
                        pos = self.positions.add()
                        pos.position = data[property]
                    elif property.startswith("DIRECTION_"):
                        dir = self.directions.add()
                        dir.direction = data[property]

        #shape settings
        self.modify_shape = "SPOT" in data
        # Handle SPOT value which may include unused values after the angle (e.g., "120 0")
        spot_value = data.get("SPOT", "120")
        if isinstance(spot_value, str):
            self.spot = int(spot_value.split(' ')[0])
        else:
            self.spot = int(spot_value)
        self.spot_sharpness = float(data.get("SPOT_SHARPNESS", 0.3))
        self.range = float(data.get("RANGE", 40))
        self.range_gradient_offset = float(data.get("RANGE_GRADIENT_OFFSET", 0.2))

        # color settings
        self.modify_color = "COLOR" in data
        if "COLOR" in data:
            color_tuple = self.int_hex_to_float(data["COLOR"])
            self.color = (color_tuple[0], color_tuple[1], color_tuple[2], 1.0)
            self.intensity = color_tuple[3]  # 4th value is intensity
        else:
            self.color = (1, 1, 1, 1)
            self.intensity = 0.05
        self.specular_multiplier = float(data.get("SPECULAR_MULTIPLIER", 0))
        self.single_frequency = data.get("SINGLE_FREQUENCY", 0) == 1
        self.diffuse_concentration = float(data.get("DIFFUSE_CONCENTRATION", 0.88))
        self.fade_at = int(data.get("FADE_AT", 400))
        self.fade_smooth = int(data.get("FADE_SMOOTH", 50))

        # condition settings
        self.condition = data.get("CONDITION", "")
        self.condition_offset = data.get("CONDITION_OFFSET", "")

        # extras
        self.volumetric_light = data.get("VOLUMETRIC_LIGHT", 0) == 1
        self.long_specular = data.get("LONG_SPECULAR", 0) == 1
        self.skip_light_map = data.get("SKIP_LIGHT_MAP", 0) == 1
        self.disable_with_bounced_light = data.get("DISABLE_WITH_BOUNCED_LIGHT", 0) == 1

        # shadow settings
        self.cast_shadows = data.get("SHADOWS", 0) == 1
        self.shadows_static = data.get("SHADOWS_STATIC", 0) == 1
        self.shadows_half_res = data.get("SHADOWS_HALF_RES", 0) == 1
        self.shadows_spot_angle = int(data.get("SHADOWS_SPOT_ANGLE", 0))
        self.shadows_range = float(data.get("SHADOWS_RANGE", 0))
        self.shadows_dir = data.get("SHADOWS_DIR", (0, 0, 0))
        self.shadows_offset = data.get("SHADOWS_OFFSET", (0, 0, 0))
        self.shadows_boost = float(data.get("SHADOWS_BOOST", 0))
        self.shadows_clip_plane = float(data.get("SHADOWS_CLIP_PLANE", 0.5))
        self.shadows_clip_sphere = float(data.get("SHADOWS_CLIP_SPHERE", 0.5))
        self.shadows_exp_factor = int(data.get("SHADOW_EXP_FACTOR", 20))
        self.shadows_extra_blur = data.get("SHADOW_EXTRA_BLUR", 0) == 1
    def int_hex_to_float(self, in_str: str) -> tuple:
        # split string by ',' and trim whitespace
        hex = in_str.split(',')
        hex = [float(i.strip()) for i in hex]
        return (hex[0] / 255, hex[1] / 255, hex[2] / 255, float(hex[3]))

    def get_effective_position(self) -> tuple:
        """Get the effective position, using linked object if enabled.
        Returns position in AC coordinate system (Y-up, right-handed)."""
        if self.use_object_transform and self.linked_object:
            loc = self.linked_object.location
            # Blender: Z-up, right-handed → AC: Y-up, right-handed
            return (loc.x, loc.z, -loc.y)
        # Convert stored Blender coords to AC coords
        return (self.position[0], self.position[2], -self.position[1])

    def get_effective_direction(self) -> tuple:
        """Get the effective direction, using linked object's rotation if enabled.
        Returns direction in AC coordinate system."""
        if self.use_object_transform and self.linked_object:
            # Get the forward direction from the object's rotation
            # For ARROWS empty, -Z is the arrow direction
            mat = self.linked_object.matrix_world.to_3x3()
            forward = mat @ mathutils.Vector((0, 0, -1))
            forward.normalize()
            # Convert from Blender coords to AC coords
            return (forward.x, forward.z, -forward.y)
        # Convert stored Blender direction to AC coords
        return (self.direction[0], self.direction[2], -self.direction[1])

    def sync_from_linked_object(self):
        """Sync position and direction from linked object to stored values (Blender coords)"""
        if self.linked_object:
            loc = self.linked_object.location
            # Store in Blender coordinates
            self.position = (loc.x, loc.y, loc.z)
            # Get direction from rotation
            mat = self.linked_object.matrix_world.to_3x3()
            forward = mat @ mathutils.Vector((0, 0, -1))
            forward.normalize()
            self.direction = (forward.x, forward.y, forward.z)

    # CSP properties to sync between AC_Light and AC_CSPLightSettings
    _CSP_SYNC_PROPERTIES = [
        # Shape settings
        'spot_sharpness',
        'range_gradient_offset',
        # Performance settings
        'fade_at',
        'fade_smooth',
        # Color settings (CSP-specific)
        'specular_multiplier',
        'single_frequency',
        'diffuse_concentration',
        # Condition settings
        'condition_preset',
        'use_condition',
        'condition',
        'condition_offset',
        # Extras
        'volumetric_light',
        'long_specular',
        'skip_light_map',
        'disable_with_bounced_light',
        # Shadow settings
        'cast_shadows',
        'shadows_static',
        'shadows_half_res',
        'shadows_spot_angle',
        'shadows_range',
        'shadows_boost',
        'shadows_clip_plane',
        'shadows_clip_sphere',
        'shadows_exp_factor',
        'shadows_extra_blur',
    ]

    def sync_csp_to_object(self):
        """Write CSP-specific settings to linked object's AC_CSP property.

        Call this when CSP settings change in the addon UI to persist them
        on the Blender object. This allows settings to survive duplication.
        """
        if not self.linked_object:
            return

        csp = self.linked_object.AC_CSP
        for prop_name in self._CSP_SYNC_PROPERTIES:
            setattr(csp, prop_name, getattr(self, prop_name))

    def sync_csp_from_object(self):
        """Read CSP-specific settings from linked object's AC_CSP property.

        Call this when scanning for new lights to pick up settings from
        duplicated Blender objects.
        """
        if not self.linked_object:
            return

        # Store reference and temporarily disconnect to prevent update callbacks
        # from writing back default values while we're reading
        obj = self.linked_object
        csp = obj.AC_CSP

        # Temporarily unset linked_object so update callbacks don't overwrite
        self.linked_object = None

        for prop_name in self._CSP_SYNC_PROPERTIES:
            setattr(self, prop_name, getattr(csp, prop_name))

        # Restore linked_object
        self.linked_object = obj

    def _format_vec3(self, vec) -> str:
        """Format a 3D vector as comma-separated string"""
        return f"{vec[0]}, {vec[1]}, {vec[2]}"

    def _get_color_and_intensity_for_export(self) -> tuple:
        """Get color (RGB 0-255) and intensity for CSP export.
        If linked to a Blender light, reads directly from it."""
        import math

        # If linked to a Blender LIGHT, read color/intensity from it
        if self.linked_object and self.linked_object.type == 'LIGHT':
            light_data = self.linked_object.data
            r = int(light_data.color[0] * 255)
            g = int(light_data.color[1] * 255)
            b = int(light_data.color[2] * 255)
            # Convert Blender Watts to CSP intensity
            # Blender 10W ≈ CSP 0.001, 100W ≈ 0.01, 1000W ≈ 0.1
            intensity = light_data.energy / 10000.0
            return r, g, b, intensity

        # Otherwise use stored values
        r = int(self.color[0] * 255)
        g = int(self.color[1] * 255)
        b = int(self.color[2] * 255)
        return r, g, b, self.intensity

    def to_dict(self) -> dict:
        data = {
            "ACTIVE": 1 if self.active else 0,
            "DESCRIPTION": self.description
        }
        if self.linked_object:
            data["LINKED_OBJECT"] = self.linked_object.name
        if self.light_type == "SPOT":
            pos = self.get_effective_position()
            data["POSITION"] = self._format_vec3(pos)
        if self.light_type == "MESH":
            data["MESH"] = self.mesh.name if self.mesh else ""
            data["OFFSET"] = self._format_vec3(self.position)
        if self.light_type == "LINE":
            line_from = self.line_from[:] if not self.line_from_helper else tuple(self.line_from_helper.location)
            line_to = self.line_to[:] if not self.line_to_helper else tuple(self.line_to_helper.location)
            data["LINE_FROM"] = self._format_vec3(line_from)
            data["LINE_TO"] = self._format_vec3(line_to)
        if self.light_type == "SERIES":
            if self.meshes:
                data["MESHES"] = ", ".join([mesh.mesh.name for mesh in self.meshes if mesh.mesh])
                if self.direction_mode == "FIXED":
                    data['DIRECTION'] = self._format_vec3(self.get_effective_direction())
                else:
                    data['DIRECTION'] = 'NORMAL'
                if tuple(self.direction_alter) != (0, 0, 0):
                    data['DIRECTION_ALTER'] = self._format_vec3(self.direction_alter)
                if tuple(self.direction_offset) != (0, 0, 0):
                    data['DIRECTION_OFFSET'] = self._format_vec3(self.direction_offset)
            elif self.materials:
                data["MATERIALS"] = ", ".join([mat.material.name for mat in self.materials if mat.material])
            else:
                for i, pos_item in enumerate(self.positions):
                    data[f"POSITION_{i}"] = self._format_vec3(pos_item.position)
                    dir_val = self.directions[i].direction[:] if len(self.directions) > i else (0, -1, 0)
                    data[f"DIRECTION_{i}"] = self._format_vec3(dir_val)
            data['OFFSET'] = self._format_vec3(self.position)
        else:
            # Use effective direction (handles linked object transform)
            direction = self.get_effective_direction()
            data["DIRECTION"] = self._format_vec3(direction)
        if self.modify_shape:
            # Auto-sync spot angle from Blender light if linked
            if self.linked_object and self.linked_object.type == 'LIGHT':
                import math
                light_data = self.linked_object.data
                if light_data.type == 'SPOT':
                    data["SPOT"] = int(math.degrees(light_data.spot_size))
                else:
                    data["SPOT"] = self.spot
            else:
                data["SPOT"] = self.spot
            data["SPOT_SHARPNESS"] = self.spot_sharpness
            data["RANGE"] = self.range
            data["RANGE_GRADIENT_OFFSET"] = self.range_gradient_offset
        if self.modify_color:
            # Get color and intensity (auto-syncs from Blender light if linked)
            r, g, b, intensity = self._get_color_and_intensity_for_export()
            data["COLOR"] = f"{r}, {g}, {b}, {intensity}"
            data["SPECULAR_MULTIPLIER"] = self.specular_multiplier
            data["SINGLE_FREQUENCY"] = 1 if self.single_frequency else 0
            data["DIFFUSE_CONCENTRATION"] = self.diffuse_concentration
            data["FADE_AT"] = self.fade_at
            data["FADE_SMOOTH"] = self.fade_smooth
        if self.use_condition:
            data["CONDITION"] = self.condition
            data["CONDITION_OFFSET"] = self.condition_offset

        if self.volumetric_light:
            data["VOLUMETRIC_LIGHT"] = 1
        if self.long_specular:
            data["LONG_SPECULAR"] = 1
        if self.skip_light_map:
            data["SKIP_LIGHT_MAP"] = 1
        if self.disable_with_bounced_light:
            data["DISABLE_WITH_BOUNCED_LIGHT"] = 1

        if self.cast_shadows:
            data["SHADOWS"] = 1
            data["SHADOWS_STATIC"] = 1 if self.shadows_static else 0
            data["SHADOWS_HALF_RES"] = 1 if self.shadows_half_res else 0
            if self.shadows_spot_angle > 0:
                data["SHADOWS_SPOT_ANGLE"] = self.shadows_spot_angle
            if self.shadows_range > 0:
                data["SHADOWS_RANGE"] = self.shadows_range
            if self.shadows_dir != (0, 0, 0):
                data["SHADOWS_DIR"] = f"{self.shadows_dir[0]}, {self.shadows_dir[1]}, {self.shadows_dir[2]}"
            if self.shadows_offset != (0, 0, 0):
                data["SHADOWS_OFFSET"] = f"{self.shadows_offset[0]}, {self.shadows_offset[1]}, {self.shadows_offset[2]}"
            if self.shadows_boost > 0:
                data["SHADOWS_BOOST"] = self.shadows_boost
            data["SHADOWS_CLIP_PLANE"] = self.shadows_clip_plane
            data["SHADOWS_CLIP_SPHERE"] = self.shadows_clip_sphere
            data["SHADOW_EXP_FACTOR"] = self.shadows_exp_factor
            data["SHADOW_EXTRA_BLUR"] = 1 if self.shadows_extra_blur else 0
        return data



class AC_Lighting(PropertyGroup):
    sun: PointerProperty(
        type=AC_SunSettings,
        name="Sun Settings"
    )

    global_lighting: PointerProperty(
        type=AC_GlobalLighting,
        name="Global Lighting"
    )

    lights: CollectionProperty(
        type=AC_Light,
        name="Lights"
    )

    active_light_index: IntProperty(
        name="Active Light Index",
        description="Index of the currently selected light",
        default=0,
        min=0
    )

    # Emissive materials (MATERIAL_ADJUSTMENT sections)
    emissive_materials: CollectionProperty(
        type=AC_EmissiveMaterial,
        name="Emissive Materials"
    )

    active_emissive_index: IntProperty(
        name="Active Emissive Index",
        description="Index of the currently selected emissive material",
        default=0,
        min=0
    )

    # Material selector for adding new emissive materials
    material_to_add: PointerProperty(
        type=Material,
        name="Material to Add",
        description="Select material to add as emissive"
    )

    def from_dict(self, data: dict):
        self.sun.sun_pitch_angle = int(data.get("SUN_PITCH_ANGLE", 45))
        self.sun.sun_heading_angle = int(data.get("SUN_HEADING_ANGLE", 0))

    def light_from_dict(self, data: dict, is_series: bool = False):
        light = self.lights.add()
        light.from_dict(data, is_series)

    def to_dict(self) -> dict:
        return {
            "LIGHTING": {
                "SUN_PITCH_ANGLE": self.sun.sun_pitch_angle,
                "SUN_HEADING_ANGLE": self.sun.sun_heading_angle
            }
        }
