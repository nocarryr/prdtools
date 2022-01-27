bl_info = {
    'name':'PRDTools',
    'description':'Tools for Primitive Root Diffusers',
    'author':'Matthew Reid',
    'version':(0, 1),
    'blender':(2, 93),
    'location':'View3D > Properties > PRDTools',
    'category':'Add Mesh',
}

if 'bpy' in locals():
    import importlib

    importlib.reload(bladdon)

try:
    import bpy
except ImportError:
    bpy = None

if bpy is not None:
    from . import bladdon

    def register():
        bladdon.register()
    def unregister():
        bladdon.unregister()

if __name__ == '__main__':
    register()
