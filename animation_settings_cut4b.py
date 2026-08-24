"""
アニメーション設定モジュール - カット 4b
フレーム 2256-2664（カメラのみを動かす回転カット、17秒）を処理する。

使い方:
    from animation_settings_cut4b import setup_cut4b_animations
    setup_cut4b_animations(scene, camera, imported_cars, previous_state=None, car_dimensions=None)

【処理内容】
- フェーズ 1 (5秒): カット4終了時の俯瞰位置から、車の左側（X=-4m）でZ=1.5mまでゆっくり降りてくる
- フェーズ 2 (7秒): 車の左側から右側に半周（orbit）。常に両台の中央を注視
- フェーズ 3 (5秒): 車の右側から開始位置（俯瞰）まで戻る

車の位置は変更しない。カメラのみをアニメーションさせる。
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at


def setup_cut4b_animations(scene, camera, imported_cars, previous_state=None, car_dimensions=None):
    """
    カット 4b のアニメーションを設定（フレーム 2256-2592）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        previous_state: CutState — 前のカットの最終状態（オプション、未指定時は固定位置使用）
        car_dimensions: {key: {"turning_radius": mm}} 車の寸法情報

    Returns:
        CutState: このカットの最終状態
    """
    from animation_cut_positions import CAMERA_POSITIONS, get_car_positions

    # Cut4終了時の車の位置を計算（スライド後の位置）
    # Cut4のシーン14で slide_distance=1.5 で車が左右にスライドしている
    car_a_base, car_b_base = get_car_positions()
    slide_distance = 1.5  # Cut4と同じスライド距離
    
    if car_dimensions:
        turning_radius_a = car_dimensions.get("carA", {}).get("turning_radius", 5200) / 1000.0
        turning_radius_b = car_dimensions.get("carB", {}).get("turning_radius", 6000) / 1000.0
    else:
        turning_radius_a = 5.2
        turning_radius_b = 6.0

    # Cut4のEmpty開始位置（回転中心はX=0からturning_radiusだけ左側）
    empty_a_start_loc = (-turning_radius_a, car_a_base[1], car_a_base[2])
    empty_b_start_loc = (-turning_radius_b, car_b_base[1], car_b_base[2])
    
    # Cut4のシーン14でのスライド後のEmpty位置
    empty_a_end_loc = (empty_a_start_loc[0] - slide_distance, empty_a_start_loc[1], empty_a_start_loc[2])
    empty_b_end_loc = (empty_b_start_loc[0] + slide_distance, empty_b_start_loc[1], empty_b_start_loc[2])

    # Cut4終了時のカメラ位置は真上からの俯瞰視点（Yオフセットなし）
    mid_turn_center_x = (empty_a_end_loc[0] + empty_b_end_loc[0]) / 2.0
    mid_turn_center_y = (empty_a_end_loc[1] + empty_b_end_loc[1]) / 2.0

    loc_cut4_end = (mid_turn_center_x, mid_turn_center_y, 25.0)
    target_cam = (mid_turn_center_x, mid_turn_center_y, 0.0)
    direction = Vector(target_cam) - Vector(loc_cut4_end)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    rot_cut4_end = rot_quat.to_euler()

    if previous_state is not None:
        loc_cut4_end = previous_state.camera_loc
        rot_cut4_end = previous_state.camera_rot

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # ============================================================
    # Cut4終了時の車の位置を直接設定（Empty不使用）
    # カット4bはカメラのみを動かすので、車の位置・向きを固定するだけ
    # ============================================================
    print("\n=== 【カット 4b】Cut4終了時の車位置を復元 ===")

    # 既存のEmptyを削除（再実行時の競合防止）
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

    # 車の親をNoneに戻す（前の親子関係を解除）
    if car_a.parent is not None:
        car_a.parent = None
    if car_b.parent is not None:
        car_b.parent = None

    # 車のアニメーションデータをクリア
    if car_a.animation_data:
        car_a.animation_data_clear()
    if car_b.animation_data:
        car_b.animation_data_clear()

    # Cut4終了時の車のグローバル位置を計算して直接設定
    # empty_end_loc + (turning_radius, 0, 0) = 車のグローバル位置
    car_a_global_x = empty_a_end_loc[0] + turning_radius_a
    car_b_global_x = empty_b_end_loc[0] + turning_radius_b

    car_a.location = (car_a_global_x, empty_a_end_loc[1], empty_a_end_loc[2])
    car_a.rotation_euler = (0.0, 0.0, -math.pi / 2)

    car_b.location = (car_b_global_x, empty_b_end_loc[1], empty_b_end_loc[2])
    car_b.rotation_euler = (0.0, 0.0, -math.pi / 2)

    bpy.context.view_layer.update()

    print(f"[カット4b] CarA位置: {car_a.location}")
    print(f"[カット4b] CarB位置: {car_b.location}")

    # ============================================================
    # カット 4b のフレーム定義
    # ============================================================
    cut4b_start = 2136  # 【改訂】カット1短縮で120フレームずらす
    phase1_end = cut4b_start + 312   # 13秒（下降）: 24fps × 13 = 312
    phase2_end = phase1_end + 144   # 6秒（回り込み）: 24fps × 6 = 144
    cut4b_end = phase2_end + 312    # 13秒（戻り）: 24fps × 13 = 312 → 合計=3024

    print("\n=== 【カット 4b】カメラ回転カット設定開始 ===")
    print(f"フレーム範囲: {cut4b_start}-{cut4b_end} (17秒)")

    # ----------------------------------------------------------
    # フレーム0に俯瞰位置・下向きのキーフレームを追加
    # カット4bを独立実行時、Blender起動時にデフォルトカメラ（右向き）が
    # 表示される問題を解消する
    # 俯瞰時は直接Euler=(0,0,0)を設定し、不要なZ回転を排除する
    # ----------------------------------------------------------
    camera.location = Vector(loc_cut4_end)
    camera.rotation_euler = (0.0, 0.0, 0.0)  # 真上から下を見る場合は(0,0,0)で十分
    camera.keyframe_insert(data_path="location", frame=0)
    camera.keyframe_insert(data_path="rotation_euler", frame=0)
    print(f"[フレーム0] 初期カメラ位置: {loc_cut4_end}（俯瞰・下向き）")
    print(f"[フレーム0] カメラ回転: (0, 0, 0)")

    # カット4終了時の注視点を正確に継承（車の向きを画面で「下」にする）
    # このターゲットはフェーズ1・フェーズ3（俯瞰位置）で使用し、前後のカットとカメラ回転が一致する
    if previous_state is not None:
        cut4_look_at = Vector((loc_cut4_end[0], loc_cut4_end[1], 0.0))
    else:
        default_turning_radius_a = 5.2
        default_turning_radius_b = 6.0
        car_a_end, car_b_end = get_car_positions()
        empty_a_loc = (-default_turning_radius_a, car_a_end[1], car_a_end[2])
        empty_b_loc = (-default_turning_radius_b, car_b_end[1], car_b_end[2])
        mid_turn_center_x = (empty_a_loc[0] + empty_b_loc[0]) / 2.0
        mid_turn_center_y = (empty_a_loc[1] + empty_b_loc[1]) / 2.0
        cut4_look_at = Vector((mid_turn_center_x, mid_turn_center_y, 0.0))

    # ============================================================
    # 両台の車の中央を回転中心にする
    # Emptyの子オブジェクトなので、グローバル座標から計算する
    # ============================================================
    car_a_global_loc = car_a.matrix_world.to_translation()
    car_b_global_loc = car_b.matrix_world.to_translation()
    cars_center_x = (car_a_global_loc.x + car_b_global_loc.x) / 2.0
    cars_center_y = (car_a_global_loc.y + car_b_global_loc.y) / 2.0

    # カメラの回転中心：両台の車の中央
    orbit_center = Vector((cars_center_x, cars_center_y, 1.0))

    print(f"[カット4b] CarAグローバル位置: {car_a_global_loc}")
    print(f"[カット4b] CarBグローバル位置: {car_b_global_loc}")
    print(f"[カット4b] 車の中央: ({cars_center_x}, {cars_center_y})")

    print(f"[カット4b] cut4_look_at: {cut4_look_at}（俯瞰時の注視点、前後カットと一致）")
    print(f"[カット4b] orbit_center: {orbit_center}（両台の車の中央）")

    # 回転半径・高さ（フェーズ1・2で共通）
    orbit_radius = 6.5  # 回転半径（車から6.5m、さらに離して広く撮る）
    orbit_height = 1.5  # 回転高さ（車の腰あたり）

    # 降りる・上がる位置を「前方寄り」にずらす角度オフセット（ラジアン）
    # π/6 (30度) ずらすと、真横(180度)→左前方(150度)、右横(0度)→右前方(30度)
    side_angle_offset = math.pi / 6  # 30度前方寄り

    # 俯瞰位置の閾値（Z位置がこの値より大きい場合は真下を向く）
    OVERHEAD_THRESHOLD = 15.0

    # ============================================================
    # フェーズ 1: 下降（5秒、120フレーム）
    # カット4終了時の俯瞰位置から、車の左側（X=-4m）でZ=1.5mまで降りてくる
    # 注視点: cut4_look_at → orbit_center に補間（開始時は前後カットと一致）
    # ============================================================
    print("\n--- フェーズ 1: 下降 ---")

    num_phase1_frames = 20
    for i in range(num_phase1_frames + 1):
        t = i / num_phase1_frames
        frame = cut4b_start + int((phase1_end - cut4b_start) * t)

        # ease-in-out で滑らかに移動
        eased_t = t * t * (3.0 - 2.0 * t)

        # 開始位置: カット4終了時の俯瞰位置
        start_loc = Vector(loc_cut4_end)
        # 終了位置: 車の左側（X負方向）、Z=1.5m
        # 終了位置: 車の左前方（真横ではなく前方寄り）
        side_angle = math.pi + side_angle_offset  # 210度（左前方）
        end_loc = Vector((
            orbit_center.x + orbit_radius * math.cos(side_angle),
            orbit_center.y + orbit_radius * math.sin(side_angle),
            orbit_height
        ))

        cam_loc = start_loc.lerp(end_loc, eased_t)
        camera.location = cam_loc

        # 俯瞰位置（Zが高い）の場合は直接Euler=(0,0,0)を設定
        # それ以外の場合は set_camera_look_at を使用
        if cam_loc.z > OVERHEAD_THRESHOLD:
            camera.rotation_euler = (0.0, 0.0, 0.0)
        else:
            # 注視点: 俯瞰時はcut4_look_at、横位置時はorbit_center に補間
            current_look_at = cut4_look_at.lerp(orbit_center, eased_t)
            set_camera_look_at(camera, cam_loc, current_look_at)
        
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)

    # フェーズ1終了位置を保存
    # フェーズ1終了位置（左前方）
    side_angle_start = math.pi + side_angle_offset  # 210度
    phase1_end_loc = Vector((
        orbit_center.x + orbit_radius * math.cos(side_angle_start),
        orbit_center.y + orbit_radius * math.sin(side_angle_start),
        orbit_height
    ))
    camera.location = phase1_end_loc
    set_camera_look_at(camera, phase1_end_loc, orbit_center)
    rot_phase1_end = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=phase1_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=phase1_end)

    print(f"[フレーム{cut4b_start}] 開始位置: {loc_cut4_end}（俯瞰）")
    print(f"[フレーム{phase1_end}] 終了位置: {phase1_end_loc}（左側低位置）")

    # ============================================================
    # フェーズ 2: 回り込み（7秒、168フレーム）
    # 車の左側から右側に半周（orbit）。常に両台の中央を注視
    # ============================================================
    print("\n--- フェーズ 2: 回り込み ---")


    num_phase2_frames = 30
    for i in range(num_phase2_frames + 1):
        t = i / num_phase2_frames
        frame = phase1_end + int((phase2_end - phase1_end) * t)

        # ease-in-out で滑らかに回転
        eased_t = t * t * (3.0 - 2.0 * t)

        # 左前方から右前方に回転（前方経由で左回り）
        start_angle = math.pi + side_angle_offset   # 210度（左前方）
        end_angle = 2 * math.pi - side_angle_offset # 330度（右前方）
        angle = start_angle + (end_angle - start_angle) * eased_t

        cam_x = orbit_center.x + orbit_radius * math.cos(angle)
        cam_y = orbit_center.y + orbit_radius * math.sin(angle)
        cam_z = orbit_height

        cam_loc = Vector((cam_x, cam_y, cam_z))
        camera.location = cam_loc
        set_camera_look_at(camera, cam_loc, orbit_center)
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)

    # フェーズ2終了位置を保存
    # フェーズ2終了位置（右前方）
    side_angle_end = 2 * math.pi - side_angle_offset  # 330度
    phase2_end_loc = Vector((
        orbit_center.x + orbit_radius * math.cos(side_angle_end),
        orbit_center.y + orbit_radius * math.sin(side_angle_end),
        orbit_height
    ))
    camera.location = phase2_end_loc
    set_camera_look_at(camera, phase2_end_loc, orbit_center)
    rot_phase2_end = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=phase2_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=phase2_end)

    print(f"[フレーム{phase1_end}] 開始位置: {phase1_end_loc}（左側）")
    print(f"[フレーム{phase2_end}] 終了位置: {phase2_end_loc}（右側）")

    # ============================================================
    # フェーズ 3: 戻り（5秒、120フレーム）
    # 車の右側から開始位置（俯瞰）まで戻る
    # 注視点: orbit_center → cut4_look_at に補間（終了時は前後カットと一致）
    # ============================================================
    print("\n--- フェーズ 3: 戻り ---")

    num_phase3_frames = 20
    for i in range(num_phase3_frames + 1):
        t = i / num_phase3_frames
        frame = phase2_end + int((cut4b_end - phase2_end) * t)

        # ease-in-out で滑らかに移動
        eased_t = t * t * (3.0 - 2.0 * t)

        # 開始位置: フェーズ2終了時の右側低位置
        start_loc = phase2_end_loc
        # 終了位置: Z=15.0mの斜め上からの位置
        end_loc = Vector((loc_cut4_end[0], loc_cut4_end[1], 15.0))

        cam_loc = start_loc.lerp(end_loc, eased_t)
        camera.location = cam_loc

        # 注視点: 常に車の中央(orbit_center)を向く（Z=8.0でも車が見えるように）
        set_camera_look_at(camera, cam_loc, orbit_center)
        
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)

    # 最終位置を保存（Z=15.0mで斜め上からの位置）
    final_loc = Vector((loc_cut4_end[0], loc_cut4_end[1], 15.0))
    camera.location = final_loc
    # 注視点は常に車の中央(orbit_center)に向ける（車が見えるように）
    set_camera_look_at(camera, final_loc, orbit_center)
    rot_final = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=cut4b_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=cut4b_end)

    print(f"[フレーム{phase2_end}] 開始位置: {phase2_end_loc}（右側）")
    print(f"[フレーム{cut4b_end}] 終了位置: {final_loc}（俯瞰、カット5開始位置と同じ）")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 4b アニメーション完了 ===")

    from animation_common import CutState
    return CutState(
        car_a_loc=tuple(car_a.location),
        car_b_loc=tuple(car_b.location),
        camera_loc=tuple(final_loc),
        camera_rot=(rot_final.x, rot_final.y, rot_final.z),
    )
