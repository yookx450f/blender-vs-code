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


def setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, strategy_config=None):
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
        strategy_config: バリエーション設定辞書（オプション。None時は既存動作）

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
    # バリエーション設定：総フレーム数・フェーズAの時間変動適用
    # ============================================================
    total_frames = 624  # デフォルト
    if strategy_config and "total_frames" in strategy_config:
        total_frames = strategy_config["total_frames"]
        print(f"  総フレーム数: {total_frames} (約{total_frames/24:.1f}秒)")

    phase_a_modifier = 1.0
    if strategy_config and "phase_a_duration_modifier" in strategy_config:
        phase_a_modifier = strategy_config["phase_a_duration_modifier"]
        print(f"  フェーズA倍率: {phase_a_modifier}x")

    # カット区間を総フレーム数に応じて再計算
    # 構成比: カット1=約46%, フェーズA=約27% * phase_a_modifier, フェーズB=残り
    cut1_end = round(total_frames * 0.46)
    cut1_end = round(cut1_end / 24) * 24  # 秒単位の整数に丸める

    base_phase_a_ratio = 0.27
    phase_a_frames = round(total_frames * base_phase_a_ratio * phase_a_modifier)
    # phase_a_frames も24の倍数に丸める
    phase_a_frames = round(phase_a_frames / 24) * 24
    if phase_a_frames < 48:  # 最短2秒以下を防止
        phase_a_frames = 48

    actual_cut1_start = 0
    actual_cut1_end = cut1_end
    actual_cut2a_start = cut1_end + 1
    actual_cut2a_end = actual_cut2a_start + phase_a_frames - 1
    actual_cut2b_start = actual_cut2a_end + 1
    actual_cut2b_end = total_frames

    print(f"  カット区間: fr{actual_cut1_start}-{actual_cut1_end} + fr{actual_cut2a_start}-{actual_cut2a_end} + fr{actual_cut2b_start}-{actual_cut2b_end}")

    # cut_frames 辞書を作成（short2_cuts の関数に渡す用）
    cut_frames = {
        "cut1_start": actual_cut1_start,
        "cut1_end": actual_cut1_end,
        "cut2a_start": actual_cut2a_start,
        "cut2a_end": actual_cut2a_end,
        "cut2b_start": actual_cut2b_start,
        "cut2b_end": actual_cut2b_end,
    }

    # ============================================================
    # --- カット1 (fr0-cut1_end): 円弧パンニング + 車スライド ---
    # ============================================================
    cut1_result = setup_cut1_overlap(
        camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CarBの半透明化 — short2専用関数で完全に再構築（CONSTANT補間で瞬時切り替え）
    # ルール2: 透明度対象車を全高が大きい車に設定する
    transparency_target = "carB"  # デフォルト
    if strategy_config and "transparency_target" in strategy_config:
        transparency_target = strategy_config["transparency_target"]
        print(f"  半透明化対象車: {transparency_target} (全高比較)")

    target_car = car_b if transparency_target == "carB" else car_a

    # キーフレームの位置をフェーズB開始に合わせて調整
    alpha_restore_frame = actual_cut2b_start  # フェーズB開始で不透明化
    _setup_short2_carb_transparency(target_car, end_frame=total_frames, restore_frame=alpha_restore_frame)
    print(f"  Alpha({transparency_target}): fr30で半透明化(1.0→0.35), fr{alpha_restore_frame}で不透明化(0.35→1.0) [CONSTANT補間]")

    # ============================================================
    # --- カット2 フェーズA: トップダウンビュー + 車スライド開始 ---
    # ============================================================
    cut1_final_cam = cut1_result['camera_loc']
    setup_cut2_phase_a_topdown(
        camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end,
        cut1_final_cam,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CarBはフェーズA中半透明状態を維持（alpha=0.35のままで良い）

    # ============================================================
    # --- カット2 フェーズB: カメラ復帰 + 不透明化 + 車スライド完了 ---
    # ============================================================
    cut2_result = setup_cut2_phase_b_camera_return(
        camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # ============================================================
    # --- カット2終了地点の状態 ---
    # ============================================================
    print(f"\n=== カット2終了 (fr{total_frames}) 状態 ===")
    print(f"  carA: {car_a_start}")
    print(f"  carB: {car_b_start}")
    print(f"  カメラ: loc={cut2_result['camera_loc']}, rot={cut2_result['camera_rot']}")

    # シーンの終了フレームを設定（動画が最後までレンダリングされるように）
    scene.frame_end = total_frames
    print(f"  scene.frame_end={total_frames}")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print(f"\n=== ショート動画v2 アニメーション完了 (total_frames={total_frames}, 約{total_frames/24:.1f}秒) ===")

    from animation_common import CutState
    return CutState(
        car_a_loc=car_a_start,
        car_b_loc=car_b_start,
        camera_loc=cut2_result['camera_loc'],
        camera_rot=cut2_result['camera_rot'],
    )
