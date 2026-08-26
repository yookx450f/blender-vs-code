"""
アニメーション設定モジュール - カット 2
フレーム 576-1152（シーン 5-7、滑らかなカメラ移動付き）を処理する。

【改訂: 停止シーンを削除】各シーン間の停止を削除し、カメラは常に動くように変更。
BEZIER interpolation でシーン間の接続を滑らかにする。

使い方:
    from animation_settings_cut2 import setup_cut2_animations
    setup_cut2_animations(scene, camera, imported_cars, cut1_result, car_dimensions=None)
"""

import bpy
import math
from mathutils import Vector
from animation_common import (
    set_camera_look_at, _calculate_length_difference, _calculate_width_difference,
    create_emission_material, _setup_char_by_char_animation, _setup_transparency_animation
)


def setup_cut2_animations(scene, camera, imported_cars, previous_state=None, car_dimensions=None):
    """
    カット 2 のアニメーションを設定（フレーム 576-1152、滑らかなカメラ移動付き）

    【改訂: 停止シーンを削除】各シーン間の停止を削除し、カメラは常に動くように変更。
    BEZIER interpolation でシーン間の接続を滑らかにする。

    【修正: カット完全分離】previous_state をオプション化し、
    指定されていない場合は固定位置から読み込む。

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        previous_state: CutState — 前のカットの最終状態（オプション、未指定時は固定位置使用）
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報

    Returns:
        CutState: このカットの最終状態
    """
    # 【カット完全分離】previous_state が指定された場合は従来通り使用、
    # 未指定の場合は固定位置から読み込む
    from animation_cut_positions import CAMERA_POSITIONS, get_car_positions, get_ground_z_positions
    
    if previous_state is not None:
        car_a_end = previous_state.car_a_loc
        car_b_end = previous_state.car_b_loc
        loc_phase4 = previous_state.camera_loc
        rot_phase4 = previous_state.camera_rot
    else:
        # 固定位置から読み込み
        car_a_end, car_b_end = get_car_positions()
        grounded_z_a = get_ground_z_positions().get('carA', 0.85)
        grounded_z_b = get_ground_z_positions().get('carB', 0.92)
        # カット2以降は車が中心位置にあるのでX座標を明示的に0.0に設定
        car_a_end = (0.0, car_a_end[1], car_a_end[2])
        car_b_end = (0.0, car_b_end[1], car_b_end[2])
        # カメラの開始位置は Cut1終了時の固定位置を使用
        cam_data = CAMERA_POSITIONS.get("cut1_end", {})
        loc_phase4 = cam_data.get("loc", (8.0, 0.0, 2.5))
        target = cam_data.get("target", (0.0, 0.0, 1.5))
        # rot_phase4はカメラの現在位置から計算
        direction = Vector(target) - Vector(loc_phase4)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        rot_phase4 = rot_quat.to_euler()

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return

    target = (0.0, 0.0, 1.5)

    # ============================================================
    # 【カット 2】シーン 5: フレーム 576-624（全長差表示エフェクト、2秒）
    # カメラは常に動く - 接近しながらテキスト表示
    # ============================================================
    print("\n=== 【カット 2】シーン 5 設定開始 ===")

    scene5_start = 576
    scene5_end = 624  # 2秒間（24fps × 2 = 48 フレーム）

    # カメラ: 全長差表示時に少し寄せる（X方向を8.0→6.0に接近）
    loc_phase4_close = (6.0, 0.0, 2.5)
    direction_close = Vector(target) - Vector(loc_phase4_close)
    rot_quat_close = direction_close.to_track_quat('-Z', 'Y')
    rot_phase4_close = rot_quat_close.to_euler()

    # フレーム 576: カット1終了位置から開始
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=scene5_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene5_start)

    # フレーム 624: 近い位置に移動（2秒で接近完了）
    camera.location = loc_phase4_close
    camera.rotation_euler = rot_phase4_close
    camera.keyframe_insert(data_path="location", frame=scene5_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene5_end)

    # 車: カット 1 の最終位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene5_start)
    car_a.keyframe_insert(data_path="location", frame=scene5_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene5_start)
    car_b.keyframe_insert(data_path="location", frame=scene5_end)

    print(f"[フレーム{scene5_start}] シーン 5 開始：カメラ={loc_phase4} → {loc_phase4_close}（全長差表示時に接近）, 車維持")

    # --- CarB の半透明化（カット1と同じ方式で半透明化）---
    _setup_transparency_animation(car_b, scene5_start, scene5_end, 0.4, 0.4)
    print(f"[フレーム{scene5_start}-{scene5_end}] CarB 半透明化：0.4（カット1終了時の状態を維持）")

    # --- シーン 5 の全長差エフェクト（レーザー線＋数値テキスト）---
    _setup_scene5_effects(scene, camera, car_a, car_b, scene5_start, scene5_end, car_dimensions)

    # ============================================================
    # 【カット 2】シーン 6: フレーム 624-816（サイドビューから正面へカメラ移動、8秒）
    # カメラは常に動く - サイド→正面への滑らかな軌道
    # ============================================================
    print("\n=== 【カット 2】シーン 6 設定開始 ===")

    scene6_start = 624
    scene6_end = 816  # 8秒間（24fps × 8 = 192 フレーム）

    # カメラ: サイドビュー位置から車の正面にゆっくり移動
    start_loc = loc_phase4_close
    start_rot = rot_phase4_close
    
    # 最終位置：車により近い正面ビュー
    end_loc = (0.0, -7.0, 2.5)  # 車に近づけた正面、やや上
    direction_end = Vector(target) - Vector(end_loc)
    rot_quat_end = direction_end.to_track_quat('-Z', 'Y')
    end_rot = rot_quat_end.to_euler()

    # 中間地点 - 距離 50%
    mid_frame = scene6_start + 96  # 192/2 = 96 フレーム目
    loc_mid = (start_loc[0] + end_loc[0]) / 2.0, (start_loc[1] + end_loc[1]) / 2.0, (start_loc[2] + end_loc[2]) / 2.0
    direction_mid = Vector(target) - Vector(loc_mid)
    rot_quat_mid = direction_mid.to_track_quat('-Z', 'Y')
    rot_mid = rot_quat_mid.to_euler()

    # 開始位置
    camera.location = start_loc
    camera.rotation_euler = start_rot
    camera.keyframe_insert(data_path="location", frame=scene6_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene6_start)

    # 中間キーフレーム（滑らかな移動のため）
    camera.location = loc_mid
    camera.rotation_euler = rot_mid
    camera.keyframe_insert(data_path="location", frame=mid_frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=mid_frame)

    # 終了位置
    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene6_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene6_end)

    # 車: シーン 6 の位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene6_start)
    car_a.keyframe_insert(data_path="location", frame=scene6_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene6_start)
    car_b.keyframe_insert(data_path="location", frame=scene6_end)

    print(f"[フレーム{scene6_start}] シーン 6 開始：カメラ移動開始（サイドビュー→正面）")
    print(f"[フレーム{scene6_end}] シーン 6 終了：カメラ={end_loc}（正面ビュー）, 車維持")

    # ============================================================
    # 【カット 2】シーン 7: フレーム 816-912（横幅差表示 + カメラゆっくり接近、4秒）
    # カメラは常に動く - 正面ビューからさらに接近
    # ============================================================
    print("\n=== 【カット 2】シーン 7 設定開始 ===")

    scene7_start = 816
    scene7_end = 912  # 4秒間（24fps × 4 = 96 フレーム）

    # カメラ: シーン6の終了位置からさらに接近
    scene7_end_loc = (0.0, -5.5, 2.5)  # さらに車に接近
    direction_scene7_end = Vector(target) - Vector(scene7_end_loc)
    rot_quat_scene7_end = direction_scene7_end.to_track_quat('-Z', 'Y')
    scene7_end_rot = rot_quat_scene7_end.to_euler()

    camera.location = end_loc
    camera.rotation_euler = end_rot
    camera.keyframe_insert(data_path="location", frame=scene7_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene7_start)
    camera.location = scene7_end_loc
    camera.rotation_euler = scene7_end_rot
    camera.keyframe_insert(data_path="location", frame=scene7_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene7_end)

    # 車: シーン 6 の位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene7_start)
    car_a.keyframe_insert(data_path="location", frame=scene7_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene7_start)
    car_b.keyframe_insert(data_path="location", frame=scene7_end)

    print(f"[フレーム{scene7_start}] シーン 7 開始：カメラ={end_loc} → {scene7_end_loc}（横幅差表示+接近）")
    print(f"[フレーム{scene7_end}] シーン 7 終了：カメラ={scene7_end_loc}, 車維持")

    # --- シーン 7 の横幅差エフェクト（テキストのみ）---
    _setup_scene7_effects(scene, camera, car_a, car_b, scene7_start, scene7_end, car_dimensions)

    # シーン 5 のテキストをフェードアウト（シーン 6 終了時）
    text_container_name = "LengthDiff_Container_Scene5"
    if text_container_name in bpy.data.objects:
        text_obj = bpy.data.objects[text_container_name]

        print(f"[フレーム{scene6_start}] テキストフェードアウト開始（{scene6_start}→{scene6_end}）")

        # コンテナ自体のスケールをアニメーションで制御（最も確実な方法）
        # フレーム 864: スケール維持（1.0, 1.0, 1.0）
        text_obj.scale = (1.0, 1.0, 1.0)
        text_obj.keyframe_insert(data_path="scale", frame=scene6_start)
        
        # フレーム 1032: スケールを 0 に（完全に消える）
        fade_end_frame = scene6_end  # フレーム 1032
        text_obj.scale = (0.0, 0.0, 0.0)
        text_obj.keyframe_insert(data_path="scale", frame=fade_end_frame)

        # 各文字オブジェクトにもキーフレームを設定（二重確保）
        for char_obj in text_obj.children:
            if char_obj.type == 'MESH':
                # まず現在のスケールを取得して保存
                current_scale = char_obj.scale.copy() if hasattr(char_obj, 'scale') else (1.0, 1.0, 1.0)

                # フレーム 864: 現在のスケールを維持（キーフレーム）
                char_obj.scale = current_scale
                char_obj.keyframe_insert(data_path="scale", frame=scene6_start)

                # フレーム 1032: スケールを 0 に
                char_obj.scale = (0.0, 0.0, 0.0)
                char_obj.keyframe_insert(data_path="scale", frame=fade_end_frame)

                # 発光強度も徐々に 0 に（確実に消えるように）
                if len(char_obj.data.materials) > 0:
                    mat = char_obj.data.materials[0]
                    if mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_EMISSION':
                                current_strength = node.inputs['Strength'].default_value

                                # フレーム 864: 現在の強度を維持（キーフレーム）
                                node.inputs['Strength'].default_value = current_strength
                                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=scene6_start)

                                # フレーム 1032: 強度を 0 に
                                node.inputs['Strength'].default_value = 0.0
                                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=fade_end_frame)
                        
                        # Mix Shader の Fac でも透明度を制御（二重確保）
                        for n in mat.node_tree.nodes:
                            if n.type == 'MIX_SHADER':
                                # フレーム816で完全不透明（Fac=1.0 → Emissionを完全に使用）
                                n.inputs['Fac'].default_value = 1.0
                                n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=scene6_start)
                                # フレーム984で完全透明（Fac=0.0 → Transparentを完全に使用）
                                n.inputs['Fac'].default_value = 0.0
                                n.inputs['Fac'].keyframe_insert(data_path="default_value", frame=fade_end_frame)
                                
                        # EEVEEの透過設定を確実に有効化
                        mat.blend_method = 'BLEND'
                        mat.shadow_method = 'BUFFER'

        print(f"[フレーム{scene6_end}] テキストオブジェクトのフェードアウト完了（スケール→0）")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 2 アニメーション完了 ===")

    # 結果を返す（カット3で使用する）
    # 【修正: カット完全分離】CutState 形式で最終状態のみを返す
    from animation_common import CutState
    return CutState(
        car_a_loc=car_a_end,
        car_b_loc=car_b_end,
        camera_loc=scene7_end_loc,
        camera_rot=scene7_end_rot,
    )


def _ensure_eevee_transparency(car_object):
    """CarB の全マテリアルにEEVEE透過設定を確実に適用する（複数メッシュ対応）"""
    if car_object is None:
        return
    
    all_meshes = _collect_all_mesh_objects(car_object)
    for mesh_obj in all_meshes:
        if not hasattr(mesh_obj, 'data') or mesh_obj.data is None:
            continue
        for material in mesh_obj.data.materials:
            if material is None:
                continue
            try:
                material.blend_method = 'BLEND'
                material.shadow_method = 'BUFFER'
            except AttributeError:
                pass


def _collect_all_mesh_objects(obj):
    """オブジェクトとその全子オブジェクトからMESHタイプを再帰的に収集
    親がEMPTYの場合でも子メッシュを収集する"""
    meshes = []
    if obj.type == 'MESH':
        meshes.append(obj)
    # すべての子オブジェクトを再帰的に探索
    for child in obj.children:
        meshes.extend(_collect_all_mesh_objects(child))
    return meshes


def _setup_car_b_transparency_for_scene5(car_object, start_frame, end_frame):
    """CarB の全マテリアルをシーン 5 用半透明化する（複数メッシュ対応）"""
    if car_object is None:
        return

    # 親オブジェクトとすべての子メッシュを取得
    all_meshes = _collect_all_mesh_objects(car_object)
    print(f"  [_setup_car_b_transparency] 対象メッシュ数: {len(all_meshes)}")
    
    for mesh_obj in all_meshes:
        _apply_transparency_to_materials(mesh_obj, start_frame, end_frame)


def _setup_scene5_effects(scene, camera, car_a, car_b, scene5_start, scene5_end, car_dimensions=None):
    """シーン 5 の全長差エフェクトを設定（寸法線なし、テキストのみ）"""
    # --- 全長差の計算と取得 ---
    length_diff_mm = _calculate_length_difference(car_a, car_b, car_dimensions)

    # 両車の実際の長さも取得（mm 単位）
    if car_dimensions:
        length_a_mm = car_dimensions.get("carA", {}).get("length", 0)
        length_b_mm = car_dimensions.get("carB", {}).get("length", 0)
    else:
        # フォールバック：バウンディングボックスから計算
        def get_car_length(car_obj):
            bounds = [Vector(b) for b in car_obj.bound_box]
            y_coords = [b.y for b in bounds]
            return max(y_coords) - min(y_coords)

        length_a = get_car_length(car_a)
        length_b = get_car_length(car_b)
        length_a_mm = int(round(length_a * 1000))
        length_b_mm = int(round(length_b * 1000))

    print(f"[シーン 5] 全長差：{length_diff_mm:+d}mm (CarB: {length_b_mm}mm, CarA: {length_a_mm}mm)")

    # --- 数値テキストの作成（ピピピッ出現アニメーション付き）---
    text_obj = _create_length_diff_text(scene, camera, length_a_mm, length_b_mm, length_diff_mm, car_a, car_b, scene5_start, scene5_end, car_dimensions)
    if text_obj:
        print(f"[シーン 5] 数値テキスト '{text_obj.name}' を作成しました")

    print(f"[フレーム{scene5_end}] シーン 5 終了：全長差表示完了")


def _create_length_diff_text(scene, camera, length_a_mm, length_b_mm, length_diff_mm, car_a, car_b, start_frame, end_frame, car_dimensions=None):
    """計算式を表示するテキストを作成（CarB - CarA → 結果）"""

    # 各車の中心座標を取得
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

    # 両車の中心座標を取得（平均）
    center_a = get_car_center(car_a)
    center_b = get_car_center(car_b)
    avg_center_x = (center_a[0] + center_b[0]) / 2.0
    avg_center_y = (center_a[1] + center_b[1]) / 2.0

    # 車の最高点を取得（Z 座標）
    def get_car_max_z(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        world_bounds = [car_obj.matrix_world @ b for b in bounds]
        return max(p.z for p in world_bounds)

    # 車の位置情報を取得（デバッグ用）
    print(f"=== DEBUG: Car Positions ===")
    print(f"carA location: {car_a.location}")
    print(f"carB location: {car_b.location}")
    print(f"carA center: {center_a}")
    print(f"carB center: {center_b}")
    print(f"avg_center: ({avg_center_x}, {avg_center_y})")

    car_max_z_a = get_car_max_z(car_a)
    car_max_z_b = get_car_max_z(car_b)
    max_height = max(car_max_z_a, car_max_z_b)
    print(f"carA max Z: {car_max_z_a}")
    print(f"carB max Z: {car_max_z_b}")
    print(f"max_height: {max_height}")

    # テキスト全体を格納する Empty を作成（コンテナ）
    # 地面からの絶対的な高さを確保し、常に明確に見えるように配置
    # 車の中心位置を使用
    avg_center_x = (center_a[0] + center_b[0]) / 2.0
    avg_center_y = (center_a[1] + center_b[1]) / 2.0
    
    # 地面からの絶対高さを確保（文字位置を下げるために2.0mに調整）
    text_container_location = (avg_center_x, avg_center_y, 2.0)
    
    bpy.ops.object.empty_add(location=text_container_location)
    text_container = bpy.context.active_object
    text_container.name = "LengthDiff_Container_Scene5"

    # カメラに向くように回転（Z軸は上方向に保つ）
    # テキストが正しく見えるように180度回転を追加
    cam_pos = camera.location
    container_pos = Vector(text_container_location)
    direction = cam_pos - container_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    euler_rot = rot_quat.to_euler()
    # Z軸に180度（πラジアン）追加してテキストの向きを修正
    euler_rot.z += math.pi
    text_container.rotation_euler = euler_rot

    # シーンにリンク
    scene.collection.objects.link(text_container)

    # 【デバッグ】コンテナの位置と回転を出力
    print(f"=== TEXT CONTAINER DEBUG ===")
    print(f"text_container.location: {text_container.location}")
    print(f"text_container.rotation_euler: {text_container.rotation_euler}")
    print(f"text_container.parent: {text_container.parent}")

    # 文字列を作成： "全長：CarB - CarA → 結果"
    # 例: "全長：4890mm - 4460mm → +430mm"
    text_str = f"全長：{length_b_mm}mm - {length_a_mm}mm → {length_diff_mm:+d}mm"

    # 各文字を個別のテキストオブジェクトとして作成
    char_objects = []
    half_spacing = 0.12  # 半角文字の基本間隔
    full_spacing = 0.20  # 全角文字の間隔（日本語など）

    # 車の色を取得（car_dimensions から、なければデフォルト使用）
    if car_dimensions:
        car_a_color = car_dimensions.get("carA", {}).get("color", (0.5, 0.5, 0.5))
        car_b_color = car_dimensions.get("carB", {}).get("color", (0.0, 0.7, 1.0))
    else:
        car_a_color = (0.5, 0.5, 0.5)  # デフォルトグレー系
        car_b_color = (0.0, 0.7, 1.0)  # デフォルト鮮やかな青

    print(f"[シーン5] carAの色: {car_a_color}, carBの色: {car_b_color}")

    # 色の定義：CarB=車の色、CarA=車の色、結果=白
    colors = {
        'carb': car_b_color,
        'cara': car_a_color,
        'yellow': (1.0, 1.0, 0.2)     # 黄色（結果）
    }

    # 文字ごとの色を定義（インデックスで管理）
    # "4890mm - 4460mm → +430mm" の各部分
    color_map = ['yellow'] * len(text_str)  # 初期値は全て黄色

    # 数字のブロックを特定：CarB (最初の数字), CarA (2 番目の数字), 結果 (3 番目の数字)
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

    # 各ブロックに色を割り当て
    for idx, block in enumerate(number_blocks):
        if idx == 0:
            color = 'carb'   # CarB (最初の数字) - carBの色
        elif idx == 1:
            color = 'cara'    # CarA (2 番目の数字) - carAの色
        else:
            color = 'yellow'  # 結果やその他

        for pos in block:
            if pos < len(color_map):
                color_map[pos] = color

    print(f"Color map: {color_map}")

    for i, char in enumerate(text_str):
        # テキストオブジェクトを作成（一時的な位置）
        # 地面からの絶対的な高さを確保（Z=4.0）
        bpy.ops.object.text_add(location=(0, 0, 4.0))
        char_obj = bpy.context.active_object
        char_obj.name = f"LengthDiff_Char_{i}"

        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char

        # サイズを大きく設定 - テキストサイズを直接調整（オブジェクトスケールは 1.0 維持）
        if hasattr(char_obj.data, 'size'):
            # すべての文字を同じサイズに統一
            char_obj.data.size = 0.22  # 通常サイズも少し拡大（調整）

        # オブジェクトスケールを 1.0 に設定（アニメーション用）
        char_obj.scale = (1.0, 1.0, 1.0)

        # 発光マテリアルを適用（色付き）
        color_name = color_map[i] if i < len(color_map) else 'yellow'
        mat_name = f"emission_label_scene5_char_{color_name}"
        if mat_name not in bpy.data.materials:
            emission_mat = create_emission_material(colors[color_name], 5.0)
            emission_mat.name = mat_name
        else:
            emission_mat = bpy.data.materials[mat_name]

        if len(char_obj.data.materials) == 0:
            char_obj.data.materials.append(emission_mat)

        # Container にペアレント設定（子オブジェクトをリンク）
        char_obj.parent = text_container

        # シーンにリンク
        scene.collection.objects.link(char_obj)

        char_objects.append(char_obj)

    # 全角/半角を考慮した位置計算
    # 各文字の幅を計算（全角は wide、半角は narrow）
    def is_fullwidth(c):
        """全角文字かどうかを判定"""
        code = ord(c)
        return (0x4E00 <= code <= 0x9FFF) or \
               (0x3000 <= code <= 0x303F) or \
               (0xFF00 <= code <= 0xFFEF) or \
               (0x3040 <= code <= 0x309F) or \
               (0x30A0 <= code <= 0x30FF)

    # 各文字の幅を計算
    char_widths = []
    for c in text_str:
        if is_fullwidth(c):
            char_widths.append(full_spacing)
        else:
            char_widths.append(half_spacing)

    total_width = sum(char_widths)

    # 各文字の位置を設定（中央揃え）
    current_x = -total_width / 2.0
    for i, char_obj in enumerate(char_objects):
        local_x = current_x
        current_x += char_widths[i]

        # ローカル Y は少し上、Z を下げて文字位置を調整
        local_y = 0.5
        local_z = -0.3

        char_obj.location = (local_x, local_y, local_z)

    # アニメーションを設定（コンテナの子オブジェクトに対して）
    _setup_char_by_char_animation(char_objects, start_frame=start_frame, end_frame=end_frame)

    print(f"[シーン 5] 計算式テキスト '{text_str}' を {len(char_objects)} 文字で作成")
    return text_container


def _apply_transparency_to_materials(car_object, start_frame, end_frame):
    """オブジェクトの全マテリアルを指定フレーム間で半透明化する
    Principled BSDFのAlpha入力を使用（シーン9と同じ方式）"""
    if car_object is None:
        return

    # デバッグ出力
    print(f"  [_apply_transparency] {car_object.name}: type={car_object.type}, materials={len(car_object.data.materials) if hasattr(car_object, 'data') and car_object.data else 0}")

    if not hasattr(car_object, 'data') or car_object.data is None:
        return

    for material in car_object.data.materials:
        if material is None:
            continue

        # EEVEE 透過対応 - 確実に有効化
        try:
            material.blend_method = 'BLEND'
            material.shadow_method = 'BUFFER'
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
        # 開始フレーム: Alpha=1.0（完全不透明）
        alpha_input.default_value = 1.0
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        # 終了フレーム: Alpha=0.35（半透明）
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)


def _setup_scene7_effects(scene, camera, car_a, car_b, scene7_start, scene7_end, car_dimensions=None):
    """シーン 7 の横幅差エフェクトを設定"""
    width_diff_mm = _calculate_width_difference(car_a, car_b, car_dimensions)

    if car_dimensions:
        # テキスト表示にはCSVの生値を使用（+20cm加算前の値）
        width_a_mm = car_dimensions.get("carA", {}).get("width_raw", car_dimensions.get("carA", {}).get("width", 0))
        width_b_mm = car_dimensions.get("carB", {}).get("width_raw", car_dimensions.get("carB", {}).get("width", 0))
    else:
        def get_car_width(car_obj):
            bounds = [Vector(b) for b in car_obj.bound_box]
            x_coords = [b.x for b in bounds]
            return max(x_coords) - min(x_coords)
        width_a = get_car_width(car_a)
        width_b = get_car_width(car_b)
        width_a_mm = int(round(width_a * 1000))
        width_b_mm = int(round(width_b * 1000))

    print(f"[シーン 7] 横幅差：{width_diff_mm:+d}mm (CarB: {width_b_mm}mm, CarA: {width_a_mm}mm)")

    text_obj = _create_width_diff_text(scene, camera, width_a_mm, width_b_mm, width_diff_mm, car_a, car_b, scene7_start, scene7_end, car_dimensions)
    if text_obj:
        print(f"[シーン 7] 数値テキスト '{text_obj.name}' を作成しました")

    print(f"[フレーム{scene7_end}] シーン 7 終了：横幅差表示完了")


def _create_width_diff_text(scene, camera, width_a_mm, width_b_mm, width_diff_mm, car_a, car_b, start_frame, end_frame, car_dimensions=None, setup_animation=True):
    """横幅の計算式を表示するテキストを作成（CarB - CarA → 結果）
    
    Parameters:
        setup_animation: Trueの場合、フェードインアニメーションを設定する。
                        Falseの場合、アニメーションキーフレームは設定しない（カット3独立実行用）。
    """
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

    center_a = get_car_center(car_a)
    center_b = get_car_center(car_b)
    avg_center_x = (center_a[0] + center_b[0]) / 2.0
    avg_center_y = (center_a[1] + center_b[1]) / 2.0

    def get_car_max_z(car_obj):
        bounds = [Vector(b) for b in car_obj.bound_box]
        world_bounds = [car_obj.matrix_world @ b for b in bounds]
        return max(p.z for p in world_bounds)

    car_max_z_a = get_car_max_z(car_a)
    car_max_z_b = get_car_max_z(car_b)
    max_height = max(car_max_z_a, car_max_z_b)

    avg_center_x = (center_a[0] + center_b[0]) / 2.0
    avg_center_y = (center_a[1] + center_b[1]) / 2.0
    
    text_container_location = (avg_center_x, avg_center_y, 2.0)
    
    bpy.ops.object.empty_add(location=text_container_location)
    text_container = bpy.context.active_object
    text_container.name = "WidthDiff_Container_Scene7"

    cam_pos = camera.location
    container_pos = Vector(text_container_location)
    direction = cam_pos - container_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    euler_rot = rot_quat.to_euler()
    euler_rot.z += math.pi
    text_container.rotation_euler = euler_rot

    scene.collection.objects.link(text_container)

    # 差の計算も表示と同じCSV生値（width_raw）で行う
    if car_dimensions:
        width_a_for_calc = car_dimensions.get("carA", {}).get("width_raw", car_dimensions.get("carA", {}).get("width", 0))
        width_b_for_calc = car_dimensions.get("carB", {}).get("width_raw", car_dimensions.get("carB", {}).get("width", 0))
        diff_mm = width_b_for_calc - width_a_for_calc
    else:
        diff_mm = width_diff_mm
    text_str = f"全幅：{width_b_mm}mm - {width_a_mm}mm → {diff_mm:+d}mm"

    char_objects = []
    half_spacing = 0.12  # 半角文字の基本間隔
    full_spacing = 0.20  # 全角文字の間隔（日本語など）

    # 車の色を取得（car_dimensions から、なければデフォルト使用）
    if car_dimensions:
        car_a_color = car_dimensions.get("carA", {}).get("color", (0.5, 0.5, 0.5))
        car_b_color = car_dimensions.get("carB", {}).get("color", (0.0, 0.7, 1.0))
    else:
        car_a_color = (0.5, 0.5, 0.5)
        car_b_color = (0.0, 0.7, 1.0)

    print(f"[シーン7] carAの色: {car_a_color}, carBの色: {car_b_color}")

    colors = {
        'carb': car_b_color,
        'cara': car_a_color,
        'yellow': (1.0, 1.0, 0.2)     # 黄色（結果）
    }

    color_map = ['yellow'] * len(text_str)

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
            color = 'carb'   # CarBの色
        elif idx == 1:
            color = 'cara'   # CarAの色
        else:
            color = 'yellow'

        for pos in block:
            if pos < len(color_map):
                color_map[pos] = color

    for i, char in enumerate(text_str):
        bpy.ops.object.text_add(location=(0, 0, 4.0))
        char_obj = bpy.context.active_object
        char_obj.name = f"WidthDiff_Char_{i}"

        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char

        if hasattr(char_obj.data, 'size'):
            char_obj.data.size = 0.22

        char_obj.scale = (1.0, 1.0, 1.0)

        color_name = color_map[i] if i < len(color_map) else 'yellow'
        mat_name = f"emission_label_scene7_char_{color_name}"
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

        local_y = 0.5
        local_z = -0.3

        char_obj.location = (local_x, local_y, local_z)

    if setup_animation:
        _setup_char_by_char_animation(char_objects, start_frame=start_frame, end_frame=end_frame)
    else:
        # アニメーションなし：初めから完全表示状態（スケール1.0）に設定
        for char_obj in char_objects:
            char_obj.scale = (1.0, 1.0, 1.0)
            # 発光強度も最大値に設定
            if len(char_obj.data.materials) > 0:
                for node in char_obj.data.materials[0].node_tree.nodes:
                    if node.type == 'BSDF_EMISSION':
                        node.inputs['Strength'].default_value = 5.0

    print(f"[シーン 7] 計算式テキスト '{text_str}' を {len(char_objects)} 文字で作成")
    return text_container
