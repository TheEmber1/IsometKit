import bpy
import math
from mathutils import Vector

class ISOMETKIT_OT_setup_camera(bpy.types.Operator):
    """Setup Isometric Camera"""
    bl_idname = "isometkit.setup_camera"
    bl_label = "Setup Isometric Camera"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wm = context.window_manager

        # If a room is selected in the IsometKit UI, append it as the room
        selection = getattr(wm, 'isometkit_selected_room', None)
        room_obj = None
        if selection and "|" in selection:
            fname, obj_name = selection.split("|", 1)
            try:
                addon_dir = __file__
                # Resolve to addon root
                import os
                addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
                assets_dir = os.path.join(addon_dir, "assets")
                fpath = os.path.join(assets_dir, fname)
                if os.path.exists(fpath):
                    with bpy.data.libraries.load(fpath, link=False) as (data_from, data_to):
                        if obj_name in data_from.objects:
                            data_to.objects = [obj_name]
                        else:
                            self.report({'WARNING'}, f"Selected asset object '{obj_name}' not found in {fname}")
                else:
                    self.report({'WARNING'}, f"Asset file not found: {fpath}")
                
                # Link appended object into the current collection if present
                if data_to and data_to.objects and data_to.objects[0]:
                    room_obj = data_to.objects[0]
                    context.collection.objects.link(room_obj)
                    # Place roughly at origin first
                    room_obj.location = (0.0, 0.0, 0.0)
                    self.report({'INFO'}, f"Appended room '{obj_name}' from {fname}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to append room: {e}")

        # Create Camera Data
        cam_data = bpy.data.cameras.new(name='IsometricCamera')
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = 5.0
        
        # Create Camera Object
        cam_obj = bpy.data.objects.new(name='IsometricCamera', object_data=cam_data)
        context.collection.objects.link(cam_obj)
        
        # Position and Rotate (Magic Isometric Numbers)
        true_iso_angle = math.radians(90 - 35.264)
        cam_obj.rotation_euler = (true_iso_angle, 0, math.radians(45))

        # If we appended (or resolved) a room object, frame the camera on it
        try:
            if room_obj is None:
                # try to resolve from selection if not appended in this call
                sel = getattr(wm, 'isometkit_selected_room', None)
                if sel and "|" in sel:
                    _, obj_name = sel.split("|", 1)
                    room_obj = context.scene.objects.get(obj_name)

            if room_obj:
                # Compute bounding box in world space using evaluated depsgraph
                depsgraph = context.evaluated_depsgraph_get()
                eval_obj = room_obj.evaluated_get(depsgraph)
                try:
                    bbox_world = [room_obj.matrix_world @ Vector(corner) for corner in eval_obj.bound_box]
                except Exception:
                    bbox_world = [room_obj.matrix_world @ Vector(corner) for corner in room_obj.bound_box]

                bb_min = Vector((min(v.x for v in bbox_world), min(v.y for v in bbox_world), min(v.z for v in bbox_world)))
                bb_max = Vector((max(v.x for v in bbox_world), max(v.y for v in bbox_world), max(v.z for v in bbox_world)))
                bb_center = (bb_min + bb_max) / 2.0
                size_vec = bb_max - bb_min
                max_size = max(size_vec.x, size_vec.y, size_vec.z)

                # Move room so its floor sits at Z=0
                if room_obj.location is not None:
                    # bb_min.z is world-space min; move object up by -bb_min.z
                    room_obj.location.z -= bb_min.z

                distance = max(max_size * 2.5, 2.0)
                cam_obj.location = bb_center + Vector((distance, -distance, distance))
                cam_data.ortho_scale = 5.0
            else:
                cam_obj.location = (20, -20, 20)

        except Exception as e:
            print(f"IsometKit: failed to frame camera on room: {e}")

        # Set render resolution to 1080x1080 for iso camera
        context.scene.render.resolution_x = 1080
        context.scene.render.resolution_y = 1080
        
        # Set as active camera
        context.scene.camera = cam_obj
        
        return {'FINISHED'}
