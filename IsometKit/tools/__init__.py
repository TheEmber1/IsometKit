from .camera import ISOMETKIT_OT_setup_camera
from .lighting import ISOMETKIT_OT_setup_lighting
from .asset_loader import ISOMETKIT_OT_refresh_assets, ISOMETKIT_OT_place_asset_modal, ISOMETKIT_OT_place_from_category, register as register_loader, unregister as unregister_loader
from .thumbnail_generator import ISOMETKIT_OT_generate_thumbnails

classes = (
    ISOMETKIT_OT_setup_camera,
    ISOMETKIT_OT_setup_lighting,
    ISOMETKIT_OT_refresh_assets,
    ISOMETKIT_OT_place_asset_modal,
    ISOMETKIT_OT_place_from_category,
    ISOMETKIT_OT_generate_thumbnails,
)

def register():
    for cls in classes:
        import bpy
        try:
            bpy.utils.register_class(cls)
        except (RuntimeError, ValueError) as e:
            # If already registered, ignore it. Otherwise raise.
            if "already registered" not in str(e):
                print(f"IsometKit: Unexpected error registering {cls.__name__}: {e}")
                # We optionally raise here if we want to stop loading, 
                # but usually it's safer to continue if just one tool fails.
                # raising e ensures the user knows something is wrong.
                raise e
    register_loader()

def unregister():
    unregister_loader()
    for cls in classes:
        import bpy
        bpy.utils.unregister_class(cls)
