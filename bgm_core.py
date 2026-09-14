import bpy, os, math
from mathutils import Vector
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
from gallery_scene_creator import (clear_scene, enable_gltf_addon, import_glb_file,
    apply_clay_material_to_meshes, apply_rotation_to_car, auto_ground_car, create_grid_floor, setup_lighting)

def get_car_info(car_id):
    csv_path = os.path.join(SCRIPT_DIR, 'cars.csv')
    if not os.path.exists(csv_path): return None
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            for row in __import__('csv').DictReader(f):
                if row.get('id') == str(car_id): return row
    except Exception: pass
    return None

def scale_car_to_dimensions(obj, car_info):
    """車の実寸法データ(mm)に合わせてスケールを適用する (Short2と同様)"""
    length_mm = float(car_info.get('length', 0))
    width_mm = float(car_info.get('width', 0))
    height_mm = float(car_info.get('height', 0))
    
    if length_mm <= 0 or width_mm <= 0 or height_mm <= 0:
        print("  警告: 寸法データが不完全のためスケールを適用しません")
        return
    
    # 現在のサイズを取得（Blender単位: メートル）
    current_x = abs(obj.dimensions.x)
    current_y = abs(obj.dimensions.y)
    current_z = abs(obj.dimensions.z)
    
    if current_x <= 0 or current_y <= 0 or current_z <= 0:
        print("  警告: 現在の寸法が取得できません")
        return
    
    # mm -> メートル変換
    target_length_m = length_mm / 1000.0
    target_width_m = width_mm / 1000.0
    target_height_m = height_mm / 1000.0
    
    scale_x = target_width_m / current_x
    scale_y = target_length_m / current_y
    scale_z = target_height_m / current_z
    
    obj.scale = (scale_x, scale_y, scale_z)
    print(f"  スケール適用: ({scale_x:.3f}, {scale_y:.3f}, {scale_z:.3f}) -> 目標寸法 L={length_mm}mm W={width_mm}mm H={height_mm}mm")

def _bold_font():
    p = r'C:\Windows\Fonts\mebold.ttc'
    if os.path.exists(p):
        for fd in bpy.data.fonts:
            if (fd.name or '').lower().startswith('mebold'): return fd
        try: return bpy.data.fonts.load(p)
        except RuntimeError: pass
    return None

def _emission_mat(name, color_rgba, strength):
    if name in bpy.data.materials:
        m = bpy.data.materials[name]
        n = next((x for x in m.node_tree.nodes if getattr(x,'type','')=='EMISSION'), None)
        if n is not None: return m, n
    m = bpy.data.materials.new(name=name); m.use_nodes = True
    nd, lk = m.node_tree.nodes, m.node_tree.links
    for o in list(nd): nd.remove(o)
    out = nd.new(type='ShaderNodeOutputMaterial')
    emi = nd.new(type='ShaderNodeEmission')
    emi.inputs['Color'].default_value = color_rgba
    emi.inputs['Strength'].default_value = strength
    lk.new(emi.outputs[0], out.inputs['Surface'])
    return m, emi

def setup_black_world():
    scene = bpy.context.scene
    world = bpy.data.worlds.new(name='BlackWorld'); world.use_nodes = True
    nd, lk = world.node_tree.nodes, world.node_tree.links
    for o in list(nd): nd.remove(o)
    bg = nd.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0,0,0,1)
    bg.inputs['Strength'].default_value = 0.0
    out = nd.new('ShaderNodeOutputWorld')
    lk.new(bg.outputs['Background'], out.inputs['Surface'])
    scene.world = world

def create_name_label(car_obj, car_name):
    """車名の3Dテキストを床面・車の前方に配置 (車固定なので親設定なし)"""
    from mathutils import Matrix
    car_obj.update_tag(); bpy.context.view_layer.update()
    _m, _n = _emission_mat('emission_bgm', (1.0, 0.95, 0.75, 1.0), 6.0)
    fd = _bold_font()
    bpy.ops.object.text_add(location=(0,0,0))
    tobj = bpy.context.active_object
    tobj.name = 'Label_' + car_name
    tobj.data.body = car_name
    tobj.data.size = 0.3
    tobj.data.extrude = 0.02
    tobj.data.align_x = 'CENTER'
    tobj.data.align_y = 'CENTER'
    if fd: tobj.data.font = fd
    
    # X軸で90度回転して上を向く
    rx = Matrix.Rotation(math.pi / 2, 4, 'X')
    
    # ワールド座標での配置位置: 車の前方(Y-2m)、床面上(Z=0.01m)
    tx = Matrix.Translation((car_obj.location.x, car_obj.location.y - 2.0, 0.01))
    tobj.matrix_world = tx @ rx
    
    # 親を設定しない（車は固定なので不要）
    
    tobj.data.materials.clear()
    tobj.data.materials.append(_m)
    return tobj

def setup_camera(car_length_m):
    """カメラをX方向スライド用の位置に配置（Yプラス方向を常に固定で見る）"""
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA': bpy.data.objects.remove(obj, do_unlink=True)
    camera = bpy.data.cameras.new(name='BGMCamera')
    cam_obj = bpy.data.objects.new('BGMCamera', camera)
    
    # 画角を広げる (35mmで広い視野を確保)
    camera.sensor_fit = 'AUTO'
    camera.lens = 35
    camera.clip_start = 0.1
    camera.clip_end = 200
    
    scene = bpy.context.scene; scene.camera = cam_obj
    scene.render.resolution_x = 1920; scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100; scene.render.engine = 'BLENDER_EEVEE'
    try: scene.eevee.use_raytracing = True
    except AttributeError: pass
    
    # カメラの初期位置: X=+5m, Y=-9m, Z=1.7m（固定）
    cam_obj.location.x = 5.0
    cam_obj.location.y = -9.0
    cam_obj.location.z = 1.7
    
    # カメラ向き: まっすぐYプラス方向を見る（X軸で90度回転）
    cam_obj.rotation_euler = (math.pi / 2 - math.radians(5), 0.0, 0.0)
    
    return cam_obj

def setup_car_animation(car_obj, fps, total_frames, start_y, end_y):
    # 車は固定なのでアニメーションなし
    pass

def setup_camera_animation(cam_obj, car_length_m, fps, total_frames, margin=3.0):
    """カメラをX=-5m → X=+5m にスライド（Y=-9m, Z=1.7m固定、視点=Yプラス固定）"""
    start_x = -7.0
    end_x = 7.0
    speed = (end_x - start_x) / total_frames
    
    for i in range(total_frames + 1):
        x_pos = start_x + speed * i
        cam_obj.location.x = x_pos
        cam_obj.keyframe_insert('location', index=0, frame=i)
    
    print(f"  カメラスライド: X={start_x:.1f} → {end_x:.1f} (Y=-9固定, 視点=Yプラス方向-5°下向き, {total_frames}フレーム)")

def setup_render(fps, total_frames):
    scene = bpy.context.scene
    desktop = os.path.expanduser('~').replace('\\', '/') + '/Desktop'
    scene.render.filepath = desktop + '/bgm_output'
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'; scene.render.ffmpeg.codec = 'H264'
    for p in ['use_frame_number', 'frame_number', 'use_placeholder']:
        try:
            if hasattr(scene.render.ffmpeg, p): setattr(scene.render.ffmpeg, p, False)
        except: pass
    scene.frame_start = 0; scene.frame_end = total_frames
