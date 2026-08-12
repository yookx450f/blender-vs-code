"""
アニメーション設定モジュール - カット 3
フレーム 1224-1416（シーン 8、停止付き）を処理する。

使い方:
    from animation_settings_cut3 import setup_cut3_animations
    setup_cut3_animations(scene, camera, imported_cars, cut2_result)
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at


def setup_cut3_animations(scene, camera, imported_cars, cut2_result):
    """
    カット 3 のアニメーションを設定（フレーム 1224-1416）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        cut2_result: setup_cut2_animations の戻り値（dict）

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
