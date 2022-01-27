bl_info = {
    'name':'PRDTools',
    'description':'Tools for Primitive Root Diffusers',
    'author':'Matthew Reid',
    'version':(0, 1),
    'blender':(2, 93),
    'location':'View3D > Properties > PRDTools',
    'category':'Add Mesh',
}

import bpy

from .table import TableParameters, TableResult
from .math import SPEED_OF_SOUND


def move_to_collection(obj, coll):
    to_remove = []
    if coll not in obj.users_collection:
        coll.objects.link(obj)
    for oth_coll in obj.users_collection:
        if oth_coll is coll:
            continue
        to_remove.append(oth_coll)
    for oth_coll in to_remove:
        oth_coll.objects.unlink(obj)

def clear_collection_objects(coll):
    to_remove = list(coll.objects.values())
    for obj in to_remove:
        coll.objects.unlink(obj)



class PrdSceneProps(bpy.types.PropertyGroup):
    base_coll_name: bpy.props.StringProperty(
        name='Base Collection Name',
        description='Base Collection Name',
        default='PrdBase',
    )
    obj_coll_name: bpy.props.StringProperty(
        name='Object Collection Name',
        description='Object Collection Name',
        default='PrdObjects',
    )
    base_coll: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name='Base Collection',
        description='Collection to place the base mesh in',
    )
    obj_coll: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name='Object Collection',
        description='Collection to store all instanced meshes',
    )
    design_freq: bpy.props.IntProperty(
        name='Design Frequency',
        description='The lowest frequency (in Hz) the diffusor is designed for',
    )
    well_width: bpy.props.IntProperty(
        name='Well Width',
        description='The width/height (in cm) of each well',
    )
    speed_of_sound: bpy.props.IntProperty(
        name='Speed of Sound',
        description='Speed of sound in meters per second',
        default=SPEED_OF_SOUND,
    )
    prime_num: bpy.props.IntProperty(
        name='Prime Number',
        description='The basis prime number where prime_num - 1 == ncols * nrows'
    )
    prime_root: bpy.props.IntProperty(
        name='Primitive root',
        description='A primitive root of prime_num',
    )
    def _get_ncols(self): return self.array_shape[1]
    def _set_ncols(self, value):
        if value != self.array_shape[1]:
            self.array_shape[1] = value
    ncols: bpy.props.IntProperty(
        name='Columns',
        description='Number of columns',
        get=_get_ncols, set=_set_ncols,
    )
    def _get_nrows(self): return self.array_shape[0]
    def _set_nrows(self, value):
        if value != self.array_shape[0]:
            self.array_shape[0] = value
    nrows: bpy.props.IntProperty(
        name='Rows',
        description='Number of rows',
        get=_get_nrows, set=_set_nrows,
    )
    array_shape: bpy.props.IntVectorProperty(
        name='Array Shape',
        description='The number of columns(x) and rows(y) of the well array',
        subtype='XYZ_LENGTH',
    )
    array_dimensions: bpy.props.FloatVectorProperty(
        name='Array Dimensions',
        description='Overall Dimensions (in scene space) of the well array',
        subtype='XYZ_LENGTH',
    )


class PrdWellProps(bpy.types.PropertyGroup):
    row: bpy.props.IntProperty(default=-1)
    column: bpy.props.IntProperty(default=-1)
    height: bpy.props.IntProperty(default=-1)

class PrdBuilderProps(bpy.types.PropertyGroup):
    instance_mode_options = [
        ('COLLECTION', 'Collection', 'Create wells as collection instances'),
        ('OBJECT', 'Object', 'Duplicate each well using the same data (mesh)'),
        ('OBJECT_DATA', 'Object/Data', 'Duplicate each well and its data (mesh)'),
    ]
    instance_mode: bpy.props.EnumProperty(
        items=instance_mode_options,
        name='Instance Mode',
        description='Method of creating the individual well objects',
        default='COLLECTION',
    )
    well_offset: bpy.props.IntProperty(
        name='Well Offset',
        description='Amount to offset well heights',
        default=1,
    )
    @classmethod
    def check(cls, value):
        return value in [opt[0] for opt in cls.instance_mode_options]

class PrdBuilderOp(bpy.types.Operator):
    """Build an array of cubes matching the wells from a PRD table
    """
    bl_idname = "prdutils.build"
    bl_label = 'Build PRD Scene'

    def execute(self, context):
        build_settings = context.scene.prd_data.builder_props
        scene_props = context.scene.prd_data

        parameters = TableParameters(
            nrows=scene_props.array_shape[0],
            ncols=scene_props.array_shape[1],
            prime_num=scene_props.prime_num,
            prime_root=scene_props.prime_root,
            design_freq=scene_props.design_freq,
            speed_of_sound=scene_props.speed_of_sound,
        )
        result = parameters.calculate()
        result.well_heights += build_settings.well_offset

        self.build_collections(context)
        self.setup_scene_props(context, result)
        self.build_objects(context, result)
        return {'FINISHED'}

    def build_collections(self, context):
        scene_props = context.scene.prd_data

        for attr in ['base_coll', 'obj_coll']:
            coll = getattr(scene_props, attr)
            if coll is not None:
                continue
            coll_name = getattr(scene_props, f'{attr}_name')
            bpy.ops.collection.create(name=coll_name)
            coll = bpy.data.collections[-1]
            setattr(scene_props, attr, coll)
            clear_collection_objects(coll)
            context.scene.collection.children.link(coll)

        scene_props.base_coll.hide_render = True

    def setup_scene_props(self, context, result: TableResult):
        scene_props = context.scene.prd_data
        p = result.parameters
        width = scene_props.well_width = p.well_width * .01

        scene_props.array_dimensions.x = p.total_width * .01
        scene_props.array_dimensions.y = p.total_height * .01
        scene_props.array_dimensions.z = result.well_heights.max() * .01

    def build_objects(self, context, result: TableResult):
        scene_props = context.scene.prd_data
        build_settings = context.scene.prd_data.builder_props

        width = scene_props.well_width
        half_width = width / 2
        total_y = scene_props.array_dimensions[1]

        base_coll, obj_coll = scene_props.base_coll, scene_props.obj_coll
        empty_size = width

        bpy.ops.mesh.primitive_cube_add(size=width)
        base_cube = context.active_object
        move_to_collection(base_cube, base_coll)

        context.scene.cursor.location = [0, 0, 0]
        base_cube.location.z = half_width
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        base_cube.dimensions.z = .01
        bpy.ops.object.transform_apply(location=False, properties=False)

        instance_mode = build_settings.instance_mode

        for col_idx in range(result.well_heights.shape[1]):
            x = width * col_idx + half_width
            for row_idx in range(result.well_heights.shape[0]):
                well_height = result.well_heights[row_idx,col_idx]
                y = width * -row_idx - half_width + total_y
                if instance_mode == 'COLLECTION':
                    bpy.ops.object.collection_instance_add(collection=base_coll.name)
                    obj = context.active_object
                    obj.empty_display_size = empty_size
                elif instance_mode == 'OBJECT':
                    bpy.ops.object.duplicate(linked=True)
                    obj = context.active_object
                elif instance_mode == 'OBJECT_DATA':
                    bpy.ops.object.duplicate(linked=False)
                    obj = context.active_object
                move_to_collection(obj, obj_coll)

                obj.location.x = x
                obj.location.y = y
                obj.scale.z = well_height
                obj.prd_data.row = row_idx
                obj.prd_data.column = col_idx
                obj.prd_data.height = well_height
                obj.name = f'Well.{row_idx:02d}.{col_idx:02d}'

class PrdParamsPanel(bpy.types.Panel):
    bl_idname = 'VIEW_3D_PT_prd_params'
    bl_label = 'PRD Parameters'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene_props = context.scene.prd_data
        build_settings = scene_props.builder_props
        main_box = layout.box()
        main_box.label(text='PRD Parameters')

        box = main_box.box()
        box.label(text='Dimensions')
        box.prop(scene_props, 'ncols')
        box.prop(scene_props, 'nrows')
        box.prop(build_settings, 'well_offset')

        box = main_box.box()
        box.label(text='General')
        box.prop(scene_props, 'prime_num')
        box.prop(scene_props, 'prime_root')
        box.prop(scene_props, 'design_freq')
        box.prop(scene_props, 'speed_of_sound')
        box.prop(build_settings, 'instance_mode')

        box = main_box.box()
        box.operator('prdutils.build')


bl_classes = [
    PrdSceneProps, PrdWellProps, PrdBuilderProps, PrdBuilderOp, PrdParamsPanel,
]

def register():
    for cls in bl_classes:
        bpy.utils.register_class(cls)
    PrdSceneProps.builder_props = bpy.props.PointerProperty(type=PrdBuilderProps)
    bpy.types.Scene.prd_data = bpy.props.PointerProperty(type=PrdSceneProps)
    bpy.types.Object.prd_data = bpy.props.PointerProperty(type=PrdWellProps)

def unregister():
    del PrdSceneProps.builder_props
    del bpy.types.Object.prd_data
    del bpy.types.Scene.prd_data
    for cls in reversed(bl_classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
