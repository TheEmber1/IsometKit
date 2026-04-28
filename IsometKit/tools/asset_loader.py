import bpy
import os
import bpy.utils.previews
from bpy_extras import view3d_utils
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hashlib
import math

# Global Preview Collection
preview_collections = {}
# Track whether we've attempted auto-generation during this session to avoid loops
auto_gen_attempted = False
# Categories supported in the UI (user requested set)
# Categories supported in the UI (user requested set)
CATEGORIES = ["All", "Furniture", "Tech", "Plants", "Props"]
CATEGORY_KEYWORDS = {
    "Furniture": ["table", "chair", "sofa", "couch", "bed", "desk", "cabinet", "bench", "shelf", "stool", "rug"],
    "Tech": ["ipad", "phone", "keyboard", "mouse", "computer", "controller", "monitor", "laptop", "speaker", "device", "appliance", "gadget", "console", "camera", "printer", "server", "router", "tablet", "headphones", "switch"],
    "Plants": ["plant", "tree", "flower", "fern", "bush", "succulent", "cactus", "christmas tree"],
    "Props": ["book", "lamp", "box", "crate", "vase", "prop", "bottle", "pillow", "curtain", "clock", "art", "board", "cushion", "drapes", "painting", "photograph", "poster", "print", "sculpture", "figurine", "ornament", "diffuser", "slipper", "pin board", "sticky note", "light", "candle", "chandelier", "sconce", "cup", "pen", "pencil", "scissor", "tool", "utensil", "cylinder", "window", "floorboard", "sign"],
}

def get_asset_items(self, context):
    """List assets with icons"""
    if "main" not in preview_collections:
        return []
    pcoll = preview_collections["main"]
    # If previews haven't been populated yet, avoid attribute errors
    if not hasattr(pcoll, "my_previews"):
        return []
    wm = context.window_manager
    cat = getattr(wm, "isometkit_category", "All")
    search_term = getattr(wm, "isometkit_search", "").lower()
    # categories stored under preview_collections['categories']
    cats = preview_collections.get("categories", {})
    
    if not cats:
        items = pcoll.my_previews
    else:
        # Return the list for the chosen category (or fallback to all)
        items = cats.get(cat, cats.get("All", pcoll.my_previews))
        
    if search_term:
        items = [item for item in items if search_term in item[1].lower()]
        
    return items


def get_room_items(self, context):
    """List only assets that look like room models (filtered by name)"""
    if "main" not in preview_collections:
        return []
    pcoll = preview_collections["main"]
    if not hasattr(pcoll, "my_previews"):
        return []
    items = []
    for itm in pcoll.my_previews:
        # itm is (identifier, display_name, desc, icon, number)
        identifier = itm[0]
        display = itm[1]
        # simple heuristic: 'room' in name or identifier
        if 'room' in display.lower() or 'room' in identifier.lower():
            items.append((identifier, display, itm[2], itm[3], itm[4]))
    return items

class ISOMETKIT_OT_refresh_assets(bpy.types.Operator):
    """Scan assets and load thumbnails"""
    bl_idname = "isometkit.refresh_assets"
    bl_label = "Refresh Assets"
    
    clean_thumbnails: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        global auto_gen_attempted
        auto_gen_attempted = False # Reset flag on manual refresh
        
        if self.clean_thumbnails:
            # Call thumbnail generator with clean_existing=True
            bpy.ops.isometkit.generate_thumbnails('INVOKE_DEFAULT', clean_existing=True, called_from_loader=True)
            return {'FINISHED'}

        load_previews()
        return {'FINISHED'}

def load_previews():
    # Use bpy.data when called from a timer to be safer
    wm = bpy.data.window_managers[0] if bpy.data.window_managers else None
    if not wm: return
    
    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    assets_dir = os.path.join(addon_dir, "assets")
    thumb_dir = os.path.join(addon_dir, "thumbnails")
    
    if "main" in preview_collections:
        bpy.utils.previews.remove(preview_collections["main"])
        
    pcoll = bpy.utils.previews.new()
    preview_collections["main"] = pcoll
    
    if not os.path.exists(assets_dir):
        return

    blend_files = sorted([f for f in os.listdir(assets_dir) if f.endswith(".blend")])
    
    # We need to list objects. 
    # If thumbnail exists, use it. If not, use generic icon.
    previews = []
    # prepare category buckets
    categories = {c: [] for c in CATEGORIES if c != "All"}
    missing_found = False
    
    for fname in blend_files:
        fpath = os.path.join(assets_dir, fname)
        base_name = os.path.splitext(fname)[0]
        with bpy.data.libraries.load(fpath) as (data_from, data_to):
            for obj_name in sorted(data_from.objects):
                # Use the actual filename (including .blend) in the identifier so we can open the file later
                identifier = f"{fname}|{obj_name}"
                thumb_name = f"{base_name}_{obj_name}.png"
                thumb_path = os.path.join(thumb_dir, thumb_name)

                icon_value = None
                if os.path.exists(thumb_path):
                    pcoll.load(identifier, thumb_path, 'IMAGE')
                    icon_value = pcoll[identifier].icon_id
                else:
                    # Thumbnail missing — do not call pcoll.load with an invalid type.
                    # Use a built-in icon name (string) as the enum icon and print a hint
                    icon_value = 'OBJECT_DATA'
                    print(f"IsometKit: thumbnail not found for {identifier}. Will attempt to generate thumbnails.")
                    missing_found = True

                # Use sequential numeric ids with deterministic ordering so enum values remain stable
                display_name = obj_name.replace("ISO_KIT ", "").replace("ISO_KIT", "").strip()
                if display_name.startswith("_") or display_name.startswith("-"):
                    display_name = display_name[1:].strip()
                unique_id = len(previews)
                item_tuple = (identifier, display_name, "", icon_value, unique_id)
                previews.append(item_tuple)

                # categorize (skip 'All' which contains everything)
                lowered = (display_name + " " + identifier).lower()
                placed = False
                for cat, keys in CATEGORY_KEYWORDS.items():
                    for k in keys:
                        if k in lowered:
                            categories.setdefault(cat, []).append(item_tuple)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    # Put into Props by default if not matched
                    categories.setdefault("Props", []).append(item_tuple)

    pcoll.my_previews = previews
    # Also provide an 'All' collection containing all previews
    categories_all = {"All": previews}
    categories_all.update(categories)
    preview_collections["categories"] = categories_all
    # Expose missing flag on WindowManager so UI can react (hide generate button when none missing)
    try:
        wm.isometkit_thumbnails_missing = missing_found
    except Exception:
        pass

    # If we found missing thumbnails, attempt to auto-generate them.
    try:
            global auto_gen_attempted
            if not auto_gen_attempted:
                print("IsometKit: missing thumbnails detected — running thumbnail generator...")
                # Call operator to generate thumbnails; operator will call refresh when done
                try:
                    auto_gen_attempted = True
                    bpy.ops.isometkit.generate_thumbnails('INVOKE_DEFAULT', called_from_loader=True)
                except Exception as e:
                    print(f"IsometKit: failed to invoke thumbnail generator: {e}")
            else:
                print("IsometKit: missing thumbnails detected but auto-gen already attempted this session.")
    except Exception:
        pass


def get_category_items_factory(cat_name):
    def _items(self, context):
        if "main" not in preview_collections:
            return []
        cats = preview_collections.get("categories", {})
        return cats.get(cat_name, [])
    return _items


class ISOMETKIT_OT_place_asset_modal(bpy.types.Operator):
    """Place Asset with Raycast Snapping"""
    bl_idname = "isometkit.place_asset" # Overwriting previous one
    bl_label = "Place Asset"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    obj_name: bpy.props.StringProperty()
    file_name: bpy.props.StringProperty()
    
    _timer = None
    _obj = None
    _scale = 1.0
    _rot_z = 0.0
    _last_mouse_y = None
    
    def _update_ui(self, context):
        if context.area:
            wm = context.window_manager
            align_str = "ON" if wm.isometkit_align_to_target else "OFF"
            # Normalize rotation to 0-360 for display
            display_rot = round(math.degrees(self._rot_z)) % 360
            text = f"IsometKit | Scale: {self._scale:.1f} | Rotation: {display_rot:.0f}° | Align: {align_str} | [Wheel / +/-] Scale, [Ctrl+Wheel] Rotate, [Shift+Drag] Scale/Rotate, [LMB] Confirm"
            context.area.header_text_set(text)

    def _snap_values(self):
        # Snap rotation to 15 degrees
        rot_deg = math.degrees(self._rot_z)
        snapped_deg = round(rot_deg / 15.0) * 15.0
        self._rot_z = math.radians(snapped_deg)
        
        # Snap scale to 0.1
        self._scale = round(self._scale * 10.0) / 10.0
        self._scale = max(0.1, min(self._scale, 10.0))

    def _get_cardinal_normal(self, normal):
        """Snaps a vector to the nearest cardinal axis"""
        # abs values to find the dominant axis
        abs_x = abs(normal.x)
        abs_y = abs(normal.y)
        abs_z = abs(normal.z)
        
        max_val = max(abs_x, abs_y, abs_z)
        
        if max_val == abs_x:
            return Vector((1.0 if normal.x > 0 else -1.0, 0.0, 0.0))
        elif max_val == abs_y:
            return Vector((0.0, 1.0 if normal.y > 0 else -1.0, 0.0))
        else:
            return Vector((0.0, 0.0, 1.0 if normal.z > 0 else -1.0))
    
    def modal(self, context, event):
        # Mouse wheel: scale or rotate depending on modifier (works with mouse wheels)
        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            if not self._obj:
                return {'RUNNING_MODAL'}

            # Wheel direction
            is_up = (event.type == 'WHEELUPMOUSE')

            # If Ctrl (or Cmd on mac) is held, rotate around Z; otherwise scale
            if event.ctrl or event.oskey:
                step_deg = 15.0
                step = math.radians(step_deg if is_up else -step_deg)
                self._rot_z += step
            else:
                step = 0.1 if is_up else -0.1
                self._scale += step
                
            self._snap_values()
            self.update_location(context, event)
            self._update_ui(context)

            return {'RUNNING_MODAL'}

        # Trackpad users: support Shift + drag (vertical) to scale and Ctrl/Cmd + Shift + drag to rotate
        if event.type == 'MOUSEMOVE':
            if not self._obj:
                return {'RUNNING_MODAL'}

            # If Shift is held, interpret vertical drag as scale change
            if event.shift:
                if self._last_mouse_y is None:
                    self._last_mouse_y = event.mouse_y
                    return {'RUNNING_MODAL'}
                dy = event.mouse_y - self._last_mouse_y
                # sensitivity: 0.005 per pixel
                if abs(dy) >= 1.0:
                    factor = 1.0 + (dy * 0.005)
                    # small multiplier to avoid negative
                    if factor <= 0:
                        factor = 0.01
                    if event.ctrl or event.oskey:
                        self._rot_z += math.radians(dy * 0.5)
                    else:
                        self._scale *= factor
                    
                    self._snap_values()
                    self.update_location(context, event)
                    self._update_ui(context)
                    self._last_mouse_y = event.mouse_y
                return {'RUNNING_MODAL'}
            else:
                # reset last mouse tracking when Shift released
                self._last_mouse_y = None

            # Alt + drag moves the object under the cursor (useful in camera view / trackpad)
            if event.alt:
                region = context.region
                rv3d = context.region_data
                if region is None or rv3d is None:
                    return {'RUNNING_MODAL'}
                coord = (event.mouse_region_x, event.mouse_region_y)
                try:
                    # Map the 2D mouse position to a 3D location at the object's depth
                    new_loc = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, self._obj.location)
                    self._obj.location = new_loc
                except Exception:
                    pass
                return {'RUNNING_MODAL'}

        # Keyboard shortcuts for trackpad users: +/- scale, Q/E rotate
        if event.type in {'EQUAL', 'NUMPAD_PLUS'} and event.value == 'PRESS':
            if self._obj:
                if event.ctrl or event.oskey:
                    self._rot_z += math.radians(15.0)
                else:
                    self._scale += 0.1
                self._snap_values()
                self.update_location(context, event)
                self._update_ui(context)
            return {'RUNNING_MODAL'}

        if event.type in {'MINUS', 'NUMPAD_MINUS'} and event.value == 'PRESS':
            if self._obj:
                if event.ctrl or event.oskey:
                    self._rot_z -= math.radians(15.0)
                else:
                    self._scale -= 0.1
                self._snap_values()
                self.update_location(context, event)
                self._update_ui(context)
            return {'RUNNING_MODAL'}

        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'}:
            if context.area:
                context.area.header_text_set(None)
            # Confirm
            self.report({'INFO'}, "Placed Asset")
            return {'FINISHED'}
            
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            if context.area:
                context.area.header_text_set(None)
            # Cancel
            if self._obj:
                bpy.data.objects.remove(self._obj, do_unlink=True)
            return {'CANCELLED'}
            
        elif event.type == 'MOUSEMOVE':
            self.update_location(context, event)
            self._update_ui(context)
            
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        wm = context.window_manager
        selection = wm.isometkit_selected_asset
        print(f"IsometKit: invoke selection='{selection}'")
        
        if not selection or "|" not in selection:
            self.report({'WARNING'}, "No asset selected")
            return {'CANCELLED'}
        
        fname, obj_name = selection.split("|", 1)
        
        # Append logic
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        fpath = os.path.join(addon_dir, "assets", fname)
        
        try:
            with bpy.data.libraries.load(fpath, link=False) as (data_from, data_to):
                if obj_name in data_from.objects:
                    data_to.objects = [obj_name]
                else:
                    return {'CANCELLED'}
            
            self._obj = data_to.objects[0]
            context.collection.objects.link(self._obj)
            # Initialize transform state
            self._scale = 1.0
            self._rot_z = 0.0
            self._obj.select_set(True)
            self._obj.scale = (self._scale, self._scale, self._scale)
            self._obj.rotation_euler.z = self._rot_z
            context.view_layer.objects.active = self._obj
            
            # Start modal
            context.window_manager.modal_handler_add(self)
            self._update_ui(context)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error: {e}")
            return {'CANCELLED'}

    def update_location(self, context, event):
        if not self._obj:
            return
            
        # Raycast logic
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        
        # If we don't have 3D region data, abort (operator should run in 3D view)
        if rv3d is None or region is None:
            return

        # Use evaluated depsgraph for more reliable raycasting
        depsgraph = context.evaluated_depsgraph_get()
        
        # Get ray direction and origin using view3d_utils
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        # Determine if we're in orthographic view
        if not rv3d.is_perspective:
            # Shift ray origin back significantly to ensure we capture objects in front of the view.
            # In orthographic view, the default origin might be too close to captured objects.
            # Shifting back by 1000 units ensures we're 'outside' the scene area.
            ray_origin = ray_origin - view_vector * 1000.0

        # We temporary hide the object so the ray doesn't hit it (self-collision)
        self._obj.hide_viewport = True
        
        # Scene raycast
        try:
            dir_vec = view_vector.normalized()
        except Exception:
            dir_vec = view_vector

        hit, location, normal, index, obj, matrix = context.scene.ray_cast(
            depsgraph,
            ray_origin,
            dir_vec
        )
        
        # Unhide immediately
        self._obj.hide_viewport = False
        
        # Apply transforms immediately
        self._obj.scale = (self._scale, self._scale, self._scale)
        
        if hit:
            self._obj.location = location
            
            # Rotation alignment
            wm = context.window_manager
            if wm.isometkit_align_to_target:
                # Use flat face normal instead of interpolated hit normal
                try:
                    # matrix_world @ normal gives us world space normal
                    # index is the polygon index
                    face_normal = (obj.matrix_world.to_quaternion() @ obj.data.polygons[index].normal).normalized()
                    # Cardinalize for perfect iso alignment
                    use_normal = self._get_cardinal_normal(face_normal)
                except Exception:
                    use_normal = self._get_cardinal_normal(normal)

                # Align Z to surface normal
                quat_align = use_normal.to_track_quat('Z', 'Y')
                # Apply user Z-rotation on top
                from mathutils import Quaternion
                quat_user = Quaternion((0, 0, 1), self._rot_z)
                self._obj.rotation_mode = 'QUATERNION'
                self._obj.rotation_quaternion = quat_align @ quat_user
            else:
                self._obj.rotation_mode = 'XYZ'
                self._obj.rotation_euler = (0, 0, self._rot_z)
        else:
            # Fallback for empty areas or planes
            # If we're looking top-down-ish, snap to Z=0
            if abs(view_vector.z) > 0.001:
                t = -ray_origin.z / view_vector.z
                if t > 0:
                    self._obj.location = ray_origin + view_vector * t
                else:
                    # In ortho mode or behind camera, the plane intersection might be 'behind' us relative to world origin
                    # but still valid in the view frustum. However, simple Z=0 fallback is usually enough.
                    self._obj.location = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, self._obj.location)
            else:
                # Flat view, use 2D to 3D mapping
                self._obj.location = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, self._obj.location)


# Register
def register():
    bpy.types.WindowManager.isometkit_selected_asset = bpy.props.EnumProperty(
        name="Asset",
        description="Choose an asset",
        items=get_asset_items
    )
    bpy.types.WindowManager.isometkit_search = bpy.props.StringProperty(
        name="Search Objects",
        description="Search for an asset by name",
        default="",
        options={'TEXTEDIT_UPDATE'}
    )
    # Single category selector
    bpy.types.WindowManager.isometkit_category = bpy.props.EnumProperty(
        items=[(c, c, "") for c in CATEGORIES],
        name="Category",
        default="All"
    )
    # Flag whether thumbnails are missing (UI uses this to show/hide generate button)
    bpy.types.WindowManager.isometkit_thumbnails_missing = bpy.props.BoolProperty(
        name="Thumbnails Missing",
        description="True when some thumbnails are missing",
        default=False
    )
    # Room selector (icon view uses same preview collections, filtered by room heuristic)
    bpy.types.WindowManager.isometkit_selected_room = bpy.props.EnumProperty(
        name="Room",
        description="Choose a room to append",
        items=get_room_items
    )
    # (removed Tech Init toggle — replaced by separate lighting operator)
    # UI collapsible sections
    bpy.types.WindowManager.isometkit_show_room_setup = bpy.props.BoolProperty(
        name="Show Room Setup",
        description="Show the Room Setup section",
        default=True
    )
    bpy.types.WindowManager.isometkit_show_asset_loader = bpy.props.BoolProperty(
        name="Show Asset Loader",
        description="Show the Asset Loader section",
        default=True
    )
    bpy.types.WindowManager.isometkit_align_to_target = bpy.props.BoolProperty(
        name="Align to Target",
        description="Align object rotation to the surface normal",
        default=True
    )
    # Populate previews after a short delay to ensure bpy.data is fully accessible
    bpy.app.timers.register(load_previews, first_interval=0.1)

def unregister():
    if "main" in preview_collections:
        bpy.utils.previews.remove(preview_collections["main"])
        del preview_collections["main"]
    # Remove our WindowManager props
    if hasattr(bpy.types.WindowManager, "isometkit_selected_asset"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_selected_asset")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_search"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_search")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_category"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_category")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_selected_room"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_selected_room")
        except Exception:
            pass
    # Tech Init property removed
    if hasattr(bpy.types.WindowManager, "isometkit_thumbnails_missing"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_thumbnails_missing")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_show_room_setup"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_show_room_setup")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_show_asset_loader"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_show_asset_loader")
        except Exception:
            pass
    if hasattr(bpy.types.WindowManager, "isometkit_align_to_target"):
        try:
            delattr(bpy.types.WindowManager, "isometkit_align_to_target")
        except Exception:
            pass


class ISOMETKIT_OT_place_from_category(bpy.types.Operator):
    """Place the currently selected item from a named category"""
    bl_idname = "isometkit.place_from_category"
    bl_label = "Place From Category"

    category: bpy.props.StringProperty()

    def execute(self, context):
        wm = context.window_manager
        cats = preview_collections.get("categories", {})
        items = cats.get(self.category, [])
        if not items:
            self.report({'WARNING'}, f"No items in category {self.category}")
            return {'CANCELLED'}

        # pick first item if no explicit selection; set common selection used by placement operator
        sel = items[0][0]
        wm.isometkit_selected_asset = sel
        try:
            bpy.ops.isometkit.place_asset('INVOKE_DEFAULT')
        except Exception as e:
            self.report({'ERROR'}, f"Failed to start placement: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}
