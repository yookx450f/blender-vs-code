"""
アニメーション設定モジュール（統合版）
カット 1、カット 2、カット 3、カット 4 を統合して使用。

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


def _get_target_cut():
    """環境変数 CUT_NUMBER から実行対象のカット番号を取得。
    
    Returns:
        str: "1", "2", "3", "4", または "all"
    """
    cut = os.environ.get("CUT_NUMBER", "all")
    return cut


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
    #     シーン 1: フレーム 0-96      斜め上の固定視点。両車が中央に集合して重なる（4 秒）
    #              フレーム 96-144    停止（2 秒）
    #     シーン 2: フレーム 144-264   トップビューへ移動（5 秒）
    #              フレーム 264-312   停止（2 秒）
    #     シーン 3: フレーム 312-408   Z 軸回転で車が横になる（4 秒）
    #              フレーム 408-456   停止（2 秒）
    #     シーン 4: フレーム 456-600   サイドビューへ移動（6 秒）
    #              フレーム 600-648   サイドビューで静止（2 秒）
    #   【カット 2】= シーン 5〜7（カット 1 の最終位置から開始）
    #     シーン 5: フレーム 648-768   真横固定視点・全長差表示エフェクト（5 秒）
    #              フレーム 768-816   停止（2 秒）
    #     シーン 6: フレーム 816-984   カメラ移動・正面ビューへ（全長差表示フェードアウト）（7 秒）
    #              フレーム 984-1032  停止（2 秒）
    #     シーン 7: フレーム 1032-1176 正面ビュー固定・横幅差表示（6 秒）
    #              フレーム 1176-1224 停止（2 秒）
    #   【カット 3】= シーン 8〜9（カット 2 の最終位置から開始）
    #     シーン 8: フレーム 1224-1368 正面から左側低位置へカメラ移動（6 秒）
    #              フレーム 1368-1416 停止（2 秒）
    #     シーン 9: フレーム 1416-1536 最低地上高差表示（5 秒）
    #              フレーム 1536-1584 停止（2 秒）
    #   【カット 4】= シーン 10〜11（カット 3 の最終位置から開始）
    #     シーン 10: フレーム 1584-1704 横並び移動＋CarB不透明化＋地上高表示フェードアウト（5 秒）
    #               フレーム 1704-1752 停止（2 秒）
    #     シーン 11: フレーム 1752-2040 最小回転半径で両台が右回り1週（CarA:10秒、CarBは出发/到达ともに2秒遅延）
    # 環境変数 CUT_NUMBER によって実行するカットを制御
    target_cut = _get_target_cut()
    print(f"[アニメーション設定] 実行対象カット: {target_cut}")
    
    scene.frame_start = 0
    scene.frame_end = 2040
    scene.render.fps = 24
    print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end} (fps={scene.render.fps})")

    # カット 1 を実行（常に必要。カット2-4はカット1の結果に依存するため）
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

    # カット 2 を実行（カット2-4が対象の場合のみ）
    if target_cut in ("all", "2", "3", "4"):
        cut2_result = setup_cut2_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            previous_state=cut1_result,
            car_dimensions=car_dimensions
        )

        if cut2_result is None:
            print("エラー: カット 2 の設定に失敗しました")
            return
    else:
        # カット1のみ実行時はダミー結果を生成（カット1の終了状態）
        cut2_result = cut1_result

    # カット 3 を実行（カット3-4が対象の場合のみ）
    if target_cut in ("all", "3", "4"):
        cut3_result = setup_cut3_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            previous_state=cut2_result,
            car_dimensions=car_dimensions
        )

        if cut3_result is None:
            print("エラー: カット 3 の設定に失敗しました")
            return
    else:
        # カット1-2のみ実行時はダミー結果を生成
        cut3_result = cut2_result

    # カット 4 を実行（カット4または全カットが対象の場合のみ）
    if target_cut in ("all", "4"):
        setup_cut4_animations(
            scene=scene,
            camera=camera,
            imported_cars=imported_cars,
            previous_state=cut3_result,
            car_dimensions=car_dimensions
        )
    else:
        print(f"[アニメーション設定] カット 4 をスキップ（対象カット: {target_cut}）")

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
    print(f"  【カット 2】シーン 5（フレーム 648-768):")
    print(f"              真横固定視点・全長差表示エフェクト（5 秒）")
    print(f"              フレーム 768-816:     停止（2 秒）")
    print(f"  【カット 2】シーン 6（フレーム 816-984):")
    print(f"              カメラ移動・正面ビューへ（全長差表示フェードアウト）（7 秒）")
    print(f"              フレーム 984-1032:    停止（2 秒）")
    print(f"  【カット 2】シーン 7（フレーム 1032-1176):")
    print(f"              正面ビュー固定・横幅差表示（6 秒）")
    print(f"              フレーム 1176-1224:   停止（2 秒）")
    print(f"  【カット 3】シーン 8（フレーム 1224-1368):")
    print(f"              正面から左側低位置へカメラ移動（6 秒）")
    print(f"              フレーム 1368-1416:   停止（2 秒）")
    print(f"  【カット 3】シーン 9（フレーム 1416-1536):")
    print(f"              最低地上高差表示（地面に張り付け）（5 秒）")
    print(f"              フレーム 1536-1584:   停止（2 秒）")
    print(f"  【カット 4】シーン 10（フレーム 1584-1704):")
    print(f"              横並び移動＋CarB不透明化＋地上高表示フェードアウト（5 秒）")
    print(f"              フレーム 1704-1752:   停止（2 秒）")
    print(f"  【カット 4】シーン 11（フレーム 1752-2040):")
    print(f"              最小回転半径で両台が右回り1週（CarA:10秒、CarBは出发/到达ともに2秒遅延）（12 秒）")


# 互換性のため、元の関数名でもインポート可能に
setup_all_animations = setup_all_animations
