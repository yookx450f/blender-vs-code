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


def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions):
    """
    すべてのアニメーションを設定（フレーム順にまとめる）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用のYオフセット値
        grounded_z_positions: {object_name: z_value} 接地後のZ位置を保存する辞書
    """
    print("\n=== アニメーション設定を開始（フレーム順）===")

    # ============================================================
    # シーンフレーム範囲を設定
    # ============================================================
    # タイムライン:
    #   シーン1: フレーム0-96     斜め上の固定視点（4秒）
    #            フレーム96-144   停止（2秒）
    #   シーン2: フレーム144-264  トップビューへ移動（5秒）
    #            フレーム264-312  停止（2秒）
    #   シーン3: フレーム312-408  Z軸回転で車が横になる（4秒）
    #            フレーム408-456  停止（2秒）
    #   シーン4: フレーム456-600  サイドビューへ移動（6秒）
    #            フレーム600-648  サイドビューで静止（2秒）
    scene.frame_start = 0
    scene.frame_end = 648
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

    # シーンをフレーム0に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== アニメーション設定完了 ===")
    print("カメラアニメーション:")
    print(f"  【シーン1】フレーム0-96:     斜め上の固定視点 {loc_phase1}（4秒）")
    print(f"              フレーム96-144:   停止（2秒）")
    print(f"  【シーン2】フレーム144-264:  トップビューへ移動（車の中心の真上）{loc_phase2}（5秒）")
    print(f"              フレーム264-312:  停止（2秒）")
    print(f"  【シーン3】フレーム312-408:  Z軸回転で車が横になる（4秒）")
    print(f"              フレーム408-456:  停止（2秒）")
    print(f"  【シーン4】フレーム456-600:  サイドビューへ移動 {loc_phase4}（6秒）")
    print(f"              フレーム600-648:  サイドビューで静止（全長差比較）（2秒）")


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
