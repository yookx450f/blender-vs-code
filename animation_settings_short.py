"""
アニメーション設定モジュール - ショート動画（縦長9:16）
フレーム 0-144（約6秒、24fps）を処理する。

カット1の「車が重なっていく部分」だけを抽出した独立動画。
YouTube Shorts用の縦長フォーマット。

使い方:
    from animation_settings_short import setup_short_animations
    setup_short_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions)
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at, _setup_transparency_animation


def get_car_visual_center_offset(car_obj):
    """車のジオメトリから視覚的な中心のオフセットを取得
    
    depsgraph評価のみで計算し、副作用を持たない。
    
    Returns:
        tuple: (offset_x, offset_y) — 視覚的中心をワールド座標(0,0)に配置するための補正値
    """
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = car_obj.evaluated_get(depsgraph)
    me_eval = obj_eval.to_mesh()
    
    if not me_eval or len(me_eval.vertices) == 0:
        obj_eval.to_mesh_clear()
        return (0.0, 0.0)
    
    mat_world = obj_eval.matrix_world
    verts_world = [mat_world @ Vector(vert.co) for vert in me_eval.vertices]
    
    min_x = min(v.x for v in verts_world)
    max_x = max(v.x for v in verts_world)
    min_y = min(v.y for v in verts_world)
    max_y = max(v.y for v in verts_world)
    
    visual_center_x = (min_x + max_x) / 2.0
    visual_center_y = (min_y + max_y) / 2.0
    
    obj_eval.to_mesh_clear()
    
    world_origin = obj_eval.matrix_world.to_translation()
    
    offset_x = visual_center_x - world_origin.x
    offset_y = visual_center_y - world_origin.y
    
    return (offset_x, offset_y)


def _setup_gradual_transparency(car_object, frames_alphas):
    """車のマテリアル不透明度を複数のキーフレームで徐々に変化させる
    
    Blender 5.x対応版: ノードツリーのアニメーションデータを完全にクリアしてから設定
    
    Parameters:
        car_object: 対象の車オブジェクト
        frames_alphas: [(frame, alpha), ...] のリスト（フレーム順にソート済み）
            例: [(0, 1.0), (32, 0.85), (64, 0.65), (96, 0.4)]
    """
    if car_object is None:
        return
    
    from animation_common import _collect_all_mesh_objects_recursive
    all_meshes = _collect_all_mesh_objects_recursive(car_object)
    
    if not all_meshes:
        if car_object.type == 'MESH' and len(car_object.data.materials) > 0:
            all_meshes = [car_object]
        else:
            return
    
    current_frame = bpy.context.scene.frame_current
    
    for mesh_obj in all_meshes:
        if not hasattr(mesh_obj, 'data') or mesh_obj.data is None:
            continue
        for material in mesh_obj.data.materials:
            if material is None or not material.use_nodes:
                continue
            
            try:
                material.blend_method = 'BLEND'
            except AttributeError:
                pass
            
            nodes = material.node_tree.nodes
            principled_node = None
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                    break
            
            if principled_node is None or 'Alpha' not in principled_node.inputs:
                continue
            
            alpha_input = principled_node.inputs['Alpha']
            node_tree = material.node_tree
            
            # ★重要: ノードツリーのアニメーションデータを完全にクリア
            try:
                if hasattr(node_tree, 'animation_data'):
                    node_tree.animation_data = None
            except Exception as e:
                print(f"    ⚠️ アニメーションデータクリア中の警告: {e}")
            
            # Alphaを1.0にリセット
            alpha_input.default_value = 1.0
            
            # キーフレームをフレーム順に設定（昇順）
            sorted_frames = sorted(frames_alphas, key=lambda x: x[0])
            
            for frame, alpha in sorted_frames:
                bpy.context.scene.frame_set(frame)
                alpha_input.default_value = alpha
                if node_tree.animation_data is None:
                    node_tree.animation_data_create()
                alpha_input.keyframe_insert(data_path="default_value", frame=frame)
            
            # F-Curveの外挿モードを設定
            try:
                if node_tree.animation_data and node_tree.animation_data.action:
                    action = node_tree.animation_data.action
                    if hasattr(action, 'fcurves'):
                        for fc in action.fcurves:
                            fc.pre_extrapolation = 'Hold'
                            fc.post_extrapolation = 'Hold'
            except Exception as e:
                print(f"    ⚠️ F-Curve外挿設定中の警告: {e}")
    
    # 元のフレームに戻す
    bpy.context.scene.frame_set(current_frame)


def _set_location_keyframe(obj, frame, x, y, z):
    """車の位置キーフレームを設定"""
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_rotation_keyframe(obj, frame, rot):
    """回転キーフレームを設定"""
    if hasattr(rot, 'x'):
        rx, ry, rz = rot.x, rot.y, rot.z
    else:
        rx, ry, rz = rot[0], rot[1], rot[2]
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.rotation_euler = (rx, ry, rz)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="rotation_euler", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_camera_location_keyframe(obj, frame, loc):
    """カメラの位置キーフレームを設定"""
    x, y, z = loc if isinstance(loc, tuple) else (loc.x, loc.y, loc.z)
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _ensure_linear_interpolation_for_object(obj, frame):
    """指定オブジェクトのF-CurveキーフレームのインターポレーションをLINEARに設定"""
    if not obj.animation_data or not obj.animation_data.action:
        return
    
    action = obj.animation_data.action
    
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            for kf in fc.keyframe_points:
                if abs(kf.co.x - frame) < 0.1:
                    kf.interpolation = 'LINEAR'
        return
    
    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type == 'KEYFRAME':
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kf in fc.keyframe_points:
                                if abs(kf.co.x - frame) < 0.1:
                                    kf.interpolation = 'LINEAR'


def setup_short_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions):
    """
    ショート動画のアニメーションを設定（フレーム 0-144、約6秒）
    
    カット1の「車が重なっていく部分」だけを抽出。
    縦長9:16フォーマット用。
    
    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
    
    Returns:
        dict: 最終状態情報
    """
    print("\n=== ショート動画 アニメーション設定を開始 ===")
    
    # ============================================================
    # 前提計算：車の位置・接地 Z を準備
    # ============================================================
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")
    
    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None
    
    grounded_z_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    grounded_z_b = grounded_z_positions.get(car_b.name, car_b.location.z)
    
    print(f"  接地Z: carA={grounded_z_a:.4f}, carB={grounded_z_b:.4f}")
    print(f"  rear_offset_y={rear_offset_y:.4f}")
    
    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)
    
    try:
        offset_a = get_car_visual_center_offset(car_a)
        offset_b = get_car_visual_center_offset(car_b)
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), carB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")
    
    # 車のターゲット位置を定義（カット1と同じ配置）
    car_a_start = (-1.25, rear_offset_y, grounded_z_a)
    car_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
    car_b_start = (1.25, 0.0, grounded_z_b)
    car_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)
    
    print(f"  carA: start={car_a_start} -> end={car_a_end}")
    print(f"  carB: start={car_b_start} -> end={car_b_end}")
    
    # カメラのターゲット（車の中心付近）
    # Z値を下げることで、車が画面上方にスライドする
    target = (0.0, 0.0, 1.0)
    
    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"  Track To コンストレイント '{constraint.name}' を無効化")
    
    # ============================================================
    # カメラパンニング設定：(0,0)をピボットとして円弧運動
    # スタート位置（向かって左）から右へゆっくり回転
    # ============================================================
    
    # スタートカメラ位置（向かって左側の視点）
    cam_start = (-3.0, -5.0, 3.5)
    # (0, 0) を中心とした円弧運動の半径と高さ
    arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
    arc_height = cam_start[2]
    print(f"  カメラ円弧: 半径={arc_radius:.2f}, 高さ={arc_height}")
    
    # スタート角度（X-Y平面上的な極座標の角度）
    start_angle = math.atan2(cam_start[0], cam_start[1])
    # 向かって左から右へ移動（角度を負の方向に減少）
    total_rotation = -0.85  # ラジアン（約49度）
    
    # レンズ焦距（数値を大きくしてズームイン）
    original_lens = camera.data.lens
    camera.data.lens = 35
    print(f"  カメラレンズ: {original_lens}mm → 35mm（ズームイン）")
    
    # 円弧上のカメラ位置を計算する関数
    def get_cam_on_arc(angle):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        return (x, y, arc_height)
    
    # ============================================================
    # フレーム順にキーフレームを設定（円弧パンニング）
    # ============================================================
    
    # キーフレーム間隔（24フレーム=1秒ごと）
    arc_keyframes = [0, 24, 48, 72, 96, 120, 144]
    num_segments = len(arc_keyframes) - 1
    
    for i, frame in enumerate(arc_keyframes):
        progress = i / num_segments if num_segments > 0 else 0
        angle = start_angle + total_rotation * progress
        cam_pos = get_cam_on_arc(angle)
        set_camera_look_at(camera, cam_pos, target)
        rot = camera.rotation_euler.copy()
        _set_camera_location_keyframe(camera, frame, cam_pos)
        _set_rotation_keyframe(camera, frame, rot)
        print(f"  [フレーム {frame}] カメラ={cam_pos} (角度={math.degrees(angle):.1f}°)")
    
    # --- フレーム 0: 車のスタート位置 ---
    _set_location_keyframe(car_a, 0, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, 0, car_b_start[0], car_b_start[1], car_b_start[2])
    print(f"           carA={car_a_start}, carB={car_b_start}")
    
    # --- フレーム 120: 中央集合完了（5秒かけてスライド）---
    _set_location_keyframe(car_a, 120, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, 120, car_b_end[0], car_b_end[1], car_b_end[2])
    print(f"  [フレーム 120] 中央集合完了: carA={car_a_end}, carB={car_b_end}")
    
    # --- フレーム 144: 車の位置維持 ---
    _set_location_keyframe(car_a, 144, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, 144, car_b_end[0], car_b_end[1], car_b_end[2])
    
    # 最終カメラ回転を保存（CutState用）
    final_angle = start_angle + total_rotation
    final_cam = get_cam_on_arc(final_angle)
    set_camera_look_at(camera, final_cam, target)
    rot_f144 = camera.rotation_euler.copy()
    
    print(f"  [フレーム 144] カメラパンニング完了（右方向に{math.degrees(total_rotation):.1f}°回転）")
    
    # ============================================================
    # CarBの半透明化を最後に設定（他のキーフレームと干渉しないように）
    # Blender 5.x対応: 専用の透明度アニメーション関数を使用
    # ============================================================
    if car_b:
        frames_alphas = [
            (0, 1.0),    # スタート: 完全不透明
            (55, 1.0),   # 2.3秒間完全不透明を維持（24fps×2.3）
            (56, 0.98),  # 半透明化開始
            (79, 0.9),   # 少し透明に
            (103, 0.75), # さらに透明に
            (127, 0.5),  # 半透明寄りに
            (144, 0.35), # 最終: 半透明完了
        ]
        _setup_gradual_transparency(car_b, frames_alphas)
        print(f"  Alpha(CarB): フレーム0-144で徐々に半透明化 (2.3秒待機後 1.0→0.98→0.9→0.75→0.5→0.35)")
    
    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)
    
    print("\n=== ショート動画 アニメーション完了 ===")
    
    from animation_common import CutState
    return CutState(
        car_a_loc=car_a_end,
        car_b_loc=car_b_end,
        camera_loc=final_cam,
        camera_rot=(rot_f144.x, rot_f144.y, rot_f144.z),
    )
