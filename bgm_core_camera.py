def setup_camera(car_length_m):
    """カメラをX方向スライド用の位置に配置（常にYプラス方向を向く）"""
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
    
    return cam_obj

def setup_camera_animation(cam_obj, car_length_m, fps, total_frames, margin=3.0):
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
    
    print(f"  カメラスライド: X={start_x:.1f} → {end_x:.1f} ({total_frames}フレーム)")
