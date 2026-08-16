"""
アニメーション設定モジュール - カット 5
フレーム 2208-2832（シーン 13:6秒、シーン 14:15秒）を処理する。

使い方:
   from animation_settings_cut5 import setup_cut5_animations
   setup_cut5_animations(scene, camera, imported_cars, cut4_result, car_dimensions=None)

【処理内容】
- シーン 13: 軌跡とテキストを3秒でフェードアウト、その後カメラをゆっくり動かす（6秒）
- シーン 14: 2台の車がx軸距離2.5mを開け、加速して走り去る（15秒）
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at


def setup_cut5_animations(scene, camera, imported_cars, previous_state=None, car_dimensions=None):
    """
    カット 5 のアニメーションを設定（フレーム 2208-2832）

    【修正: カット完全分離】previous_state をオプション化し、
    指定されていない場合は固定位置から読み込む。

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        previous_state: CutState — 前のカットの最終状態（オプション、未指定時は固定位置使用）
        car_dimensions: {key: {"turning_radius": mm}} 車の寸法情報

    Returns:
        CutState: このカットの最終状態
    """
    # 【カット完全分離】previous_state が指定された場合は従来通り使用、
    # 未指定の場合は固定位置から読み込む
    from animation_cut_positions import CAMERA_POSITIONS, get_car_positions
    
    if previous_state is not None:
        car_a_end = previous_state.car_a_loc
        car_b_end = previous_state.car_b_loc
        loc_scene12_end = previous_state.camera_loc
        rot_scene12_end = previous_state.camera_rot
    else:
        # 固定位置から読み込み（Cut4終了時のカメラ位置を計算）
        car_a_end, car_b_end = get_car_positions()
        
        # Cut4の終了カメラ位置は俯瞰視点であり、回転中心の中間点上空にある
        # 回転半径デフォルト値: carA=5.2m, carB=6.0m
        default_turning_radius_a = 5.2
        default_turning_radius_b = 6.0
        
        # Emptyピボット位置（回転中心）を計算
        empty_a_loc = (-default_turning_radius_a, car_a_end[1], car_a_end[2])
        empty_b_loc = (-default_turning_radius_b, car_b_end[1], car_b_end[2])
        
        # 回転中心の中間点
        mid_turn_center_x = (empty_a_loc[0] + empty_b_loc[0]) / 2.0
        mid_turn_center_y = (empty_a_loc[1] + empty_b_loc[1]) / 2.0
        
        # カメラ位置: Cut4終了時の俯瞰視点（Z=25m, Y=-3m手前）
        loc_scene12_end = (mid_turn_center_x, mid_turn_center_y - 3.0, 25.0)
        
        # 注視点は回転中心の中間点
        target_cam = (mid_turn_center_x, mid_turn_center_y, 0.0)
        direction = Vector(target_cam) - Vector(loc_scene12_end)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        rot_scene12_end = rot_quat.to_euler()

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # ============================================================
    # 【カット 5】シーン 13: フレーム 2208-2352（カメラ回転6秒、最初の3秒で軌跡とテキストをフェードアウト）
    # ============================================================
    print("\n=== 【カット 5】シーン 13 設定開始 ===")

    scene13_start = 2256
    fade_out_end = 2376  # フェードアウト完了（3秒：24fps × 3 = 72フレーム）
    scene13_end = 2400  # カメラ移動完了（計6秒：24fps × 6 = 144フレーム）

    # カメラ: 6秒かけてゆっくり90度回転（フェードアウト中も含めて）
    # 開始位置: シーン12終了時のカメラ位置・回転
    camera.location = loc_scene12_end
    camera.rotation_euler = rot_scene12_end
    camera.keyframe_insert(data_path="location", frame=scene13_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene13_start)
    
    # 終了位置: Z軸を中心に90度（π/2ラジアン）回転したカメラ
    start_rot = rot_scene12_end  # タプル
    end_rot = (start_rot[0], start_rot[1], start_rot[2] + math.pi / 2)
    
    camera.location = loc_scene12_end  # 位置は変えずに回転のみ
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene13_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene13_end)

    # シーン14でもカメラ位置は固定（この変数を保存）
    fixed_camera_loc = loc_scene12_end

    print(f"[フレーム{scene13_start}] カメラ位置をシーン12と同じに維持: {loc_scene12_end}")

    # 車の位置: 6秒かけてX軸方向に3m離す（carA: X=-1.5m, carB: X=+1.5m）
    # カット5はEmptyを使わず、車の位置を直接制御する
    
    # 車のアニメーションデータをクリア（前のカットのキーフレームと競合しないように）
    if car_a.animation_data:
        car_a.animation_data_clear()
    if car_b.animation_data:
        car_b.animation_data_clear()

    bpy.context.view_layer.update()

    # Emptyの親子関係を解除（もし親が設定されていれば）
    if car_a.parent is not None:
        car_a.parent = None
    if car_b.parent is not None:
        car_b.parent = None

    bpy.context.view_layer.update()

    # 開始位置: カット4終了時の車の位置（X=0, Y, Z）
    # car_a_end/car_b_end はカット4の戻り値から取得（X=0に設定されているはず）
    start_loc_a = (0.0, car_a_end[1], car_a_end[2])
    start_loc_b = (0.0, car_b_end[1], car_b_end[2])

    print(f"[シーン13] 車の開始位置 carA: {start_loc_a}")
    print(f"[シーン13] 車の開始位置 carB: {start_loc_b}")

    # === 開始フレームに移動してからキーフレームを挿入 ===
    bpy.context.scene.frame_set(scene13_start)
    bpy.context.view_layer.update()

    car_a.location = start_loc_a
    car_b.location = start_loc_b
    
    car_a.keyframe_insert(data_path="location", frame=scene13_start)
    car_b.keyframe_insert(data_path="location", frame=scene13_start)

    print(f"[フレーム{scene13_start}] キーフレーム挿入後 carA: ({car_a.location.x:.4f}, {car_a.location.y:.4f}, {car_a.location.z:.4f})")
    print(f"[フレーム{scene13_start}] キーフレーム挿入後 carB: ({car_b.location.x:.4f}, {car_b.location.y:.4f}, {car_b.location.z:.4f})")

    # === 終了フレームに移動してからキーフレームを挿入 ===
    bpy.context.scene.frame_set(scene13_end)
    bpy.context.view_layer.update()

    # 終了位置: グローバルXを±1.5m（合計3m離れる）
    end_loc_a = (-1.5, car_a_end[1], car_a_end[2])
    end_loc_b = (1.5, car_b_end[1], car_b_end[2])

    car_a.location = end_loc_a
    car_a.keyframe_insert(data_path="location", frame=scene13_end)
    car_b.location = end_loc_b
    car_b.keyframe_insert(data_path="location", frame=scene13_end)

    print(f"[シーン13] グローバルX: 開始=(0, 0), 終了=(-1.5, +1.5)")

    # 軌跡ガイドラインとテキストが存在しない場合は作成（独立実行時の対応）
    _ensure_fade_out_targets_exist(car_a, car_b, camera, car_dimensions)
    
    # 軌跡ガイドラインのフェードアウト（3秒）
    _fade_out_track_objects("CarA_TurningCircle", scene13_start, fade_out_end)
    _fade_out_track_objects("CarB_TurningCircle", scene13_start, fade_out_end)
    _fade_out_track_objects("CarA_TireTrack", scene13_start, fade_out_end)
    _fade_out_track_objects("CarB_TireTrack", scene13_start, fade_out_end)

    # 最小回転半径比較式テキストのフェードアウト（3秒）
    _fade_out_text_container("TurningRadiusDiff_Container_Scene12", scene13_start, fade_out_end)

    print(f"[フレーム{fade_out_end}] フェードアウト完了")
    print(f"[フレーム{scene13_end}] シーン 13 終了：カメラ移動完了")

    # ============================================================
    # 【カット 5】シーン 14: フレーム 2352-2832（走り去るアニメーション、15秒）
    # ============================================================
    print("\n=== 【カット 5】シーン 14 設定開始 ===")

    scene14_start = scene13_end  # 2400
    scene14_end = 2880  # 15秒間（24fps × 15 = 480フレーム）

    # Empty親オブジェクトを削除
    bpy.ops.object.select_all(action='DESELECT')
    empties_to_delete = []
    for empty_name in ["CarA_TurnPivot", "CarB_TurnPivot"]:
        if empty_name in bpy.data.objects:
            empties_to_delete.append(bpy.data.objects[empty_name])
    for obj in empties_to_delete:
        obj.select_set(True)
    if empties_to_delete:
        bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')

    # 車の親をNoneに戻す
    if car_a.parent is not None:
        car_a.parent = None
    if car_b.parent is not None:
        car_b.parent = None

    # シーン13で設定した車の位置キーフレームを保持する
    # そのため、アニメーションデータはクリアせず、新しいキーフレームを追加するのみ

    bpy.context.view_layer.update()

    print(f"[シーン14] Empty親オブジェクトを削除（車のアニメーションデータは保持）")

    # 車の向きをY負方向（前方）に向ける（-Z回転で後方に進む）
    # 位置はシーン13の終了キーフレームから連続させる
    car_a.rotation_euler = (0.0, 0.0, -math.pi / 2)
    car_a.keyframe_insert(data_path="rotation_euler", frame=scene14_start)

    car_b.rotation_euler = (0.0, 0.0, -math.pi / 2)
    car_b.keyframe_insert(data_path="rotation_euler", frame=scene14_start)

    # シーン13終了時の車の位置を取得（キーフレームから）
    bpy.context.scene.frame_set(scene14_start)
    bpy.context.view_layer.update()
    scene13_end_loc_a = car_a.location.copy()
    scene13_end_loc_b = car_b.location.copy()

    print(f"[フレーム{scene14_start}] carA 開始位置（シーン13終了から連続）: {scene13_end_loc_a}")
    print(f"[フレーム{scene14_start}] carB 開始位置（シーン13終了から連続）: {scene13_end_loc_b}")

    # 加速アニメーション（JSONの0-100km/h加速時間に基づいて各車個別に計算）
    duration_seconds = 15.0

    def ease_in_acceleration(t):
        """ease-in: 実車の発進のようにゆっくり加速し、徐々に速度を上げるカーブ"""
        return t ** 3

    # JSONから加速時間を取得（デフォルト値: carA=9.4s, carB=6.7s）
    if car_dimensions:
        accel_a = car_dimensions.get("carA", {}).get("acceleration_0_to_100_km_h", 9.4)
        accel_b = car_dimensions.get("carB", {}).get("acceleration_0_to_100_km_h", 6.7)
    else:
        accel_a = 9.4
        accel_b = 6.7

    # 加速度計算 (m/s²): a = (100/3.6) / T
    acceleration_a = (100.0 / 3.6) / accel_a
    acceleration_b = (100.0 / 3.6) / accel_b

    # 6秒後の到達速度 (m/s): v = a * t
    final_speed_a = acceleration_a * duration_seconds
    final_speed_b = acceleration_b * duration_seconds

    # ease-inカーブ (t³) を適用した移動距離を積分で計算
    # ∫₀^T a·(t/6)³ dt = a·T⁴/(3·6³) → 簡易的に: 平均速度 × 時間
    # 物理的な加速距離: d = ∫v(t)dt, v(t) = a_max · (t/duration)³
    # d = a_max · duration / 4
    total_distance_a = acceleration_a * duration_seconds ** 4 / (4 * duration_seconds ** 3) * duration_seconds
    total_distance_b = acceleration_b * duration_seconds ** 4 / (4 * duration_seconds ** 3) * duration_seconds

    print(f"[シーン14] carA 0-100km/h: {accel_a}s → 加速度: {acceleration_a:.2f}m/s² → 6秒後速度: {final_speed_a:.1f}m/s ({final_speed_a*3.6:.0f}km/h) → 移動距離: {total_distance_a:.1f}m")
    print(f"[シーン14] carB 0-100km/h: {accel_b}s → 加速度: {acceleration_b:.2f}m/s² → 6秒後速度: {final_speed_b:.1f}m/s ({final_speed_b*3.6:.0f}km/h) → 移動距離: {total_distance_b:.1f}m")

    num_keyframes = 50
    for i in range(num_keyframes + 1):
        t = i / num_keyframes
        eased_t = ease_in_acceleration(t)

        frame = scene14_start + int((scene14_end - scene14_start) * t)
        distance_a = total_distance_a * eased_t
        distance_b = total_distance_b * eased_t

        # Y負方向に移動（前方に進む）
        # X位置はシーン13終了時から維持、Y位置を加速カーブで移動
        car_a.location = (scene13_end_loc_a.x, scene13_end_loc_a.y - distance_a, scene13_end_loc_a.z)
        car_a.keyframe_insert(data_path="location", frame=frame)

        car_b.location = (scene13_end_loc_b.x, scene13_end_loc_b.y - distance_b, scene13_end_loc_b.z)
        car_b.keyframe_insert(data_path="location", frame=frame)

    final_distance_a = total_distance_a
    final_distance_b = total_distance_b
    car_a.location = (scene13_end_loc_a.x, scene13_end_loc_a.y - final_distance_a, scene13_end_loc_a.z)
    car_a.keyframe_insert(data_path="location", frame=scene14_end)

    car_b.location = (scene13_end_loc_b.x, scene13_end_loc_b.y - final_distance_b, scene13_end_loc_b.z)
    car_b.keyframe_insert(data_path="location", frame=scene14_end)

    print(f"[フレーム{scene14_end}] carA 終了位置: ({scene13_end_loc_a.x}, {scene13_end_loc_a.y - final_distance_a:.2f}, {scene13_end_loc_a.z})")
    print(f"[フレーム{scene14_end}] carB 終了位置: ({scene13_end_loc_b.x}, {scene13_end_loc_b.y - final_distance_b:.2f}, {scene13_end_loc_b.z})")

    # カメラアニメーション（位置固定・回転のみで車を追う）
    # 車の加速カーブに合わせて注視点を逐次更新
    camera.location = fixed_camera_loc
    camera.keyframe_insert(data_path="location", frame=scene14_start)

    # 各フレームで車の実際の位置を計算し、カメラの注視点をそれに合わせる
    # 2台の車の平均位置を追う
    # シーン13終了時の車のY位置の平均を基準にする
    car_start_y_avg = (scene13_end_loc_a.y + scene13_end_loc_b.y) / 2.0
    
    for i in range(num_keyframes + 1):
        t = i / num_keyframes
        eased_t = ease_in_acceleration(t)

        frame = scene14_start + int((scene14_end - scene14_start) * t)
        distance_a = total_distance_a * eased_t
        distance_b = total_distance_b * eased_t
        # 2台の車の平均位置を注視点にする
        distance_avg = (distance_a + distance_b) / 2.0

        # 車の位置の少し手前を注視点にする（車が遠ざかるにつれて注視点も追従）
        if t < 0.5:
            # 前半は車の近くを追う
            look_at_target = Vector((0.0, car_start_y_avg - distance_avg - 3.0, 1.0))
        else:
            # 後半は車が遠ざかる方向を見る
            progress_second_half = (t - 0.5) / 0.5
            look_at_y = car_start_y_avg - distance_avg - 3.0 - progress_second_half * 20.0
            look_at_z = 1.0 - progress_second_half * 0.5
            look_at_target = Vector((0.0, look_at_y, look_at_z))

        set_camera_look_at(camera, fixed_camera_loc, look_at_target)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
        camera.keyframe_insert(data_path="location", frame=frame)

    # 最終フレームの回転を保存
    rot_scene14_end = camera.rotation_euler.copy()

    print(f"[フレーム{scene14_start}] カメラ位置固定: {fixed_camera_loc}")
    print(f"[フレーム{scene14_start}] 注視点: (0.0, {car_start_y_avg - 3.0}, 1.0)（車の近く）")
    print(f"[フレーム{scene14_end}] 注視点: (0.0, {car_start_y_avg - (final_distance_a + final_distance_b)/2 - 23.0}, 0.5)（遠くへ・点がなる方向）")

    # カメラ終了位置も固定位置を使用
    camera_end_loc = fixed_camera_loc

    # 各車の上に0-100km/h加速時間テキストを表示（車にペアレントして追従）
    _create_acceleration_texts(car_a, car_b, accel_a, accel_b, scene14_start, scene14_end)

    # 各車に個別のライトをペアレント設定して、車がどこに行っても明るく照らす
    _attach_lights_to_cars(car_a, car_b, scene14_start, scene14_end)

    print(f"[フレーム{scene14_end}] シーン 14 終了：走り去るアニメーション完了")

    bpy.context.scene.frame_set(0)

    print("\n=== カット 5 アニメーション完了 ===")

    from animation_common import CutState
    return CutState(
        car_a_loc=(scene13_end_loc_a.x, scene13_end_loc_a.y - final_distance_a, car_a_end[2]),
        car_b_loc=(scene13_end_loc_b.x, scene13_end_loc_b.y - final_distance_b, car_b_end[2]),
        camera_loc=camera_end_loc,
        camera_rot=(rot_scene14_end.x, rot_scene14_end.y, rot_scene14_end.z),
    )


def _ensure_fade_out_targets_exist(car_a, car_b, camera, car_dimensions=None):
    """
    フェードアウト対象（軌跡ガイドライン、タイヤ跡、最小回転半径テキスト）が存在するか確認し、
    存在しない場合はカット4と同じ方法で完全なオブジェクトを作成する。
    カット5を独立実行した時の対応用。
    """
    import bmesh
    
    # 軌跡オブジェクトが既に存在するか確認
    has_track = False
    for obj in bpy.data.objects:
        if "TurningCircle" in obj.name or "TireTrack" in obj.name:
            has_track = True
            break
    
    if has_track:
        print("[シーン13] 軌跡オブジェクトが既に存在します（フェードアウト対象あり）")
        return
    
    print("[シーン13] 軌跡オブジェクトが見つかりません。カット4と同じ方法で完全な軌跡を作成します...")
    
    # 回転半径を取得
    if car_dimensions:
        turning_radius_a = car_dimensions.get("carA", {}).get("turning_radius", 5200) / 1000.0
        turning_radius_b = car_dimensions.get("carB", {}).get("turning_radius", 6000) / 1000.0
        radius_a_mm = car_dimensions.get("carA", {}).get("turning_radius", 5200)
        radius_b_mm = car_dimensions.get("carB", {}).get("turning_radius", 6000)
    else:
        turning_radius_a = 5.2
        turning_radius_b = 6.0
        radius_a_mm = 5200
        radius_b_mm = 6000
    
    # Emptyピボット位置（回転中心）を計算
    empty_a_loc = (-turning_radius_a, car_a.location.y, car_a.location.z)
    empty_b_loc = (-turning_radius_b, car_b.location.y, car_b.location.z)
    
    # カット4と同じ方法で軌跡ガイドラインを作成（60セグメント）
    _create_turning_radius_visualization_for_cut5(empty_a_loc, turning_radius_a, "CarA_TurningCircle", 2256, 2400, (0.5, 0.5, 0.5))
    _create_turning_radius_visualization_for_cut5(empty_b_loc, turning_radius_b, "CarB_TurningCircle", 2256, 2400, (0.0, 0.7, 1.0))
    
    # カット4と同じ方法でタイヤ跡軌跡を作成（車の横幅に合わせる）
    _create_tire_track_for_cut5(car_a, empty_a_loc, turning_radius_a, "CarA_TireTrack", 2256, 2400, (0.5, 0.5, 0.5))
    _create_tire_track_for_cut5(car_b, empty_b_loc, turning_radius_b, "CarB_TireTrack", 2256, 2400, (0.0, 0.7, 1.0))
    
    # カット4と同じ方法で最小回転半径比較式テキストを作成
    radius_diff_mm = radius_b_mm - radius_a_mm
    _create_turning_radius_diff_text_for_cut5(camera, radius_a_mm, radius_b_mm, radius_diff_mm,
                                              empty_a_loc, empty_b_loc, 2256, 2400, car_dimensions)
    
    print("[シーン13] 完全な軌跡オブジェクトとテキストコンテナを作成完了")


def _create_turning_radius_visualization_for_cut5(center, radius, name_prefix, start_frame, end_frame, color=(1.0, 1.0, 1.0)):
    """カット4と同じ方法で回転半径ガイドラインを作成（60セグメント）"""
    import bmesh
    
    num_segments = 60
    track_width = 0.05
    
    # 発光マテリアル
    mat_name = f"{name_prefix}_Mat"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial')
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        principled.inputs['Metallic'].default_value = 0.0
        principled.inputs['Roughness'].default_value = 1.0
        principled.inputs['Emission Color'].default_value = (*color, 1.0)
        principled.inputs['Emission Strength'].default_value = 3.0
        mat.node_tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    # 各セグメントを細長い面として作成
    for seg in range(num_segments):
        seg_start_angle = -2.0 * math.pi * seg / num_segments
        seg_end_angle = -2.0 * math.pi * (seg + 1) / num_segments
        
        mesh = bpy.data.meshes.new(f"{name_prefix}_Seg{seg}")
        bm = bmesh.new()
        
        arc_points = 3
        inner_verts = []
        outer_verts = []
        
        for p in range(arc_points + 1):
            t = p / arc_points
            angle = seg_start_angle + (seg_end_angle - seg_start_angle) * t
            
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            inner_r = radius - track_width / 2
            wx_inner = center[0] + (inner_r * cos_a)
            wy_inner = center[1] + (inner_r * sin_a)
            inner_verts.append(bm.verts.new((wx_inner, wy_inner, 0.05)))
            
            outer_r = radius + track_width / 2
            wx_outer = center[0] + (outer_r * cos_a)
            wy_outer = center[1] + (outer_r * sin_a)
            outer_verts.append(bm.verts.new((wx_outer, wy_outer, 0.05)))
        
        for p in range(arc_points):
            bm.faces.new([inner_verts[p], inner_verts[p+1], outer_verts[p+1], outer_verts[p]])
        
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"{name_prefix}_Seg{seg}_Obj", mesh)
        bpy.context.collection.objects.link(obj)
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(bpy.data.materials[mat_name])
        
        # カット5では既に表示されている状態なので、frame=0から表示
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=0)
        obj.keyframe_insert(data_path="hide_render", frame=0)


def _create_tire_track_for_cut5(car_object, empty_pivot_loc, turning_radius, name_prefix, start_frame, end_frame, color=(1.0, 0.2, 0.2)):
    """カット4と同じ方法でタイヤ跡軌跡を作成（車の横幅に合わせる）"""
    import bmesh
    
    # 車のバウンディングボックスから後輪のYオフセットと横幅を計算
    car_object.update_tag()
    bpy.context.view_layer.update()
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"[警告] {car_object.name} のバウンディングボックスが取得できません")
        return
    
    corners_local = [Vector(corner) for corner in local_bounds]
    rear_y = min(c.y for c in corners_local)
    
    # 軌跡幅を車の横幅に設定
    x_coords = [c.x for c in corners_local]
    car_width_m = max(x_coords) - min(x_coords)
    track_width = car_width_m
    
    print(f"[シーン13] {car_object.name} の横幅: {car_width_m:.3f}m → 軌跡幅として設定")
    
    num_segments = 30
    
    # 発光マテリアル
    mat_name = f"{name_prefix}_Mat"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial')
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
        principled.inputs['Metallic'].default_value = 0.0
        principled.inputs['Roughness'].default_value = 1.0
        principled.inputs['Emission Color'].default_value = (*color, 1.0)
        principled.inputs['Emission Strength'].default_value = 5.0
        mat.node_tree.links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    for seg in range(num_segments):
        seg_start_angle = -2.0 * math.pi * seg / num_segments
        seg_end_angle = -2.0 * math.pi * (seg + 1) / num_segments
        
        mesh = bpy.data.meshes.new(f"{name_prefix}_Seg{seg}")
        bm = bmesh.new()
        
        arc_points = 4
        inner_verts = []
        outer_verts = []
        
        for p in range(arc_points + 1):
            t = p / arc_points
            angle = seg_start_angle + (seg_end_angle - seg_start_angle) * t
            
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            inner_r = turning_radius - track_width / 2
            wx_inner = empty_pivot_loc[0] + (inner_r * cos_a - rear_y * sin_a)
            wy_inner = empty_pivot_loc[1] + (inner_r * sin_a + rear_y * cos_a)
            inner_verts.append(bm.verts.new((wx_inner, wy_inner, 0.06)))
            
            outer_r = turning_radius + track_width / 2
            wx_outer = empty_pivot_loc[0] + (outer_r * cos_a - rear_y * sin_a)
            wy_outer = empty_pivot_loc[1] + (outer_r * sin_a + rear_y * cos_a)
            outer_verts.append(bm.verts.new((wx_outer, wy_outer, 0.06)))
        
        for p in range(arc_points):
            bm.faces.new([inner_verts[p], inner_verts[p+1], outer_verts[p+1], outer_verts[p]])
        
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"{name_prefix}_Seg{seg}_Obj", mesh)
        bpy.context.collection.objects.link(obj)
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(bpy.data.materials[mat_name])
        
        # カット5では既に表示されている状態
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=0)
        obj.keyframe_insert(data_path="hide_render", frame=0)
    
    print(f"[シーン13] タイヤ跡軌跡 '{name_prefix}' を作成（セグメント数={num_segments}, 色={color}）")


def _create_turning_radius_diff_text_for_cut5(camera, radius_a_mm, radius_b_mm, radius_diff_mm,
                                              empty_a_loc, empty_b_loc, start_frame, end_frame, car_dimensions=None):
    """カット4と同じ方法で最小回転半径比較式テキストを作成"""
    from animation_common import create_emission_material
    
    mid_x = (empty_a_loc[0] + empty_b_loc[0]) / 2.0
    mid_y = (empty_a_loc[1] + empty_b_loc[1]) / 2.0
    
    text_container_location = (mid_x, mid_y, 2.0)
    
    bpy.ops.object.empty_add(location=text_container_location)
    text_container = bpy.context.active_object
    text_container.name = "TurningRadiusDiff_Container_Scene12"
    
    # テキストをX軸と平行にする（Z回転=0）
    # 俯瞰カメラから見たときに水平に表示されるようにする
    text_container.rotation_euler = (0.0, 0.0, 0.0)
    
    # 2行のテキスト
    text_line1 = "最小回転半径："
    text_line2 = f"{radius_b_mm}mm - {radius_a_mm}mm → {radius_diff_mm:+d}mm"
    
    # 車の色を取得
    if car_dimensions:
        car_a_color = car_dimensions.get("carA", {}).get("color", (0.5, 0.5, 0.5))
        car_b_color = car_dimensions.get("carB", {}).get("color", (0.0, 0.7, 1.0))
    else:
        car_a_color = (0.5, 0.5, 0.5)
        car_b_color = (0.0, 0.7, 1.0)
    
    colors = {
        'carb': car_b_color,
        'cara': car_a_color,
        'yellow': (1.0, 1.0, 0.2)
    }
    
    def is_fullwidth(c):
        code = ord(c)
        return (0x4E00 <= code <= 0x9FFF) or \
               (0x3000 <= code <= 0x303F) or \
               (0xFF00 <= code <= 0xFFEF) or \
               (0x3040 <= code <= 0x309F) or \
               (0x30A0 <= code <= 0x30FF)
    
    # 2行目の色マップ
    color_map_line2 = ['yellow'] * len(text_line2)
    number_blocks = []
    current_block = []
    
    for i, char in enumerate(text_line2):
        if char in '0123456789':
            current_block.append(i)
        else:
            if current_block:
                number_blocks.append(current_block)
                current_block = []
    if current_block:
        number_blocks.append(current_block)
    
    for idx, block in enumerate(number_blocks):
        if idx == 0:
            color = 'carb'
        elif idx == 1:
            color = 'cara'
        else:
            color = 'yellow'
        for pos in block:
            if pos < len(color_map_line2):
                color_map_line2[pos] = color
    
    half_spacing = 0.30
    full_spacing = 0.60
    
    all_char_objects = []
    
    # 1行目の文字を作成
    for i, char in enumerate(text_line1):
        bpy.ops.object.text_add(location=(0, 0, 0))
        char_obj = bpy.context.active_object
        char_obj.name = f"TurningRadiusDiff_Line1_Char_{i}"
        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char
        if hasattr(char_obj.data, 'size'):
            char_obj.data.size = 0.66
        mat_name = "emission_label_scene12_char_yellow"
        if mat_name not in bpy.data.materials:
            emission_mat = create_emission_material(colors['yellow'], 5.0)
            emission_mat.name = mat_name
        else:
            emission_mat = bpy.data.materials[mat_name]
        if len(char_obj.data.materials) == 0:
            char_obj.data.materials.append(emission_mat)
        char_obj.parent = text_container
        all_char_objects.append(char_obj)
    
    # 2行目の文字を作成
    for i, char in enumerate(text_line2):
        bpy.ops.object.text_add(location=(0, 0, 0))
        char_obj = bpy.context.active_object
        char_obj.name = f"TurningRadiusDiff_Line2_Char_{i}"
        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char
        if hasattr(char_obj.data, 'size'):
            char_obj.data.size = 0.66
        color_name = color_map_line2[i] if i < len(color_map_line2) else 'yellow'
        mat_name = f"emission_label_scene12_char_{color_name}"
        if mat_name not in bpy.data.materials:
            emission_mat = create_emission_material(colors[color_name], 5.0)
            emission_mat.name = mat_name
        else:
            emission_mat = bpy.data.materials[mat_name]
        if len(char_obj.data.materials) == 0:
            char_obj.data.materials.append(emission_mat)
        char_obj.parent = text_container
        all_char_objects.append(char_obj)
    
    # 文字の位置を設定（2行配置）
    def calc_line_width(text):
        widths = []
        for c in text:
            if is_fullwidth(c):
                widths.append(full_spacing)
            else:
                widths.append(half_spacing)
        return sum(widths), widths
    
    line1_width, line1_widths = calc_line_width(text_line1)
    line2_width, line2_widths = calc_line_width(text_line2)
    
    # 1行目（上部）
    current_x = -line1_width / 2.0
    char_idx = 0
    for i in range(len(text_line1)):
        local_x = current_x
        current_x += line1_widths[i]
        all_char_objects[char_idx].location = (local_x, 0.5, -0.3)
        char_idx += 1
    
    # 2行目（下部）
    current_x = -line2_width / 2.0
    for i in range(len(text_line2)):
        local_x = current_x
        current_x += line2_widths[i]
        all_char_objects[char_idx].location = (local_x, -0.5, -0.3)
        char_idx += 1
    
    # カット5では既に表示されている状態なので、スケール=1.0で固定
    for char_obj in all_char_objects:
        char_obj.scale = (1.0, 1.0, 1.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame)


def _fade_out_track_objects(name_prefix, start_frame, end_frame):
    """軌跡オブジェクトのセグメントをフェードアウト"""
    faded_count = 0
    for obj in bpy.data.objects:
        if name_prefix in obj.name and obj.type == 'MESH':
            if len(obj.data.materials) > 0:
                mat = obj.data.materials[0]
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_PRINCIPLED':
                            if 'Alpha' in node.inputs:
                                alpha_input = node.inputs['Alpha']
                                alpha_input.default_value = 1.0
                                alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
                                alpha_input.default_value = 0.0
                                alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)
                                faded_count += 1
                        elif node.type == 'BSDF_EMISSION':
                            strength_input = node.inputs['Strength']
                            current_strength = strength_input.default_value
                            strength_input.default_value = current_strength
                            strength_input.keyframe_insert(data_path="default_value", frame=start_frame)
                            strength_input.default_value = 0.0
                            strength_input.keyframe_insert(data_path="default_value", frame=end_frame)
                            faded_count += 1

    if faded_count > 0:
        print(f"[シーン13] '{name_prefix}' の {faded_count} オブジェクトをフェードアウト")


def _fade_out_text_container(container_name, start_frame, end_frame):
    """テキストコンテナをスケールでフェードアウト"""
    if container_name not in bpy.data.objects:
        print(f"[警告] '{container_name}' が見つかりません。フェードアウトをスキップします。")
        return

    text_obj = bpy.data.objects[container_name]

    text_obj.scale = (1.0, 1.0, 1.0)
    text_obj.keyframe_insert(data_path="scale", frame=start_frame)
    text_obj.scale = (0.0, 0.0, 0.0)
    text_obj.keyframe_insert(data_path="scale", frame=end_frame)

    for child in text_obj.children:
        if child.type == 'MESH' and len(child.data.materials) > 0:
            mat = child.data.materials[0]
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_EMISSION':
                        current_strength = node.inputs['Strength'].default_value
                        node.inputs['Strength'].default_value = current_strength
                        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)
                        node.inputs['Strength'].default_value = 0.0
                        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=end_frame)

    print(f"[シーン13] '{container_name}' をフェードアウト（スケール→0）")


def _create_acceleration_texts(car_a, car_b, accel_a, accel_b, start_frame, end_frame):
    """各車の上に0-100km/h加速時間テキストを表示（車にペアレントして追従）"""
    from animation_common import create_emission_material

    # 車のマテリアルから色を取得して、同じ色で発光させる
    car_a_color = (0.5, 0.5, 0.5)  # デフォルトグレー系
    car_b_color = (0.0, 0.7, 1.0)  # デフォルト鮮やかな青

    # 車のマテリアルから色を取得
    for obj in [car_a, car_b]:
        if obj and len(obj.data.materials) > 0:
            mat = obj.data.materials[0]
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        base_color = node.inputs['Base Color'].default_value
                        if obj.name.startswith('CarA'):
                            car_a_color = (base_color[0], base_color[1], base_color[2])
                        elif obj.name.startswith('CarB'):
                            car_b_color = (base_color[0], base_color[1], base_color[2])

    mat_name_a = "emission_accel_text_carA"
    mat_name_b = "emission_accel_text_carB"

    if mat_name_a not in bpy.data.materials:
        accel_mat_a = create_emission_material(car_a_color, 5.0)
        accel_mat_a.name = mat_name_a
    else:
        accel_mat_a = bpy.data.materials[mat_name_a]

    if mat_name_b not in bpy.data.materials:
        accel_mat_b = create_emission_material(car_b_color, 5.0)
        accel_mat_b.name = mat_name_b
    else:
        accel_mat_b = bpy.data.materials[mat_name_b]

    # CarAのテキスト: "0-100m X.Xs"
    text_a = f"0-100m {accel_a}s"
    _create_car_acceleration_text(car_a, text_a, accel_mat_a, "AccelText_CarA", start_frame, end_frame)

    # CarBのテキスト
    text_b = f"0-100m {accel_b}s"
    _create_car_acceleration_text(car_b, text_b, accel_mat_b, "AccelText_CarB", start_frame, end_frame)

    print(f"[シーン14] 加速時間テキスト carA='{text_a}', carB='{text_b}' を作成")


def _create_car_acceleration_text(car_obj, text, material, container_name, start_frame, end_frame):
    """単一車の加速時間テキストを作成し、車にペアレント設定"""
    import bpy

    # Emptyを車の真上に作成
    bpy.ops.object.empty_add(location=(0, 0, 0))
    text_container = bpy.context.active_object
    text_container.name = container_name

    # 車にペアレント設定
    bpy.context.view_layer.objects.active = car_obj
    text_container.parent = car_obj
    text_container.location = (0.0, 0.0, 2.0)  # 車の上面から2.0mの位置
    # テキストを90度時計回りに回転（車と水平に表示）
    text_container.rotation_euler = (0.0, 0.0, -math.pi / 2)

    half_spacing = 0.15
    full_spacing = 0.30

    def is_fullwidth(c):
        code = ord(c)
        return (0x4E00 <= code <= 0x9FFF) or \
               (0x3000 <= code <= 0x303F) or \
               (0xFF00 <= code <= 0xFFEF) or \
               (0x3040 <= code <= 0x309F) or \
               (0x30A0 <= code <= 0x30FF)

    char_objects = []

    for i, char in enumerate(text):
        bpy.ops.object.text_add(location=(0, 0, 0))
        char_obj = bpy.context.active_object
        char_obj.name = f"{container_name}_Char_{i}"

        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char

        # Blenderのデフォルトフォントを使用（車名テキストと同じ）
        default_font = bpy.data.fonts.get("Levenim MT Bold")
        if not default_font:
            # デフォルトフォントが存在しない場合は、既存のフォントから取得
            for font in bpy.data.fonts:
                default_font = font
                break
        if default_font:
            char_obj.data.font = default_font

        if hasattr(char_obj.data, 'size'):
            char_obj.data.size = 0.35  # 車名テキストと同じサイズ

        char_obj.scale = (1.0, 1.0, 1.0)

        if len(char_obj.data.materials) == 0:
            char_obj.data.materials.append(material)

        char_obj.parent = text_container
        bpy.context.scene.collection.objects.link(char_obj)

        char_objects.append(char_obj)

    def calc_line_width(text):
        widths = []
        for c in text:
            if is_fullwidth(c):
                widths.append(full_spacing)
            else:
                widths.append(half_spacing)
        return sum(widths), widths

    line_width, char_widths = calc_line_width(text)

    current_x = -line_width / 2.0
    for i, char_obj in enumerate(char_objects):
        local_x = current_x
        current_x += char_widths[i]
        char_obj.location = (local_x, 0.0, 0.0)

    # フェードインアニメーション（1秒）
    fade_in_end = start_frame + 24

    # 5秒間表示維持、その後3秒かけてゆっくりフェードアウト
    hold_duration = 120  # 5秒（24fps × 5 = 120フレーム）
    fade_out_start = fade_in_end + hold_duration
    fade_out_end = fade_out_start + 72  # 3秒（24fps × 3 = 72フレーム）

    for char_obj in char_objects:
        char_obj.scale = (0.0, 0.0, 0.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame)

        char_obj.scale = (1.0, 1.0, 1.0)
        char_obj.keyframe_insert(data_path="scale", frame=fade_in_end)

        # 5秒間表示されたまま維持
        char_obj.keyframe_insert(data_path="scale", frame=fade_out_start)

        # 3秒かけてフェードアウト完了（消える）
        char_obj.scale = (0.0, 0.0, 0.0)
        char_obj.keyframe_insert(data_path="scale", frame=fade_out_end)


def _attach_lights_to_cars(car_a, car_b, start_frame, end_frame):
    """各車に個別のライトをペアレント設定して、車がどこに行っても明るく照らす"""
    
    # --- CarA用のライトを作成 ---
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 0))
    light_a = bpy.context.active_object
    light_a.name = "CarA_Light"
    light_a.data.energy = 800   # 元のKeyLightと同じ明るさ
    light_a.data.size = 3       # 元のKeyLightと同じサイズ
    if hasattr(light_a.data, 'distance'):
        light_a.data.distance = 0
    if hasattr(light_a.data, 'use_custom_distance'):
        light_a.data.use_custom_distance = False
    
    # CarAにペアレント設定（車の斜め上に配置）
    bpy.context.view_layer.objects.active = car_a
    light_a.parent = car_a
    light_a.location = (0.0, 0.0, 3.0)  # ローカル座標で車の真上3m
    light_a.rotation_euler = (-math.pi / 4, 0.0, 0.0)  # 斜め下向き
    
    # --- CarB用のライトを作成 ---
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 0))
    light_b = bpy.context.active_object
    light_b.name = "CarB_Light"
    light_b.data.energy = 800   # 元のKeyLightと同じ明るさ
    light_b.data.size = 3       # 元のKeyLightと同じサイズ
    if hasattr(light_b.data, 'distance'):
        light_b.data.distance = 0
    if hasattr(light_b.data, 'use_custom_distance'):
        light_b.data.use_custom_distance = False
    
    # CarBにペアレント設定
    bpy.context.view_layer.objects.active = car_b
    light_b.parent = car_b
    light_b.location = (0.0, 0.0, 3.0)  # ローカル座標で車の真上3m
    light_b.rotation_euler = (-math.pi / 4, 0.0, 0.0)  # 斜め下向き
    
    # --- 既存のライトはエネルギー変更しない（元の明るさを維持）---
    bpy.context.view_layer.update()
    
    print(f"[シーン14] CarA_Light (energy=800, size=3) を CarA にペアレント設定")
    print(f"[シーン14] CarB_Light (energy=800, size=3) を CarB にペアレント設定")
