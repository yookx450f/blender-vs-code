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


class CutState:
    """カット間の状態継承用データ構造
    
    各カットは前のカットの最終状態（位置情報のみ）を受け取り、
    自分の最終状態を返すことで、完全な分離を実現する。
    
    animation_data を共有しないため、後続カットの処理が前面に影響しない。
    """
    def __init__(self, car_a_loc, car_b_loc, camera_loc, camera_rot):
        self.car_a_loc = car_a_loc  # (x, y, z)
        self.car_b_loc = car_b_loc  # (x, y, z)
        self.camera_loc = camera_loc  # (x, y, z)
        self.camera_rot = camera_rot  # (x, y, z) euler
    
    def __repr__(self):
        return (f"CutState(car_a={self.car_a_loc}, car_b={self.car_b_loc}, "
                f"camera_loc={self.camera_loc}, camera_rot={self.camera_rot})")


def set_camera_look_at(cam, loc, tgt):
    """カメラを指定位置に配置し、ターゲット方向に向ける"""
    cam.location = loc
    direction = Vector(tgt) - Vector(loc)
    rot_quat = direction.to_track_quat('-Z', 'Y')  # カメラの-Z軸をターゲット方向へ
    cam.rotation_euler = rot_quat.to_euler()


def create_emission_material(color_rgb, strength):
    """発光マテリアルを作成（再利用用）
    
    Mix Shader + Transparent BSDF + Emission の構成を使用し、
    透明度をアニメーションで制御できるようにする。
    """
    mat = bpy.data.materials.new(name="emission_temp")
    mat.use_nodes = True
    # EEVEEで透過を有効化
    mat.blend_method = 'BLEND'

    nodes = mat.node_tree.nodes
    nodes.clear()

    links = mat.node_tree.links

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (500, 0)

    # Mix Shader ノード（透明度制御用）
    mix_shader = nodes.new(type='ShaderNodeMixShader')
    mix_shader.location = (300, 0)
    # Fac = 1.0 で Emission を完全に使用、0.0 で Transparent を完全に使用
    mix_shader.inputs['Fac'].default_value = 1.0

    # Transparent BSDF ノード
    transparent_node = nodes.new(type='ShaderNodeBsdfTransparent')
    transparent_node.location = (100, -100)

    # Emission ノード
    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.location = (100, 100)
    emission_node.inputs['Color'].default_value = (*color_rgb, 1.0)
    emission_node.inputs['Strength'].default_value = strength * 2  # 発光強度を2倍に強化

    # ノード接続
    links.new(emission_node.outputs['Emission'], mix_shader.inputs[2])  # Shader A
    links.new(transparent_node.outputs['BSDF'], mix_shader.inputs[1])   # Shader B
    links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])

    return mat


def _collect_all_mesh_objects_recursive(obj):
    """オブジェクトとその全子オブジェクトからMESHタイプを再帰的に収集"""
    meshes = []
    if obj and obj.type == 'MESH':
        meshes.append(obj)
    if obj:
        for child in obj.children:
            meshes.extend(_collect_all_mesh_objects_recursive(child))
    return meshes


def clear_material_animation(node_tree):
    """マテリアルノードツリーのアニメーションデータを完全にクリアする
    Blender 5.xのレイヤー化アクションシステムに対応
    
    Parameters:
        node_tree: bpy.types.NodeTree (マテリアルのノードツリー)
    """
    if not hasattr(node_tree, 'animation_data'):
        return
    
    if node_tree.animation_data is None:
        return
    
    action = node_tree.animation_data.action
    if not action:
        return
    
    # Blender 4.x以前: fcurves直接アクセス
    if hasattr(action, 'fcurves'):
        while len(action.fcurves) > 0:
            action.fcurves.remove(0)
    # Blender 5.x: レイヤー化アクションシステム
    elif hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type == 'KEYFRAME':
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            while len(fc.keyframe_points) > 0:
                                fc.keyframe_points.remove(0)


def _setup_transparency_animation(car_object, start_frame, end_frame, start_alpha, end_alpha):
    """車のマテリアル不透明度をアニメーションさせる（内部用）
    
    Blender 5.xのNodeTreeアニメーションの問題を回避するため、
    ドライバーベースのアプローチを使用。
    
    ドライバー式に直接計算式を書き、フレーム番号からAlpha値を計算する方式。
    clamp(frame, start_frame, end_frame) を使用して範囲外をクリップ。
    """
    if car_object is None:
        return

    all_meshes = _collect_all_mesh_objects_recursive(car_object)
    
    if not all_meshes:
        if car_object.type == 'MESH' and len(car_object.data.materials) > 0:
            all_meshes = [car_object]
        else:
            return

    # ドライバー式: フレーム番号からAlpha値を計算
    # alpha = start_alpha - (start_alpha - end_alpha) * clamp((frame - start_frame) / (end_frame - start_frame), 0, 1)
    # Blenderのドライバーでは clamp(a, min, max) 関数を使用可能
    sf = float(start_frame)
    ef = float(end_frame)
    sa = float(start_alpha)
    ea = float(end_alpha)
    
    # 式: frame < start_frame なら常に完全不透明(1.0)を返し、それ以外は通常計算
    # これにより、アニメーション開始前はstart_alphaの影響を受けず、常に不透明になる
    expr = f"1.0 if frame < {sf} else {sa} + ({ea} - {sa}) * clamp((frame - {sf}) / ({ef} - {sf}), 0.0, 1.0)"

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
            alpha_input.driver_remove("default_value")
            driver = alpha_input.driver_add("default_value").driver
            driver.type = 'SCRIPTED'
            driver.expression = expr
            print(f"    ドライバー式: {expr}")

    print(f"  Alphaアニメーション(ドライバー式): {car_object.name} フレーム{start_frame}-{end_frame} ({start_alpha}→{end_alpha})")

def _get_material_color(material):
    """マテリアルからベースカラーを取得"""
    if not material or not material.use_nodes:
        return (0.5, 0.5, 0.5)
    
    nodes = material.node_tree.nodes
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            if 'Base Color' in node.inputs:
                return tuple(node.inputs['Base Color'].default_value[:3])
            elif 'Color' in node.inputs:
                return tuple(node.inputs['Color'].default_value[:3])
    return (0.5, 0.5, 0.5)


def _setup_transparency_keyframe_animation(car_object, start_frame, end_frame, start_alpha, end_alpha, step_frames=8):
    """車のマテリアル不透明度をキーフレームでアニメーションさせる（Mix Shader Fac 方式）
    
    Blender 5.x の NodeTree アニメーションの問題を回避するため、
    Mix Shader + Transparent BSDF + Principled BSDF の構成を使用し、
    Mix Shader の Fac（混合比率）にキーフレームを設定する。
    
    Fac = 1.0 で完全不透明、Fac = 0.0 で完全透明
    
    Parameters:
        car_object: 半透明化対象の車オブジェクト
        start_frame: 半透明化開始フレーム
        end_frame: 半透明化終了フレーム
        start_alpha: 開始時のAlpha値 (1.0=完全不透明)
        end_alpha: 終了時のAlpha値 (0.0=完全透明)
        step_frames: キーフレーム間隔（フレーム数、デフォルト8=約0.33秒）
    """
    if car_object is None:
        return

    all_meshes = _collect_all_mesh_objects_recursive(car_object)
    
    if not all_meshes:
        if car_object.type == 'MESH' and len(car_object.data.materials) > 0:
            all_meshes = [car_object]
        else:
            return

    # キーフレームを設定するフレームリストを生成
    frames = list(range(start_frame, end_frame + 1, step_frames))
    if frames[-1] != end_frame:
        frames.append(end_frame)

    processed_materials = set()  # 同じマテリアルを複数回処理しないようにする

    for mesh_obj in all_meshes:
        if not hasattr(mesh_obj, 'data') or mesh_obj.data is None:
            continue
        for material in mesh_obj.data.materials:
            if material is None or not material.use_nodes:
                continue
            # 同じマテリアルは1回だけ処理
            if id(material) in processed_materials:
                continue
            processed_materials.add(id(material))
            
            try:
                material.blend_method = 'BLEND'
            except AttributeError:
                pass
            
            # 元のマテリアルの色を取得
            original_color = _get_material_color(material)
            
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            
            # 既存のノードをクリアして Mix Shader 構成を作成
            nodes.clear()
            
            # Output ノード
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (600, 0)
            
            # Mix Shader ノード（Fac をキーフレームで制御）
            mix_shader = nodes.new(type='ShaderNodeMixShader')
            mix_shader.location = (400, 0)
            mix_shader.inputs['Fac'].default_value = start_alpha
            
            # Transparent BSDF（完全透明）
            transparent_bsdf = nodes.new(type='ShaderNodeBsdfTransparent')
            transparent_bsdf.location = (200, -150)
            
            # Principled BSDF（元のマテリアルの色を使用）
            principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled_bsdf.location = (200, 150)
            principled_bsdf.inputs['Base Color'].default_value = (*original_color, 1.0)
            principled_bsdf.inputs['Roughness'].default_value = 0.8
            principled_bsdf.inputs['Metallic'].default_value = 0.0
            
            # ノード接続
            # Mix Shader: Fac=0.0 → Shader A、Fac=1.0 → Shader B
            # Fac = 1.0 で完全不透明にするため、Principled BSDFをinput[2]に接続
            links.new(transparent_bsdf.outputs['BSDF'], mix_shader.inputs[1])   # Shader A (透明)
            links.new(principled_bsdf.outputs['BSDF'], mix_shader.inputs[2])    # Shader B (車)
            links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])
            
            # Fac にキーフレームを設定
            fac_input = mix_shader.inputs['Fac']
            
            # フレーム0で完全不透明のキーフレームを追加（開始前も完全に不透明）
            bpy.context.scene.frame_set(0)
            fac_input.default_value = start_alpha
            fac_input.keyframe_insert(data_path="default_value", frame=0)
            
            for frame in frames:
                progress = (frame - start_frame) / max(1, (end_frame - start_frame))
                fac_value = start_alpha + (end_alpha - start_alpha) * progress
                
                bpy.context.scene.frame_set(frame)
                fac_input.default_value = fac_value
                fac_input.keyframe_insert(data_path="default_value", frame=frame)
            
            # 終了フレームで最終値を確実に設定
            bpy.context.scene.frame_set(end_frame)
            fac_input.default_value = end_alpha
            fac_input.keyframe_insert(data_path="default_value", frame=end_frame)
            
            # インターポレーションをLINEARに設定
            try:
                if hasattr(material.node_tree, 'animation_data') and material.node_tree.animation_data:
                    action = material.node_tree.animation_data.action
                    if action and hasattr(action, 'fcurves'):
                        for fc in action.fcurves:
                            if 'Fac' in fc.data_path:
                                for kf in fc.keyframe_points:
                                    kf.interpolation = 'LINEAR'
            except Exception as e:
                print(f"    ⚠ インターポレーション設定エラー: {e}")

    # シーンをフレーム0に戻す
    bpy.context.scene.frame_set(0)
    
    print(f"  Alphaアニメーション(Mix Shader Fac): {car_object.name} フレーム{start_frame}-{end_frame} ({start_alpha}→{end_alpha})")


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


def _calculate_width_difference(car_a, car_b, car_dimensions=None):
    """2 台の車の横幅差を計算（mm 単位、carB - carA）

    設定ファイルの寸法値がある場合はそれを使用。
    ない場合はバウンディングボックスから計算するフォールバック。
    """
    if car_dimensions:
        width_a_mm = car_dimensions.get("carA", {}).get("width", 0)
        width_b_mm = car_dimensions.get("carB", {}).get("width", 0)
        diff_mm = width_b_mm - width_a_mm
        print(f"  carA 横幅：{width_a_mm}mm, carB 横幅：{width_b_mm}mm（設定値）, 差 (carB-carA): {diff_mm:+d}mm")
        return diff_mm
    
    # フォールバック：バウンディングボックスから計算
    def get_car_width(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        x_coords = [b.x for b in bounds]
        return max(x_coords) - min(x_coords)

    width_a = get_car_width(car_a)
    width_b = get_car_width(car_b)
    diff_meters = width_b - width_a
    diff_mm = int(round(diff_meters * 1000))
    print(f"  carA 横幅：{width_a:.3f}m, carB 横幅：{width_b:.3f}m（バウンディングボックス）, 差 (carB-carA): {diff_mm:+d}mm")
    return diff_mm


def _calculate_ground_clearance_difference(car_a, car_b, car_dimensions=None):
    """2台の車の最低地上高差を計算（mm単位、carB - carA）

    設定ファイルの寸法値がある場合はそれを使用。
    """
    if car_dimensions:
        clearance_a_mm = car_dimensions.get("carA", {}).get("ground_clearance", 0)
        clearance_b_mm = car_dimensions.get("carB", {}).get("ground_clearance", 0)
        diff_mm = clearance_b_mm - clearance_a_mm
        print(f"  carA 最低地上高：{clearance_a_mm}mm, carB 最低地上高：{clearance_b_mm}mm（設定値）, 差 (carB-carA): {diff_mm:+d}mm")
        return diff_mm
    
    # フォールバック：0を返す（バウンディングボックスからの自動検出は困難）
    print("  警告: 最低地上高の設定値が見つかりません。差は0として計算します。")
    return 0


def _calculate_turning_radius_difference(car_a, car_b, car_dimensions=None):
    """2台の車の最小回転半径差を計算（mm単位、carB - carA）

    設定ファイルの寸法値がある場合はそれを使用。
    """
    if car_dimensions:
        radius_a_mm = car_dimensions.get("carA", {}).get("turning_radius", 0)
        radius_b_mm = car_dimensions.get("carB", {}).get("turning_radius", 0)
        diff_mm = radius_b_mm - radius_a_mm
        print(f"  carA 最小回転半径：{radius_a_mm}mm, carB 最小回転半径：{radius_b_mm}mm（設定値）, 差 (carB-carA): {diff_mm:+d}mm")
        return diff_mm
    
    # フォールバック：0を返す
    print("  警告: 最小回転半径の設定値が見つかりません。差は0として計算します。")
    return 0
