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


def setup_cut5_animations(scene, camera, imported_cars, previous_state, car_dimensions=None):
    """
    カット 5 のアニメーションを設定（フレーム 2208-2832）

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
    loc_scene12_end = previous_state.camera_loc
    rot_scene12_end = previous_state.camera_rot

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # ============================================================
    # 【カット 5】シーン 13: フレーム 2208-2352（カメラ回転6秒、最初の3秒で軌跡とテキストをフェードアウト）
    # ============================================================
    print("\n=== 【カット 5】シーン 13 設定開始 ===")

    scene13_start = 2208
    fade_out_end = 2328  # フェードアウト完了（3秒：24fps × 3 = 72フレーム）
    scene13_end = 2352  # カメラ移動完了（計6秒：24fps × 6 = 144フレーム）

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
    # Emptyの位置は変えず、車のローカル位置（Emptyからの相対位置）を動かす
    empty_a = bpy.data.objects.get("CarA_TurnPivot")
    empty_b = bpy.data.objects.get("CarB_TurnPivot")

    if empty_a and empty_b:
        total_angle = -2.0 * math.pi
        empty_a.rotation_euler.z = total_angle
        empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene13_start)
        empty_b.rotation_euler.z = total_angle
        empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene13_start)
        # Empty回転も終了時まで維持
        empty_a.keyframe_insert(data_path="rotation_euler", index=2, frame=scene13_end)
        empty_b.keyframe_insert(data_path="rotation_euler", index=2, frame=scene13_end)

        # 車のアニメーションデータをクリア（前のカットのキーフレームと競合しないように）
        if car_a.animation_data:
            car_a.animation_data_clear()
        if car_b.animation_data:
            car_b.animation_data_clear()

        # Emptyの位置からturning_radiusを取得（Empty.location.x = -turning_radius）
        turning_radius_a = abs(empty_a.location.x)
        turning_radius_b = abs(empty_b.location.x)

        # 開始位置: ローカルX = turning_radius（グローバルX=0、2台が重なる状態）
        car_a.location.x = turning_radius_a
        car_b.location.x = turning_radius_b
        car_a.keyframe_insert(data_path="location", index=0, frame=scene13_start)
        car_b.keyframe_insert(data_path="location", index=0, frame=scene13_start)

        # 終了位置: ローカルXを±1.5mずらす（グローバルで合計3m離れる）
        end_local_x_a = turning_radius_a - 1.5
        end_local_x_b = turning_radius_b + 1.5
        car_a.location.x = end_local_x_a
        car_a.keyframe_insert(data_path="location", index=0, frame=scene13_end)
        car_b.location.x = end_local_x_b
        car_b.keyframe_insert(data_path="location", index=0, frame=scene13_end)

        print(f"[シーン13] 車のローカルXを±1.5mずらす (carA: {end_local_x_a:.2f}, carB: {end_local_x_b:.2f})")

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

    scene14_start = scene13_end  # 2352
    scene14_end = 2832  # 15秒間（24fps × 15 = 480フレーム）

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

    # アニメーションデータをクリア
    if car_a.animation_data:
        car_a.animation_data_clear()
    if car_b.animation_data:
        car_b.animation_data_clear()

    bpy.context.view_layer.update()

    print(f"[シーン14] Empty親オブジェクトを削除、車のアニメーションデータをクリア")

    # 車の初期位置を設定（x軸距離2.5m = 各車±1.25m）
    car_a_start_x = -1.25
    car_b_start_x = 1.25
    car_start_y = 0.0

    # 車の向きをY負方向（前方）に向ける（-Z回転で後方に進む）
    car_a.location = (car_a_start_x, car_start_y, car_a_end[2])
    car_a.rotation_euler = (0.0, 0.0, -math.pi / 2)
    car_a.keyframe_insert(data_path="location", frame=scene14_start)
    car_a.keyframe_insert(data_path="rotation_euler", frame=scene14_start)

    car_b.location = (car_b_start_x, car_start_y, car_b_end[2])
    car_b.rotation_euler = (0.0, 0.0, -math.pi / 2)
    car_b.keyframe_insert(data_path="location", frame=scene14_start)
    car_b.keyframe_insert(data_path="rotation_euler", frame=scene14_start)

    print(f"[フレーム{scene14_start}] carA 開始位置: ({car_a_start_x}, {car_start_y}, {car_a_end[2]})")
    print(f"[フレーム{scene14_start}] carB 開始位置: ({car_b_start_x}, {car_start_y}, {car_b_end[2]})")

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
        car_a.location = (car_a_start_x, car_start_y - distance_a, car_a_end[2])
        car_a.keyframe_insert(data_path="location", frame=frame)

        car_b.location = (car_b_start_x, car_start_y - distance_b, car_b_end[2])
        car_b.keyframe_insert(data_path="location", frame=frame)

    final_distance_a = total_distance_a
    final_distance_b = total_distance_b
    car_a.location = (car_a_start_x, car_start_y - final_distance_a, car_a_end[2])
    car_a.keyframe_insert(data_path="location", frame=scene14_end)

    car_b.location = (car_b_start_x, car_start_y - final_distance_b, car_b_end[2])
    car_b.keyframe_insert(data_path="location", frame=scene14_end)

    print(f"[フレーム{scene14_end}] carA 終了位置: ({car_a_start_x}, {car_start_y - final_distance_a:.2f}, {car_a_end[2]})")
    print(f"[フレーム{scene14_end}] carB 終了位置: ({car_b_start_x}, {car_start_y - final_distance_b:.2f}, {car_b_end[2]})")

    # カメラアニメーション（位置固定・回転のみで車を追う）
    # 車の加速カーブに合わせて注視点を逐次更新
    camera.location = fixed_camera_loc
    camera.keyframe_insert(data_path="location", frame=scene14_start)

    # 各フレームで車の実際の位置を計算し、カメラの注視点をそれに合わせる
    # 2台の車の平均位置を追う
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
            look_at_target = Vector((0.0, car_start_y - distance_avg - 3.0, 1.0))
        else:
            # 後半は車が遠ざかる方向を見る
            progress_second_half = (t - 0.5) / 0.5
            look_at_y = car_start_y - distance_avg - 3.0 - progress_second_half * 20.0
            look_at_z = 1.0 - progress_second_half * 0.5
            look_at_target = Vector((0.0, look_at_y, look_at_z))

        set_camera_look_at(camera, fixed_camera_loc, look_at_target)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
        camera.keyframe_insert(data_path="location", frame=frame)

    # 最終フレームの回転を保存
    rot_scene14_end = camera.rotation_euler.copy()

    print(f"[フレーム{scene14_start}] カメラ位置固定: {fixed_camera_loc}")
    print(f"[フレーム{scene14_start}] 注視点: (0.0, {car_start_y - 3.0}, 1.0)（車の近く）")
    print(f"[フレーム{scene14_end}] 注視点: (0.0, {car_start_y - (final_distance_a + final_distance_b)/2 - 23.0}, 0.5)（遠くへ・点がなる方向）")

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
        car_a_loc=(car_a_start_x, car_start_y + final_distance_a, car_a_end[2]),
        car_b_loc=(car_b_start_x, car_start_y + final_distance_b, car_b_end[2]),
        camera_loc=camera_end_loc,
        camera_rot=(rot_scene14_end.x, rot_scene14_end.y, rot_scene14_end.z),
    )


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
    car_a_color = (0.8, 0.2, 0.2)  # デフォルト赤系
    car_b_color = (0.2, 0.2, 0.8)  # デフォルト青系

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
