"""
アニメーション設定モジュール（統合版）
カット 1 とカット 2 を統合して使用。

使い方:
    from animation_settings import setup_all_animations
    setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None)
"""

import bpy
from animation_settings_cut1 import setup_cut1_animations
from animation_settings_cut2 import setup_cut2_animations


def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    """
    すべてのアニメーションを設定（フレーム順にまとめる）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
        car_dimensions: {key: {"length": mm, "width": mm, "height": mm}} 車の寸法情報（設定ファイルから）
    """
    print("\n=== アニメーション設定を開始（フレーム順）===")

    # タイムライン（カット割り）:
    #   【カット 1】= シーン 1〜4 の連続
    #     シーン 1: フレーム 0-96      斜め上の固定視点（4 秒）
    #              フレーム 96-144    停止（2 秒）
    #     シーン 2: フレーム 144-264   トップビューへ移動（5 秒）
    #              フレーム 264-312   停止（2 秒）
    #     シーン 3: フレーム 312-408   Z 軸回転で車が横になる（4 秒）
    #              フレーム 408-456   停止（2 秒）
    #     シーン 4: フレーム 456-600   サイドビューへ移動（6 秒）
    #              フレーム 600-648   サイドビューで静止（2 秒）
    #   【カット 2】= シーン 5（カット 1 の最終位置から開始）
    #     シーン 5: フレーム 648-792   真横固定視点・全長差表示エフェクト（6 秒）
    scene.frame_start = 0
    scene.frame_end = 936
    scene.render.fps = 24
    print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end} (fps={scene.render.fps})")

    # カット 1 を実行
    cut1_result = setup_cut1_animations(
        scene=scene,
        camera=camera,
        imported_cars=imported_cars,
        rear_offset_y=rear_offset_y,
        grounded_z_positions=grounded_z_positions,
        car_dimensions=car_dimensions
    )

    if cut1_result is None:
        print("エラー: カット 1 の設定に失敗しました")
        return

    # カット 2 を実行
    setup_cut2_animations(
        scene=scene,
        camera=camera,
        imported_cars=imported_cars,
        cut1_result=cut1_result,
        car_dimensions=car_dimensions
    )

    print("\n=== アニメーション設定完了 ===")
    print("カメラアニメーション:")
    print(f"  【カット 1】シーン 1-4（フレーム 0-648）:")
    print(f"    【シーン 1】フレーム 0-96:      斜め上の固定視点 (6.5, -6.5, 4.0)（4 秒）")
    print(f"               フレーム 96-144:     停止（2 秒）")
    print(f"    【シーン 2】フレーム 144-264:   トップビューへ移動 (0.0, 0.0, 14.0)（5 秒）")
    print(f"               フレーム 264-312:    停止（2 秒）")
    print(f"    【シーン 3】フレーム 312-408:   Z 軸回転で車が横になる（4 秒）")
    print(f"               フレーム 408-456:    停止（2 秒）")
    print(f"    【シーン 4】フレーム 456-600:   サイドビューへ移動 (8.0, 0.0, 2.5)（6 秒）")
    print(f"               フレーム 600-648:    サイドビューで静止（全長差比較）（2 秒）")
    print(f"  【カット 2】シーン 5（フレーム 648-792):")
    print(f"              カメラ固定・真横構図・CarB 半透明化・全長差エフェクト表示（6 秒）")
    print(f"  【カット 2】シーン 6（フレーム 792-936):")
    print(f"              カメラ移動・正面ビューへ（6 秒）")


# 互換性のため、元の関数名でもインポート可能に
setup_all_animations = setup_all_animations
