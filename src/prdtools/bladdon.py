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
from .designer import Designer
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


class PrdBaseProps(bpy.types.PropertyGroup):
    design_freq: bpy.props.IntProperty(
        name='Design Frequency',
        description='The lowest frequency (in Hz) the diffusor is designed for',
    )
    well_width: bpy.props.FloatProperty(
        name='Well Width',
        description='The width/height (in cm) of each well',
        default=3.81,
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

class PrdSceneProps(PrdBaseProps):
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

class PrdDesignerProps(PrdBaseProps):
    mode: bpy.props.EnumProperty(
        items=[
            ('COLUMNS', 'Columns', 'Design from number of columns'),
            ('PRIME', 'Prime', 'Design from a prime number'),
        ],
        name='Mode',
        description='Designer Mode',
        default='COLUMNS',
    )
    state: bpy.props.EnumProperty(
        items=[
            ('INITIAL', 'initial', 'initial state'),
            ('RESULTS_BUILT', 'results_built', 'results built'),
            ('SET_INDEX', 'set_index', 'set designer props to chosen index'),
            ('BUILD', 'build', 'build'),
            ('RESET', 'reset', 'reset'),
        ],
        default='INITIAL',
        name='State',
    )
    chosen_index: bpy.props.IntProperty(
        name='chosen_index',
        min=0,
    )
    ncols: bpy.props.IntProperty(
        name='Columns',
        description='Number of columns',
    )
    nrows: bpy.props.IntProperty(
        name='Rows',
        description='Number of rows',
    )
    aspect_ratio: bpy.props.FloatProperty(
        name='Aspect Ratio',
    )
    aspect_ratio_min: bpy.props.FloatProperty(
        name='Minimum Aspect',
        description='Minimum aspect ratio',
        default=0.4,
    )
    aspect_ratio_max: bpy.props.FloatProperty(
        name='Maximum Aspect',
        description='Maximum aspect ratio',
        default=2.5,
    )


class PrdDesignerResultProps(bpy.types.PropertyGroup):
    MAX_RESULTS = 32
    MAX_PRIM_ROOTS = 32
    num_results: bpy.props.IntProperty(
        name='num_results',
        default=0,
    )
    primitive_roots: bpy.props.IntVectorProperty(   # <-- not indexed with other props
        name='primitive_roots',
        min=0,
        size=MAX_PRIM_ROOTS,
    )
    prime_num: bpy.props.IntVectorProperty(
        name='prime_num',
        min=0,
        size=MAX_RESULTS,
    )
    ncols: bpy.props.IntVectorProperty(
        name='ncols',
        min=0,
        size=MAX_RESULTS,
    )
    nrows: bpy.props.IntVectorProperty(
        name='nrows',
        min=0,
        size=MAX_RESULTS,
    )
    aspect_ratio: bpy.props.FloatVectorProperty(
        name='aspect_ratio',
        size=MAX_RESULTS,
    )
    def reset(self):
        self.num_results = 0
        self.primitive_roots = [0] * self.MAX_PRIM_ROOTS
        self.prime_num = [0] * self.MAX_RESULTS
        self.ncols = [0] * self.MAX_RESULTS
        self.nrows = [0] * self.MAX_RESULTS
        self.aspect_ratio = [0] * self.MAX_RESULTS

class PrdDesignerOp(bpy.types.Operator):
    bl_idname='prdutils.design'
    bl_label='Design PRD Parameters'

    action: bpy.props.EnumProperty(
        items=[
            ('NORMAL', 'normal', 'normal'),
            ('RESET', 'reset', 'reset'),
        ],
        default='NORMAL',
    )

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        if self.action == 'RESET':
            self.reset_props(context)
            designer_props.state = 'INITIAL'
        elif designer_props.state == 'INITIAL':
            self.build_results(context)
            designer_props.state = 'RESULTS_BUILT'
            designer_props.chosen_index = 0
            self.set_chosen_index(context)
        elif designer_props.state == 'SET_INDEX':
            self.set_chosen_index(context)
            designer_props.state = 'RESULTS_BUILT'
        elif designer_props.state in ['RESULTS_BUILT', 'BUILD']:
            self.build(context)
            designer_props.state = 'RESULTS_BUILT'
        return {'FINISHED'}

    def reset_props(self, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        designer_props.chosen_index = 0
        result_props.reset()

    def build_results(self, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        designer = Designer(
            aspect_ratio_min=designer_props.aspect_ratio_min,
            aspect_ratio_max=designer_props.aspect_ratio_max,
        )
        designer_props.chosen_index = 0
        result_props.reset()
        if designer_props.mode == 'COLUMNS':
            result_iter = designer.from_ncols(designer_props.ncols)
        elif designer_props.mode == 'PRIME':
            result_iter = designer.from_prime_num(designer_props.prime_num)

        for result in result_iter:
            i = result_props.num_results
            if i == 0 and designer_props.prime_root == 0:
                for j, root in enumerate(result.iter_primitive_roots()):
                    if j >= PrdDesignerResultProps.MAX_PRIM_ROOTS:
                        break
                    result_props.primitive_roots[j] = root
                    if j == 0:
                        designer_props.prime_root = root

            result_props.prime_num[i] = result.prime_num
            result_props.ncols[i] = result.ncols
            result_props.nrows[i] = result.nrows
            result_props.aspect_ratio[i] = result.aspect_ratio
            result_props.num_results += 1
        self.report({'INFO'}, f'{result_props.num_results=}')

    def set_chosen_index(self, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        i = designer_props.chosen_index
        assert 0 <= i < result_props.num_results
        keys = ['prime_num', 'ncols', 'nrows', 'aspect_ratio']
        for key in keys:
            val = getattr(result_props, key)[i]
            setattr(designer_props, key, val)

    def build(self, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        build_settings = context.scene.prd_data.builder_props
        scene_props = context.scene.prd_data
        keys = [
            'prime_num', 'ncols', 'nrows', 'prime_root',
            'design_freq', 'well_width', 'speed_of_sound',
        ]
        for key in keys:
            val = getattr(designer_props, key)
            setattr(scene_props, key, val)
        bpy.ops.prdutils.build('INVOKE_DEFAULT')

class PrdDesignerResetOp(bpy.types.Operator):
    bl_idname = 'prdutils.design_reset'
    bl_label = 'Reset'

    def execute(self, context):
        bpy.ops.prdutils.design('EXEC_DEFAULT', action='RESET')
        return {'FINISHED'}

class PrdDesignerNextIndex(bpy.types.Operator):
    bl_idname = 'prdutils.design_next_index'
    bl_label = 'Next result index'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        if designer_props.state != 'RESULTS_BUILT':
            return False
        if designer_props.chosen_index >= result_props.num_results - 1:
            return False
        return True

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        designer_props.chosen_index += 1
        designer_props.state = 'SET_INDEX'
        bpy.ops.prdutils.design('INVOKE_DEFAULT')
        return {'FINISHED'}

class PrdDesignerPrevIndex(bpy.types.Operator):
    bl_idname = 'prdutils.design_prev_index'
    bl_label = 'Previous result index'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        if designer_props.state != 'RESULTS_BUILT':
            return False
        if designer_props.chosen_index <= 0:
            return False
        return True

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        designer_props.chosen_index -= 1
        designer_props.state = 'SET_INDEX'
        bpy.ops.prdutils.design('INVOKE_DEFAULT')
        return {'FINISHED'}

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
    bl_options = {'DEFAULT_CLOSED'}

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

class PrdDesignerPanel(bpy.types.Panel):
    bl_idname = 'VIEW_3D_PT_prd_designer'
    bl_label = 'PRD Designer'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene_props = context.scene.prd_data
        build_settings = scene_props.builder_props
        designer_props = context.scene.prd_designer_props
        result_props = context.scene.prd_designer_results
        main_box = layout.box()
        main_box.label(text='PRD Designer')

        box = main_box.box()

        if designer_props.state == 'INITIAL':
            grid = box.grid_flow(
                row_major=True, columns=2, even_columns=True, align=False,
            )
            grid.label(text='Mode')
            grid.prop(designer_props, 'mode', text='')
            if designer_props.mode == 'COLUMNS':
                grid.label(text='Num Colums')
                grid.prop(designer_props, 'ncols', text='')
            elif designer_props.mode == 'PRIME':
                grid.label(text='Prime number')
                grid.prop(designer_props, 'prime_num', text='')

            grid.label(text='Aspect Min')
            grid.prop(designer_props, 'aspect_ratio_min', text='')
            grid.label(text='Aspect Max')
            grid.prop(designer_props, 'aspect_ratio_max', text='')
            box.operator(PrdDesignerOp.bl_idname, text='Find Results')

        elif designer_props.state == 'RESULTS_BUILT':
            row = box.row()
            row.operator(PrdDesignerPrevIndex.bl_idname, icon='TRIA_LEFT')
            row.operator(PrdDesignerNextIndex.bl_idname, icon='TRIA_RIGHT')
            box.operator(PrdDesignerResetOp.bl_idname)

        if designer_props.state != 'INITIAL':
            box = main_box.box()
            grid = box.grid_flow(
                row_major=True, columns=2, even_columns=True, align=False,
            )
            grid.label(text='Columns')
            grid.prop(designer_props, 'ncols', text='')
            grid.label(text='Rows')
            grid.prop(designer_props, 'nrows', text='')
            grid.label(text='Aspect Ratio')
            grid.prop(designer_props, 'aspect_ratio', text='')
            grid.enabled = False

            grid = box.grid_flow(
                row_major=True, columns=2, even_columns=True, align=False,
            )
            grid.label(text='Primitive Root')
            grid.prop(designer_props, 'prime_root', text='')
            grid.label(text='Design Frequency')
            grid.prop(designer_props, 'design_freq', text='')
            grid.label(text='Speed of Sound')
            grid.prop(designer_props, 'speed_of_sound', text='')
            grid.label(text='Well width')
            grid.prop(designer_props, 'well_width', text='')
            grid.label(text='Well Offset')
            grid.prop(build_settings, 'well_offset', text='')
            grid.label(text='Instance Mode')
            grid.prop(build_settings, 'instance_mode', text='')

        if designer_props.state == 'RESULTS_BUILT':
            main_box.operator(PrdDesignerOp.bl_idname, text='Build')
        elif designer_props.state != 'INITIAL':
            main_box.operator(PrdDesignerOp.bl_idname, text='Find Results')


bl_classes = [
    PrdSceneProps, PrdWellProps, PrdBuilderProps, PrdBuilderOp,
    PrdDesignerProps, PrdDesignerResultProps, PrdDesignerOp,
    PrdDesignerNextIndex, PrdDesignerPrevIndex, PrdDesignerResetOp,
    PrdDesignerPanel, PrdParamsPanel,
]

def register():
    for cls in bl_classes:
        bpy.utils.register_class(cls)
    PrdSceneProps.builder_props = bpy.props.PointerProperty(type=PrdBuilderProps)
    bpy.types.Scene.prd_data = bpy.props.PointerProperty(type=PrdSceneProps)
    bpy.types.Scene.prd_designer_props = bpy.props.PointerProperty(type=PrdDesignerProps)
    bpy.types.Scene.prd_designer_results = bpy.props.PointerProperty(type=PrdDesignerResultProps)
    bpy.types.Object.prd_data = bpy.props.PointerProperty(type=PrdWellProps)

def unregister():
    del PrdSceneProps.builder_props
    del bpy.types.Object.prd_data
    del bpy.types.Scene.prd_designer_results
    del bpy.types.Scene.prd_designer_props
    del bpy.types.Scene.prd_data
    for cls in reversed(bl_classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
