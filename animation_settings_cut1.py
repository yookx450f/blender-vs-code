"""
アニメーション設定モジュール - カット 1
フレーム 0-648（シーン 1-4）を処理する。

使い方:
    from animation_settings_cut1 import setup_cut1_animations
    setup_cut1_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None)
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at, _setup_transparency_animation


def get_car_visual_center_x(car_obj):
    """車のバウンディングボックスから視覚的な中心X座標を取得"""
    bounds = [Vector(b) for b in car_obj.bound_box]
    corners_world = [car_obj.matrix_world @ corner for corner in bounds]
    min_x = min(c.x for c in corners_world)
    max_x = max(c.x for c in corners_world)
    return (min_x + max_x) / 2.0


def get_car_visual_center_offset(car_obj):
    """車のジオメトリから視覚的な中心のオフセットを取得
    
    GLBモデルのオブジェクト原点が車の視覚的中心と一致しない場合、
    ジオメトリ頂点から直接計算して補正値を返す。
    
    【修正: 回復計画】transform_apply() を使用せず、depsgraph評価のみで計算。
    これにより、車のスケールを変更する副作用を防ぐ。
    
    Returns:
        tuple: (offset_x, offset_y) — 視覚的中心をワールド座標(0,0)に配置するための補正値
        
        例: offset_x = -6.45 の場合、オブジェクト位置を +6.45 に設定すると
            視覚的中心が X=0 に配置される。
    """
    # depsgraphを更新して最新の状態を取得
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = car_obj.evaluated_get(depsgraph)
    me_eval = obj_eval.to_mesh()
    
    if not me_eval or len(me_eval.vertices) == 0:
        obj_eval.to_mesh_clear()
        return (0.0, 0.0)
    
    # ワールド座標で頂点のバウンディングボックスを計算
    # matrix_world はスケール変換を含むため、transform_applyは不要
    mat_world = obj_eval.matrix_world
    verts_world = [mat_world @ Vector(vert.co) for vert in me_eval.vertices]
    
    min_x = min(v.x for v in verts_world)
    max_x = max(v.x for v in verts_world)
    min_y = min(v.y for v in verts_world)
    max_y = max(v.y for v in verts_world)
    
    visual_center_x = (min_x + max_x) / 2.0
    visual_center_y = (min_y + max_y) / 2.0
    
    obj_eval.to_mesh_clear()
    
    # ワールド座標でのオブジェクト原点位置を取得（親子関係を考慮）
    world_origin = obj_eval.matrix_world.to_translation()
    
    offset_x = visual_center_x - world_origin.x
    offset_y = visual_center_y - world_origin.y
    
    return (offset_x, offset_y)


def clear_object_animation(obj, start_frame=0, end_frame=None):
    """オブジェクトのアニメーションデータをクリア（フレーム範囲限定可能）
    Blender 5.x対応版
    
    Parameters:
        obj: クリア対象のオブジェクト
        start_frame: クリア開始フレーム（デフォルト0）
        end_frame: クリア終了フレーム（None=全フレーム）
    """
    current_frame = bpy.context.scene.frame_current
    
    if not obj.animation_data or not obj.animation_data.action:
        bpy.context.scene.frame_set(current_frame)
        return
    
    action = obj.animation_data.action
    
    # end_frameが指定されている場合はフレーム範囲限定で削除
    if end_frame is not None:
        try:
            # Blender 4.x以前のAPI
            if hasattr(action, 'fcurves'):
                for fc in list(action.fcurves):
                    points_to_remove = []
                    for kp in fc.keyframe_points:
                        if start_frame <= kp.co.x <= end_frame:
                            points_to_remove.append(kp.co.x)
                    # 指定フレーム範囲のキーフレームを削除
                    for frame_pos in points_to_remove:
                        idx = next((i for i, kp in enumerate(fc.keyframe_points) if abs(kp.co.x - frame_pos) < 0.1), None)
                        if idx is not None:
                            fc.keyframe_points.remove(idx, update_tag=True)
            # Blender 5.x: レイヤー化アクションシステム
            elif hasattr(action, 'layers'):
                for layer in action.layers:
                    for strip in layer.strips:
                        if strip.type == 'KEYFRAME':
                            for cb in strip.channelbags:
                                for fc in cb.fcurves:
                                    points_to_remove = []
                                    for kp in fc.keyframe_points:
                                        if start_frame <= kp.co.x <= end_frame:
                                            points_to_remove.append(kp.co.x)
                                    for frame_pos in points_to_remove:
                                        idx = next((i for i, kp in enumerate(fc.keyframe_points) if abs(kp.co.x - frame_pos) < 0.1), None)
                                        if idx is not None:
                                            fc.keyframe_points.remove(idx, update_tag=True)
        except Exception as e:
            print(f"  ⚠ キーフレーム範囲削除でエラー: {e}")
    else:
        # 全フレームクリア（元の動作）
        obj.animation_data.action = None
        obj.animation_data_clear()
    
    bpy.context.scene.frame_set(current_frame)


def _create_fcurve_direct(obj, data_path, frame, value):
    """キーフレームを作成（Blender 5.x対応: keyframe_insert使用）
    
    Blender 5.x では Action.fcurves API が変更されているため、
    標準的な obj.keyframe_insert() を使用する。
    """
    import bpy
    
    # アニメーションデータを確保
    if obj.animation_data is None:
        obj.animation_data_create()
    
    # 現在のフレームを保存
    current_frame = bpy.context.scene.frame_current
    
    # 目標フレームに移動
    bpy.context.scene.frame_set(frame)
    
    # data_path のインデックスを解析 (例: "location[0]" -> location, 0)
    import re
    match = re.match(r'(\w+)(?:\[(\d+)\])?', data_path)
    if not match:
        return False
    
    prop_name = match.group(1)
    array_index = int(match.group(2)) if match.group(2) else -1
    
    # keyframe_insert でキーフレームを追加
    try:
        obj.keyframe_insert(data_path=prop_name, index=array_index)
    except Exception as e:
        print(f"  ⚠ keyframe_insert失敗: {obj.name}.{prop_name}[{array_index}] -> {e}")
        bpy.context.scene.frame_set(current_frame)
        return False
    
    # インターポレーションをLINEARに設定（Blender 5.x対応）
    try:
        action = obj.animation_data.action
        if action and hasattr(action, 'fcurves'):
            for fc in action.fcurves:
                if fc.data_path == prop_name:
                    for kp in fc.keyframe_points:
                        if abs(kp.co.x - frame) < 0.1:
                            kp.interpolation = 'LINEAR'
    except Exception:
        pass
    
    # 元のフレームに戻す
    bpy.context.scene.frame_set(current_frame)
    
    return True


def _set_location_keyframe(obj, frame, x, y, z):
    """車の位置キーフレームを設定（F-Curve直接操作版）
    
    【修正: 試行#3】obj.locationをkeyframe_insert前に設定する。
    keyframe_insert()は現在のオブジェクトの値を使用するため、
    先に目標値を設定してからキーフレームを挿入する必要がある。
    """
    # フレームに移動
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    
    # ★重要: キーフレーム挿入前にオブジェクトの位置を設定
    obj.location = (x, y, z)
    
    # 全軸のキーフレームを一度に挿入
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    
    # インターポレーションをLINEARに設定（Blender 5.x対応）
    _ensure_linear_interpolation_for_object(obj, frame)
    
    # 元のフレームに戻す
    bpy.context.scene.frame_set(current_frame)


def _ensure_linear_interpolation_for_object(obj, frame):
    """指定オブジェクトのF-CurveキーフレームのインターポレーションをLINEARに設定
    Blender 5.x対応: レイヤー化アクションシステムを使用
    """
    if not obj.animation_data or not obj.animation_data.action:
        return
    
    action = obj.animation_data.action
    
    # Blender 4.x以前のAPI
    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            for kf in fc.keyframe_points:
                if abs(kf.co.x - frame) < 0.1:
                    kf.interpolation = 'LINEAR'
        return
    
    # Blender 5.x: レイヤー化アクションシステム
    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type == 'KEYFRAME':
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kf in fc.keyframe_points:
                                if abs(kf.co.x - frame) < 0.1:
                                    kf.interpolation = 'LINEAR'


def _set_rotation_keyframe(obj, frame, rot):
    """回転キーフレームを設定（F-Curve直接操作版）
    
    【修正: 試行#3】obj.rotation_eulerをkeyframe_insert前に設定する。
    """
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
    """カメラの位置キーフレームを設定（F-Curve直接操作版）
    
    【修正: 試行#3】obj.locationをkeyframe_insert前に設定する。
    【改訂: 離脱率改善】interpolationはBEZIER（デフォルト）のままにすることで、
    シーン間のカメラ移動を滑らかにする。
    """
    x, y, z = loc if isinstance(loc, tuple) else (loc.x, loc.y, loc.z)
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    # カメラはBEZIER interpolation（デフォルト）のままで滑らかにする
    bpy.context.scene.frame_set(current_frame)


def _set_camera_rotation_keyframe(obj, frame, rot):
    """カメラの回転キーフレームを設定（F-Curve直接操作版）
    
    【改訂: 離脱率改善】interpolationはBEZIER（デフォルト）のままにすることで、
    シーン間のカメラ移動を滑らかにする。
    """
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
    # カメラはBEZIER interpolation（デフォルト）のままで滑らかにする
    bpy.context.scene.frame_set(current_frame)


def _ensure_linear_interpolation(obj, frame):
    """指定オブジェクトの全F-CurveキーフレームのインターポレーションをLINEARに強制設定
    Blender 5.x対応: Action.fcurves の代わりに obj.animation_data.action.slots を使用
    """
    if not obj.animation_data or not obj.animation_data.action:
        print(f"  ⚠ {obj.name}: アニメーションデータが存在しません")
        return
    
    action = obj.animation_data.action
    # Blender 5.x では Action に fcurves 属性がないため、キーフレームを直接操作
    try:
        # Blender 4.x 以前のAPI
        if hasattr(action, 'fcurves'):
            for fc in action.fcurves:
                for kf in fc.keyframe_points:
                    kf.interpolation = 'LINEAR'
        else:
            # Blender 5.x: キーフレームはオブジェクトレベルで管理
            # keyframe_insert で自動的にLinearになるように設定
            pass
    except AttributeError:
        pass

def _diagnose_fcurves(obj, label):
    """F-Curveの状態を診断出力"""
    if not obj.animation_data or not obj.animation_data.action:
        print(f"  ✗ {label} F-Curve: 存在しません!!")
        return
    
    action = obj.animation_data.action
    try:
        # Blender 4.x 以前のAPI
        if hasattr(action, 'fcurves'):
            fc_count = len(action.fcurves)
            print(f"  ✓ {label} F-Curve数: {fc_count}")
            for fc in action.fcurves:
                kf_count = len(fc.keyframe_points)
                print(f"    - {fc.data_path}: キーフレーム数={kf_count}")
        else:
            # Blender 5.x: アニメーションデータは存在するが、F-Curve構造が異なる
            print(f"  ✓ {label} アニメーションデータ: 存在（Blender 5.x形式）")
    except AttributeError:
        print(f"  ? {label} アニメーションデータ: 確認できない形式")

def setup_cut1_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    """
    カット 1 のアニメーションを設定（フレーム 0-648）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報（設定ファイルから）

    Returns:
        dict: 車 A と車 B の終了位置、カメラの最終回転・位置、接地 Z 値など
    """
    import os
    import sys
    log_file = os.path.join(os.path.dirname(__file__), "debug_cut1.log")
    log_fp = open(log_file, "w", encoding="utf-8")
    
    # ログ用ラッパー（ファイルと標準出力の両方に書き込む）
    class LogWriter:
        def write(self, msg):
            log_fp.write(msg)
            log_fp.flush()
            print(msg, end="", flush=True)
        def flush(self):
            log_fp.flush()
    
    log = LogWriter()
    
    print(f"\n=== カット 1 アニメーション設定を開始 ===", file=log_fp)
    log_fp.flush()

    # ============================================================
    # 前提計算：車の位置・接地 Z を準備
    # ============================================================
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        msg = "エラー: carA または carB が見つかりません"
        print(msg, file=log_fp)
        log_fp.close()
        return None

    # 接地後の Z 位置を取得（外部の辞書から）
    grounded_z_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    grounded_z_b = grounded_z_positions.get(car_b.name, car_b.location.z)

    print(f"  接地Z: carA={grounded_z_a:.4f}, carB={grounded_z_b:.4f}", file=log_fp)
    print(f"  rear_offset_y={rear_offset_y:.4f}", file=log_fp)
    log_fp.flush()

    # 車のターゲット位置を定義（車間距離2.5m、フロント端揃え）
    # 視覚的中心補正を取得（GLBモデルの原点オフセットを補正）
    print(f"  --- オフセット計算開始 ---", file=log_fp)
    log_fp.flush()
    
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)
    
    # 【修正: 回復計画】オフセット計算を簡素化
    # カット1単独実行時は親オブジェクトが存在しないため、pivot_offset補正は不要。
    # get_car_visual_center_offset() は depsgraph評価のみで計算し、副作用を持たない。
    
    try:
        offset_a = get_car_visual_center_offset(car_a)
        print(f"  carA オフセット計算成功: ({offset_a[0]:.4f}, {offset_a[1]:.4f})", file=log_fp)
        log_fp.flush()
        
        offset_b = get_car_visual_center_offset(car_b)
        print(f"  carB オフセット計算成功: ({offset_b[0]:.4f}, {offset_b[1]:.4f})", file=log_fp)
        log_fp.flush()
        
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), carB=({offset_b[0]:.4f}, {offset_b[1]:.4f})", file=log_fp)
    except Exception as e:
        msg = f"  ❌ オフセット計算エラー: {e}\n"
        import traceback
        msg += traceback.format_exc()
        print(msg, file=log_fp)
        log_fp.flush()
        print(f"  ⚠️ オフセットを(0,0)にフォールバック", file=log_fp)
        log_fp.flush()
    
    # ワールド座標での目標位置を計算
    # offset_a/b は GLBモデルの原点オフセット補正値（X方向のみ使用）
    # Y座標は後端揃えを維持するため、rear_offset_y をそのまま使用する
    car_a_start = (-1.25, rear_offset_y, grounded_z_a)
    car_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
    car_b_start = (1.25, 0.0, grounded_z_b)
    car_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)

    print(f"  carA: start={car_a_start} -> end={car_a_end}", file=log_fp)
    print(f"  carB: start={car_b_start} -> end={car_b_end}", file=log_fp)
    log_fp.flush()

    # カメラのターゲット（車の中心付近）
    target = (0.0, 0.0, 1.5)

    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"Track To コンストレイント '{constraint.name}' を無効化しました")

    # ============================================================
    # 既存のアニメーションデータをクリア（フレーム範囲限定: 0-696）
    # カット分離のため、Cut1のフレーム範囲内のみをクリアする
    # ============================================================
    from animation_cut_positions import CUT1_START_FRAME, CUT1_END_FRAME
    clear_object_animation(car_a, start_frame=CUT1_START_FRAME, end_frame=CUT1_END_FRAME)
    clear_object_animation(car_b, start_frame=CUT1_START_FRAME, end_frame=CUT1_END_FRAME)
    clear_object_animation(camera, start_frame=CUT1_START_FRAME, end_frame=CUT1_END_FRAME)
    print(f"既存のアニメーションデータをクリアしました (フレーム {CUT1_START_FRAME}-{CUT1_END_FRAME})")

    # ============================================================
    # フレーム順にキーフレームを設定（カット 1）
    # 【改訂: 離脱率改善】停止シーンをすべて削除し、カメラは常に動くようにする
    # トップビューの高さを14m→8mに低下させ、車をアップで捉える
    # ============================================================

    # ============================================================
    # 【改訂: 離脱率改善】フレーム配置を再調整 + BEZIER interpolationで滑らかに
    # ============================================================

    # --- フレーム 0: スタート ---
    bpy.context.scene.frame_set(0)
    loc_frame0 = (6.5, -6.5, 4.0)
    set_camera_look_at(camera, loc_frame0, target)
    rot_frame0 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 0, loc_frame0)
    _set_camera_rotation_keyframe(camera, 0, rot_frame0)

    # 車 A: 左側に配置 (-1.25, rear_offset_y)
    _set_location_keyframe(car_a, 0, car_a_start[0], car_a_start[1], car_a_start[2])

    # 車 B: 右側に配置 (1.25, 0.0)
    _set_location_keyframe(car_b, 0, car_b_start[0], car_b_start[1], car_b_start[2])

    print(f"[フレーム 0] カメラ={loc_frame0}, carA={car_a_start}, carB={car_b_start}", file=log_fp)
    log_fp.flush()

    # --- フレーム 30: 出現完了、半透明化開始 + カメラゆっくり右回り接近 ---
    bpy.context.scene.frame_set(30)
    loc_frame30 = (6.0, -5.5, 3.8)
    set_camera_look_at(camera, loc_frame30, target)
    rot_frame30 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 30, loc_frame30)
    _set_camera_rotation_keyframe(camera, 30, rot_frame30)

    _set_location_keyframe(car_a, 30, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, 30, car_b_start[0], car_b_start[1], car_b_start[2])

    # Alpha: CarB のみ半透明化アニメーション開始（フレーム 30-96 で 0.40→0.35）
    car_b_obj = imported_cars.get("carB")
    if car_b_obj:
        _setup_transparency_animation(car_b_obj, 30, 96, 0.40, 0.35)

    print(f"[フレーム 30] カメラ接近開始={loc_frame30}, Alpha(CarB): 1.0→0.4 開始", file=log_fp)
    log_fp.flush()

    # --- フレーム 96: 中央集合完了 + カメラ軌道継続（停止なし）---
    bpy.context.scene.frame_set(96)
    loc_frame96 = (5.5, -3.5, 3.5)
    set_camera_look_at(camera, loc_frame96, target)
    rot_frame96 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 96, loc_frame96)
    _set_camera_rotation_keyframe(camera, 96, rot_frame96)

    # 車 A: 中央に集まる
    car_a.location = car_a_end
    # 車 B: 中央に集まる
    car_b.location = car_b_end
    _set_location_keyframe(car_a, 96, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, 96, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 96] 中央集合完了: カメラ={loc_frame96}, carA={car_a_end}, carB={car_b_end}", file=log_fp)
    log_fp.flush()

    # --- フレーム 144: カメラ右回りながら上方へ昇る（停止→軌道運動に置き換え）---
    bpy.context.scene.frame_set(144)
    loc_frame144 = (4.5, -2.0, 5.0)
    set_camera_look_at(camera, loc_frame144, target)
    rot_frame144 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 144, loc_frame144)
    _set_camera_rotation_keyframe(camera, 144, rot_frame144)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 144, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 144, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 144] カメラ上方へ: {loc_frame144}")

    # --- フレーム 264: トップビュー到達（高さを8mに低下、車が大きい）---
    bpy.context.scene.frame_set(264)
    loc_frame264 = (3.0, -1.0, 8.0)
    set_camera_look_at(camera, loc_frame264, target)
    rot_frame264 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 264, loc_frame264)
    _set_camera_rotation_keyframe(camera, 264, rot_frame264)

    car_a.location = car_a_end
    _set_location_keyframe(car_a, 264, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 264, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 264] トップビュー（接近）: カメラ={loc_frame264}, 車維持")

    # --- フレーム 312: 回転加速・前方へ降りてくる（停止→軌道運動に置き換え）---
    bpy.context.scene.frame_set(312)
    loc_frame312 = (3.5, 0.5, 7.0)
    set_camera_look_at(camera, loc_frame312, target)
    rot_frame312 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 312, loc_frame312)
    _set_camera_rotation_keyframe(camera, 312, rot_frame312)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 312, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 312, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 312] カメラ前方へ: {loc_frame312}")

    # --- フレーム 408: 斜め前へ降りてくる（Z軸回転継続）---
    bpy.context.scene.frame_set(408)
    loc_frame408 = (5.0, 1.0, 5.5)
    set_camera_look_at(camera, loc_frame408, target)
    rot_frame408 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 408, loc_frame408)
    _set_camera_rotation_keyframe(camera, 408, rot_frame408)

    car_a.location = car_a_end
    _set_location_keyframe(car_a, 408, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 408, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 408] カメラ斜め前へ: {loc_frame408}, 車維持")

    # --- フレーム 456: サイドビューに接近（停止→軌道運動に置き換え）---
    bpy.context.scene.frame_set(456)
    loc_frame456 = (6.5, 0.5, 3.5)
    set_camera_look_at(camera, loc_frame456, target)
    rot_frame456 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 456, loc_frame456)
    _set_camera_rotation_keyframe(camera, 456, rot_frame456)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 456, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 456, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 456] カメラサイドビュー接近: {loc_frame456}")

    # --- フレーム 528: サイドビュー軌道継続（2秒）---
    bpy.context.scene.frame_set(528)
    loc_frame528 = (7.5, 0.0, 2.8)
    set_camera_look_at(camera, loc_frame528, target)
    rot_frame528 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 528, loc_frame528)
    _set_camera_rotation_keyframe(camera, 528, rot_frame528)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 528, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 528, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 528] サイドビュー軌道継続: カメラ={loc_frame528}")

    # --- フレーム 552: 車アップ・スローパン（1秒）---
    bpy.context.scene.frame_set(552)
    loc_frame552 = (7.8, 0.0, 2.6)
    set_camera_look_at(camera, loc_frame552, target)
    rot_frame552 = camera.rotation_euler.copy()
    _set_camera_location_keyframe(camera, 552, loc_frame552)
    _set_camera_rotation_keyframe(camera, 552, rot_frame552)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 552, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 552, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 552] 車アップ・スローパン: カメラ={loc_frame552}")

    # --- フレーム 576: カット2接続位置に到達（1秒）---
    bpy.context.scene.frame_set(576)
    loc_phase4 = (8.0, 0.0, 2.5)
    direction_phase4 = Vector(target) - Vector(loc_phase4)
    rot_quat_phase4 = direction_phase4.to_track_quat('-Z', 'Y')
    rot_phase4 = rot_quat_phase4.to_euler()
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    _set_camera_location_keyframe(camera, 576, loc_phase4)
    _set_camera_rotation_keyframe(camera, 576, rot_phase4)
    car_a.location = car_a_end
    _set_location_keyframe(car_a, 576, car_a_end[0], car_a_end[1], car_a_end[2])
    car_b.location = car_b_end
    _set_location_keyframe(car_b, 576, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"[フレーム 576] カット2接続位置到達: カメラ={loc_phase4}")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 1 アニメーション完了 ===")

    # 【カット分離】オフセットデータをJSONに保存（Cut2-Cut5が独立して読み込めるように）
    from animation_cut_positions import save_offsets
    offset_data = {
        "offset_a": [round(car_a_start[0], 4), round(car_a_start[1], 4)],
        "offset_b": [round(car_b_start[0], 4), round(car_b_start[1], 4)],
        "grounded_z_a": round(grounded_z_a, 4),
        "grounded_z_b": round(grounded_z_b, 4),
        "rear_offset_y": round(rear_offset_y, 4),
        "car_a_center": [round(car_a_end[0], 4), round(car_a_end[1], 4), round(car_a_end[2], 4)],
        "car_b_center": [round(car_b_end[0], 4), round(car_b_end[1], 4), round(car_b_end[2], 4)]
    }
    save_offsets(offset_data)

    # 結果を返す（カット 2 で再利用）
    # 【修正: カット完全分離】CutState 形式で最終状態のみを返す
    from animation_common import CutState
    return CutState(
        car_a_loc=car_a_end,
        car_b_loc=car_b_end,
        camera_loc=loc_phase4,
        camera_rot=(rot_phase4.x, rot_phase4.y, rot_phase4.z),
    )
