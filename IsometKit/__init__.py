bl_info = {
    "name": "IsometKit",
    "author": "nova",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > IsometKit Tab",
    "description": "Isometric Asset Distribution & Tools",
    "category": "3D View",
}

import bpy
import os
from . import tools

class ISOMETKIT_PT_main_panel(bpy.types.Panel):
    """IsometKit Main Panel"""
    bl_label = "IsometKit"
    bl_idname = "ISOMETKIT_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "IsometKit"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        # Room Setup collapsible header
        icon = 'TRIA_DOWN' if getattr(wm, 'isometkit_show_room_setup', True) else 'TRIA_RIGHT'
        row = layout.row(align=True)
        row.prop(wm, "isometkit_show_room_setup", emboss=False, icon=icon, text="Room Setup")
        if getattr(wm, 'isometkit_show_room_setup', True):
            rbox = layout.box()
            try:
                rbox.template_icon_view(wm, "isometkit_selected_room", show_labels=True, scale=4.0)
            except Exception:
                rbox.label(text="(No rooms)")
            rbox.operator("isometkit.setup_camera", text="Generate Iso Setup", icon='CAMERA_DATA')
            rbox.operator("isometkit.setup_lighting", text="Generate Simple Light Setup", icon='LIGHT_DATA')

        layout.separator()

        # Asset Loader collapsible header
        icon2 = 'TRIA_DOWN' if getattr(wm, 'isometkit_show_asset_loader', True) else 'TRIA_RIGHT'
        row2 = layout.row(align=True)
        row2.prop(wm, "isometkit_show_asset_loader", emboss=False, icon=icon2, text="Asset Loader")
        if getattr(wm, 'isometkit_show_asset_loader', True):
            box = layout.box()
            box.label(text="Asset Loader", icon='IMPORT')
            row = box.row()
            row.operator("isometkit.refresh_assets", text="", icon='FILE_REFRESH')
            # Category selector moved inside Asset Loader below the buttons
            box.prop(wm, "isometkit_category", text="Category")
            box.prop(wm, "isometkit_search", text="", icon='VIEWZOOM')
            # Grid View (filtered by category)
            box.template_icon_view(wm, "isometkit_selected_asset", show_labels=True, scale=4.0)
            box.prop(wm, "isometkit_align_to_target", text="Align to Target")
            box.operator("isometkit.place_asset", text="Place Asset", icon='OBJECT_DATAMODE')

        layout.separator()
        layout.label(text="Or use Asset Browser:", icon='ASSET_MANAGER')

class ISOMETKIT_PT_links_panel(bpy.types.Panel):
    """IsometKit Links Panel"""
    bl_label = "Links"
    bl_idname = "ISOMETKIT_PT_links_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "IsometKit"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.url_open", text="YouTube (@wussupnova)", icon='URL').url = "https://www.youtube.com/@wussupnova"
        layout.operator("wm.url_open", text="Website", icon='URL').url = "https://nova-3d.netlify.app"
        layout.operator("wm.url_open", text="GitHub", icon='URL').url = "https://github.com/TheEmber1"

def register_asset_library():
    """Registers the local assets folder as an Asset Library in Blender"""
    preferences = bpy.context.preferences
    filepaths = preferences.filepaths
    
    # Path to assets folder inside the addon
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    assets_dir = os.path.join(addon_dir, "assets")
    
    if not os.path.exists(assets_dir):
        print(f"IsometKit: Assets directory not found at {assets_dir}")
        return

    # Check if already registered
    if "IsometKit" not in filepaths.asset_libraries:
        try:
            bpy.ops.preferences.asset_library_add(directory=assets_dir)
            # rename the newly added library (which defaults to directory name)
            # Finding the library we just added can be tricky if 'assets' name is taken.
            # But usually it adds with the folder name.
            lib = filepaths.asset_libraries.get("assets")
            if lib:
                lib.name = "IsometKit"
            
            # If for some reason it didn't name it assets or we want to be safe:
            # We can iterate and find path
            for lib in filepaths.asset_libraries:
                if lib.path == assets_dir:
                    lib.name = "IsometKit"
                    break
                    
        except Exception as e:
            print(f"IsometKit: Failed to register asset library: {e}")

def unregister_asset_library():
    """Unregisters the IsometKit Asset Library"""
    preferences = bpy.context.preferences
    filepaths = preferences.filepaths
    
    if "IsometKit" in filepaths.asset_libraries:
        # Finding index to remove
        idx = filepaths.asset_libraries.find("IsometKit")
        if idx != -1:
            try:
                # We need to set active index to remove it via ops, or just remove from collection?
                # The collection property doesn't have a remove() method exposed easily for python in some versions,
                # but bpy.ops.preferences.asset_library_remove() uses the active index.
                # However, manipulating preferences UI from script can be flaky if UI isn't open.
                # A safer way requires context override or finding it in the collection.
                # Actually, asset_libraries is a collection property, we usually can't just del it.
                # For safety in this simple script, we might choose NOT to auto-remove to avoid errors,
                # or warn user. But let's try to be clean.
                
                # Warning: Removing asset libraries via script is historically tricky in Blender API.
                # We will log it for now.
                print("IsometKit: Please manually remove 'IsometKit' from Asset Libraries if uninstalling.")
            except Exception as e:
                print(f"IsometKit: Error unregistering library: {e}")

def register():
    tools.register()
    try:
        bpy.utils.register_class(ISOMETKIT_PT_main_panel)
        bpy.utils.register_class(ISOMETKIT_PT_links_panel)
    except (RuntimeError, ValueError) as e:
        if "already registered" not in str(e):
            print(f"IsometKit: Unexpected error registering panel: {e}")
            raise e
    
    # Defer execution to ensure context is ready? 
    # Actually register is called on load. We can run this safely.
    # We use a timer to ensure it runs after Blender is fully loaded if needed,
    # but usually immediate is fine for paths.
    bpy.app.timers.register(register_asset_library, first_interval=1.0)

def unregister():
    bpy.utils.unregister_class(ISOMETKIT_PT_main_panel)
    try:
        bpy.utils.unregister_class(ISOMETKIT_PT_links_panel)
    except Exception:
        pass
    tools.unregister()
    unregister_asset_library()

if __name__ == "__main__":
    register()
