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
    scene.frame_start = 0
    scene.frame_end = 400
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
    # カメラ: 同じ位置維持（固定視点）
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=30)
    camera.keyframe_insert(data_path="rotation_euler", frame=30)

    # 車A・B: 同じ位置維持（出現状態）
    car_a.location = car_a_start
    car_a.keyframe_insert(data_path="location", frame=30)
    car_b.location = car_b_start
    car_b.keyframe_insert(data_path="location", frame=30)

    # Alpha: 半透明化アニメーション開始（フレーム30-90で1.0→0.4）
    for key, car_obj in imported_cars.items():
        _setup_transparency_animation(car_obj, 30, 90, 1.0, 0.4)

    print(f"[フレーム30] カメラ維持, 車維持, Alpha: 1.0→0.4開始")

    # --- フレーム90: 中央集合・半透明化完了、カメラ上昇開始 ---
    # カメラ: 同じ位置維持（固定視点終了）
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=90)
    camera.keyframe_insert(data_path="rotation_euler", frame=90)

    # 車A: 中央に集まる (0.0, rear_offset_y) - リア端揃え状態を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=90)

    # 車B: 中央に集まる (0.0, 0.0) - 基準位置
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=90)

    print(f"[フレーム90] カメラ維持, carA={car_a_end}, carB={car_b_end}")

    # --- フレーム200: トップビュー到達（車が縦に見える）---
    # カメラ: (0.0, 0.0, 14.0)、ターゲットを下向きに見る
    loc_phase2 = (0.0, 0.0, 14.0)
    set_camera_look_at(camera, loc_phase2, target)
    rot_phase2 = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=200)
    camera.keyframe_insert(data_path="rotation_euler", frame=200)

    # 車A・B: リア端揃えて重なり静止（フレーム90で既に到達済み）
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=200)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=200)

    print(f"[フレーム200] カメラ={loc_phase2}（トップビュー、車が縦）, 車維持")

    # --- フレーム240: Z軸回転完了（車が横に見える）---
    # カメラ: 同じ位置、Z成分にπ/2加算して車を横から見えるように
    loc_phase3 = (0.0, 0.0, 14.0)
    rot_phase3 = (rot_phase2.x, rot_phase2.y, rot_phase2.z + math.pi / 2)
    camera.location = loc_phase3
    camera.rotation_euler = rot_phase3
    camera.keyframe_insert(data_path="location", frame=240)
    camera.keyframe_insert(data_path="rotation_euler", frame=240)

    # 車A・B: 維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=240)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=240)

    print(f"[フレーム240] カメラ={loc_phase3}（Z軸回転、車が横）, 車維持")

    # --- フレーム340: サイドビュー到達 ---
    # カメラ: (8.0, 0.0, 2.5)、車の側面を見る
    loc_phase4 = (8.0, 0.0, 2.5)
    direction_phase4 = Vector(target) - Vector(loc_phase4)
    rot_quat_phase4 = direction_phase4.to_track_quat('-Z', 'Y')
    rot_phase4 = rot_quat_phase4.to_euler()
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=340)
    camera.keyframe_insert(data_path="rotation_euler", frame=340)

    # 車A・B: 維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=340)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=340)

    print(f"[フレーム340] カメラ={loc_phase4}（サイドビュー）, 車維持")

    # --- フレーム400: サイドビュー静止（全長差比較）---
    # カメラ: 同じ位置維持
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=400)
    camera.keyframe_insert(data_path="rotation_euler", frame=400)

    # 車A・B: 維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=400)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=400)

    print(f"[フレーム400] カメラ維持（サイドビュー静止）, 車維持")

    # シーンをフレーム0に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== アニメーション設定完了 ===")
    print("カメラアニメーション:")
    print(f"  - フレーム0-90:   斜め上の固定視点 {loc_phase1}")
    print(f"  - フレーム90-200: トップビューへ移動（車の中心の真上）{loc_phase2}")
    print(f"  - フレーム200-240: Z軸回転で車が横になる")
    print(f"  - フレーム240-340: サイドビューへ移動 {loc_phase4}")
    print(f"  - フレーム340-400: サイドビューで静止（全長差比較）")


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
