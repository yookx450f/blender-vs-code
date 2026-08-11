"""
アニメーション設定モジュール

フレーム順にカメラ・車・エフェクトのキーフレームを設定する。
blend_scene_creator.py からインポートして使用。

使い方:
    from animation_settings import setup_all_animations
    setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions)
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


def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    """
    すべてのアニメーションを設定（フレーム順にまとめる）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用のYオフセット値
        grounded_z_positions: {object_name: z_value} 接地後のZ位置を保存する辞書
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報（設定ファイルから）
    """
    print("\n=== アニメーション設定を開始（フレーム順）===")

    # ============================================================
    # カット割り・シーンフレーム範囲を設定
    # ============================================================
    # タイムライン（カット割り）:
    #   【カット1】= シーン1〜4の連続
    #     シーン1: フレーム0-96      斜め上の固定視点（4秒）
    #              フレーム96-144    停止（2秒）
    #     シーン2: フレーム144-264   トップビューへ移動（5秒）
    #              フレーム264-312   停止（2秒）
    #     シーン3: フレーム312-408   Z軸回転で車が横になる（4秒）
    #              フレーム408-456   停止（2秒）
    #     シーン4: フレーム456-600   サイドビューへ移動（6秒）
    #              フレーム600-648   サイドビューで静止（2秒）
    #   【カット2】= シーン5（カット1の最終位置から開始）
    #     シーン5: フレーム648-792   真横固定視点・全長差表示エフェクト（6秒）
    scene.frame_start = 0
    scene.frame_end = 936
    scene.render.fps = 24
    print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end} (fps={scene.render.fps})")

    # ============================================================
    # 前提計算：車の位置・接地Zを準備
    # ============================================================
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return

    # 接地後のZ位置を取得（外部の辞書から）
    grounded_z_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    grounded_z_b = grounded_z_positions.get(car_b.name, car_b.location.z)

    # 車のターゲット位置を定義
    car_a_start = (-2.0, rear_offset_y, grounded_z_a)   # 左・リア端揃え
    car_a_end = (0.0, rear_offset_y, grounded_z_a)      # 中央・リア端揃え
    car_b_start = (2.0, 0.0, grounded_z_b)              # 右・基準
    car_b_end = (0.0, 0.0, grounded_z_b)                # 中央・基準

    # カメラのターゲット（車の中心付近）
    target = (0.0, 0.0, 1.5)

    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"Track To コンストレイント '{constraint.name}' を無効化しました")

    # ============================================================
    # フレーム順にキーフレームを設定
    # ============================================================

    # --- フレーム0: スタート ---
    # カメラ: 斜め上の固定視点 (6.5, -6.5, 4.0)
    loc_phase1 = (6.5, -6.5, 4.0)
    set_camera_look_at(camera, loc_phase1, target)
    rot_phase1 = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=0)
    camera.keyframe_insert(data_path="rotation_euler", frame=0)

    # 車A: 左側に配置 (-2.0, rear_offset_y)
    car_a.location = car_a_start
    car_a.keyframe_insert(data_path="location", frame=0)

    # 車B: 右側に配置 (2.0, 0.0)
    car_b.location = car_b_start
    car_b.keyframe_insert(data_path="location", frame=0)

    print(f"[フレーム0] カメラ={loc_phase1}, carA={car_a_start}, carB={car_b_start}")

    # --- フレーム30: 出現完了、半透明化開始 ---
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=30)
    camera.keyframe_insert(data_path="rotation_euler", frame=30)

    car_a.location = car_a_start
    car_a.keyframe_insert(data_path="location", frame=30)
    car_b.location = car_b_start
    car_b.keyframe_insert(data_path="location", frame=30)

    # Alpha: CarBのみ半透明化アニメーション開始（フレーム30-96で1.0→0.4）
    car_b_obj = imported_cars.get("carB")
    if car_b_obj:
        _setup_transparency_animation(car_b_obj, 30, 96, 1.0, 0.4)

    print(f"[フレーム30] カメラ維持, 車維持, Alpha(CarBのみ): 1.0→0.4開始")

    # --- シーン1終了・シーン2開始: フレーム96（中央集合・半透明化完了）---
    # カメラ: 同じ位置維持（固定視点終了）
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=96)
    camera.keyframe_insert(data_path="rotation_euler", frame=96)

    # 車A: 中央に集まる (0.0, rear_offset_y) - リア端揃え状態を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=96)

    # 車B: 中央に集まる (0.0, 0.0) - 基準位置
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=96)

    print(f"[フレーム96] シーン1終了: カメラ維持, carA={car_a_end}, carB={car_b_end}")

    # --- 停止（2秒）: フレーム144 ---
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=144)
    camera.keyframe_insert(data_path="rotation_euler", frame=144)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=144)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=144)

    print(f"[フレーム144] 停止（2秒）")

    # --- シーン2: フレーム264（トップビュー到達・車が縦に見える）---
    loc_phase2 = (0.0, 0.0, 14.0)
    set_camera_look_at(camera, loc_phase2, target)
    rot_phase2 = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=264)
    camera.keyframe_insert(data_path="rotation_euler", frame=264)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=264)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=264)

    print(f"[フレーム264] シーン2終了: カメラ={loc_phase2}（トップビュー、車が縦）, 車維持")

    # --- 停止（2秒）: フレーム312 ---
    camera.location = loc_phase2
    camera.rotation_euler = rot_phase2
    camera.keyframe_insert(data_path="location", frame=312)
    camera.keyframe_insert(data_path="rotation_euler", frame=312)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=312)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=312)

    print(f"[フレーム312] 停止（2秒）")

    # --- シーン3: フレーム408（Z軸回転完了・車が横に見える）---
    loc_phase3 = (0.0, 0.0, 14.0)
    rot_phase3 = (rot_phase2.x, rot_phase2.y, rot_phase2.z + math.pi / 2)
    camera.location = loc_phase3
    camera.rotation_euler = rot_phase3
    camera.keyframe_insert(data_path="location", frame=408)
    camera.keyframe_insert(data_path="rotation_euler", frame=408)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=408)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=408)

    print(f"[フレーム408] シーン3終了: カメラ={loc_phase3}（Z軸回転、車が横）, 車維持")

    # --- 停止（2秒）: フレーム456 ---
    camera.location = loc_phase3
    camera.rotation_euler = rot_phase3
    camera.keyframe_insert(data_path="location", frame=456)
    camera.keyframe_insert(data_path="rotation_euler", frame=456)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=456)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=456)

    print(f"[フレーム456] 停止（2秒）")

    # --- シーン4: フレーム600（サイドビュー到達）---
    loc_phase4 = (8.0, 0.0, 2.5)
    direction_phase4 = Vector(target) - Vector(loc_phase4)
    rot_quat_phase4 = direction_phase4.to_track_quat('-Z', 'Y')
    rot_phase4 = rot_quat_phase4.to_euler()
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=600)
    camera.keyframe_insert(data_path="rotation_euler", frame=600)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=600)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=600)

    print(f"[フレーム600] シーン4終了: カメラ={loc_phase4}（サイドビュー）, 車維持")

    # --- サイドビュー静止（2秒）: フレーム648 ---
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=648)
    camera.keyframe_insert(data_path="rotation_euler", frame=648)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=648)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=648)

    print(f"[フレーム648] サイドビュー静止（2秒）, 車維持")

    # ============================================================
    # 【カット2】シーン5: フレーム648-792（真横固定視点・全長差表示エフェクト）
    # カット1の最終位置から開始（カメラはピタッと止まった状態）
    # ============================================================
    print("\n=== 【カット2】シーン5設定開始 ===")

    scene5_start = 648
    scene5_end = 792  # 6秒間（24fps × 6 = 144フレーム）

    # カメラ: カット1の最終位置を維持（真横固定視点・ピタッと停止）
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=scene5_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene5_start)
    camera.keyframe_insert(data_path="location", frame=scene5_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene5_end)

    # 車: カット1の最終位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene5_start)
    car_a.keyframe_insert(data_path="location", frame=scene5_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene5_start)
    car_b.keyframe_insert(data_path="location", frame=scene5_end)

    print(f"[フレーム{scene5_start}] カット2開始: カメラ={loc_phase4}（真横固定）, 車維持")

    # --- CarBの半透明化（シーン5用：0.35の不透明度で表示）---
    _setup_car_b_transparency_for_scene5(car_b, scene5_start, scene5_end)
    print(f"[フレーム{scene5_start}-{scene5_end}] CarB半透明化: 1.0→0.35")

    # --- シーン5の全長差エフェクト（レーザー線＋数値テキスト）---
    _setup_scene5_effects(scene, camera, car_a, car_b, scene5_start, scene5_end, car_dimensions)

    # ============================================================
    # 【カット2】シーン6: フレーム792-936（車の正面にカメラ移動・6秒間）
    # シーン5の終了位置から開始
    # ============================================================
    print("\n=== 【カット2】シーン6設定開始 ===")

    scene6_start = 792
    scene6_end = 936  # 6秒間（24fps × 6 = 144フレーム）

    # カメラ: 車の正面にゆっくり移動（距離70%）
    # サイドビュー位置から車の前方へ移動
    loc_phase5 = (0.0, -10.0, 3.0)  # 車前方、やや上
    direction_phase5 = Vector(target) - Vector(loc_phase5)
    rot_quat_phase5 = direction_phase5.to_track_quat('-Z', 'Y')
    rot_phase5 = rot_quat_phase5.to_euler()

    # 中間地点（フレーム864）- 距離50%
    mid_frame = scene6_start + 72
    # サイドビュー位置から正面位置へのベクトルを50%に縮小
    loc_mid = (4.0, -5.0, 2.75)  # サイドビューと正面の中間（距離50%）
    direction_mid = Vector(target) - Vector(loc_mid)
    rot_quat_mid = direction_mid.to_track_quat('-Z', 'Y')
    rot_mid = rot_quat_mid.to_euler()

    camera.location = loc_phase5
    camera.rotation_euler = rot_phase5
    camera.keyframe_insert(data_path="location", frame=scene6_start)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene6_start)
    
    # 中間キーフレーム（滑らかな移動のため）
    camera.location = loc_mid
    camera.rotation_euler = rot_mid
    camera.keyframe_insert(data_path="location", frame=mid_frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=mid_frame)
    
    camera.location = loc_phase5
    camera.rotation_euler = rot_phase5
    camera.keyframe_insert(data_path="location", frame=scene6_end)
    camera.keyframe_insert(data_path="rotation_euler", frame=scene6_end)

    # 車: シーン5の位置を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=scene6_start)
    car_a.keyframe_insert(data_path="location", frame=scene6_end)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=scene6_start)
    car_b.keyframe_insert(data_path="location", frame=scene6_end)

    # シーン5のテキストをフェードアウト（シーン6開始時）
    text_container_name = "LengthDiff_Container_Scene5"
    if text_container_name in bpy.data.objects:
        text_obj = bpy.data.objects[text_container_name]
        
        print(f"[フレーム{scene6_start}] テキストフェードアウト開始（792→840）")
        
        # 各文字オブジェクトに直接キーフレームを設定
        for char_obj in text_obj.children:
            if char_obj.type == 'MESH':
                # スケールを徐々に0にフェードアウト（フレーム792→840で）
                
                # まず現在のスケールを取得して保存
                current_scale = char_obj.scale.copy() if hasattr(char_obj, 'scale') else (1.0, 1.0, 1.0)
                
                # フレーム792: 現在のスケールを維持（キーフレーム）
                char_obj.scale = current_scale
                char_obj.keyframe_insert(data_path="scale", frame=scene6_start)
                
                # フレーム840: スケールを0に
                fade_end_frame = scene6_start + 48  # フレーム840
                char_obj.scale = (0.0, 0.0, 0.0)
                char_obj.keyframe_insert(data_path="scale", frame=fade_end_frame)
                
                # 発光強度も徐々に0に
                for node in char_obj.data.materials[0].node_tree.nodes:
                    if node.type == 'BSDF_EMISSION':
                        current_strength = node.inputs['Strength'].default_value
                        
                        # フレーム792: 現在の強度を維持（キーフレーム）
                        node.inputs['Strength'].default_value = current_strength
                        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=scene6_start)
                        
                        # フレーム840: 強度を0に
                        node.inputs['Strength'].default_value = 0.0
                        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=fade_end_frame)

    print(f"[フレーム{scene6_start}] シーン6開始: カメラ移動開始（正面へ）")
    print(f"[フレーム{scene6_end}] シーン6終了: カメラ={loc_phase5}（正面ビュー）, 車維持")

    # シーンをフレーム0に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== アニメーション設定完了 ===")
    print("カメラアニメーション:")
    print(f"  【カット1】シーン1-4（フレーム0-648）:")
    print(f"    【シーン1】フレーム0-96:      斜め上の固定視点 {loc_phase1}（4秒）")
    print(f"               フレーム96-144:     停止（2秒）")
    print(f"    【シーン2】フレーム144-264:   トップビューへ移動（車の中心の真上）{loc_phase2}（5秒）")
    print(f"               フレーム264-312:    停止（2秒）")
    print(f"    【シーン3】フレーム312-408:   Z軸回転で車が横になる（4秒）")
    print(f"               フレーム408-456:    停止（2秒）")
    print(f"    【シーン4】フレーム456-600:   サイドビューへ移動 {loc_phase4}（6秒）")
    print(f"               フレーム600-648:    サイドビューで静止（全長差比較）（2秒）")
    print(f"  【カット2】シーン5（フレーム{scene5_start}-{scene5_end}):")
    print(f"              カメラ固定・真横構図・CarB半透明化・全長差エフェクト表示（6秒）")
    print(f"  【カット2】シーン6（フレーム{scene6_start}-{scene6_end}):")
    print(f"              カメラ移動・正面ビューへ（6秒）")


def _setup_car_b_transparency_for_scene5(car_object, start_frame, end_frame):
    """CarBの全マテリアルをシーン5用半透明化する（複数メッシュ対応）"""
    if car_object is None:
        return

    # オブジェクト自体のマテリアルを設定
    _apply_transparency_to_materials(car_object, start_frame, end_frame)

    # 子オブジェクトのマテリアルも設定（GLBインポートで複数のメッシュがある場合）
    for child in car_object.children:
        if child.type == 'MESH':
            _apply_transparency_to_materials(child, start_frame, end_frame)


def _apply_transparency_to_materials(obj, start_frame, end_frame):
    """オブジェクトの全マテリアルに半透明化キーフレームを設定"""
    if obj is None or len(obj.data.materials) == 0:
        return

    for slot in obj.material_slots:
        material = slot.material
        if material is None:
            continue

        # EEVEE透過対応
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
        # シーン5開始から最初から半透明（0.35）
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        alpha_input.default_value = 0.35
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)

    print(f"  {obj.name} のマテリアルに半透明化キーフレームを設定しました（シーン5: Alpha=0.35）")


# ============================================================
# setup_all_animations() の続き：シーン5のエフェクト設定
# （_apply_transparency_to_materials() から分離）
# ============================================================

def _setup_scene5_effects(scene, camera, car_a, car_b, scene5_start, scene5_end, car_dimensions=None):
    """シーン5の全長差エフェクトを設定（寸法線なし、テキストのみ）"""
    # --- 全長差の計算と取得 ---
    length_diff_mm = _calculate_length_difference(car_a, car_b, car_dimensions)
    
    # 両車の実際の長さも取得（mm単位）
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
    
    print(f"[シーン5] 全長差: {length_diff_mm:+d}mm (CarB: {length_b_mm}mm, CarA: {length_a_mm}mm)")

    # --- 数値テキストの作成（ピピピッ出現アニメーション付き）---
    text_obj = _create_length_diff_text(scene, camera, length_a_mm, length_b_mm, length_diff_mm, car_a, car_b)
    if text_obj:
        print(f"[シーン5] 数値テキスト '{text_obj.name}' を作成しました")

    print(f"[フレーム{scene5_end}] シーン5終了: 全長差表示完了")


def _calculate_length_difference(car_a, car_b, car_dimensions=None):
    """2台の車の全長差を計算（mm単位、carB - carA）

    設定ファイルの寸法値がある場合はそれを使用。
    ない場合はバウンディングボックスから計算するフォールバック。
    """
    if car_dimensions:
        length_a_mm = car_dimensions.get("carA", {}).get("length", 0)
        length_b_mm = car_dimensions.get("carB", {}).get("length", 0)
        diff_mm = length_b_mm - length_a_mm
        print(f"  carA全長: {length_a_mm}mm, carB全長: {length_b_mm}mm（設定値）, 差(carB-carA): {diff_mm:+d}mm")
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
    print(f"  carA長さ: {length_a:.3f}m, carB長さ: {length_b:.3f}m（バウンディングボックス）, 差(carB-carA): {diff_mm:+d}mm")
    return diff_mm


def _create_length_diff_text(scene, camera, length_a_mm, length_b_mm, length_diff_mm, car_a, car_b):
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

    # 車の最高点を取得（Z座標）
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
    bpy.ops.object.empty_add(location=(avg_center_x, avg_center_y - 0.5, max_height + 0.3))
    text_container = bpy.context.active_object
    text_container.name = "LengthDiff_Container_Scene5"

    # コンテナの位置と回転を設定（文字がカメラに向くように）
    # X軸は車の中心、Y軸は車の上、Z軸は少し上
    text_container.location = (avg_center_x, avg_center_y - 0.3, max_height + 0.35)
    
    # カメラから読める向きに回転（サイドビューなのでZ軸回転のみ）
    # カメラの回転を計算して、テキストが常にカメラの方を向くようにする
    cam_rot = camera.rotation_euler.copy()
    text_container.rotation_euler = (cam_rot.x, cam_rot.y, cam_rot.z)

    # シーンにリンク
    scene.collection.objects.link(text_container)

    # 文字列を作成： "Length: CarB - CarA → 結果"
    # 例: "Length: 4890mm - 4460mm → +430mm"
    text_str = f"Length: {length_b_mm}mm - {length_a_mm}mm → {length_diff_mm:+d}mm"

    # 各文字を個別のテキストオブジェクトとして作成
    char_objects = []
    spacing = 0.12  # 文字間隔（狭めて調整）
    
    # 色の定義：CarB=青、CarA=赤、結果=白
    colors = {
        'blue': (0.0, 1.0, 1.0),      # シアンブルー（発光）
        'red': (1.0, 0.0, 0.0),       # 赤
        'white': (1.0, 1.0, 1.0)      # 白
    }
    
    # 文字ごとの色を定義（インデックスで管理）
    # "4890mm - 4460mm → +430mm" の各部分
    color_map = ['white'] * len(text_str)  # 初期値は全て白
    
    # 数字のブロックを特定：CarB (最初の数字), CarA (2番目の数字), 結果 (3番目の数字)
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
            color = 'blue'   # CarB (最初の数字)
        elif idx == 1:
            color = 'red'    # CarA (2番目の数字)
        else:
            color = 'white'  # 結果やその他
        
        for pos in block:
            if pos < len(color_map):
                color_map[pos] = color
    
    print(f"Color map: {color_map}")

    for i, char in enumerate(text_str):
        # テキストオブジェクトを作成（一時的な位置）
        bpy.ops.object.text_add(location=(0, 0, max_height + 0.3))
        char_obj = bpy.context.active_object
        char_obj.name = f"LengthDiff_Char_{i}"

        if hasattr(char_obj.data, 'string'):
            char_obj.data.string = char
        else:
            char_obj.data.body = char

        # サイズを大きく設定 - テキストサイズを直接調整（オブジェクトスケールは1.0維持）
        if hasattr(char_obj.data, 'size'):
            # すべての文字を同じサイズに統一
            char_obj.data.size = 0.22  # 通常サイズも少し拡大（調整）
        
        # オブジェクトスケールを1.0に設定（アニメーション用）
        char_obj.scale = (1.0, 1.0, 1.0)

        # 発光マテリアルを適用（色付き）
        color_name = color_map[i] if i < len(color_map) else 'white'
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

        # 各文字のローカル位置を設定してX軸に沿って左から右に一列に並べる（親設定後）
        # 開始位置を画面左側へ6文字分ずらす（全長差テキストが長くなるため）
        forward_offset = 6 * spacing
        local_x = -((len(text_str) - 1) * spacing) / 2 + (i * spacing) - forward_offset
        
        # ローカルYは中央、Zは少し上
        local_y = 0.0
        local_z = 0.1
        
        # 文字列全体を右に3文字分、上に1文字分ずらす（グローバルオフセット）
        global_shift_x = 3 * spacing  # 右に3文字分
        global_shift_y = 1 * spacing  # 上に1文字分
        local_x += global_shift_x
        local_y += global_shift_y
        
        char_obj.location = (local_x, local_y, local_z)

        char_objects.append(char_obj)

    # アニメーションを設定（コンテナの子オブジェクトに対して）
    _setup_char_by_char_animation(char_objects, start_frame=648, end_frame=792)

    print(f"[シーン5] 計算式テキスト '{text_str}' を {len(char_objects)} 文字で作成")
    return text_container


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


def _setup_char_by_char_animation(char_objects, start_frame, end_frame):
    """各文字に単一フェードインアニメーションを設定"""
    
    # 初期状態：全て透明でスケール0（同時に）
    for char_obj in char_objects:
        char_obj.scale = (0.0, 0.0, 0.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame)
        
        # 発光強度を0に設定（同時に）
        for node in char_obj.data.materials[0].node_tree.nodes:
            if node.type == 'BSDF_EMISSION':
                node.inputs['Strength'].default_value = 0.0
                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

    # 全ての文字が同時にフェードインするアニメーション（単一フェードイン）
    for char_obj in char_objects:
        # ステップ1: 最終サイズ（1.0倍）と安定状態
        char_obj.scale = (1.0, 1.0, 1.0)
        char_obj.keyframe_insert(data_path="scale", frame=start_frame + 8)

        for node in char_obj.data.materials[0].node_tree.nodes:
            if node.type == 'BSDF_EMISSION':
                node.inputs['Strength'].default_value = 5.0
                node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 8)
        
        # 最終安定状態 - オブジェクトスケールを1.0に維持、テキストサイズは0.09
        char_obj.keyframe_insert(data_path="scale", frame=end_frame)

    print(f"[シーン5] {len(char_objects)} 文字に単一フェードインアニメーションを設定")


def _setup_pipipi_animation(obj, start_frame, end_frame):
    """ピピピッ出現アニメーション（3段階の拡大・点滅エフェクト）"""
    # Emptyオブジェクトの場合は最終スケールを(1.0, 1.0, 1.0)、それ以外は現在のスケールを使用
    if obj.type == 'EMPTY':
        final_scale = (1.0, 1.0, 1.0)
    else:
        # テキストオブジェクトなどは既存のスケールを保持
        fs = obj.scale.copy() if hasattr(obj, 'scale') and not isinstance(obj.scale, tuple) else (1.5, 1.5, 1.5)
        final_scale = (fs.x if hasattr(fs, 'x') else fs[0],
                       fs.y if hasattr(fs, 'y') else fs[1],
                       fs.z if hasattr(fs, 'z') else fs[2])

    # 初期状態：スケール0
    obj.scale = (0.0, 0.0, 0.0)
    obj.keyframe_insert(data_path="scale", frame=start_frame)

    # ピピピッアニメーション（3段階）
    # ステップ1: フレーム648→656（初期出現・小規模点滅）
    obj.scale = (final_scale[0] * 0.5, final_scale[1] * 0.5, final_scale[2] * 0.5)
    obj.keyframe_insert(data_path="scale", frame=start_frame + 8)

    # ステップ2: フレーム656→664（中規模拡大・点滅）
    obj.scale = (final_scale[0], final_scale[1], final_scale[2])
    obj.keyframe_insert(data_path="scale", frame=start_frame + 16)

    # ステップ3: フレーム664→672（最終サイズに到達・ピキッ）
    obj.scale = (final_scale[0] * 1.2, final_scale[1] * 1.2, final_scale[2] * 1.2)
    obj.keyframe_insert(data_path="scale", frame=start_frame + 24)

    # 最終安定状態（フレーム672以降）
    obj.scale = (final_scale[0], final_scale[1], final_scale[2])
    obj.keyframe_insert(data_path="scale", frame=start_frame + 32)
    obj.keyframe_insert(data_path="scale", frame=end_frame)


def _setup_emission_pipipi_animation(emission_nodes, start_frame, end_frame):
    """Emission Strengthでピピピッ出現アニメーション（3段階の点滅エフェクト）"""
    if not emission_nodes:
        return

    # 各ノードの元の強度を保存
    original_strengths = []
    for node in emission_nodes:
        original_strengths.append(node.inputs['Strength'].default_value)

    # ステップ1: フレーム648（初期状態・消灯）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = 0.0
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame)

    # ステップ2: フレーム656（初期出現・弱く点灯）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 0.3
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 8)

    # ステップ3: フレーム664（中規模・点滅）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 0.7
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 16)

    # ステップ4: フレーム672（最終強度に到達・ピキッ）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i] * 1.3
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 24)

    # ステップ5: フレーム680以降（安定状態）
    for i, node in enumerate(emission_nodes):
        node.inputs['Strength'].default_value = original_strengths[i]
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=start_frame + 32)
        node.inputs['Strength'].keyframe_insert(data_path="default_value", frame=end_frame)


def _setup_transparency_animation(car_object, start_frame, end_frame, start_alpha, end_alpha):
    """車のマテリアル不透明度をアニメーションさせる（内部用）"""
    if car_object is None or len(car_object.data.materials) == 0:
        return

    material = car_object.data.materials[0]
    if not material.use_nodes:
        return

    # EEVEE透過対応
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
