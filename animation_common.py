"""
アニメーション共通ユーティリティモジュール

カット1・カット2で共通して使用される関数群を定義。
animation_settings.py からインポートして使用。

使い方:
    from animation_common import set_camera_look_at, create_emission_material
"""

import bpy
import math
from mathutils import Vector


def set_camera_look_at(cam, loc, tgt):
    """カメラを指定位置に配置し、ターゲット方向に向ける"""
    cam.location = loc
    direction = Vector(tgt) - Vector(loc)
    rot_quat = direction.to_track_quat('-Z', 'Y')  # カメラの-Z軸をターゲット方向へ
    cam.rotation_euler = rot_quat.to_euler()


def create_emission_material(color_rgb, strength):
    """発光マテリアルを作成（再利用用）"""
    mat = bpy.data.materials.new(name="emission_temp")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    nodes.clear()

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.location = (100, 0)
    emission_node.inputs['Color'].default_value = (*color_rgb, 1.0)
    emission_node.inputs['Strength'].default_value = strength * 2  # 発光強度を2倍に強化

    mat.node_tree.links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])

    return mat


def _setup_transparency_animation(car_object, start_frame, end_frame, start_alpha, end_alpha):
    """車のマテリアル不透明度をアニメーションさせる（内部用）"""
    if car_object is None or len(car_object.data.materials) == 0:
        return

    material = car_object.data.materials[0]
    if not material.use_nodes:
        return

    # EEVEE 透過対応
    material.blend_method = 'BLEND'

    nodes = material.node_tree.nodes
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break

    if principled_node is None or 'Alpha' not in principled_node.inputs:
        return

    alpha_input = principled_node.inputs['Alpha']
    alpha_input.default_value = start_alpha
    alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
    alpha_input.default_value = end_alpha
    alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)


def _apply_transparency_to_materials(obj, start_frame, end_frame):
    """オブジェクトの全マテリアルに半透明化キーフレームを設定"""
    if obj is None or len(obj.data.materials) == 0:
        return

    for slot in obj.material_slots:
        material = slot.material
        if material is None:
            continue

        # EEVEE 透過対応
        material.blend_method = 'BLEND'

        nodes = material.node_tree.nodes
        principled_node = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break

        if principled_node is None or 'Alpha' not in principled_node.inputs:
            continue

        alpha_input = principled_node.inputs['Alpha']
        # シーン 5 開始から最初から半透明（0.35）
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)

    print(f"  {obj.name} のマテリアルに半透明化キーフレームを設定しました（シーン 5: Alpha=0.35）")


def _setup_char_by_char_animation(char_objects, start_frame, end_frame):
    """各文字に単一フェードインアニメーションを設定"""
    
    # 初期状態：全て透明でスケール 0（同時に）
    for char_obj in char_objects:
        char_obj.scale = (0.0, 0.0, 0.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame)
        
        # 発光強度を 0 に設定（同時に）
        for node in char_obj.data.materials[0].node_tree.nodes:
            if node.type == 'BSDF_EMISSION':
                node.inputs['Strength'].default_value = 0.0
                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

    # 全ての文字が同時にフェードインするアニメーション（単一フェードイン）
    for char_obj in char_objects:
        # ステップ 1: 最終サイズ（1.0 倍）と安定状態
        char_obj.scale = (1.0, 1.0, 1.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame + 8)

        for node in char_obj.data.materials[0].node_tree.nodes:
            if node.type == 'BSDF_EMISSION':
                node.inputs['Strength'].default_value = 5.0
                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 8)

        # 最終安定状態 - オブジェクトスケールを 1.0 に維持、テキストサイズは 0.09
        char_obj.keyframe_insert(data_path="scale", frame=end_frame)

    print(f"[シーン 5] {len(char_objects)} 文字に単一フェードインアニメーションを設定")


def _setup_pipipi_animation(obj, start_frame, end_frame):
    """ピピピッ出現アニメーション（3 段階の拡大・点滅エフェクト）"""
    # Empty オブジェクトの場合は最終スケールを (1.0, 1.0, 1.0)、それ以外は現在のスケールを使用
    if obj.type == 'EMPTY':
        final_scale = (1.0, 1.0, 1.0)
    else:
        # テキストオブジェクトなどは既存のスケールを保持
        fs = obj.scale.copy() if hasattr(obj, 'scale') and not isinstance(obj.scale, tuple) else (1.5, 1.5, 1.5)
        final_scale = (fs.x if hasattr(fs, 'x') else fs[0],
                       fs.y if hasattr(fs, 'y') else fs[1],
                       fs.z if hasattr(fs, 'z') else fs[2])

    # 初期状態：スケール 0
    obj.scale = (0.0, 0.0, 0.0)
    obj.keyframe_insert(data_path="scale", frame=start_frame)

    # ピピピッアニメーション（3 段階）
    # ステップ 1: フレーム 648→656（初期出現・小規模点滅）
    obj.scale = (final_scale[0] * 0.5, final_scale[1] * 0.5, final_scale[2] * 0.5)
    obj.keyframe_insert(data_path="scale", frame=start_frame + 8)

    # ステップ 2: フレーム 656→664（中規模拡大・点滅）
    obj.scale = (final_scale[0], final_scale[1], final_scale[2])
    obj.keyframe_insert(data_path="scale", frame=start_frame + 16)

    # ステップ 3: フレーム 664→672（最終サイズに到達・ピキッ）
    obj.scale = (final_scale[0] * 1.2, final_scale[1] * 1.2, final_scale[2] * 1.2)
    obj.keyframe_insert(data_path="scale", frame=start_frame + 24)

    # 最終安定状態（フレーム 672 以降）
    obj.scale = (final_scale[0], final_scale[1], final_scale[2])
    obj.keyframe_insert(data_path="scale", frame=start_frame + 32)
    obj.keyframe_insert(data_path="scale", frame=end_frame)


def _setup_emission_pipipi_animation(emission_nodes, start_frame, end_frame):
    """Emission Strength でピピピッ出現アニメーション（3 段階の点滅エフェクト）"""
    if not emission_nodes:
        return

    # 各ノードの元の強度を保存
    original_strengths = []
    for node in emission_nodes:
        original_strengths.append(node.inputs['Strength'].default_value)

    # ステップ 1: フレーム 648（初期状態・消灯）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = 0.0
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

    # ステップ 2: フレーム 656（初期出現・弱く点灯）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 0.3
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 8)

    # ステップ 3: フレーム 664（中規模・点滅）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 0.7
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 16)

    # ステップ 4: フレーム 672（最終強度に到達・ピキッ）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 1.3
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 24)

    # ステップ 5: フレーム 680 以降（安定状態）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i]
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 32)
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=end_frame)


def _calculate_length_difference(car_a, car_b, car_dimensions=None):
    """2 台の車の全長差を計算（mm 単位、carB - carA）

    設定ファイルの寸法値がある場合はそれを使用。
    ない場合はバウンディングボックスから計算するフォールバック。
    """
    if car_dimensions:
        length_a_mm = car_dimensions.get("carA", {}).get("length", 0)
        length_b_mm = car_dimensions.get("carB", {}).get("length", 0)
        diff_mm = length_b_mm - length_a_mm
        print(f"  carA 全長：{length_a_mm}mm, carB 全長：{length_b_mm}mm（設定値）, 差 (carB-carA): {diff_mm:+d}mm")
        return diff_mm
    
    # フォールバック：バウンディングボックスから計算
    def get_car_length(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        y_coords = [b.y for b in bounds]
        return max(y_coords) - min(y_coords)

    length_a = get_car_length(car_a)
    length_b = get_car_length(car_b)
    diff_meters = length_b - length_a
    diff_mm = int(round(diff_meters * 1000))
    print(f"  carA 長さ：{length_a:.3f}m, carB 長さ：{length_b:.3f}m（バウンディングボックス）, 差 (carB-carA): {diff_mm:+d}mm")
    return diff_mm
