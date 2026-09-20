"""
アニメーション設定モジュール - ゲームキャラクターショート動画（縦長9:16）
フレーム 0-624（約26秒、24fps）を処理する。

カット1 (fr0-288): 「キャラクターが重なっていく部分」の円弧パンニング
カット2 (fr289-624): トップダウンビュー → カメラ復帰 → キャラクターズスライド復帰（同時進行）
  フェーズA (fr289-456): 7秒 - トップダウンへ移動（イージング適用）
  フェーズB (fr457-624): 7秒 - カメラ復帰（イージング適用）

YouTube Shorts用の縦長フォーマット。

shortGame の違い:
    Short2と同じ構造だが、ゲームキャラクター向けに調整。
    games_config.json から設定を読み込む。

【動的スケーリング】
    キャラクターの寸法に基づいて、カメラ距離とキャラクター間隔を自動調整する。
    大きなキャラほど、カメラを遠ざけ・間隔を広げる。

使い方:
    from animation_settings_shortGame import setup_shortGame_animations
    setup_shortGame_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions, strategy_config=None, char_dimensions=None)
"""

import bpy
import copy
from animation_common import _setup_transparency_keyframe_animation, _add_transparency_keyframe_existing, _force_constant_interpolation_car_b_alpha, _setup_short2_carb_transparency
from short_game_utils import get_character_visual_center_offset, clear_animation_data
from short_game_cuts import (
    setup_cut1_overlap,
    setup_cut2_phase_a_topdown,
    setup_cut2_phase_b_camera_return,
)


def _calculate_scale_factor(char_dimensions):
    """
    キャラクターの寸法からスケール倍率を計算する。

    基準サイズ(2.0m)に対して、両キャラクターの最大寸法の大きい方を比較し、
    スケール係数を算出。範囲は 0.8〜4.0 でクリップする。

    Parameters:
        char_dimensions: {key: {"length": mm値, "height": mm値}} の辞書 (None時はデフォルト1.0)

    Returns:
        float: スケール倍率 (デフォルト=1.0)
    """
    if not char_dimensions:
        return 1.0

    base_size_m = 2.0  # 基準サイズ（mm単位）

    # 両キャラクターの最大寸法をメートルで取得
    max_dims_m = []
    for key, dims in char_dimensions.items():
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

    # クリップ範囲 0.8 〜 6.0（巨大モンスターでもカメラが離れるよう上限を拡大）
    scale_factor = max(0.8, min(6.0, scale_factor))

    print(f"  スケール倍率計算: 最大寸法={largest_dim_m:.2f}m / 基準={base_size_m:.1f}m → scale_factor={scale_factor:.2f}")
    return scale_factor


def setup_shortGame_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions, strategy_config=None, char_dimensions=None):
    """
    ゲームキャラクターショート動画のアニメーションをオーケストレーション（フレーム 0-624）

    カット1 (fr0-288): キャラクターが中央へスライド + 円弧パンニング
    カット2 (fr289-624): トップダウン→カメラ復帰→キャラクターズスライド復帰（同時進行、イージング適用）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_chars: {key: char_object} の辞書 (carA, carB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
        strategy_config: バリエーション設定辞書（オプション。None時は既存動作）
        char_dimensions: {key: {"length": mm, "height": mm}} 寸法情報（オプション。None時はデフォルト値使用）

    Returns:
        CutState: 最終状態情報
    """
    print(f"\n=== ゲームキャラクターショート動画 アニメーション設定を開始 (total_frames=624, 約26秒) ===")

    # ============================================================
    # 動的スケーリング計算
    # ============================================================
    scale_factor = _calculate_scale_factor(char_dimensions)

    # スケーリング適用後の基本値
    # キャラクター間隔: スケール係数の0.5乗で弱く補正（大きな変化を抑制）
    char_scale = scale_factor ** 0.5
    # カメラ距離: フィールドを広げるよう倍率を低下させ、後方から構図を捉える
    cam_scale = scale_factor * 0.75
    char_start_half_dist = 2.1125 * char_scale          # キャラクター開始位置の半間隔（1.25×1.3×1.3倍）
    cam_start_x = -4.5 * cam_scale                      # カメラ起始X座標（距離を拡大）
    cam_start_y = -8.0 * cam_scale                      # カメラ起始Y座標（フィールドを広く）
    cam_start_z = 4.5 * min(cam_scale, 1.5)            # カメラ高度Z（高さも上げる）
    topdown_height = 8.0 * cam_scale                    # トップダウンカメラ高さ

    print(f"  動的スケーリング: scale_factor={scale_factor:.2f}, char_scale={char_scale:.2f}, cam_scale={cam_scale:.2f}")
    print(f"  キャラクター間隔: ±{char_start_half_dist:.2f}m")
    print(f"  カメラ起始位置: ({cam_start_x:.1f}, {cam_start_y:.1f}, {cam_start_z:.1f})")
    print(f"  トップダウン高さ: {topdown_height:.1f}m")

    # ============================================================
    # 前提計算：キャラクターの位置・接地 Z を準備
    # ============================================================
    char_a = imported_chars.get("carA")
    char_b = imported_chars.get("carB")

    if not char_a or not char_b:
        print("エラー: carA または carB が見つかりません")
        return None

    grounded_z_a = grounded_z_positions.get(char_a.name, char_a.location.z)
    grounded_z_b = grounded_z_positions.get(char_b.name, char_b.location.z)

    print(f"  接地Z: carA={grounded_z_a:.4f}, carB={grounded_z_b:.4f}")
    print(f"  rear_offset_y={rear_offset_y:.4f}")

    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)

    try:
        offset_a = get_character_visual_center_offset(char_a)
        offset_b = get_character_visual_center_offset(char_b)
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), carB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")

    # ============================================================
    # キャラクターのターゲット位置を定義（スケーリング適用）
    # ============================================================
    char_a_start = (-char_start_half_dist, 0.0, grounded_z_a)
    char_b_start = (char_start_half_dist, 0.0, grounded_z_b)
    char_a_end = (0.0 - offset_a[0], 0.0, grounded_z_a)
    char_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)

    print(f"  carA: start={char_a_start} -> end={char_a_end}")
    print(f"  carB: start={char_b_start} -> end={char_b_end}")

    # カメラのターゲット（キャラクターの中心付近）— 高さもcam_scaleでスケーリング
    target_z = 1.0 * min(cam_scale, 2.0)
    target = (0.0, 0.0, target_z)

    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"  Track To コンストレイント '{constraint.name}' を無効化")
    
    # CameraTarget のアニメーションデータもクリア
    target_name = "CameraTarget"
    if target_name in bpy.data.objects:
        camera_target = bpy.data.objects[target_name]
        if camera_target.animation_data:
            camera_target.animation_data_clear()
            print(f"  {camera_target.name} のアニメーションデータをクリア")
    
    # アニメーションデータを完全にクリア（前回実行の残骸を削除）
    print("  アニメーションデータのクリーンアップ...")
    clear_animation_data([camera, char_a, char_b])

    # レンズ設定 — 広角で環境全体の構図を捉えるよう固定（24mm基準、18-50mm範囲）
    original_lens = camera.data.lens
    adjusted_lens = round(24 * min(cam_scale, 1.0))
    adjusted_lens = max(18, min(50, adjusted_lens))  # より広角の範囲に収める
    camera.data.lens = adjusted_lens
    print(f"  カメラレンズ: {original_lens}mm → {adjusted_lens}mm（広角調整）")
    
    # センサーサイズを少し拡大してキャラクターが大きく見えるように
    # スマホ縦画面で見たときにちょうど良いサイズ感に調整
    camera.data.sensor_height = max(camera.data.sensor_height, 22.0)
    print(f"  カメラセンサー高: {camera.data.sensor_height}mm")

    # ============================================================
    # バリエーションプリセットの座標にもスケールを適用（Short2と同じ方式）
    # グローバル定数を汚染しないようディープコピーしてから修正
    # ============================================================
    if "camera_pattern" in strategy_config:
        cam_pat = copy.deepcopy(strategy_config["camera_pattern"])
        sp = tuple(cam_pat.get("start_position", (-4.5, -8.0, 4.5)))
        scaled_sp = (
            sp[0] * cam_scale,
            sp[1] * cam_scale,
            sp[2] * min(cam_scale, 2.0)
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
            max(tp[2], tp[2] * char_scale)  # topdown高さはsqrt補正で緩やかに拡大
        )
        td_var["position"] = list(scaled_tp)
        strategy_config["topdown_variation"] = td_var
        print(f"  トップダウン '{td_var.get('name','?')}': position {tp} → {scaled_tp}")

    # ============================================================
    # スケール情報を strategy_config に注入（カット関数へ渡すため）
    # ============================================================
    if strategy_config is None:
        strategy_config = {}
    strategy_config["scale_factor"] = scale_factor       # 生スケール値（参照用）
    strategy_config["char_scale"] = char_scale           # キャラクター間隔用
    strategy_config["cam_scale"] = cam_scale             # カメラ距離用
    strategy_config["cam_start_x"] = cam_start_x
    strategy_config["cam_start_y"] = cam_start_y
    strategy_config["cam_start_z"] = cam_start_z
    strategy_config["topdown_height"] = topdown_height

    # カメラZの最低値保証（キャラクターの最大全高 + 安全マージン3.0m）
    max_char_height_m = 3.0  # デフォルト
    if char_dimensions:
        heights = []
        for dims in char_dimensions.values():
            h = dims.get("height", 0) / 1000.0 if dims.get("height") else 0
            if h > 0:
                heights.append(h)
        if heights:
            max_char_height_m = max(heights)
    min_camera_z = max_char_height_m + 3.0  # キャラクターの上部から最低3m離す
    strategy_config["min_camera_z"] = min_camera_z
    print(f"  カメラZ最低値保証: {min_camera_z:.1f}m (キャラ高{max_char_height_m:.1f}m + マージン3.0m)")

    # ============================================================
    # バリエーション設定：総フレーム数・フェーズAの時間変動適用
    # ============================================================
    total_frames = 624  # デフォルト
    if "total_frames" in strategy_config:
        total_frames = strategy_config["total_frames"]
        print(f"  総フレーム数: {total_frames} (約{total_frames/24:.1f}秒)")

    phase_a_modifier = 1.0
    if "phase_a_duration_modifier" in strategy_config:
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

    # cut_frames 辞書を作成（short_game_cuts の関数に渡す用）
    cut_frames = {
        "cut1_start": actual_cut1_start,
        "cut1_end": actual_cut1_end,
        "cut2a_start": actual_cut2a_start,
        "cut2a_end": actual_cut2a_end,
        "cut2b_start": actual_cut2b_start,
        "cut2b_end": actual_cut2b_end,
    }

    # ============================================================
    # クォータニオン状態をリセット（跨カット残留の防止）
    # ============================================================
    from short_game_cuts import reset_camera_quat_state
    reset_camera_quat_state()

    # ============================================================
    # --- カット1 (fr0-cut1_end): 円弧パンニング + キャラクターズスライド ---
    # ============================================================
    cut1_result = setup_cut1_overlap(
        camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CharBの半透明化 — short2専用関数で完全に再構築（CONSTANT補間で瞬時切り替え）
    # ルール2: 透明度対象キャラクターを全高が大きいキャラに設定する
    transparency_target = "carB"  # デフォルト
    if "transparency_target" in strategy_config:
        transparency_target = strategy_config["transparency_target"]
        print(f"  半透明化対象キャラクター: {transparency_target} (全高比較)")

    target_char = char_b if transparency_target == "carB" else char_a

    # キーフレームの位置をフェーズB開始に合わせて調整
    alpha_restore_frame = actual_cut2b_start  # フェーズB開始で不透明化
    _setup_short2_carb_transparency(target_char, end_frame=total_frames, restore_frame=alpha_restore_frame)
    print(f"  Alpha({transparency_target}): fr30で半透明化(1.0→0.35), fr{alpha_restore_frame}で不透明化(0.35→1.0) [CONSTANT補間]")

    # ============================================================
    # --- カット2 フェーズA: トップダウンビュー + キャラクターズスライド開始 ---
    # ============================================================
    cut1_final_cam = cut1_result['camera_loc']
    setup_cut2_phase_a_topdown(
        camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end,
        cut1_final_cam,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CharBはフェーズA中半透明状態を維持（alpha=0.35のままで良い）

    # ============================================================
    # --- カット2 フェーズB: カメラ復帰 + 不透明化 + キャラクターズスライド完了 ---
    # ============================================================
    cut2_result = setup_cut2_phase_b_camera_return(
        camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # ============================================================
    # --- カット2終了地点の状態 ---
    # ============================================================
    print(f"\n=== カット2終了 (fr{total_frames}) 状態 ===")
    print(f"  carA: {char_a_start}")
    print(f"  carB: {char_b_start}")
    print(f"  カメラ: loc={cut2_result['camera_loc']}, rot={cut2_result['camera_rot']}")

    # シーンの終了フレームを設定（動画が最後までレンダリングされるように）
    scene.frame_end = total_frames
    print(f"  scene.frame_end={total_frames}")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print(f"\n=== ゲームキャラクターショート動画 アニメーション完了 (total_frames={total_frames}, 約{total_frames/24:.1f}秒) ===")

    from animation_common import CutState
    return CutState(
        car_a_loc=char_a_start,
        car_b_loc=char_b_start,
        camera_loc=cut2_result['camera_loc'],
        camera_rot=cut2_result['camera_rot'],
    )
