"""
アニメーション設定モジュール - ショート動画v2（縦長9:16）
フレーム 0-312（約13秒、24fps）を処理する。

カット1 (fr0-144): 「車が重なっていく部分」の円弧パンニング
カット2 (fr145-312): トップダウンビュー → カメラ復帰 → 車スライド復帰（同時進行）
  フェーズA (fr289-456): 7秒 - トップダウンへ移動（イージング適用）
  フェーズB (fr457-624): 7秒 - カメラ復帰（イージング適用）

YouTube Shorts用の縦長フォーマット。

short2 の違い:
    半透明化をドライバー式ではなくキーフレーム直接設定方式を使用。

【動的スケーリング】
    車の寸法に基づいて、カメラ距離と車間隔を自動調整する。
    大きな車ほど、カメラを遠ざけ・間隔を広げる。

使い方:
    from animation_settings_short2 import setup_short2_animations
    setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, strategy_config=None, car_dimensions=None)
"""

import bpy
import copy
from animation_common import _setup_transparency_keyframe_animation, _add_transparency_keyframe_existing, _force_constant_interpolation_car_b_alpha, _setup_short2_carb_transparency
from short2_utils import get_car_visual_center_offset, clear_animation_data
from short2_cuts import (
    setup_cut1_overlap,
    setup_cut2_phase_a_topdown,
    setup_cut2_phase_b_camera_return,
)


def _calculate_scale_factor(car_dimensions):
    """
    車の寸法からスケール倍率を計算する。

    基準サイズ(4.5m)に対して、両車の最大寸法の大きい方を比較し、
    スケール係数を算出。範囲は 0.8〜4.0 でクリップする。

    Parameters:
        car_dimensions: {key: {"length": mm値, "height": mm値}} の辞書 (None時はデフォルト1.0)

    Returns:
        float: スケール倍率 (デフォルト=1.0)
    """
    if not car_dimensions:
        return 1.0

    base_size_m = 4.5  # 基準サイズ（車の平均全長目安）

    # 両車の最大寸法をメートルで取得
    max_dims_m = []
    for key, dims in car_dimensions.items():
        length_m = dims.get("length", 0) / 1000.0 if dims.get("length") else 0
        height_m = dims.get("height", 0) / 1000.0 if dims.get("height") else 0
        max_dim_m = max(length_m, height_m)
        if max_dim_m > 0:
            max_dims_m.append(max_dim_m)

    if not max_dims_m:
        return 1.0

    # 両者のうち最大寸法の大きい方を基準に計算
    largest_dim_m = max(max_dims_m)
    scale_factor = largest_dim_m / base_size_m

    # クリップ範囲 0.8 〜 4.0
    scale_factor = max(0.8, min(4.0, scale_factor))

    print(f"  スケール倍率計算: 最大寸法={largest_dim_m:.2f}m / 基準={base_size_m:.1f}m → scale_factor={scale_factor:.2f}")
    return scale_factor


def setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, strategy_config=None, car_dimensions=None):
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
        car_dimensions: {key: {"length": mm, "height": mm}} 寸法情報（オプション。None時はデフォルト値使用）

    Returns:
        CutState: 最終状態情報
    """
    print(f"\n=== ショート動画v2 アニメーション設定を開始 (total_frames=312, 約13秒) ===")

    # ============================================================
    # 動的スケーリング計算
    # ============================================================
    scale_factor = _calculate_scale_factor(car_dimensions)

    # スケーリング適用後の基本値
    # 車間隔: スケール係数の0.5乗で弱く補正（大きな変化を抑制）
    char_scale = scale_factor ** 0.5
    # カメラ距離: スケール係数に1.5倍を掛けて強く補正（巨大車でも画面に収まる）
    cam_scale = scale_factor * 1.5
    car_start_half_dist = 1.25 * char_scale           # 車開始位置の半間隔
    cam_start_x = -3.0 * cam_scale                    # カメラ起始X座標
    cam_start_y = -6.0 * cam_scale                    # カメラ起始Y座標
    cam_start_z = 3.5 * min(cam_scale, 2.0)          # カメラ高度Z
    topdown_height = max(8.0, 8.0 * char_scale)      # トップダウンカメラ高さ（sqrt補正で緩やかに拡大、8m以下にはしない）

    print(f"  動的スケーリング: scale_factor={scale_factor:.2f}, char_scale={char_scale:.2f}, cam_scale={cam_scale:.2f}")
    print(f"  車間隔: ±{car_start_half_dist:.2f}m")
    print(f"  カメラ起始位置: ({cam_start_x:.1f}, {cam_start_y:.1f}, {cam_start_z:.1f})")
    print(f"  トップダウン高さ: {topdown_height:.1f}m")

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
    # 車のターゲット位置を定義（スケーリング適用）
    # ============================================================
    car_a_start = (-car_start_half_dist, rear_offset_y, grounded_z_a)
    car_b_start = (car_start_half_dist, 0.0, grounded_z_b)
    car_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
    car_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)

    print(f"  carA: start={car_a_start} -> end={car_a_end}")
    print(f"  carB: start={car_b_start} -> end={car_b_end}")

    # カメラのターゲット（車の中心付近）— 高さもcam_scaleでスケーリング
    target_z = 1.0 * min(cam_scale, 2.0)
    target = (0.0, 0.0, target_z)

    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"  Track To コンストレイント '{constraint.name}' を無効化")

    # CameraTarget のアニメーションデータもクリア（前回実行の残骸を削除）
    # → これがないと、CameraTargetの位置キーフレームが残り、カメラが暴走する
    target_name = "CameraTarget"
    if target_name in bpy.data.objects:
        camera_target = bpy.data.objects[target_name]
        if camera_target.animation_data:
            camera_target.animation_data_clear()
            print(f"  {camera_target.name} のアニメーションデータをクリア")

    # アニメーションデータを完全にクリア（前回実行の残骸を削除）
    print("  アニメーションデータのクリーンアップ...")
    clear_animation_data([camera, car_a, car_b])

    # レンズ設定 — cam_scaleに応じてFOVを調整
    original_lens = camera.data.lens
    adjusted_lens = round(35 * min(cam_scale, 1.5))  # cam_scale上限: 2.0→1.5（カメラ飛防止）
    adjusted_lens = max(24, min(85, adjusted_lens))  # 広角〜望遠の範囲に収める
    camera.data.lens = adjusted_lens
    print(f"  カメラレンズ: {original_lens}mm → {adjusted_lens}mm（スケール調整）")

    # ============================================================
    # スケール情報を strategy_config に注入（カット関数へ渡すため）
    # ============================================================
    if strategy_config is None:
        strategy_config = {}
    strategy_config["scale_factor"] = scale_factor       # 生スケール値（参照用）
    strategy_config["char_scale"] = char_scale           # 車間隔用
    strategy_config["cam_scale"] = cam_scale             # カメラ距離用
    strategy_config["cam_start_x"] = cam_start_x
    strategy_config["cam_start_y"] = cam_start_y
    strategy_config["cam_start_z"] = cam_start_z
    strategy_config["topdown_height"] = topdown_height

    # カメラZの最低値保証（車の最大全高 + 安全マージン2.0m）
    max_car_height_m = 2.0  # デフォルト
    if car_dimensions:
        heights = []
        for dims in car_dimensions.values():
            h = dims.get("height", 0) / 1000.0 if dims.get("height") else 0
            if h > 0:
                heights.append(h)
        if heights:
            max_car_height_m = max(heights)
    min_camera_z = max_car_height_m + 2.0  # 車の上部から最低2m離す
    strategy_config["min_camera_z"] = min_camera_z
    print(f"  カメラZ最低値保証: {min_camera_z:.1f}m (車高{max_car_height_m:.1f}m + マージン2.0m)")

    # ============================================================
    # バリエーションプリセットの座標にもスケールを適用
    # グローバル定数を汚染しないようディープコピーしてから修正
    # ============================================================
    if "camera_pattern" in strategy_config:
        cam_pat = copy.deepcopy(strategy_config["camera_pattern"])
        sp = tuple(cam_pat.get("start_position", (-3.0, -6.0, 3.5)))
        scaled_sp = (
            sp[0] * min(cam_scale, 1.5),  # カメラ飛防止: 上限1.5
            sp[1] * min(cam_scale, 1.5),
            sp[2] * min(cam_scale, 1.5)
        )
        cam_pat["start_position"] = list(scaled_sp)
        strategy_config["camera_pattern"] = cam_pat
        print(f"  カメラパターン '{cam_pat.get('name','?')}': start_position {sp} → {scaled_sp}")

    if "topdown_variation" in strategy_config:
        td_var = copy.deepcopy(strategy_config["topdown_variation"])
        tp = tuple(td_var.get("position", (0.0, 0.0, 8.0)))
        scaled_tp = (
            tp[0],  # X,Yは変更不要（中心上）
            tp[1],
            max(tp[2], tp[2] * char_scale)  # topdown高さはsqrt補正で緩やかに拡大（元の高さ以下にはしない）
        )
        td_var["position"] = list(scaled_tp)
        strategy_config["topdown_variation"] = td_var
        print(f"  トップダウン '{td_var.get('name','?')}': position {tp} → {scaled_tp}")

    # ============================================================
    # バリエーション設定：総フレーム数・フェーズAの時間変動適用
    # ============================================================
    total_frames = 312  # デフォルト（約13秒、2倍速化）
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
    if phase_a_frames < 24:  # 最短1秒以下を防止
        phase_a_frames = 24

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
    # クォータニオン状態をリセット（跨実行残留の防止）
    # ============================================================
    from short2_cuts import reset_camera_quat_state
    reset_camera_quat_state()

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
