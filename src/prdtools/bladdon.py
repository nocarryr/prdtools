bl_info = {
    'name':'PRDTools',
    'description':'Tools for Primitive Root Diffusers',
    'author':'Matthew Reid',
    'version':(0, 1),
    'blender':(2, 93),
    'location':'View3D > Properties > PRDTools',
    'category':'Add Mesh',
}

import json
import bpy
import bmesh

from .table import TableParameters, TableResult, ValidationError
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
        default=500,
    )
    well_width: bpy.props.FloatProperty(
        name='Well Width',
        description='The width/height (in cm) of each well',
        default=.0381,
        subtype='DISTANCE',
        unit='LENGTH',
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
    @classmethod
    def register(cls):
        bpy.types.Scene.prd_data = bpy.props.PointerProperty(type=cls)
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.prd_data

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
    def on_material_update(self, context):
        base_obj = self.get_base_obj()
        if base_obj is not None:
            base_obj.active_material = self.material
        if self.builder_props.instance_mode == 'OBJECT_DATA':
            for obj in self.iter_well_objs():
                obj.active_material = self.material
    material: bpy.props.PointerProperty(
        type=bpy.types.Material,
        name='Material',
        update=on_material_update,
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
        unit='LENGTH',
    )

    def get_base_obj(self):
        coll = self.base_coll
        if coll is None:
            return None
        objs = [obj for obj in coll.objects if obj.prd_data.is_base_obj]
        if not len(objs):
            return None
        assert len(objs) == 1
        return objs[0]

    def iter_well_objs(self):
        coll = self.obj_coll
        if coll is not None:
            for obj in coll.objects:
                if obj.prd_data.is_well_obj:
                    yield obj


class PrdWellProps(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        bpy.types.Object.prd_data = bpy.props.PointerProperty(type=cls)
    @classmethod
    def unregister(cls):
        del bpy.types.Object.prd_data

    is_base_obj: bpy.props.BoolProperty(
        name='Is Base Obj',
        default=False,
    )
    is_well_obj: bpy.props.BoolProperty(
        name='Is Well Obj',
        default=False,
    )
    is_bbox: bpy.props.BoolProperty(default=False)
    row: bpy.props.IntProperty(name='Row', default=-1)
    column: bpy.props.IntProperty(name='Column', default=-1)
    height: bpy.props.FloatProperty(
        name='Height',
        default=-1,
        subtype='DISTANCE',
        unit='LENGTH',
    )

class PrdBuilderProps(bpy.types.PropertyGroup):
    @classmethod
    def register(cls):
        PrdSceneProps.builder_props = bpy.props.PointerProperty(type=cls)
    @classmethod
    def unregister(cls):
        del PrdSceneProps.builder_props

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
    well_offset: bpy.props.FloatProperty(
        name='Well Offset',
        description='Amount to offset well heights',
        default=.01,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    state: bpy.props.EnumProperty(
        items=[
            ('INITIAL', 'initial', 'initial'),
            ('BUILDING', 'building', 'building'),
            ('BUILT', 'built', 'built'),
        ],
        default='INITIAL',
    )
    error: bpy.props.BoolProperty(
        name='Error',
        default=False,
    )
    error_message: bpy.props.StringProperty(
        name='Error Message',
        default='',
    )
    error_field_names: bpy.props.StringProperty(
        name='Error Field Names',
        default='',
    )
    error_fields: bpy.props.StringProperty(
        name='Error Fields',
        default='',
    )

    @classmethod
    def check(cls, value):
        return value in [opt[0] for opt in cls.instance_mode_options]

    def get_error(self):
        if not self.error:
            return None, None, None
        field_names = [s.strip(' ') for s in self.error_field_names.split(',')]
        fields = json.loads(self.error_fields)
        return self.error_message, field_names, fields

    def set_error(self, exc: ValidationError):
        self.error = True
        self.error_message = exc.msg
        self.error_field_names = ','.join(exc.field_names)
        self.error_fields = json.dumps(exc.fields)

    def clear_error(self):
        self.error = False
        self.error_message = ''
        self.error_field_names = ''
        self.error_fields = ''


class PrdDesignerProps(PrdBaseProps):
    @classmethod
    def register(cls):
        bpy.types.Scene.prd_designer_props = bpy.props.PointerProperty(type=cls)
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.prd_designer_props

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
        min=-1,
        default=-1,
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
    def get_prim_root_choices(self, context):
        ix = self.chosen_index
        num_results = len(context.scene.prd_designer_results)
        if ix < 0 or num_results == 0:
            return []
        result_props = context.scene.prd_designer_results[ix]
        roots = list(result_props.primitive_roots)
        roots = roots[:result_props.num_prim_roots]
        choices = [tuple([str(r)]*3) for r in roots]
        return choices
    prime_root: bpy.props.EnumProperty(
        name='Primitive root',
        description='A primitive root of prime_num',
        items=get_prim_root_choices,
    )

class PrdDesignerResultProps(bpy.types.PropertyGroup):
    MAX_RESULTS = 32
    MAX_PRIM_ROOTS = 32

    @classmethod
    def register(cls):
        bpy.types.Scene.prd_designer_results = bpy.props.CollectionProperty(type=cls)
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.prd_designer_results

    num_prim_roots: bpy.props.IntProperty(
        name='num_prim_roots',
        min=-1,
    )
    primitive_roots: bpy.props.IntVectorProperty(
        name='primitive_roots',
        min=0,
        size=MAX_PRIM_ROOTS,
    )
    prime_num: bpy.props.IntProperty(
        name='prime_num',
        min=0,
    )
    ncols: bpy.props.IntProperty(
        name='ncols',
        min=0,
    )
    nrows: bpy.props.IntProperty(
        name='nrows',
        min=0,
    )
    aspect_ratio: bpy.props.FloatProperty(
        name='aspect_ratio',
    )

class PrdDesignerOp(bpy.types.Operator):
    """Find design results from the given parameters"""
    bl_idname='prdutils.design'
    bl_label='Design PRD Parameters'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        return designer_props.state != 'RESULTS_BUILT'

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        if designer_props.state == 'RESET':
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
        return {'FINISHED'}

    def reset_props(self, context):
        designer_props = context.scene.prd_designer_props
        designer_props.chosen_index = -1
        context.scene.prd_designer_results.clear()

    def build_results(self, context):
        designer_props = context.scene.prd_designer_props
        designer = Designer(
            aspect_ratio_min=designer_props.aspect_ratio_min,
            aspect_ratio_max=designer_props.aspect_ratio_max,
        )
        designer_props.chosen_index = 0
        if designer_props.mode == 'COLUMNS':
            result_iter = designer.from_ncols(designer_props.ncols)
        elif designer_props.mode == 'PRIME':
            result_iter = designer.from_prime_num(designer_props.prime_num)

        for result in result_iter:
            root_iter = result.iter_primitive_roots()
            max_roots = PrdDesignerResultProps.MAX_PRIM_ROOTS
            roots = [r for r, _ in zip(root_iter, range(max_roots))]
            nroots = len(roots)
            result_props = context.scene.prd_designer_results.add()
            result_props.num_prim_roots = nroots
            result_props.primitive_roots[:nroots] = roots
            for attr in ['prime_num', 'ncols', 'nrows', 'aspect_ratio']:
                val = getattr(result, attr)
                setattr(result_props, attr, val)

    def set_chosen_index(self, context):
        designer_props = context.scene.prd_designer_props
        i = designer_props.chosen_index
        result_props = context.scene.prd_designer_results[i]
        keys = ['prime_num', 'ncols', 'nrows', 'aspect_ratio']
        for key in keys:
            val = getattr(result_props, key)
            setattr(designer_props, key, val)

class PrdDesignerBuildOp(bpy.types.Operator):
    """Build the current design"""
    bl_idname = 'prdutils.design_build'
    bl_label = 'Build'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        build_settings = context.scene.prd_data.builder_props
        if build_settings.state != 'INITIAL':
            return False
        if designer_props.state != 'RESULTS_BUILT':
            return False
        return True

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        build_settings = context.scene.prd_data.builder_props
        scene_props = context.scene.prd_data
        keys = [
            'prime_num', 'ncols', 'nrows', 'prime_root',
            'design_freq', 'well_width', 'speed_of_sound',
        ]
        for key in keys:
            val = getattr(designer_props, key)
            if key == 'prime_root':
                val = int(val)
            setattr(scene_props, key, val)
        bpy.ops.prdutils.build('INVOKE_DEFAULT')
        designer_props.state = 'RESULTS_BUILT'
        return {'FINISHED'}

class PrdDesignerResetOp(bpy.types.Operator):
    """Reset design parameters"""
    bl_idname = 'prdutils.design_reset'
    bl_label = 'Reset'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        if designer_props.state != 'RESULTS_BUILT':
            return False
        build_settings = context.scene.prd_data.builder_props
        return build_settings.state == 'INITIAL'

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        designer_props.state = 'RESET'
        bpy.ops.prdutils.design('INVOKE_DEFAULT')
        return {'FINISHED'}

class PrdDesignerNextIndex(bpy.types.Operator):
    """Show the next set of design parameters"""
    bl_idname = 'prdutils.design_next_index'
    bl_label = 'Next result index'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
        num_results = len(context.scene.prd_designer_results)
        if designer_props.state != 'RESULTS_BUILT':
            return False
        if designer_props.chosen_index >= num_results - 1:
            return False
        return True

    def execute(self, context):
        designer_props = context.scene.prd_designer_props
        designer_props.chosen_index += 1
        designer_props.state = 'SET_INDEX'
        bpy.ops.prdutils.design('INVOKE_DEFAULT')
        return {'FINISHED'}

class PrdDesignerPrevIndex(bpy.types.Operator):
    """Show the previous set of design parameters"""
    bl_idname = 'prdutils.design_prev_index'
    bl_label = 'Previous result index'

    @classmethod
    def poll(cls, context):
        designer_props = context.scene.prd_designer_props
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
    """Build an array of cubes matching the wells from a PRD table"""
    bl_idname = "prdutils.build"
    bl_label = 'Build PRD Scene'

    @classmethod
    def poll(cls, context):
        build_settings = context.scene.prd_data.builder_props
        return build_settings.state != 'BUILT'

    def execute(self, context):
        build_settings = context.scene.prd_data.builder_props
        scene_props = context.scene.prd_data
        build_settings.clear_error()

        try:
            parameters = TableParameters(
                nrows=scene_props.array_shape[0],
                ncols=scene_props.array_shape[1],
                prime_num=scene_props.prime_num,
                prime_root=scene_props.prime_root,
                design_freq=scene_props.design_freq,
                speed_of_sound=scene_props.speed_of_sound,
                well_width=scene_props.well_width * 100,
            )
            result = parameters.calculate()
        except ValidationError as exc:
            build_settings.set_error(exc)
            self.report({'WARNING'}, str(exc))
            return {'CANCELLED'}

        result.well_heights = result.well_heights * .01 + build_settings.well_offset

        build_settings.state = 'BUILDING'
        self.build_collections(context)
        self.setup_scene_props(context, result)
        self.build_objects(context, result)
        build_settings.state = 'BUILT'
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
            context.scene.collection.children.link(coll)
            clear_collection_objects(coll)

        scene_props.base_coll.hide_render = True

    def setup_scene_props(self, context, result: TableResult):
        scene_props = context.scene.prd_data
        p = result.parameters
        width = scene_props.well_width = p.well_width * .01

        scene_props.array_dimensions.x = p.total_width * .01
        scene_props.array_dimensions.y = p.total_height * .01
        scene_props.array_dimensions.z = result.well_heights.max()

    def build_objects(self, context, result: TableResult):
        scene_props = context.scene.prd_data
        build_settings = context.scene.prd_data.builder_props

        width = scene_props.well_width
        half_width = width / 2
        total_y = scene_props.array_dimensions[1]

        base_coll, obj_coll = scene_props.base_coll, scene_props.obj_coll
        base_coll.hide_viewport = False
        empty_size = width
        context.scene.cursor.location = [0, 0, 0]

        bbox = self.build_bbox(context)

        bpy.ops.mesh.primitive_cube_add(size=width)
        base_cube = context.active_object
        base_cube.name = 'Well.Base'
        base_cube.data.name = 'Well.Base'
        base_cube.prd_data.is_base_obj = True
        base_cube.active_material = scene_props.material
        move_to_collection(base_cube, base_coll)

        base_cube.location.z = half_width
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        base_cube.dimensions.z = 1
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
                    obj = base_cube.copy()
                elif instance_mode == 'OBJECT_DATA':
                    obj = base_cube.copy()
                    obj.data = obj.data.copy()
                move_to_collection(obj, obj_coll)
                obj.parent = bbox

                obj.location.x = x
                obj.location.y = y
                obj.scale.z = well_height
                obj.prd_data.row = row_idx
                obj.prd_data.column = col_idx
                obj.prd_data.height = well_height
                obj.prd_data.is_well_obj = True
                obj.name = f'Well.{row_idx:02d}.{col_idx:02d}'
                if instance_mode == 'OBJECT_DATA':
                    obj.data.name = obj.name
        if instance_mode != 'COLLECTION':
            base_coll.hide_viewport = True

    def build_bbox(self, context):
        scene_props = context.scene.prd_data

        bpy.ops.mesh.primitive_cube_add(size=1)
        bbox = context.active_object
        bbox.name = 'Prd Diffuser'
        bbox.data.name = bbox.name

        bbox_mesh = bbox.data
        bm = bmesh.new()
        bm.from_mesh(bbox_mesh)
        bmesh.ops.delete(bm, geom=bm.faces, context='FACES_ONLY')
        bm.to_mesh(bbox_mesh)
        bbox_mesh.update()

        bbox.location = [x / 2 for x in scene_props.array_dimensions]
        bbox.dimensions = scene_props.array_dimensions
        bpy.ops.object.transform_apply(location=True, properties=False)
        bbox.prd_data.is_bbox = True
        move_to_collection(bbox, scene_props.obj_coll)
        return bbox

class PrdBuilderClear(bpy.types.Operator):
    """Delete all built objects"""
    bl_idname = 'prdutils.clear'
    bl_label = 'Clear Objects'

    @classmethod
    def poll(cls, context):
        build_settings = context.scene.prd_data.builder_props
        return build_settings.state != 'INITIAL'

    def execute(self, context):
        scene_props = context.scene.prd_data
        build_settings = context.scene.prd_data.builder_props

        for attr in ['base_coll', 'obj_coll']:
            coll = getattr(scene_props, attr)
            if coll is None:
                continue
            objs = set(coll.objects.values())
            for obj in objs:
                if obj.type == 'MESH':
                    bpy.data.meshes.remove(obj.data)
                else:
                    bpy.data.objects.remove(obj)
        build_settings.state = 'INITIAL'
        return {'FINISHED'}


class PrdSceneMaterialNew(bpy.types.Operator):
    """New Material"""
    bl_idname = 'prdutils.scene_material_new'
    bl_label = 'Add Material'

    def execute(self, context):
        mat = bpy.data.materials.new('Material')
        scene_props = context.scene.prd_data
        scene_props.material = mat
        return {'FINISHED'}


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

        if build_settings.error:
            error_msg, error_field_names, error_fields = build_settings.get_error()
        else:
            error_msg = None
            error_field_names = []

        def prop_row(parent_layout, data, prop_name):
            if prop_name in error_field_names:
                row = parent_layout.row()
                row.alert = True
                row.prop(data, prop_name)
            else:
                parent_layout.prop(data, prop_name)

        box = main_box.box()
        box.label(text='Dimensions')
        prop_row(box, scene_props, 'ncols')
        prop_row(box, scene_props, 'nrows')
        box.prop(build_settings, 'well_offset')

        box = main_box.box()
        box.label(text='General')
        prop_row(box, scene_props, 'prime_num')
        prop_row(box, scene_props, 'prime_root')
        prop_row(box, scene_props, 'design_freq')
        prop_row(box, scene_props, 'speed_of_sound')
        box.prop(scene_props, 'speed_of_sound')
        box.prop(build_settings, 'instance_mode')

        box = main_box.box()
        box.label(text='Material')
        box.template_ID(scene_props, 'material', new=PrdSceneMaterialNew.bl_idname)

        box = main_box.box()
        if error_msg is not None:
            box.label(text=error_msg)
        row = box.row()
        row.operator(PrdBuilderOp.bl_idname)
        row.operator(PrdBuilderClear.bl_idname)

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

        box = main_box.box()
        box.template_ID(scene_props, 'material', new=PrdSceneMaterialNew.bl_idname)

        if designer_props.state == 'RESULTS_BUILT':
            row = box.row()
            row.operator(PrdDesignerBuildOp.bl_idname)
            row.operator(PrdBuilderClear.bl_idname)
        elif designer_props.state != 'INITIAL':
            main_box.operator(PrdDesignerOp.bl_idname, text='Find Results')


bl_classes = [
    PrdSceneProps, PrdWellProps, PrdBuilderProps, PrdBuilderOp, PrdBuilderClear,
    PrdDesignerProps, PrdDesignerResultProps, PrdDesignerOp, PrdDesignerBuildOp,
    PrdDesignerNextIndex, PrdDesignerPrevIndex, PrdDesignerResetOp, PrdSceneMaterialNew,
    PrdDesignerPanel, PrdParamsPanel,
]

def register():
    for cls in bl_classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(bl_classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
