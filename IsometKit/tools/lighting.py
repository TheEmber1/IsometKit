import bpy
import math


def _get_or_create_collection(name, scene):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        scene.collection.children.link(col)
    return col


class ISOMETKIT_OT_setup_lighting(bpy.types.Operator):
    """Generate a simple lighting setup for IsometKit

    Creates dedicated collections and adds an area light and a sun light.
    """
    bl_idname = "isometkit.setup_lighting"
    bl_label = "Generate Simple Light Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # Create or get collections for addon parts
        objs_col = _get_or_create_collection("IsometKit_Objects", scene)
        setup_col = _get_or_create_collection("IsometKit_Setup", scene)
        light_col = _get_or_create_collection("IsometKit_Lighting", scene)

        # Area Light: 3m high, size 2m, power 10
        area_name = "IsometKit_Area"
        if area_name in bpy.data.objects:
            area_obj = bpy.data.objects[area_name]
            area_data = area_obj.data
        else:
            area_data = bpy.data.lights.new(name=area_name, type='AREA')
            area_obj = bpy.data.objects.new(name=area_name, object_data=area_data)
            # link into lighting collection
            light_col.objects.link(area_obj)

        area_data.energy = 10.0
        # area_size attribute: use 'size' for square area
        try:
            area_data.size = 2.0
        except Exception:
            pass
        area_obj.location = (0.0, 0.0, 3.0)
        area_obj.rotation_euler = (0.0, 0.0, 0.0)

        # Sun Light: small angle
        sun_name = "IsometKit_Sun"
        if sun_name in bpy.data.objects:
            sun_obj = bpy.data.objects[sun_name]
            sun_data = sun_obj.data
        else:
            sun_data = bpy.data.lights.new(name=sun_name, type='SUN')
            sun_obj = bpy.data.objects.new(name=sun_name, object_data=sun_data)
            light_col.objects.link(sun_obj)

        sun_data.energy = 2.0
        # small angular tilt
        sun_obj.location = (5.0, -5.0, 8.0)
        sun_obj.rotation_euler = (math.radians(-15.0), 0.0, math.radians(15.0))

        # Optionally parent setup objects under the setup collection's empty for cleanup
        # Create a named empty in the setup collection to group setup items
        setup_empty_name = "IsometKit_Setup_Root"
        setup_root = bpy.data.objects.get(setup_empty_name)
        if setup_root is None:
            setup_root = bpy.data.objects.new(setup_empty_name, None)
            setup_col.objects.link(setup_root)

        # Parent lights to setup root for tidy hierarchy (if not already parented)
        try:
            area_obj.parent = setup_root
            sun_obj.parent = setup_root
        except Exception:
            pass

        # Set world color and strength
        try:
            world = scene.world
            if world is None:
                world = bpy.data.worlds.new("IsometKit_World")
                scene.world = world

            # Set simple color (non-node fallback)
            try:
                world.color = (0.5, 0.5, 0.5)
            except Exception:
                pass

            # Ensure nodes are enabled so we can set background strength
            if not world.use_nodes:
                world.use_nodes = True

            try:
                nodes = world.node_tree.nodes
                links = world.node_tree.links
                # Find or create Background node
                bg = None
                for n in nodes:
                    if n.type == 'BACKGROUND':
                        bg = n
                        break
                if bg is None:
                    bg = nodes.new(type='ShaderNodeBackground')
                bg.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1.0)
                bg.inputs['Strength'].default_value = 1.0

                # Find or create World Output node
                wo = None
                for n in nodes:
                    if n.type == 'OUTPUT_WORLD':
                        wo = n
                        break
                if wo is None:
                    wo = nodes.new(type='ShaderNodeOutputWorld')

                # Ensure a link from bg -> wo
                try:
                    links.new(bg.outputs['Background'], wo.inputs['Surface'])
                except Exception:
                    # If link exists or fails, try to remove existing Surface links then recreate
                    try:
                        for l in list(links):
                            if l.to_node == wo and l.to_socket.name == 'Surface':
                                links.remove(l)
                    except Exception:
                        pass
                    try:
                        links.new(bg.outputs['Background'], wo.inputs['Surface'])
                    except Exception:
                        pass
            except Exception as e:
                print(f"IsometKit: failed to configure world nodes: {e}")
        except Exception as e:
            print(f"IsometKit: failed to set world: {e}")

        self.report({'INFO'}, "IsometKit: simple lighting setup created")
        return {'FINISHED'}
