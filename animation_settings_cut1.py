"""
アニメーション設定モジュール - カット 1
フレーム 0-648（シーン 1-4）を処理する。

使い方:
    from animation_settings_cut1 import setup_cut1_animations
    setup_cut1_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None)
"""

import bpy
import math
from mathutils import Vector
from animation_common import set_camera_look_at, _setup_transparency_animation


def setup_cut1_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    """
    カット 1 のアニメーションを設定（フレーム 0-648）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報（設定ファイルから）

    Returns:
        dict: 車 A と車 B の終了位置、カメラの最終回転・位置、接地 Z 値など
    """
    print("\n=== カット 1 アニメーション設定を開始 ===")

    # ============================================================
    # 前提計算：車の位置・接地 Z を準備
    # ============================================================
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # 接地後の Z 位置を取得（外部の辞書から）
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
    # フレーム順にキーフレームを設定（カット 1）
    # ============================================================

    # --- フレーム 0: スタート ---
    # カメラ: 斜め上の固定視点 (6.5, -6.5, 4.0)
    loc_phase1 = (6.5, -6.5, 4.0)
    set_camera_look_at(camera, loc_phase1, target)
    rot_phase1 = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=0)
    camera.keyframe_insert(data_path="rotation_euler", frame=0)

    # 車 A: 左側に配置 (-2.0, rear_offset_y)
    car_a.location = car_a_start
    car_a.keyframe_insert(data_path="location", frame=0)

    # 車 B: 右側に配置 (2.0, 0.0)
    car_b.location = car_b_start
    car_b.keyframe_insert(data_path="location", frame=0)

    print(f"[フレーム 0] カメラ={loc_phase1}, carA={car_a_start}, carB={car_b_start}")

    # --- フレーム 30: 出現完了、半透明化開始 ---
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=30)
    camera.keyframe_insert(data_path="rotation_euler", frame=30)

    car_a.location = car_a_start
    car_a.keyframe_insert(data_path="location", frame=30)
    car_b.location = car_b_start
    car_b.keyframe_insert(data_path="location", frame=30)

    # Alpha: CarB のみ半透明化アニメーション開始（フレーム 30-96 で 1.0→0.4）
    car_b_obj = imported_cars.get("carB")
    if car_b_obj:
        _setup_transparency_animation(car_b_obj, 30, 96, 1.0, 0.4)

    print(f"[フレーム 30] カメラ維持，車維持，Alpha(CarB のみ): 1.0→0.4 開始")

    # --- シーン 1 終了・シーン 2 開始: フレーム 96（中央集合・半透明化完了）---
    # カメラ: 同じ位置維持（固定視点終了）
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=96)
    camera.keyframe_insert(data_path="rotation_euler", frame=96)

    # 車 A: 中央に集まる (0.0, rear_offset_y) - リア端揃え状態を維持
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=96)

    # 車 B: 中央に集まる (0.0, 0.0) - 基準位置
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=96)

    print(f"[フレーム 96] シーン 1 終了：カメラ維持，carA={car_a_end}, carB={car_b_end}")

    # --- 停止（2 秒）: フレーム 144 ---
    camera.location = loc_phase1
    camera.rotation_euler = rot_phase1
    camera.keyframe_insert(data_path="location", frame=144)
    camera.keyframe_insert(data_path="rotation_euler", frame=144)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=144)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=144)

    print(f"[フレーム 144] 停止（2 秒）")

    # --- シーン 2: フレーム 264（トップビュー到達・車が縦に見える）---
    loc_phase2 = (0.0, 0.0, 14.0)
    set_camera_look_at(camera, loc_phase2, target)
    rot_phase2 = camera.rotation_euler.copy()
    camera.keyframe_insert(data_path="location", frame=264)
    camera.keyframe_insert(data_path="rotation_euler", frame=264)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=264)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=264)

    print(f"[フレーム 264] シーン 2 終了：カメラ={loc_phase2}（トップビュー、車が縦）, 車維持")

    # --- 停止（2 秒）: フレーム 312 ---
    camera.location = loc_phase2
    camera.rotation_euler = rot_phase2
    camera.keyframe_insert(data_path="location", frame=312)
    camera.keyframe_insert(data_path="rotation_euler", frame=312)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=312)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=312)

    print(f"[フレーム 312] 停止（2 秒）")

    # --- シーン 3: フレーム 408（Z 軸回転完了・車が横に見える）---
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

    print(f"[フレーム 408] シーン 3 終了：カメラ={loc_phase3}（Z 軸回転、車が横）, 車維持")

    # --- 停止（2 秒）: フレーム 456 ---
    camera.location = loc_phase3
    camera.rotation_euler = rot_phase3
    camera.keyframe_insert(data_path="location", frame=456)
    camera.keyframe_insert(data_path="rotation_euler", frame=456)
    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=456)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=456)

    print(f"[フレーム 456] 停止（2 秒）")

    # --- シーン 4: フレーム 600（サイドビュー到達）---
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

    print(f"[フレーム 600] シーン 4 終了：カメラ={loc_phase4}（サイドビュー）, 車維持")

    # --- サイドビュー静止（2 秒）: フレーム 648 ---
    camera.location = loc_phase4
    camera.rotation_euler = rot_phase4
    camera.keyframe_insert(data_path="location", frame=648)
    camera.keyframe_insert(data_path="rotation_euler", frame=648)

    car_a.location = car_a_end
    car_a.keyframe_insert(data_path="location", frame=648)
    car_b.location = car_b_end
    car_b.keyframe_insert(data_path="location", frame=648)

    print(f"[フレーム 648] サイドビュー静止（2 秒）, 車維持")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print("\n=== カット 1 アニメーション完了 ===")

    # 結果を返す（カット 2 で再利用）
    return {
        'car_a_end': car_a_end,
        'car_b_end': car_b_end,
        'loc_phase4': loc_phase4,
        'rot_phase4': rot_phase4,
        'grounded_z_a': grounded_z_a,
        'grounded_z_b': grounded_z_b,
    }
