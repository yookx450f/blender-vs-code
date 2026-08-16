"""
アニメーション設定モジュール（統合版）
カット 1、カット 2、カット 3、カット 4、カット 5 を統合して使用。

使い方:
    from animation_settings import setup_all_animations
    setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None)
"""

import bpy
import os
from animation_settings_cut1 import setup_cut1_animations
from animation_settings_cut2 import setup_cut2_animations
from animation_settings_cut3 import setup_cut3_animations
from animation_settings_cut4 import setup_cut4_animations
from animation_settings_cut5 import setup_cut5_animations


def _get_target_cut():
    """環境変数 CUT_NUMBER から実行対象のカット番号を取得。
    
    Returns:
        str: "1", "2", "3", "4", または "all"
    """
    cut = os.environ.get("CUT_NUMBER", "all")
    return cut


def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    """
    すべてのアニメーションを設定（カット完全分離版）

    【修正: カット完全分離】各カットを独立して呼び出し、
    previous_state の受け渡しを行わない。
    各カットは animation_cut_positions.py から固定位置を読み込む。

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値（Cut1用）
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書（Cut1用）
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報（設定ファイルから）
    """
    print("\n=== アニメーション設定を開始（カット完全分離モード）===")

    # 環境変数 CUT_NUMBER によって実行するカットを制御
    target_cut = _get_target_cut()
    print(f"[アニメーション設定] 実行対象カット: {target_cut}")
    
    scene.frame_start = 0
    scene.frame_end = 2880
    scene.render.fps = 24
    print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end} (fps={scene.render.fps})")

    # 【カット完全分離】各カットを独立して実行（previous_state不要）
    # カット 1 を実行（カット1または全カットが対象の場合）
    if target_cut in ("all", "1"):
        cut1_result = setup_cut1_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            rear_offset_y=rear_offset_y,
            grounded_z_positions=grounded_z_positions,
            car_dimensions=car_dimensions
        )
        if cut1_result is None:
            print("警告: カット 1 の設定に失敗しました")
    else:
        print(f"[アニメーション設定] カット 1 をスキップ（対象カット: {target_cut}）")

    # カット 2 を実行（独立実行: previous_state不要）
    if target_cut in ("all", "2"):
        setup_cut2_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            car_dimensions=car_dimensions
        )
    else:
        print(f"[アニメーション設定] カット 2 をスキップ（対象カット: {target_cut}）")

    # カット 3 を実行（独立実行: previous_state不要）
    if target_cut in ("all", "3"):
        setup_cut3_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            car_dimensions=car_dimensions
        )
    else:
        print(f"[アニメーション設定] カット 3 をスキップ（対象カット: {target_cut}）")

    # カット 4 を実行（独立実行: previous_state不要）
    if target_cut in ("all", "4"):
        setup_cut4_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            car_dimensions=car_dimensions
        )
    else:
        print(f"[アニメーション設定] カット 4 をスキップ（対象カット: {target_cut}）")

    # カット 5 を実行（独立実行: previous_state不要）
    if target_cut in ("all", "5"):
        setup_cut5_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            car_dimensions=car_dimensions
        )
    else:
        print(f"[アニメーション設定] カット 5 をスキップ（対象カット: {target_cut}）")

    print("\n=== アニメーション設定完了 ===")


# 互換性のため、元の関数名でもインポート可能に
setup_all_animations = setup_all_animations
