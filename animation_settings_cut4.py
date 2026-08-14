"""
アニメーション設定モジュール - カット 4
フレーム 1584-1992（シーン 10、シーン 11、停止付き）を処理する。

使い方:
    from animation_settings_cut4 import setup_cut4_animations
    setup_cut4_animations(scene, camera, imported_cars, cut3_result, car_dimensions=None)

【処理内容】
- シーン 10: 2台の車を横並びに移動（5秒）＋ CarBを不透明に戻す ＋ 最低地上高差表示をフェードアウト
- 停止: 2秒
- シーン 11: 最小回転半径で両台が右回り1週（10秒）
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at, _calculate_turning_radius_difference, create_emission_material

def setup_cut4_animations(scene, camera, imported_cars, previous_state, car_dimensions=None):
    """
    カット 4 のアニメーションを設定（フレーム 1584-1992）

    【修正: カット完全分離】前のカットの最終状態のみを受け取り、
    変数を共有しない。animation_data_clear() は使用しない。

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        previous_state: CutState — 前のカットの最終状態（位置情報のみ）
        car_dimensions: {key: {"turning_radius": mm}} 車の寸法情報

    Returns:
        CutState: このカットの最終状態
    """
    if previous_state is None:
        print("エラー: 前のカットの状態が指定されていません")
        return None

    # カット完全分離: 前のカットの最終位置のみを取得
    car_a_end = previous_state.car_a_loc
    car_b_end = previous_state.car_b_loc
    loc_scene8_end = previous_state.camera_loc
    rot_scene8_end = previous_state.camera_rot

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    target = (0.0, 0.0, 1.5)

    # ============================================================
    # 【カット 4】シーン 10: フレーム 1584-1704（横並び移動＋CarB不透明化＋地上高表示フェードアウト、5秒）
    #                    停止: フレーム 1704-1752（2秒）
    # ============================================================
    print("\n=== 【カット 4】シーン 10 設定開始 ===")

    scene10_start = 1584
    scene10_end = 1704  # 5秒間（24fps × 5 = 120フレーム）
    scene10_pause_end = 1752  # 停止2秒（24fps × 2 = 48フレーム）

    # カメラ: シーン8の位置から始まり、車に対して斜め上の少し前にゆっくり移動
    # 開始位置: シーン8の最終位置（左側低位置）
    camera.location = loc_scene8_end
    camera.rotation_euler = rot_scene8_end
    camera.keyframe_insert(data_path="location", frame=scene10_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene10_start)
    
    # 終了位置: 2台の車の中央に対して斜め上の少し前
    # 車の中央位置 (carA=-2.5, carB=2.5 の中心 = X=0)
    center_x = 0.0
    center_y = (car_a_end[1] + car_b_end[1]) / 2.0
    # 斜め上: Zを高く、前方向: Yを負の方向に（車を向いてもっと手前）
    camera_scene10_end_loc = (center_x, center_y - 6.0, 12.0)
    camera.location = camera_scene10_end_loc
    camera.keyframe_insert(data_path="location", frame=scene10_end)
    
    # カメラの注視点を車の中央に設定して回転を計算
    look_at_target = Vector((center_x, center_y, 1.5))
    set_camera_look_at(camera, camera_scene10_end_loc, look_at_target)
    rot_scene10_end = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="rotation_euler", frame=scene10_end)
    
    print(f"[フレーム{scene10_start}] カメラ開始位置: {loc_scene8_end}")
    print(f"[フレーム{scene10_end}] カメラ終了位置: {camera_scene10_end_loc}（斜め上の少し前）")

    # 最小回転半径を取得（mm → m に変換）
    if car_dimensions:
        turning_radius_a = car_dimensions.get("carA", {}).get("turning_radius", 5200) / 1000.0
        turning_radius_b = car_dimensions.get("carB", {}).get("turning_radius", 6000) / 1000.0
    else:
        turning_radius_a = 5.2  # デフォルト 5.2m
        turning_radius_b = 6.0  # デフォルト 6.0m

    print(f"[シーン10] CarA 最小回転半径: {turning_radius_a}m, CarB 最小回転半径: {turning_radius_b}m")

    # Empty親オブジェクトをシーン10から作成（親子関係をフレームに関係なく適用するため）
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

    # Emptyを作成（回転中心はX=0からturning_radiusだけ左側）
    empty_a = bpy.data.objects.new("CarA_TurnPivot", None)
    bpy.context.collection.objects.link(empty_a)
    empty_a.location = (-turning_radius_a, car_a_end[1], car_a_end[2])
    empty_a.rotation_euler = (0.0, 0.0, 0.0)

    empty_b = bpy.data.objects.new("CarB_TurnPivot", None)
    bpy.context.collection.objects.link(empty_b)
    empty_b.location = (-turning_radius_b, car_b_end[1], car_b_end[2])
    empty_b.rotation_euler = (0.0, 0.0, 0.0)

    # 車をEmptyの子オブジェクトにする
    # 【重要】前のカットからのアニメーションデータをクリア（Blender 5.xではキーフレーム評価がローカル位置を上書きするため）
    if car_a.animation_data:
        car_a.animation_data_clear()
    if car_b.animation_data:
        car_b.animation_data_clear()

    bpy.context.view_layer.objects.active = empty_a
    car_a.parent = empty_a
    car_a.location = (turning_radius_a, 0.0, 0.0)
    car_a.rotation_euler = (0.0, 0.0, math.pi / 2)

    bpy.context.view_layer.objects.active = empty_b
    car_b.parent = empty_b
    car_b.location = (turning_radius_b, 0.0, 0.0)
    car_b.rotation_euler = (0.0, 0.0, math.pi / 2)

    bpy.context.view_layer.update()

    print(f"[シーン10] Empty親オブジェクトを作成（アニメーションデータクリア済み）")
    print(f"  CarA_TurnPivot: {empty_a.location}")
    print(f"  CarB_TurnPivot: {empty_b.location}")
    print(f"  CarA グローバル位置: {car_a.matrix_world.to_translation()}")
    print(f"  CarB グローバル位置: {car_b.matrix_world.to_translation()}")

    # Emptyの回転キーフレームを設定（シーン10では回転しない）
    empty_a.rotation_euler.z = 0.0
    empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_start)
    empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_end)
    empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_pause_end)

    empty_b.rotation_euler.z = 0.0
    empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_start)
    empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_end)
    empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene10_pause_end)

    print(f"[フレーム{scene10_start}] シーン 10 開始：車はX=0位置（Emptyの子として制御）")
    print(f"[フレーム{scene10_end}] シーン 10 終了：車はX=0位置を維持")

    # --- 最低地上高差表示をフェードアウト（早く消えるように1秒で完了）---
    fade_out_end = scene10_start + 24  # 1秒（24fps × 1 = 24フレーム）
    _fade_out_ground_clearance_text(scene10_start, fade_out_end)

    # --- 停止（2秒）: フレーム 1752 ---
    camera.location = camera_scene10_end_loc
    camera.rotation_euler = rot_scene10_end
    camera.keyframe_insert(data_path="location", frame=scene10_pause_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene10_pause_end)
    print(f"[フレーム{scene10_pause_end}] 停止（2秒）")

    # ============================================================
    # 【カット 4】シーン 11: フレーム 1752-1992（最小回転半径で右回り1週、10秒）
    # Empty親オブジェクト手法で実装（シーン10で作成したEmptyをそのまま使用）
    # ============================================================
    print("\n=== 【カット 4】シーン 11 設定開始 ===")

    scene11_start = 1752
    scene11_car_a_end = 1992  # CarAの回転終了（10秒間、24fps × 10 = 240フレーム）
    car_b_delay = 48  # 2秒遅延（24fps × 2）
    scene11_car_b_end = scene11_car_a_end + car_b_delay  # CarBはCarA終了後2秒で完了
    scene11_end = scene11_car_b_end  # シーン全体の終了フレーム

    print(f"[シーン11] CarA 最小回転半径: {turning_radius_a}m, CarB 最小回転半径: {turning_radius_b}m")

    # --- CarB を不透明に戻す（シーン11の最初の1秒で完了）---
    opaque_end = scene11_start + 24  # 1秒（24fps × 1 = 24フレーム）
    _setup_car_b_opaque_for_scene10(car_b, scene11_start, opaque_end)
    print(f"[フレーム{scene11_start}-{opaque_end}] CarB 不透明化：Alpha 0.8→1.0（最初の1秒で完了）")

    # --- EmptyのZ軸回転にキーフレームを設定（-Z方向 = 時計回り = 右回り）---
    # CarAが通常通り出发し、CarBは2秒（48フレーム）遅れて出发する
    # CarAが先に戻り、その2秒後にCarBも戻る
    # ease-in/ease-outでゆっくり加速・減速するように角度を計算
    num_keyframes = 25  # 24分割で滑らかに
    total_angle = -2.0 * math.pi  # -360度（右回り）

    def ease_in_out(t):
        """ease-in-out曲線: 0→1 の範囲でゆっくり加速・減速"""
        return t * t * (3.0 - 2.0 * t)

    # CarA: scene11_start から scene11_car_a_end まで回転（ease-in/out）
    car_a_duration = scene11_car_a_end - scene11_start
    for i in range(num_keyframes):
        frame = scene11_start + int(car_a_duration * i / (num_keyframes - 1))
        t = i / (num_keyframes - 1)  # 0 → 1
        eased_t = ease_in_out(t)
        angle = total_angle * eased_t  # ease-in/out適用

        empty_a.rotation_euler.z = angle
        empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
    # CarAが戻った後、scene11_endまで静止
    empty_a.rotation_euler.z = total_angle
    empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene11_end)

    # CarB: CarA出发から2秒（48フレーム）後に出发（ease-in/out）
    car_b_start = scene11_start + car_b_delay
    # CarBはdelay分だけ待機（angle=0で固定）
    empty_b.rotation_euler.z = 0.0
    empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene11_start)
    empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=car_b_start)
    # CarBの回転アニメーション（delay後のフレーム範囲で1週完了、ease-in/out）
    car_b_duration = scene11_car_b_end - car_b_start
    for i in range(num_keyframes):
        frame = car_b_start + int(car_b_duration * i / (num_keyframes - 1))
        t = i / (num_keyframes - 1)  # 0 → 1
        eased_t = ease_in_out(t)
        angle = total_angle * eased_t  # ease-in/out適用

        empty_b.rotation_euler.z = angle
        empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)


    print(f"[フレーム{scene11_start}] シーン11開始：CarAが回転を開始（EmptyのZ回転=0）")
    print(f"[フレーム{car_b_start}] CarBが回転を開始（CarA出发から{car_b_delay}フレーム={car_b_delay/24:.1f}秒後）")
    print(f"[フレーム{scene11_car_a_end}] CarAが元の位置に戻る（右回り1週完了）")
    print(f"[フレーム{scene11_car_b_end}] CarBが元の位置に戻る（CarA戻りから{car_b_delay}フレーム={car_b_delay/24:.1f}秒後）")

    # CarBの軌跡表示用開始フレームを保存
    car_b_track_start = car_b_start

    # カメラ: 上から両台の回転を俯瞰できる位置に移動
    # 2つの回転中心の中間点上空
    mid_turn_center_x = (empty_a.location.x + empty_b.location.x) / 2.0
    mid_turn_center_y = (empty_a.location.y + empty_b.location.y) / 2.0
    
    # カメラ開始位置（シーン10の最終位置）
    camera.location = camera_scene10_end_loc
    camera.rotation_euler = rot_scene10_end
    camera.keyframe_insert(data_path="location", frame=scene11_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene11_start)
    
    # カメラ終了位置（回転円の中心上空から斜め上）
    camera_scene11_end_loc = (mid_turn_center_x, mid_turn_center_y - 3.0, 25.0)
    look_at_target = Vector((mid_turn_center_x, mid_turn_center_y, 0.0))
    camera.location = camera_scene11_end_loc
    set_camera_look_at(camera, camera_scene11_end_loc, look_at_target)
    rot_scene11_end = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=scene11_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene11_end)

    print(f"[フレーム{scene11_start}] カメラ開始位置: {camera_scene10_end_loc}")
    print(f"[フレーム{scene11_end}] カメラ終了位置: {camera_scene11_end_loc}（俯瞰視点）")

    # 回転半径の可視化：円を描くガイドラインを作成
    # CarAは通常通り、CarBは出发遅延に合わせて軌跡表示を遅らせる
    _create_turning_radius_visualization(empty_a.location, turning_radius_a, "CarA_TurningCircle", scene11_start, scene11_car_a_end, color=(1.0, 0.2, 0.2))
    _create_turning_radius_visualization(empty_b.location, turning_radius_b, "CarB_TurningCircle", car_b_track_start, scene11_car_b_end, color=(0.2, 0.2, 1.0))

    # タイヤ跡軌跡を作成（発光曲線）
    # CarAは通常通り、CarBは出发遅延に合わせて軌跡表示を遅らせる
    _create_tire_track(car_a, empty_a, turning_radius_a, "CarA_TireTrack", scene11_start, scene11_car_a_end, color=(1.0, 0.2, 0.2))
    _create_tire_track(car_b, empty_b, turning_radius_b, "CarB_TireTrack", car_b_track_start, scene11_car_b_end, color=(0.2, 0.2, 1.0))

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 4 アニメーション完了 ===")

    # 結果を返す
    # 【修正: カット完全分離】CutState 形式で最終状態のみを返す
    from animation_common import CutState
    return CutState(
        car_a_loc=(0.0, car_a_end[1], car_a_end[2]),  # 1週するのでX=0に戻る
        car_b_loc=(0.0, car_b_end[1], car_b_end[2]),
        camera_loc=camera_scene11_end_loc,
        camera_rot=(rot_scene11_end.x, rot_scene11_end.y, rot_scene11_end.z),
    )


def _create_turning_radius_visualization(center, radius, name_prefix, start_frame, end_frame, color=(1.0, 1.0, 1.0)):
    """回転半径を可視化する円ガイドラインを作成（車が通過した後に軌跡として表示）
    
    円を複数のセグメントに分割し、フレームごとに順に表示することで
    徐々に描画される軌跡を実現する。
    
    車の動きに合わせて軌跡を表示するために、線形タイミングに遅延を追加。
    
    Parameters:
        center: 回転中心の座標 (x, y, z)
        radius: 回転半径 (m)
        name_prefix: オブジェクト名のプレフィックス
        start_frame: 開始フレーム
        end_frame: 終了フレーム
        color: ガイドラインの色 (R, G, B) デフォルトは白
    """
    import bmesh
    
    # セグメント数
    num_segments = 60
    
    # 軌跡幅（細く設定）
    track_width = 0.05
    
    # 発光マテリアルを作成（EEVEE対応: Principled BSDF使用）
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
        try:
            mat.blend_method = 'HASHED'
        except AttributeError:
            pass
        try:
            mat.shadow_method = 'NONE'
        except AttributeError:
            pass
    
    # 各セグメントを細長い面として作成
    for seg in range(num_segments):
        seg_start_angle = -2.0 * math.pi * seg / num_segments
        seg_end_angle = -2.0 * math.pi * (seg + 1) / num_segments
        
        # メッシュを作成
        mesh_name = f"{name_prefix}_Seg{seg}"
        mesh = bpy.data.meshes.new(mesh_name)
        
        # bmeshを使用してポリゴンを追加
        bm = bmesh.new()
        
        # 頂点を作成（内側と外側の2列）
        arc_points = 3
        inner_verts = []
        outer_verts = []
        
        for p in range(arc_points + 1):
            t = p / arc_points
            angle = seg_start_angle + (seg_end_angle - seg_start_angle) * t
            
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # 内側の点
            inner_r = radius - track_width / 2
            wx_inner = center[0] + (inner_r * cos_a)
            wy_inner = center[1] + (inner_r * sin_a)
            inner_verts.append(bm.verts.new((wx_inner, wy_inner, 0.05)))
            
            # 外側の点
            outer_r = radius + track_width / 2
            wx_outer = center[0] + (outer_r * cos_a)
            wy_outer = center[1] + (outer_r * sin_a)
            outer_verts.append(bm.verts.new((wx_outer, wy_outer, 0.05)))
        
        # ポリゴンを作成（4頂点の面）
        for p in range(arc_points):
            bm.faces.new([inner_verts[p], inner_verts[p+1], outer_verts[p+1], outer_verts[p]])
        
        # bmeshをメッシュに適用
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"{name_prefix}_Seg{seg}_Obj", mesh)
        bpy.context.collection.objects.link(obj)
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(bpy.data.materials[mat_name])
        
        # このセグメントが表示されるフレームを計算（ease-inカーブ + 固定遅延）
        # 初動は固定遅延でカバー、カーブはease-inで後半を速く
        t = seg / num_segments  # 0 → 1
        eased_t = t ** 1.5  # ease-inカーブ（前半を遅く、後半を速く）
        # 固定遅延：2.5秒（60フレーム）で軌跡の表示を遅らせる
        track_delay = 60  # 2.5秒遅延
        # 範囲を調整して、最後のセグメントがend_frameに収まるように
        show_frame = start_frame + track_delay + int(eased_t * (end_frame - start_frame - track_delay))
        
        # フレーム0から非表示（確実に初期状態が非表示になる）
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=0)
        obj.keyframe_insert(data_path="hide_render", frame=0)
        
        # 指定フレームで表示
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=show_frame)
        obj.keyframe_insert(data_path="hide_render", frame=show_frame)
    
    print(f"[シーン11] 回転半径ガイドライン '{name_prefix}' を作成（セグメント数={num_segments}, 半径={radius}m）")



def _create_tire_track(car_object, empty_pivot, turning_radius, name_prefix, start_frame, end_frame, color=(1.0, 0.2, 0.2)):
    """車のタイヤ跡軌跡を発光円弧として作成（bmeshベース）
    
    円弧を複数のセグメントに分割し、フレームごとに順に表示することで
    徐々に描画されるタイヤ跡を実現する。
    
    車の動きに合わせて軌跡を表示するために、線形タイミングに遅延を追加。
    
    Parameters:
        car_object: 車オブジェクト
        empty_pivot: 回転中心のEmptyオブジェクト
        turning_radius: 最小回転半径 (m)
        name_prefix: オブジェクト名のプレフィックス
        start_frame: 開始フレーム
        end_frame: 終了フレーム
        color: 軌跡の色 (R, G, B)
    """
    import bmesh
    
    # 車のバウンディングボックスから後輪のYオフセットを計算
    car_object.update_tag()
    bpy.context.view_layer.update()
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"[警告] {car_object.name} のバウンディングボックスが取得できません")
        return
    
    # ローカル座標の8隅を取得
    corners_local = [Vector(corner) for corner in local_bounds]
    
    # Y軸の最小値（リア端）を取得
    rear_y = min(c.y for c in corners_local)
    
    # セグメント数
    num_segments = 30
    
    # 軌跡幅（タイヤ跡の太さ）
    track_width = 0.2
    
    # 発光マテリアルを作成（EEVEE対応: Principled BSDF使用）
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
        
        # EEVEE設定: 発光を正しく表示するために透過モードを有効化
        try:
            mat.blend_method = 'HASHED'
        except AttributeError:
            pass
        try:
            mat.shadow_method = 'NONE'
        except AttributeError:
            pass
        
        print(f"[シーン11] 発光マテリアル '{mat_name}' を作成（色={color}, Principled BSDF Emission）")
    
    # 各セグメントを細長い面として作成
    for seg in range(num_segments):
        seg_start_angle = -2.0 * math.pi * seg / num_segments
        seg_end_angle = -2.0 * math.pi * (seg + 1) / num_segments
        
        # メッシュを作成
        mesh_name = f"{name_prefix}_Seg{seg}"
        mesh = bpy.data.meshes.new(mesh_name)
        
        # bmeshを使用してポリゴンを追加
        bm = bmesh.new()
        
        # 頂点を作成（内側と外側の2列）
        arc_points = 4
        inner_verts = []
        outer_verts = []
        
        for p in range(arc_points + 1):
            t = p / arc_points
            angle = seg_start_angle + (seg_end_angle - seg_start_angle) * t
            
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            # 内側の点
            inner_r = turning_radius - track_width / 2
            wx_inner = empty_pivot.location.x + (inner_r * cos_a - rear_y * sin_a)
            wy_inner = empty_pivot.location.y + (inner_r * sin_a + rear_y * cos_a)
            inner_verts.append(bm.verts.new((wx_inner, wy_inner, 0.06)))
            
            # 外側の点
            outer_r = turning_radius + track_width / 2
            wx_outer = empty_pivot.location.x + (outer_r * cos_a - rear_y * sin_a)
            wy_outer = empty_pivot.location.y + (outer_r * sin_a + rear_y * cos_a)
            outer_verts.append(bm.verts.new((wx_outer, wy_outer, 0.06)))
        
        # ポリゴンを作成（4頂点の面）
        for p in range(arc_points):
            bm.faces.new([inner_verts[p], inner_verts[p+1], outer_verts[p+1], outer_verts[p]])
        
        # bmeshをメッシュに適用
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new(f"{name_prefix}_Seg{seg}_Obj", mesh)
        bpy.context.collection.objects.link(obj)
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(bpy.data.materials[mat_name])
        
        # このセグメントが表示されるフレームを計算（ease-inカーブ + 固定遅延）
        # 初動は固定遅延でカバー、カーブはease-inで後半を速く
        t = seg / num_segments  # 0 → 1
        eased_t = t ** 1.5  # ease-inカーブ（前半を遅く、後半を速く）
        # 固定遅延：2.5秒（60フレーム）で軌跡の表示を遅らせる
        track_delay = 60  # 2.5秒遅延
        # 範囲を調整して、最後のセグメントがend_frameに収まるように
        show_frame = start_frame + track_delay + int(eased_t * (end_frame - start_frame - track_delay))
        
        # フレーム0から非表示（確実に初期状態が非表示になる）
        obj.hide_viewport = True
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_viewport", frame=0)
        obj.keyframe_insert(data_path="hide_render", frame=0)
        
        # 指定フレームで表示
        obj.hide_viewport = False
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_viewport", frame=show_frame)
        obj.keyframe_insert(data_path="hide_render", frame=show_frame)
    
    print(f"[シーン11] タイヤ跡軌跡 '{name_prefix}' を作成（セグメント数={num_segments}, 色={color}）")


def _setup_car_b_opaque_for_scene10(car_object, start_frame, end_frame):
    """CarB の全マテリアルをシーン 10 で不透明に戻す（複数メッシュ対応）
    シーン9と同じ Principled BSDF Alpha 方式を使用"""
    if car_object is None:
        return

    # オブジェクト自体のマテリアルを設定
    _apply_opaque_to_materials_scene10(car_object, start_frame, end_frame)

    # 子オブジェクトのマテリアルも設定（GLB インポートで複数のメッシュがある場合）
    for child in car_object.children:
        if child.type == 'MESH':
            _apply_opaque_to_materials_scene10(child, start_frame, end_frame)


def _apply_opaque_to_materials_scene10(car_object, start_frame, end_frame):
    """オブジェクトの全マテリアルを指定フレーム間で不透明に戻す
    シーン9と同じ Principled BSDF Alpha 方式を使用"""
    if car_object is None:
        return

    for material in car_object.data.materials:
        if material is None:
            continue
        
        # EEVEE 透過対応
        try:
            material.blend_method = 'BLEND'
        except AttributeError:
            pass

        if not material.use_nodes:
            continue

        nodes = material.node_tree.nodes
        principled_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break

        if principled_node is None or 'Alpha' not in principled_node.inputs:
            continue

        alpha_input = principled_node.inputs['Alpha']
        # 開始フレーム: Alpha=0.8（シーン9の最終値を維持）
        alpha_input.default_value = 0.8
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        # 終了フレーム: Alpha=1.0（完全不透明）
        alpha_input.default_value = 1.0
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)


def _fade_out_ground_clearance_text(start_frame, end_frame):
    """最低地上高差表示テキストをフェードアウト"""
    text_container_name = "GroundClearanceDiff_Container_Scene9"
    if text_container_name not in bpy.data.objects:
        print(f"[警告] '{text_container_name}' が見つかりません。フェードアウトをスキップします。")
        return

    text_obj = bpy.data.objects[text_container_name]

    print(f"[フレーム{start_frame}] 最低地上高差テキストフェードアウト開始（{start_frame}→{end_frame}）")

    # コンテナ自体のスケールをアニメーションで制御
    # 開始フレーム: スケール維持（1.0, 1.0, 1.0）
    text_obj.scale = (1.0, 1.0, 1.0)
    text_obj.keyframe_insert(data_path="scale", frame=start_frame)
    
    # 終了フレーム: スケールを 0 に（完全に消える）
    text_obj.scale = (0.0, 0.0, 0.0)
    text_obj.keyframe_insert(data_path="scale", frame=end_frame)

    # 各文字オブジェクトにもキーフレームを設定（二重確保）
    for char_obj in text_obj.children:
        if char_obj.type == 'MESH':
            # まず現在のスケールを取得して保存
            current_scale = char_obj.scale.copy() if hasattr(char_obj, 'scale') else (1.0, 1.0, 1.0)

            # 開始フレーム: 現在のスケールを維持（キーフレーム）
            char_obj.scale = current_scale
            char_obj.keyframe_insert(data_path="scale", frame=start_frame)

            # 終了フレーム: スケールを 0 に
            char_obj.scale = (0.0, 0.0, 0.0)
            char_obj.keyframe_insert(data_path="scale", frame=end_frame)

            # 発光強度も徐々に 0 に（確実に消えるように）
            if len(char_obj.data.materials) > 0:
                mat = char_obj.data.materials[0]
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'BSDF_EMISSION':
                            current_strength = node.inputs['Strength'].default_value

                            # 開始フレーム: 現在の強度を維持（キーフレーム）
                            node.inputs['Strength'].default_value = current_strength
                            node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

                            # 終了フレーム: 強度を 0 に
                            node.inputs['Strength'].default_value = 0.0
                            node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=end_frame)
                        
                    # Mix Shader の Fac でも透明度を制御（二重確保）
                    for n in mat.node_tree.nodes:
                        if n.type == 'MIX_SHADER':
                            # 開始フレームで完全不透明（Fac=1.0 → Emissionを完全に使用）
                            n.inputs['Fac'].default_value = 1.0
                            n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=start_frame)
                            # 終了フレームで完全透明（Fac=0.0 → Transparentを完全に使用）
                            n.inputs['Fac'].default_value = 0.0
                            n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=end_frame)
                            
                    # EEVEEの透過設定を確実に有効化
                    mat.blend_method = 'BLEND'
                    mat.shadow_method = 'BUFFER'

    print(f"[フレーム{end_frame}] 最低地上高差テキストのフェードアウト完了（スケール→0）")
