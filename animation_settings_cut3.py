"""
アニメーション設定モジュール - カット 3
フレーム 1224-1584（シーン 8-9、停止付き）を処理する。

使い方:
    from animation_settings_cut3 import setup_cut3_animations
    setup_cut3_animations(scene, camera, imported_cars, cut2_result, car_dimensions=None)

【透明度処理のまとめ】
CarBの透明度アニメーションは以下の場所で制御されています：
  - シーン1-2（フレーム30-96）: animation_common.py の _setup_transparency_animation()
    → Principled BSDFのAlphaを 1.0→0.4 にアニメーション
  - シーン5（フレーム648-768）: animation_settings_cut2.py の _apply_transparency_to_materials()
    → material.transparency を 1.0→0.65 にアニメーション
  - シーン9（フレーム1416-1536）: 本ファイルの _setup_car_b_transparency_for_scene9()
    → Principled BSDFのAlphaを 0.35→0.9 にアニメーション（より不透明に）

※透明度を変更する場合は、上記3箇所を確認してください。
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at, _calculate_ground_clearance_difference, create_emission_material


def setup_cut3_animations(scene, camera, imported_cars, cut2_result, car_dimensions=None):
    """
    カット 3 のアニメーションを設定（フレーム 1224-1584）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        cut2_result: setup_cut2_animations の戻り値（dict）
        car_dimensions: {key: {"ground_clearance": mm}} 車の寸法情報

    Returns:
        dict: カメラの最終位置・回転、車の位置など
    """
    if cut2_result is None:
        print("エラー: カット 2 の結果が指定されていません")
        return None

    # カット 2 から結果を取得
    car_a_end = cut2_result['car_a_end']
    car_b_end = cut2_result['car_b_end']
    loc_scene7_end = cut2_result['loc_scene7_end']
    rot_scene7_end = cut2_result['rot_scene7_end']

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    target = (0.0, 0.0, 1.5)

    # ============================================================
    # 【カット 3】シーン 8: フレーム 1224-1368（正面から左側低位置へカメラ移動、6秒）
    #                  停止: フレーム 1368-1416（2秒）
    # ============================================================
    print("\n=== 【カット 3】シーン 8 設定開始 ===")

    scene8_start = 1224
    scene8_end = 1368  # 6秒間（24fps × 6 = 144フレーム）
    scene8_pause_end = 1416  # 停止2秒（24fps × 2 = 48フレーム）

    # カメラ: 正面ビューから左側の低い位置へ移動
    # 初期位置：シーン7の終了位置（正面ビュー）
    start_loc = loc_scene7_end
    start_rot = rot_scene7_end

    # 最終位置：向かって左側（負のX方向）の低い位置
    # 最低地上高を確認するための低いアングル
    end_loc = (-6.0, -2.0, 0.8)  # 左前方から低い位置
    direction_end = Vector(target) - Vector(end_loc)
    rot_quat_end = direction_end.to_track_quat('-Z', 'Y')
    end_rot = rot_quat_end.to_euler()

    # 中間地点 - 距離50%
    mid_frame = scene8_start + 72  # 144/2 = 72フレーム目
    loc_mid = (start_loc[0] + end_loc[0]) / 2.0, (start_loc[1] + end_loc[1]) / 2.0, (start_loc[2] + end_loc[2]) / 2.0
    direction_mid = Vector(target) - Vector(loc_mid)
    rot_quat_mid = direction_mid.to_track_quat('-Z', 'Y')
    rot_mid = rot_quat_mid.to_euler()

    # 開始位置
    camera.location = start_loc
    camera.rotation_euler = start_rot
    camera.keyframe_insert(data_path="location", frame=scene8_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene8_start)

    # 中間キーフレーム（滑らかな移動のため）
    camera.location = loc_mid
    camera.rotation_euler = rot_mid
    camera.keyframe_insert(data_path="location", frame=mid_frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=mid_frame)

    # 終了位置
    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene8_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene8_end)

    # 車: 位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene8_start)
    car_a.keyframe_insert(data_path="location", frame=scene8_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene8_start)
    car_b.keyframe_insert(data_path="location", frame=scene8_end)

    print(f"[フレーム{scene8_start}] シーン 8 開始：カメラ移動開始（正面ビューから）")
    print(f"[フレーム{scene8_end}] シーン 8 終了：カメラ={end_loc}（左側低位置）, 車維持")

    # --- 停止（2秒）: フレーム 1416 ---
    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene8_pause_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene8_pause_end)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene8_pause_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene8_pause_end)
    print(f"[フレーム{scene8_pause_end}] 停止（2秒）")

    # --- シーン 8 で全幅差表示をフェードアウト（シーン 6 の全長差フェードアウトと同じパターン）---
    text_container_name = "WidthDiff_Container_Scene7"
    if text_container_name in bpy.data.objects:
        text_obj = bpy.data.objects[text_container_name]

        print(f"[フレーム{scene8_start}] 全幅差テキストフェードアウト開始（1224→1368）")

        # コンテナ自体のスケールをアニメーションで制御
        # フレーム 1224: スケール維持（1.0, 1.0, 1.0）
        text_obj.scale = (1.0, 1.0, 1.0)
        text_obj.keyframe_insert(data_path="scale", frame=scene8_start)
        
        # フレーム 1368: スケールを 0 に（完全に消える）
        fade_end_frame = scene8_end  # フレーム 1368
        text_obj.scale = (0.0, 0.0, 0.0)
        text_obj.keyframe_insert(data_path="scale", frame=fade_end_frame)

        # 各文字オブジェクトにもキーフレームを設定（二重確保）
        for char_obj in text_obj.children:
            if char_obj.type == 'MESH':
                # まず現在のスケールを取得して保存
                current_scale = char_obj.scale.copy() if hasattr(char_obj, 'scale') else (1.0, 1.0, 1.0)

                # フレーム 1224: 現在のスケールを維持（キーフレーム）
                char_obj.scale = current_scale
                char_obj.keyframe_insert(data_path="scale", frame=scene8_start)

                # フレーム 1368: スケールを 0 に
                char_obj.scale = (0.0, 0.0, 0.0)
                char_obj.keyframe_insert(data_path="scale", frame=fade_end_frame)

                # 発光強度も徐々に 0 に（確実に消えるように）
                if len(char_obj.data.materials) > 0:
                    mat = char_obj.data.materials[0]
                    if mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_EMISSION':
                                current_strength = node.inputs['Strength'].default_value

                                # フレーム 1224: 現在の強度を維持（キーフレーム）
                                node.inputs['Strength'].default_value = current_strength
                                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=scene8_start)

                                # フレーム 1368: 強度を 0 に
                                node.inputs['Strength'].default_value = 0.0
                                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=fade_end_frame)
                        
                        # Mix Shader の Fac でも透明度を制御（二重確保）
                        for n in mat.node_tree.nodes:
                            if n.type == 'MIX_SHADER':
                                # フレーム 1224 で完全不透明（Fac=1.0 → Emission を完全に使用）
                                n.inputs['Fac'].default_value = 1.0
                                n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=scene8_start)
                                # フレーム 1368 で完全透明（Fac=0.0 → Transparent を完全に使用）
                                n.inputs['Fac'].default_value = 0.0
                                n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=fade_end_frame)
                                
                        # EEVEE の透過設定を確実に有効化
                        mat.blend_method = 'BLEND'
                        mat.shadow_method = 'BUFFER'

        print(f"[フレーム{scene8_end}] 全幅差テキストのフェードアウト完了（スケール→0）")

    # ============================================================
    # 【カット 3】シーン 9: フレーム 1416-1536（最低地上高差表示、5秒）
    #                    停止: フレーム 1536-1584（2秒）
    # ============================================================
    print("\n=== 【カット 3】シーン 9 設定開始 ===")

    scene9_start = 1416
    scene9_end = 1536  # 5秒間（24fps × 5 = 120フレーム）
    scene9_pause_end = 1584  # 停止2秒（24fps × 2 = 48フレーム）

    # カメラ: シーン8の終了位置を維持
    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene9_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene9_start)
    camera.keyframe_insert(data_path="location", frame=scene9_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene9_end)

    # 車: 位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene9_start)
    car_a.keyframe_insert(data_path="location", frame=scene9_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene9_start)
    car_b.keyframe_insert(data_path="location", frame=scene9_end)

    print(f"[フレーム{scene9_start}] シーン 9 開始：最低地上高差表示")

    # --- CarB の透明度を少し緩める（シーン 9 用：0.8 の不透明度で表示）---
    _setup_car_b_transparency_for_scene9(car_b, scene9_start, scene9_end)
    print(f"[フレーム{scene9_start}-{scene9_end}] CarB 透明度緩和：0.35→0.9")

    # --- シーン 9 の最低地上高差エフェクト（地面に張り付けたテキスト）---
    _setup_scene9_effects(scene, camera, car_a, car_b, scene9_start, scene9_end, car_dimensions)

    # --- 停止（2秒）: フレーム 1584 ---
    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene9_pause_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene9_pause_end)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene9_pause_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene9_pause_end)
    print(f"[フレーム{scene9_pause_end}] 停止（2秒）")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 3 アニメーション完了 ===")

    # 結果を返す
    return {
        'car_a_end': car_a_end,
        'car_b_end': car_b_end,
        'loc_scene8_end': end_loc,
        'rot_scene8_end': end_rot,
    }


# ============================================================
# シーン 9: 最低地上高差表示（地面に張り付け）
# ============================================================

def _setup_scene9_effects(scene, camera, car_a, car_b, scene9_start, scene9_end, car_dimensions=None):
    """シーン 9 の最低地上高差エフェクトを設定（地面に張り付けたテキスト）"""
    clearance_diff_mm = _calculate_ground_clearance_difference(car_a, car_b, car_dimensions)

    if car_dimensions:
        clearance_a_mm = car_dimensions.get("carA", {}).get("ground_clearance", 0)
        clearance_b_mm = car_dimensions.get("carB", {}).get("ground_clearance", 0)
    else:
        clearance_a_mm = 0
        clearance_b_mm = 0

    print(f"[シーン 9] 最低地上高差：{clearance_diff_mm:+d}mm (CarB: {clearance_b_mm}mm, CarA: {clearance_a_mm}mm)")

    text_obj = _create_ground_clearance_diff_text(scene, camera, clearance_a_mm, clearance_b_mm, clearance_diff_mm, car_a, car_b, scene9_start, scene9_end)
    if text_obj:
        print(f"[シーン 9] 数値テキスト '{text_obj.name}' を作成しました")

    print(f"[フレーム{scene9_end}] シーン 9 終了：最低地上高差表示完了")


def _create_ground_clearance_diff_text(scene, camera, clearance_a_mm, clearance_b_mm, clearance_diff_mm, car_a, car_b, start_frame, end_frame):
    """最低地上高の計算式を表示するテキストを作成（車の上に配置）"""

    # 両車の中心座標を取得
    def get_car_center(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        world_bounds = [car_obj.matrix_world @ b for b in bounds]
        min_x = min(p.x for p in world_bounds)
        max_x = max(p.x for p in world_bounds)
        min_y = min(p.y for p in world_bounds)
        max_y = max(p.y for p in world_bounds)
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        return (center_x, center_y)

    # 車の最高点を取得（Z 座標）
    def get_car_max_z(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        world_bounds = [car_obj.matrix_world @ b for b in bounds]
        return max(p.z for p in world_bounds)

    center_a = get_car_center(car_a)
    center_b = get_car_center(car_b)
    avg_center_x = (center_a[0] + center_b[0]) / 2.0
    avg_center_y = (center_a[1] + center_b[1]) / 2.0

    car_max_z_a = get_car_max_z(car_a)
    car_max_z_b = get_car_max_z(car_b)
    max_height = max(car_max_z_a, car_max_z_b)

    # 車の上に配置（他のシーンと同じパターン）
    text_container_location = (avg_center_x, avg_center_y, 2.0)

    bpy.ops.object.empty_add(location=text_container_location)
    text_container = bpy.context.active_object
    text_container.name = "GroundClearanceDiff_Container_Scene9"

    # カメラに向くように回転（Z軸は上方向に保つ）
    cam_pos = camera.location
    container_pos = Vector(text_container_location)
    direction = cam_pos - container_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    euler_rot = rot_quat.to_euler()
    # Z軸に180度（πラジアン）追加してテキストの向きを修正
    euler_rot.z += math.pi
    text_container.rotation_euler = euler_rot

    scene.collection.objects.link(text_container)

    print(f"=== TEXT CONTAINER DEBUG (Scene 9) ===")
    print(f"text_container.location: {text_container.location}")
    print(f"text_container.rotation_euler: {text_container.rotation_euler}")

    # 文字列を作成："最低地上高：CarB - CarA → 結果"
    text_str = f"最低地上高：{clearance_b_mm}mm - {clearance_a_mm}mm → {clearance_diff_mm:+d}mm"

    # 各文字を個別のテキストオブジェクトとして作成
    char_objects = []
    half_spacing = 0.12
    full_spacing = 0.20

    # 色の定義：CarB=青、CarA=赤、結果=白
    colors = {
        'blue': (0.0, 1.0, 1.0),
        'red': (1.0, 0.0, 0.0),
        'white': (1.0, 1.0, 1.0)
    }

    color_map = ['white'] * len(text_str)

    # 数字のブロックを特定
    number_blocks = []
    current_block = []

    for i, char in enumerate(text_str):
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
            color = 'blue'
        elif idx == 1:
            color = 'red'
        else:
            color = 'white'

        for pos in block:
            if pos < len(color_map):
                color_map[pos] = color

    for i, char in enumerate(text_str):
        bpy.ops.object.text_add(location=(0, 0, 0))
        char_obj = bpy.context.active_object
        char_obj.name = f"GroundClearanceDiff_Char_{i}"

        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char

        if hasattr(char_obj.data, 'size'):
            char_obj.data.size = 0.22

        char_obj.scale = (1.0, 1.0, 1.0)

        color_name = color_map[i] if i < len(color_map) else 'white'
        mat_name = f"emission_label_scene9_char_{color_name}"
        if mat_name not in bpy.data.materials:
            emission_mat = create_emission_material(colors[color_name], 5.0)
            emission_mat.name = mat_name
        else:
            emission_mat = bpy.data.materials[mat_name]

        if len(char_obj.data.materials) == 0:
            char_obj.data.materials.append(emission_mat)

        char_obj.parent = text_container
        scene.collection.objects.link(char_obj)

        char_objects.append(char_obj)

    # 全角/半角を考慮した位置計算
    def is_fullwidth(c):
        """全角文字かどうかを判定"""
        code = ord(c)
        return (0x4E00 <= code <= 0x9FFF) or \
               (0x3000 <= code <= 0x303F) or \
               (0xFF00 <= code <= 0xFFEF) or \
               (0x3040 <= code <= 0x309F) or \
               (0x30A0 <= code <= 0x30FF)

    char_widths = []
    for c in text_str:
        if is_fullwidth(c):
            char_widths.append(full_spacing)
        else:
            char_widths.append(half_spacing)

    total_width = sum(char_widths)

    current_x = -total_width / 2.0
    for i, char_obj in enumerate(char_objects):
        local_x = current_x
        current_x += char_widths[i]

        # 地面に張り付けるのでY=0, Zを文字サイズ分上げる
        local_y = 0.0
        local_z = 0.11

        char_obj.location = (local_x, local_y, local_z)

    # アニメーションを設定（フェードイン）
    _setup_char_by_char_animation_scene9(char_objects, start_frame=start_frame, end_frame=end_frame)

    print(f"[シーン 9] 計算式テキスト '{text_str}' を {len(char_objects)} 文字で作成")
    return text_container


def _setup_char_by_char_animation_scene9(char_objects, start_frame, end_frame):
    """各文字に単一フェードインアニメーションを設定（シーン9用）"""

    # 初期状態：全て透明でスケール 0
    for char_obj in char_objects:
        char_obj.scale = (0.0, 0.0, 0.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame)

        # 発光強度を 0 に設定
        if len(char_obj.data.materials) > 0:
            for node in char_obj.data.materials[0].node_tree.nodes:
                if node.type == 'BSDF_EMISSION':
                    node.inputs['Strength'].default_value = 0.0
                    node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

    # 全ての文字が同時にフェードインするアニメーション
    for char_obj in char_objects:
        char_obj.scale = (1.0, 1.0, 1.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame + 8)

        if len(char_obj.data.materials) > 0:
            for node in char_obj.data.materials[0].node_tree.nodes:
                if node.type == 'BSDF_EMISSION':
                    node.inputs['Strength'].default_value = 5.0
                    node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 8)

        char_obj.keyframe_insert(data_path="scale", frame=end_frame)

    print(f"[シーン 9] {len(char_objects)} 文字に単一フェードインアニメーションを設定")


# ============================================================
# CarB の透明度をシーン 9 で緩和する処理
# ============================================================

def _setup_car_b_transparency_for_scene9(car_object, start_frame, end_frame):
    """CarB の全マテリアルをシーン 9 用透明度に緩和する（複数メッシュ対応）
    シーン1と同じ Principled BSDF Alpha 方式を使用"""
    if car_object is None:
        return

    # オブジェクト自体のマテリアルを設定
    _apply_transparency_to_materials_scene9(car_object, start_frame, end_frame)

    # 子オブジェクトのマテリアルも設定（GLB インポートで複数のメッシュがある場合）
    for child in car_object.children:
        if child.type == 'MESH':
            _apply_transparency_to_materials_scene9(child, start_frame, end_frame)


def _apply_transparency_to_materials_scene9(car_object, start_frame, end_frame):
    """オブジェクトの全マテリアルを指定フレーム間で透明度を緩和する
    シーン1と同じ Principled BSDF Alpha 方式を使用"""
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
        # 開始フレーム: Alpha=0.35（シーン5の最終値を維持）
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        # 終了フレーム: Alpha=0.8（半透明ながら实体感を維持）
        alpha_input.default_value = 0.8
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)
