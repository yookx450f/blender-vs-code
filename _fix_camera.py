"""Helper: Update bgm_core.py camera functions"""
import re

path = 'bgm_core.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# --- Fix setup_camera function (lines 113-144) ---
old_camera = '''def setup_camera(car_length_m):
    """カメラをX方向スライド用の位置に配置（車を向くように設定）"""
    from mathutils import Matrix
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
    
    # カメラの初期位置: X=車全長/2 + 3m、Y=5m（車の前方）、Z=1.7m
    cam_obj.location.x = car_length_m / 2.0 + 3.0
    cam_obj.location.y = 5.0  # 車の前方からの距離
    cam_obj.location.z = 1.7
    
    # カメラ向き: 車を向くように設定（X=0, Y=0, Z=1.0をターゲット）
    target = Vector((0.0, 0.0, 1.0))
    direction = (target - cam_obj.location).normalized()
    rot_q = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_q.to_euler()
    
    return cam_obj'''

new_camera = '''def setup_camera(car_length_m):
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
    
    # カメラの初期位置: X=+10m, Y=-5m, Z=1.7m（固定）
    cam_obj.location.x = 10.0
    cam_obj.location.y = -5.0
    cam_obj.location.z = 1.7
    
    # カメラ向き: まっすぐYプラス方向を見る（X軸で90度回転）
    cam_obj.rotation_euler = (math.pi / 2, 0.0, 0.0)
    
    return cam_obj'''

content = content.replace(old_camera, new_camera)

# --- Fix setup_camera_animation function (lines 150-165) ---
old_anim = '''def setup_camera_animation(cam_obj, car_length_m, fps, total_frames, margin=3.0):
    """カメラをXプラス側→Xマイナス側にスライド（Y,Z固定）"""
    start_x = car_length_m / 2.0 + margin
    end_x = -(car_length_m / 2.0 + margin)
    speed = (end_x - start_x) / total_frames
    
    # YとZは固定
    fixed_y = cam_obj.location.y
    fixed_z = cam_obj.location.z
    
    for i in range(total_frames + 1):
        x_pos = start_x + speed * i
        cam_obj.location.x = x_pos
        cam_obj.keyframe_insert('location', index=0, frame=i)
    
    print(f"  カメラスライド: X={start_x:.1f} → {end_x:.1f} ({total_frames}フレーム)")'''

new_anim = '''def setup_camera_animation(cam_obj, car_length_m, fps, total_frames, margin=3.0):
    """カメラをX=+10m → X=-10m にスライド（Y=-5m, Z=1.7m固定、視点=Yプラス固定）"""
    start_x = 10.0
    end_x = -10.0
    speed = (end_x - start_x) / total_frames
    
    for i in range(total_frames + 1):
        x_pos = start_x + speed * i
        cam_obj.location.x = x_pos
        cam_obj.keyframe_insert('location', index=0, frame=i)
    
    print(f"  カメラスライド: X={start_x:.1f} → {end_x:.1f} (Y=-5固定, 視点=Yプラス固定, {total_frames}フレーム)")'''

content = content.replace(old_anim, new_anim)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("bgm_core.py updated successfully")
