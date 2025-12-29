from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from ...utils.constants import SAVE_PRECISION


class AC_Surface(PropertyGroup):
    custom: BoolProperty(
        name="Custom",
        description="Is this a custom surface",
        default=True
    )
    name: StringProperty(
        name="Name",
        description="Standard name of the surface",
        default="Track Surface"
    )
    key: StringProperty(
        name="Key",
        description="Unique prefix used to assign the surface to an object",
        default="SURFACE"
    )
    friction: FloatProperty(
        name="Friction",
        description="dry surface grip (slip <--------> grip)",
        default=0.96,
        min=0,
        soft_max=1,
        precision=3
    )
    damping: FloatProperty(
        name="Damping",
        description="speed reduction on the surface (road <-------> sand)",
        default=0,
        min=0,
        soft_max=1,
        precision=3
    )
    wav: StringProperty(
        name="Wav",
        description="Wav file to play while driving on the surface",
        default=""
    )
    wav_pitch: FloatProperty(
        name="Wav Pitch",
        description="Pitch shift of the wav file",
        default=0,
        min=0.0,
        soft_max=2.0,
    )
    ff_effect: StringProperty(
        name="FF Effect",
        description="Force Feedback Effect [optional]",
        default="",
        update=lambda s, c: s.update_ff_effect(c)
    )
    def update_ff_effect(self, _):
        if self.ff_effect == 'NULL':
            self.ff_effect = ''

    dirt_additive: FloatProperty(
        name="Dirt Additive",
        description="Amount of dirt added from the surface",
        default=0,
        min=0,
        soft_max=1,
        precision=3
    )
    is_pit_lane: BoolProperty(
        name="Is Pit Lane",
        description="Apply Pit Lane rules to surface?",
        default=False
    )
    is_valid_track: BoolProperty(
        name="Is Valid Track",
        description="Is this surface part of the track?",
        default=True
    )
    black_flag_time: IntProperty(
        name="Black Flag Time",
        description="Seconds on surface before black flag is issued",
        default=0,
        min=0,
        soft_max=60,
        step=5
    )
    sin_height: FloatProperty(
        name="Sin Height",
        description="Height of the sin wave",
        default=0,
        min=0,
        soft_max=3,
        precision=3
    )
    sin_length: FloatProperty(
        name="Sin Length",
        description="Length of the sin wave",
        default=0,
        min=0,
        soft_max=3,
        precision=3
    )
    vibration_gain: FloatProperty(
        name="Vibration Gain",
        description="Gain of the vibration",
        default=0,
        min=0,
        soft_max=3,
        precision=3
    )
    vibration_length: FloatProperty(
        name="Vibration Length",
        description="Length of the vibration",
        default=0,
        min=0,
        soft_max=3,
        precision=3
    )

    # CSP Surface Tweaks Extensions
    ext_surface_type: EnumProperty(
        name="Surface Type",
        description="CSP: Explicitly defines surface characteristics (overrides auto-detection)",
        items=[
            ('NONE', 'None', 'Use auto-detection based on other properties'),
            ('EXTRATURF', 'Extra Turf', 'Extra turf surface'),
            ('GRASS', 'Grass', 'Grass surface'),
            ('GRAVEL', 'Gravel', 'Gravel surface'),
            ('KERB', 'Kerb', 'Kerb surface'),
            ('OLD', 'Old', 'Old surface'),
            ('SAND', 'Sand', 'Sand surface'),
            ('ICE', 'Ice', 'Ice surface (CSP 0.2.5+)'),
            ('SNOW', 'Snow', 'Snow surface (CSP 0.2.5+)'),
        ],
        default='NONE'
    )
    ext_surface_type_modifier: EnumProperty(
        name="Surface Modifier",
        description="CSP: Adjusts SurfacesFX behavior for loose materials",
        items=[
            ('REGULAR', 'Regular', 'Regular surface firmness'),
            ('LOOSE', 'Loose', 'Loose surface material'),
            ('FIRM', 'Firm', 'Firm surface material'),
        ],
        default='REGULAR'
    )
    ext_perlin_noise: BoolProperty(
        name="Use Perlin Noise",
        description="CSP: Replace sine noise with Perlin noise using existing SIN_HEIGHT and SIN_LENGTH",
        default=False
    )
    ext_perlin_octaves: IntProperty(
        name="Perlin Octaves",
        description="CSP: Perlin noise complexity (only used if Perlin Noise is enabled)",
        default=1,
        min=1,
        max=10
    )
    ext_perlin_persistence: FloatProperty(
        name="Perlin Persistence",
        description="CSP: Amplitude multiplier for successive octaves (only used if Perlin Noise is enabled)",
        default=0.5,
        min=0.0,
        max=1.0,
        precision=3
    )

    def to_dict(self) -> dict:
        # Note: NAME is intentionally omitted - AC's surfaces.ini format
        # does not include it, and including it may cause parsing issues.
        # The addon stores name internally but from_dict() auto-generates
        # it from KEY if not present in the file.
        data = {
            "KEY": self.key,
            "FRICTION": round(self.friction, SAVE_PRECISION),
            "DAMPING": round(self.damping, SAVE_PRECISION),
            "WAV": self.wav,
            "WAV_PITCH": round(self.wav_pitch, SAVE_PRECISION) if self.wav != '' else 0,
            "FF_EFFECT": 'NULL' if self.ff_effect == '' else self.ff_effect,
            "DIRT_ADDITIVE": round(self.dirt_additive, SAVE_PRECISION),
            # boolean should be converted to int for saving
            "IS_PITLANE": int(self.is_pit_lane),
            "IS_VALID_TRACK": int(self.is_valid_track),
            "BLACK_FLAG_TIME": self.black_flag_time,
            "SIN_HEIGHT": round(self.sin_height, SAVE_PRECISION),
            "SIN_LENGTH": round(self.sin_length, SAVE_PRECISION),
            "VIBRATION_GAIN": round(self.vibration_gain, SAVE_PRECISION),
            "VIBRATION_LENGTH": round(self.vibration_length, SAVE_PRECISION)
        }

        # Add CSP extension properties only if non-default
        if self.ext_surface_type != 'NONE':
            data["_EXT_SURFACE_TYPE"] = self.ext_surface_type

        if self.ext_surface_type_modifier != 'REGULAR':
            data["_EXT_SURFACE_TYPE_MODIFIER"] = self.ext_surface_type_modifier

        if self.ext_perlin_noise:
            data["_EXT_PERLIN_NOISE"] = 1
            if self.ext_perlin_octaves != 1:
                data["_EXT_PERLIN_OCTAVES"] = self.ext_perlin_octaves
            if self.ext_perlin_persistence != 0.5:
                data["_EXT_PERLIN_PERSISTENCE"] = round(self.ext_perlin_persistence, SAVE_PRECISION)

        return data

    # long floats may be interpreted as strings when reading from file
    # so we should cast non-string types to prevent errors
    def from_dict(self, data: dict, custom: bool = True):
        self.name = data.get("NAME", data["KEY"].replace("_", " ").title())
        self.key = data["KEY"]
        self.custom = custom
        self.friction = float(data.get("FRICTION", 0.99))
        self.damping = float(data.get("DAMPING", 0))
        self.wav = data.get("WAV", "")
        self.wav_pitch = float(data.get("WAV_PITCH", 1))
        self.ff_effect = f'{data.get("FF_EFFECT", "")}'
        self.dirt_additive = float(data.get("DIRT_ADDITIVE", 0))
        self.is_pit_lane = bool(int(data.get("IS_PITLANE", 0)))
        self.is_valid_track = bool(int(data.get("IS_VALID_TRACK", 1)))
        self.black_flag_time = int(data.get("BLACK_FLAG_TIME", 0))
        self.sin_height = float(data.get("SIN_HEIGHT", 0))
        self.sin_length = float(data.get("SIN_LENGTH", 0))
        self.vibration_gain = float(data.get("VIBRATION_GAIN", 0))
        self.vibration_length = float(data.get("VIBRATION_LENGTH", 0))

        # Load CSP extension properties
        self.ext_surface_type = data.get("_EXT_SURFACE_TYPE", 'NONE')
        self.ext_surface_type_modifier = data.get("_EXT_SURFACE_TYPE_MODIFIER", 'REGULAR')
        self.ext_perlin_noise = bool(int(data.get("_EXT_PERLIN_NOISE", 0)))
        self.ext_perlin_octaves = int(data.get("_EXT_PERLIN_OCTAVES", 1))
        self.ext_perlin_persistence = float(data.get("_EXT_PERLIN_PERSISTENCE", 0.5))
