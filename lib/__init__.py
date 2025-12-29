import bpy

from .configs.audio_source import AC_AudioSource
from .configs.grassfx import AC_GrassFX, AC_GrassFXMaterial, AC_GrassFXOccludingMaterial
from .configs.kn5 import (AC_MaterialSettings, AC_ShaderProperty,
                          AC_TextureSettings)
from .configs.lighting import (AC_CSPLightSettings, AC_DirectionList, AC_EmissiveMaterial,
                               AC_GlobalLighting, AC_Light, AC_Lighting, AC_MaterialList,
                               AC_MeshList, AC_PositionList, AC_SunSettings)
from .configs.rainfx import AC_RainFX
from .configs.surface import AC_Surface
from .configs.track import AC_Track
from .gizmos.pitbox import (AC_GizmoGate, AC_GizmoGroup,
                            AC_GizmoPitbox, AC_GizmoStartPos, AC_SelectGizmoObject)
from .menus.context import (WM_MT_AssignSurface, WM_MT_ObjectSetup,
                            surface_menu)
from .menus.ops.audio import AC_AddAudioSource, AC_ToggleAudio
from .menus.ops.extensions import (AC_AddGlobalExtension,
                                   AC_AddGlobalExtensionItem,
                                   AC_RemoveGlobalExtension,
                                   AC_RemoveGlobalExtensionItem,
                                   AC_ToggleGlobalExtension)
from .menus.ops.object_setup import (AC_AutoSetupObjects, AC_SetupAsGrass,
                                     AC_SetupAsStandard, AC_SetupAsTree)
from .menus.ops.image_generation import (AC_CreatePreviewCamera,
                                         AC_GenerateMap, AC_GeneratePreview)
from .menus.ops.project import (AC_AddABFinishGate, AC_AddABStartGate,
                                AC_AddAudioEmitter, AC_AddHotlapStart,
                                AC_AddPitbox, AC_AddStart, AC_AddTimeGate,
                                AC_AddRaceSetup,
                                AC_AutofixPreflight,
                                AC_SaveSettings, AC_ValidateAll, AC_UpdateMaterialConfig,
                                AC_SaveSurfaces, AC_SaveExtensions, AC_SaveLighting,
                                AC_SaveAudio, AC_SaveTrackData, AC_ScanForIssues, AC_ShowPreflightErrors)
from .menus.ops.surface import (AC_AddSurface, AC_AddSurfaceExt,
                                AC_AssignPhysProp, AC_AssignSurface,
                                AC_AssignWall, AC_DeleteSurfaceExt,
                                AC_InitSurfaces, AC_RefreshSurfaces, AC_RemoveSurface,
                                AC_SelectAllSurfaces, AC_ToggleSurface)
from .menus.ops.track import (AC_AddGeoTag, AC_AddTag, AC_RemoveGeoTag,
                              AC_RemoveTag, AC_SelectByName, AC_ToggleGeoTag,
                              AC_ToggleTag)
from .menus.ops.material_setup import (AC_AutoAssignTextureSlots, AC_SetupNormalMap, AC_ApplyShaderDefaults, AC_ResetShaderDefaults)
from .menus.ops.grassfx import (AC_AddGrassFXMaterial, AC_RemoveGrassFXMaterial,
                                AC_ClearGrassFXMaterials, AC_AutoDetectGrassFXMaterials,
                                AC_AddOccludingMaterial, AC_RemoveOccludingMaterial,
                                AC_ClearOccludingMaterials)
from .menus.ops.lighting import (AC_AddLight, AC_AddLightFromSelection, AC_AddLightAtCursor,
                                 AC_RemoveLight, AC_ToggleLightShadows, AC_DuplicateLight, AC_SyncLightFromObject,
                                 AC_SyncAllLights, AC_SelectLightObject,
                                 AC_MoveLightUp, AC_MoveLightDown,
                                 AC_AddBlenderSpotLight, AC_SyncFromBlenderLight, AC_AddLightFromBlenderLights,
                                 AC_ScanLights, AC_SyncAllFromBlender, AC_ExportAndUpdateLights,
                                 AC_AddEmissiveMaterial, AC_AddEmissiveFromMesh, AC_RemoveEmissiveMaterial,
                                 AC_ToggleEmissiveShadows, AC_ClearEmissiveMaterials, AC_SelectEmissiveObject)
from .menus.ops.rainfx import (AC_AutoDetectRainFXMaterials, AC_ClearRainFXMaterials,
                               AC_ToggleRainFX)
from .menus.ops.treefx import AC_ExportTreeList
from .menus.ops.sync import (AC_ExtConfigSyncCheck, AC_ExtConfigSyncDialog,
                              AC_ExtConfigSyncAction, AC_ExtConfigSyncCancel,
                              AC_ExtConfigViewDiff, AC_ImportExtConfig)
from .configs.bulk_edit import (AC_BulkMaterialItem, AC_BulkPropertyValue,
                                 AC_BulkEditSettings)
from .menus.ops.bulk_edit import (AC_UL_BulkMaterials, AC_BulkEditSelectMaterials,
                                   AC_BulkEditToggleAll, AC_BulkEditToggleNone,
                                   AC_BulkEditProperties)
from .ai import AC_ExportAILine
from .ai import ai_ops as ai_ops_module
from .menus.panels import (AC_AddShaderProperty, AC_RemoveShaderProperty,
                           AC_UL_ShaderProperties, NODE_PT_AC_Texture,
                           PROPERTIES_PT_AC_Material)
from .menus.sidebar import (AC_UL_Extensions,
                            AC_UL_SurfaceExtensions, AC_UL_Tags,
                            AC_UL_GrassFXMaterials, AC_UL_Materials,
                            AC_UL_Lights, AC_UL_EmissiveMaterials,
                            AC_ClearMaterialSearch, AC_ScanMaterials,
                            VIEW3D_PT_AC_Setup,
                            VIEW3D_PT_AC_SurfaceTools,
                            VIEW3D_PT_AC_Surfaces,
                            VIEW3D_PT_AC_Objects,
                            VIEW3D_PT_AC_TrackImages,
                            VIEW3D_PT_AC_Export,
                            VIEW3D_PT_AC_Sidebar_Extra,
                            VIEW3D_PT_AC_Sidebar_GrassFX,
                            VIEW3D_PT_AC_Sidebar_RainFX,
                            VIEW3D_PT_AC_Sidebar_TreeFX,
                            VIEW3D_PT_AC_Sidebar_AILines,
                            VIEW3D_PT_AC_Sidebar_CSPLights,
                            VIEW3D_PT_AC_Sidebar_EmissiveMaterials,
                            VIEW3D_PT_AC_MaterialEditor,
                            VIEW3D_PT_AC_MaterialProperties,
                            VIEW3D_PT_AC_ShaderProperties)
from .settings import AC_Settings, ExportSettings, KN5_MeshSettings
from .preferences import AC_Preferences
from .kn5.exporter_ops import (
    AC_ContinueSmartExport,
    ReportOperator,
    CopyClipboardButtonOperator,
    ExportKN5,
    menu_func,
)
from .kn5 import export_utils
from .kn5.ui_properties import (
    NodeProperties,
    KN5_PT_NodePanel,
    MaterialProperties,
    TextureProperties,
)

__classes__ = (
    AC_InitSurfaces, AC_RefreshSurfaces, AC_AddSurface, AC_RemoveSurface, AC_ToggleSurface, AC_AssignSurface, AC_SelectAllSurfaces, AC_AssignWall, AC_AssignPhysProp,
    AC_AddSurfaceExt, AC_DeleteSurfaceExt,
    AC_AddTag, AC_RemoveTag, AC_AddGeoTag, AC_RemoveGeoTag, AC_ToggleTag, AC_ToggleGeoTag,
    AC_AutofixPreflight, AC_ValidateAll, AC_UpdateMaterialConfig, AC_ScanForIssues, AC_ShowPreflightErrors,
    AC_SaveSettings,
    AC_SaveSurfaces, AC_SaveExtensions, AC_SaveLighting, AC_SaveAudio, AC_SaveTrackData,
    AC_SelectByName,
    AC_SelectGizmoObject, AC_GizmoPitbox, AC_GizmoStartPos, AC_GizmoGate, AC_GizmoGroup,
    AC_AddAudioSource, AC_ToggleAudio,
    AC_AddGlobalExtension, AC_RemoveGlobalExtension, AC_ToggleGlobalExtension, AC_AddGlobalExtensionItem, AC_RemoveGlobalExtensionItem,
    AC_AddStart, AC_AddHotlapStart, AC_AddPitbox, AC_AddTimeGate, AC_AddABStartGate, AC_AddABFinishGate, AC_AddAudioEmitter, AC_AddRaceSetup,
    AC_SetupAsGrass, AC_SetupAsStandard, AC_SetupAsTree, AC_AutoSetupObjects,
    AC_AddShaderProperty, AC_RemoveShaderProperty,
    AC_AutoAssignTextureSlots, AC_SetupNormalMap, AC_ApplyShaderDefaults, AC_ResetShaderDefaults,
    AC_ClearMaterialSearch, AC_ScanMaterials,
    AC_AddGrassFXMaterial, AC_RemoveGrassFXMaterial, AC_ClearGrassFXMaterials, AC_AutoDetectGrassFXMaterials,
    AC_AddOccludingMaterial, AC_RemoveOccludingMaterial, AC_ClearOccludingMaterials,
    AC_AutoDetectRainFXMaterials, AC_ClearRainFXMaterials, AC_ToggleRainFX,
    AC_ExportTreeList,
    AC_ExportAILine,
    AC_ExtConfigSyncCheck, AC_ExtConfigSyncDialog, AC_ExtConfigSyncAction, AC_ExtConfigSyncCancel, AC_ExtConfigViewDiff, AC_ImportExtConfig,
    AC_AddLight, AC_AddLightFromSelection, AC_AddLightAtCursor, AC_RemoveLight, AC_ToggleLightShadows, AC_DuplicateLight,
    AC_SyncLightFromObject, AC_SyncAllLights, AC_SelectLightObject,
    AC_MoveLightUp, AC_MoveLightDown,
    AC_AddBlenderSpotLight, AC_SyncFromBlenderLight, AC_AddLightFromBlenderLights,
    AC_ScanLights, AC_SyncAllFromBlender, AC_ExportAndUpdateLights,
    AC_AddEmissiveMaterial, AC_AddEmissiveFromMesh, AC_RemoveEmissiveMaterial,
    AC_ToggleEmissiveShadows, AC_ClearEmissiveMaterials, AC_SelectEmissiveObject,
    AC_GenerateMap, AC_GeneratePreview, AC_CreatePreviewCamera,
    AC_GrassFXMaterial, AC_GrassFXOccludingMaterial, AC_GrassFX,
    AC_RainFX,
    AC_Track, AC_Surface, AC_AudioSource,
    AC_MeshList, AC_MaterialList, AC_PositionList, AC_DirectionList,
    AC_CSPLightSettings, AC_SunSettings, AC_GlobalLighting, AC_EmissiveMaterial, AC_Light, AC_Lighting,
    AC_ShaderProperty, AC_MaterialSettings, AC_TextureSettings,
    # Bulk edit PropertyGroups (must be before AC_Settings)
    AC_BulkMaterialItem, AC_BulkPropertyValue, AC_BulkEditSettings,
    KN5_MeshSettings, ExportSettings, AC_Settings,
    # Bulk edit operators and UI
    AC_UL_BulkMaterials, AC_BulkEditSelectMaterials, AC_BulkEditToggleAll, AC_BulkEditToggleNone, AC_BulkEditProperties,
    AC_UL_Tags, AC_UL_Extensions, AC_UL_SurfaceExtensions, AC_UL_ShaderProperties, AC_UL_GrassFXMaterials, AC_UL_Materials, AC_UL_Lights, AC_UL_EmissiveMaterials,
    # Main panels (parent panels must be registered first)
    VIEW3D_PT_AC_Setup,
    VIEW3D_PT_AC_SurfaceTools,
    VIEW3D_PT_AC_Surfaces,  # subpanel of SurfaceTools
    VIEW3D_PT_AC_Objects,
    VIEW3D_PT_AC_Sidebar_Extra,
    VIEW3D_PT_AC_Export,
    VIEW3D_PT_AC_TrackImages,  # subpanel of Export
    # Extra subpanels
    VIEW3D_PT_AC_Sidebar_GrassFX,
    VIEW3D_PT_AC_Sidebar_RainFX,
    VIEW3D_PT_AC_Sidebar_TreeFX,
    VIEW3D_PT_AC_Sidebar_AILines,
    VIEW3D_PT_AC_Sidebar_CSPLights,
    VIEW3D_PT_AC_Sidebar_EmissiveMaterials,
    VIEW3D_PT_AC_MaterialEditor,
    VIEW3D_PT_AC_MaterialProperties,  # subpanel of MaterialEditor
    VIEW3D_PT_AC_ShaderProperties,    # subpanel of MaterialEditor
    PROPERTIES_PT_AC_Material, NODE_PT_AC_Texture,
    WM_MT_AssignSurface, WM_MT_ObjectSetup,
    # KN5 Export (v0.2.0 style) - Legacy UI classes for backward compatibility
    AC_ContinueSmartExport,
    ReportOperator,
    CopyClipboardButtonOperator,
    ExportKN5,
    NodeProperties,
    KN5_PT_NodePanel,
    MaterialProperties,
    TextureProperties,
)

# Handler to automatically initialize surfaces when a file is loaded
@bpy.app.handlers.persistent
def initialize_surfaces_on_load(dummy):
    """Automatically initialize default surfaces if surfaces list is empty"""
    for scene in bpy.data.scenes:
        if hasattr(scene, 'AC_Settings'):
            settings = scene.AC_Settings
            if not settings.surfaces:
                settings.load_surfaces({})

# Track the last active object to detect selection changes
_last_active_object = None

@bpy.app.handlers.persistent
def sync_light_selection(scene, depsgraph):
    """Sync light list selection when viewport selection changes"""
    global _last_active_object

    context = bpy.context
    if not hasattr(context, 'active_object'):
        return

    active_obj = context.active_object

    # Only process if active object changed
    if active_obj == _last_active_object:
        return
    _last_active_object = active_obj

    # Check if active object is a light linked to our list
    if active_obj and active_obj.type == 'LIGHT':
        if hasattr(scene, 'AC_Settings'):
            lighting = scene.AC_Settings.lighting
            for i, light in enumerate(lighting.lights):
                if light.linked_object == active_obj:
                    if lighting.active_light_index != i:
                        lighting.active_light_index = i
                    break

def register():
    from bpy.utils import register_class
    for cls in __classes__:
        register_class(cls)
    # Register export utilities
    export_utils.register()
    bpy.types.Scene.AC_Settings = bpy.props.PointerProperty(type=AC_Settings)
    bpy.types.Object.AC_KN5 = bpy.props.PointerProperty(type=KN5_MeshSettings)
    bpy.types.Object.AC_CSP = bpy.props.PointerProperty(type=AC_CSPLightSettings)
    bpy.types.Material.AC_Material = bpy.props.PointerProperty(type=AC_MaterialSettings)
    bpy.types.ShaderNodeTexImage.AC_Texture = bpy.props.PointerProperty(type=AC_TextureSettings)
    # Context menus
    bpy.types.VIEW3D_MT_object_context_menu.append(surface_menu)
    # File > Export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func)
    # Register load handler for automatic surface initialization
    bpy.app.handlers.load_post.append(initialize_surfaces_on_load)
    # Register depsgraph handler for light selection sync
    bpy.app.handlers.depsgraph_update_post.append(sync_light_selection)
    # Register AI line import/export menus
    ai_ops_module.register()

def unregister():
    from bpy.utils import unregister_class
    # Unregister AI line import/export menus
    ai_ops_module.unregister()
    # Remove handlers
    if sync_light_selection in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_light_selection)
    if initialize_surfaces_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(initialize_surfaces_on_load)
    # Remove context menus
    bpy.types.VIEW3D_MT_object_context_menu.remove(surface_menu)
    # Remove File > Export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    # Remove properties
    del bpy.types.ShaderNodeTexImage.AC_Texture
    del bpy.types.Material.AC_Material
    del bpy.types.Object.AC_CSP
    del bpy.types.Object.AC_KN5
    del bpy.types.Scene.AC_Settings
    # Unregister export utilities
    export_utils.unregister()
    # Unregister classes
    for cls in reversed(__classes__):
        unregister_class(cls)
