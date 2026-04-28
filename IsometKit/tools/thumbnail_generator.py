import bpy
import os
import math
from mathutils import Vector
import traceback

class ISOMETKIT_OT_generate_thumbnails(bpy.types.Operator):
    """Generate Thumbnails for all Assets"""
    bl_idname = "isometkit.generate_thumbnails"
    bl_label = "Generate Thumbnails"
    bl_options = {'REGISTER'}

    clean_existing: bpy.props.BoolProperty(
        name="Clean Existing Thumbnails",
        description="Remove all existing PNG thumbnails in the thumbnails folder before generating new ones",
        default=False,
    )

    called_from_loader: bpy.props.BoolProperty(
        default=False
    )

    def execute(self, context):
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        assets_dir = os.path.join(addon_dir, "assets")
        thumb_dir = os.path.join(addon_dir, "thumbnails")
        
        if not os.path.exists(thumb_dir):
            os.makedirs(thumb_dir)

        # Optionally remove existing thumbnails first (user requested)
        if self.clean_existing:
            removed = 0
            for f in os.listdir(thumb_dir):
                if f.lower().endswith('.png'):
                    try:
                        os.remove(os.path.join(thumb_dir, f))
                        removed += 1
                    except Exception:
                        pass
            print(f"IsometKit: removed {removed} existing thumbnails from {thumb_dir}")
            
        blend_files = [f for f in os.listdir(assets_dir) if f.endswith(".blend")]
        if not blend_files:
            self.report({'WARNING'}, "No .blend files found in assets/")
            return {'CANCELLED'}

        # Save current file to return to it? Or usually we do this in the current file.
        # Ideally, we should open a fresh factory file or use the current one.
        # We will use the current one but isolate the render.
        
        # 1. Setup Render Engine - Save original settings first
        scene = context.scene
        orig_engine = scene.render.engine
        orig_res_x = scene.render.resolution_x
        orig_res_y = scene.render.resolution_y
        orig_film_transp = scene.render.film_transparent
        orig_filepath = scene.render.filepath

        shading = scene.display.shading
        orig_light = shading.light
        orig_color_type = shading.color_type
        orig_show_shadows = shading.show_shadows

        # We'll use Workbench for speed and "Texture" look
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = 256
        scene.render.resolution_y = 256
        scene.render.film_transparent = True
        
        # Configure Workbench shading for Textures
        shading.light = 'FLAT' # Use Flat lighting to avoid shading artifacts on icons
        shading.color_type = 'TEXTURE'
        shading.show_shadows = False # Keep icons clean
        
        # 2. Setup Camera & Lights (Temporary Collection)
        # Save the original active camera so we can restore it later
        prev_camera = scene.camera

        temp_coll = bpy.data.collections.new("IsometKit_Thumb_Gen")
        context.scene.collection.children.link(temp_coll)
        created_objects = []
        created_cameras = []
        created_lights = []

        # Camera
        cam_data = bpy.data.cameras.new("ThumbCam")
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = 5.0 # Adjusted per object later?
        cam_obj = bpy.data.objects.new("ThumbCam", cam_data)
        temp_coll.objects.link(cam_obj)
        created_objects.append(cam_obj)
        created_cameras.append(cam_data)
        # Iso Angle
        cam_obj.location = (10, -10, 10)
        cam_obj.rotation_euler = (math.radians(54.736), 0, math.radians(45))
        # set scene camera temporarily
        scene.camera = cam_obj

        # Light
        light_data = bpy.data.lights.new("ThumbLight", 'SUN')
        light_data.energy = 5.0
        light_obj = bpy.data.objects.new("ThumbLight", light_data)
        temp_coll.objects.link(light_obj)
        created_objects.append(light_obj)
        created_lights.append(light_data)
        light_obj.rotation_euler = (0.5, 0, 0.8)
        
        # Loop Assets
        processed_count = 0
        
        for fname in blend_files:
            fpath = os.path.join(assets_dir, fname)
            base_name = os.path.splitext(fname)[0]
            
            # Get object names first
            img_names = []
            with bpy.data.libraries.load(fpath) as (data_from, data_to):
                img_names = data_from.objects
            
            for obj_name in img_names:
                # Append Object
                try:
                    # Prepare thumbnail path
                    thumb_name = f"{base_name}_{obj_name}.png"
                    out_path = os.path.join(thumb_dir, thumb_name)

                    # If thumbnail already exists and looks valid, skip
                    if os.path.exists(out_path):
                        try:
                            size = os.path.getsize(out_path)
                        except Exception:
                            size = 0
                        # Treat very small files (<500 bytes) as invalid and regenerate
                        # Valid PNGs are usually larger. Simple check.
                        if size > 500:
                            processed_count += 1
                            continue
                        else:
                            print(f"IsometKit: existing thumbnail {out_path} is too small ({size} bytes); regenerating")

                    # Skip preview fallback and always render for best quality and texture support

                    with bpy.data.libraries.load(fpath, link=False) as (data_from, data_to):
                        data_to.objects = [obj_name]
                    
                    obj = data_to.objects[0]
                    if obj:
                        temp_coll.objects.link(obj)

                        # Workbench 'TEXTURE' mode requires an active texture node in the material
                        # We'll try to find an Image Texture node and set it as active
                        for mat_slot in obj.material_slots:
                            mat = mat_slot.material
                            if mat and mat.use_nodes:
                                nodes = mat.node_tree.nodes
                                # Try to find first image texture node
                                tex_node = None
                                for n in nodes:
                                    if n.type == 'TEX_IMAGE':
                                        tex_node = n
                                        break
                                if tex_node:
                                    nodes.active = tex_node

                        # Prepare and center object for rendering
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        context.view_layer.objects.active = obj

                        # Ensure depsgraph evaluation for accurate bounding box (modifiers applied)
                        depsgraph = context.evaluated_depsgraph_get()
                        eval_obj = obj.evaluated_get(depsgraph)

                        # Compute world-space bounding box corners
                        try:
                            bbox_world = [obj.matrix_world @ Vector(corner) for corner in eval_obj.bound_box]
                        except Exception:
                            # Fallback to local bound box
                            bbox_world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

                        bb_min = Vector((min(v.x for v in bbox_world), min(v.y for v in bbox_world), min(v.z for v in bbox_world)))
                        bb_max = Vector((max(v.x for v in bbox_world), max(v.y for v in bbox_world), max(v.z for v in bbox_world)))
                        bb_center = (bb_min + bb_max) / 2.0
                        size_vec = bb_max - bb_min
                        max_size = max(size_vec.x, size_vec.y, size_vec.z)

                        # Move object so its center is at origin for consistent renders
                        # We'll offset the object temporarily by moving its location so center -> origin
                        offset = bb_center
                        obj.location -= offset

                        # Compute camera framing: use camera rotation to derive forward direction
                        cam_rot = cam_obj.rotation_euler.to_matrix()
                        forward = cam_rot @ Vector((0.0, 0.0, -1.0))

                        # Distance doesn't affect orthographic scale, but keep camera positioned reasonably
                        distance = max(max_size * 2.5, 2.0)
                        cam_obj.location = Vector((0.0, 0.0, 0.0)) - forward * distance

                        # Set ortho scale based on object size with padding
                        pad = 1.5
                        cam_data.ortho_scale = max(1.0, max_size * pad)

                        # Using track_to constraint is safer: create temporary empty as target
                        target = bpy.data.objects.new("IsometKit_Temp_Target", None)
                        temp_coll.objects.link(target)
                        target.location = Vector((0.0, 0.0, 0.0))
                        tr = cam_obj.constraints.new(type='TRACK_TO')
                        tr.target = target
                        tr.track_axis = 'TRACK_NEGATIVE_Z'
                        tr.up_axis = 'UP_Y'

                        # Render
                        try:
                            scene.render.filepath = out_path
                            bpy.ops.render.render(write_still=True)
                        except Exception as e:
                            print(f"IsometKit: failed rendering thumbnail for {obj_name}: {e}")

                        # Cleanup temporary constraint and target
                        cam_obj.constraints.remove(tr)
                        bpy.data.objects.remove(target, do_unlink=True)

                        # Revert object offset and remove
                        obj.location += offset
                        bpy.data.objects.remove(obj, do_unlink=True)
                        processed_count += 1
                        
                except Exception as e:
                    print(f"Failed to render {obj_name}: {e}")
        
        # Cleanup: restore previous camera and remove temporary objects/collection
        try:
            # Restore previous active camera
            try:
                scene.camera = prev_camera
            except Exception:
                pass

            # Restore original scene settings
            try:
                scene.render.engine = orig_engine
                scene.render.resolution_x = orig_res_x
                scene.render.resolution_y = orig_res_y
                scene.render.film_transparent = orig_film_transp
                scene.render.filepath = orig_filepath

                shading = scene.display.shading
                shading.light = orig_light
                shading.color_type = orig_color_type
                shading.show_shadows = orig_show_shadows
            except Exception as e:
                print(f"IsometKit: failed to restore scene settings: {e}")

            # Remove any remaining temporary objects we created
            for o in created_objects:
                try:
                    # unlink from all collections
                    for coll in list(o.users_collection):
                        try:
                            coll.objects.unlink(o)
                        except Exception:
                            pass
                    # remove object
                    if o.name in bpy.data.objects:
                        bpy.data.objects.remove(o, do_unlink=True)
                except Exception:
                    pass

            # Remove camera data blocks
            for cd in created_cameras:
                try:
                    if cd.name in bpy.data.cameras:
                        bpy.data.cameras.remove(cd)
                except Exception:
                    pass

            # Remove light data blocks
            for ld in created_lights:
                try:
                    if ld.name in bpy.data.lights:
                        bpy.data.lights.remove(ld)
                except Exception:
                    pass

            # Remove temporary collection if still present
            try:
                if temp_coll.name in bpy.data.collections:
                    bpy.data.collections.remove(temp_coll)
            except Exception:
                pass
        except Exception as e:
            print(f"IsometKit: cleanup after thumbnail generation failed: {e}")

        self.report({'INFO'}, f"Generated {processed_count} thumbnails")

        # Trigger refresh of loader to show new icons, if not called from loader
        if not getattr(self, 'called_from_loader', False):
            if "isometkit.refresh_assets" in dir(bpy.ops.isometkit):
                bpy.ops.isometkit.refresh_assets()

        return {'FINISHED'}
