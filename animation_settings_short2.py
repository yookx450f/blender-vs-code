"""
アニメーション設定モジュール - ショート動画v2（縦長9:16）
フレーム 0-624（約26秒、24fps）を処理する。

カット1 (fr0-288): 「車が重なっていく部分」の円弧パンニング
カット2 (fr289-624): トップダウンビュー → カメラ復帰 → 車スライド復帰（同時進行）
  フェーズA (fr289-456): 7秒 - トップダウンへ移動（イージング適用）
  フェーズB (fr457-624): 7秒 - カメラ復帰（イージング適用）

YouTube Shorts用の縦長フォーマット。

short2 の違い:
    半透明化をドライバー式ではなくキーフレーム直接設定方式を使用。

使い方:
    from animation_settings_short2 import setup_short2_animations
    setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions)
"""

import bpy
from animation_common import _setup_transparency_keyframe_animation, _add_transparency_keyframe_existing, _force_constant_interpolation_car_b_alpha, _setup_short2_carb_transparency
from short2_utils import get_car_visual_center_offset
from short2_cuts import (
    setup_cut1_overlap,
    setup_cut2_phase_a_topdown,
    setup_cut2_phase_b_camera_return,
)


def setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions):
    """
    ショート動画v2のアニメーションをオーケストレーション（フレーム 0-624）
    
    カット1 (fr0-288): 車が中央へスライド + 円弧パンニング
    カット2 (fr289-624): トップダウン→カメラ復帰→車スライド復帰（同時進行、イージング適用）
    
    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_cars: {key: car_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
    
    Returns:
        CutState: 最終状態情報
    """
    print(f"\n=== ショート動画v2 アニメーション設定を開始 (total_frames=624, 約26秒) ===")
    
    # ============================================================
    # 前提計算：車の位置・接地 Z を準備
    # ============================================================
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")
    
    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None
    
    grounded_z_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    grounded_z_b = grounded_z_positions.get(car_b.name, car_b.location.z)
    
    print(f"  接地Z: carA={grounded_z_a:.4f}, carB={grounded_z_b:.4f}")
    print(f"  rear_offset_y={rear_offset_y:.4f}")
    
    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)
    
    try:
        offset_a = get_car_visual_center_offset(car_a)
        offset_b = get_car_visual_center_offset(car_b)
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), carB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")
    
    # ============================================================
    # 車のターゲット位置を定義
    # ============================================================
    car_a_start = (-1.25, rear_offset_y, grounded_z_a)
    car_b_start = (1.25, 0.0, grounded_z_b)
    car_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
    car_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)
    
    print(f"  carA: start={car_a_start} -> end={car_a_end}")
    print(f"  carB: start={car_b_start} -> end={car_b_end}")
    
    # カメラのターゲット（車の中心付近）
    target = (0.0, 0.0, 1.0)
    
    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"  Track To コンストレイント '{constraint.name}' を無効化")
    
    # レンズ設定
    original_lens = camera.data.lens
    camera.data.lens = 35
    print(f"  カメラレンズ: {original_lens}mm → 35mm（ズームイン）")
    
    # ============================================================
    # --- カット1 (fr0-288): 円弧パンニング + 車スライド ---
    # ============================================================
    cut1_result = setup_cut1_overlap(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end)
    
    # CarBの半透明化 — short2専用関数で完全に再構築（CONSTANT補間で瞬時切り替え）
    if car_b:
        _setup_short2_carb_transparency(car_b, end_frame=624)
        print(f"  Alpha(CarB): fr30で半透明化(1.0→0.35), fr457で不透明化(0.35→1.0) [CONSTANT補間]")
    
    # ============================================================
    # --- カット2 フェーズA (fr289-fr456): トップダウンビュー + 車スライド開始 ---
    # ============================================================
    cut1_final_cam = cut1_result['camera_loc']
    setup_cut2_phase_a_topdown(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, cut1_final_cam)
    
    # CarBはフェーズA中（fr289-fr456）半透明状態を維持（alpha=0.35のままで良い）
    
    # ============================================================
    # --- カット2 フェーズB (fr457-fr624): カメラ復帰 + 不透明化 + 車スライド完了 ---
    # ============================================================
    cut2_result = setup_cut2_phase_b_camera_return(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end)
    
    
    # ============================================================
    # --- カット2終了地点 (fr624) の状態 ---
    # ============================================================
    print(f"\n=== カット2終了 (fr624) 状態 ===")
    print(f"  carA: {car_a_start}")
    print(f"  carB: {car_b_start}")
    print(f"  カメラ: loc={cut2_result['camera_loc']}, rot={cut2_result['camera_rot']}")
    
    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)
    
    print(f"\n=== ショート動画v2 アニメーション完了 (total_frames=624) ===")
    
    from animation_common import CutState
    return CutState(
        car_a_loc=car_a_start,
        car_b_loc=car_b_start,
        camera_loc=cut2_result['camera_loc'],
        camera_rot=cut2_result['camera_rot'],
    )
