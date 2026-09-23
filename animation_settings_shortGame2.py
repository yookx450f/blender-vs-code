"""
アニメーション設定モジュール - ゲームキャラクターショート動画v2（縦長9:16）
フレーム 0-576（約24秒、24fps）を処理する。

カット1 (fr0-576): キャラクター中央スライド + カメラ360度一周円弧パンニング
  - fr0-120 (5秒): キャラクターが両側から中央へスライド
  - fr0-576 (24秒): カメラがキャラクター周りを360度一周

YouTube Shorts用の縦長フォーマット。

shortGame2 の違い:
    shortGameと同じ構造だが、カット1のみで360度一周するシンプルな構成。
    games_config.json から設定を読み込む。

【動的スケーリング】
    キャラクターの寸法に基づいて、カメラ距離とキャラクター間隔を自動調整する。
    大きなキャラほど、カメラを遠ざけ・間隔を広げる。

使い方:
    from animation_settings_shortGame2 import setup_shortGame2_animations
    setup_shortGame2_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions, strategy_config=None, char_dimensions=None)
"""

import bpy
import copy
from animation_common import _setup_transparency_keyframe_animation, _add_transparency_keyframe_existing, _force_constant_interpolation_car_b_alpha, _setup_short2_carb_transparency
from short_game2_utils import get_character_visual_center_offset, clear_animation_data
from short_game2_cuts import (
    setup_cut1_360,
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


def setup_shortGame2_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions, strategy_config=None, char_dimensions=None):
    """
    ゲームキャラクターショート動画v2のアニメーションをオーケストレーション（フレーム 0-576）

    カット1 (fr0-576): キャラクターが中央へスライド + カメラ360度一周円弧パンニング

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
    print(f"\n=== ゲームキャラクターショート動画v2 アニメーション設定を開始 (total_frames=576, 約24秒) ===")

    # ============================================================
    # 動的スケーリング計算
    # ============================================================
    scale_factor = _calculate_scale_factor(char_dimensions)

    # スケーリング適用後の基本値
    char_scale = scale_factor ** 0.5
    cam_scale = scale_factor * 0.75
    char_start_half_dist = 2.1125 * char_scale          # キャラクター開始位置の半間隔
    cam_start_x = -4.5 * cam_scale                      # カメラ起始X座標
    cam_start_y = -8.0 * cam_scale                      # カメラ起始Y座標
    cam_start_z = 4.5 * min(cam_scale, 1.5)            # カメラ高度Z

    print(f"  動的スケーリング: scale_factor={scale_factor:.2f}, char_scale={char_scale:.2f}, cam_scale={cam_scale:.2f}")
    print(f"  キャラクター間隔: ±{char_start_half_dist:.2f}m")
    print(f"  カメラ起始位置: ({cam_start_x:.1f}, {cam_start_y:.1f}, {cam_start_z:.1f})")

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

    print(f"  接地Z: carA={grounded_z_a:.4f}, charB={grounded_z_b:.4f}")
    print(f"  rear_offset_y={rear_offset_y:.4f}")

    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)

    try:
        offset_a = get_character_visual_center_offset(char_a)
        offset_b = get_character_visual_center_offset(char_b)
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), charB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")

    # ============================================================
    # キャラクターのターゲット位置を定義（スケーリング適用）
    # ============================================================
    char_a_start = (-char_start_half_dist, 0.0, grounded_z_a)
    char_b_start = (char_start_half_dist, 0.0, grounded_z_b)
    char_a_end = (0.0 - offset_a[0], 0.0, grounded_z_a)
    char_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)

    print(f"  charA: start={char_a_start} -> end={char_a_end}")
    print(f"  charB: start={char_b_start} -> end={char_b_end}")

    # カメラのターゲット（キャラクターの中心付近）
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

    # レンズ設定 — 広角で環境全体の構図を捉えるよう固定
    original_lens = camera.data.lens
    adjusted_lens = round(24 * min(cam_scale, 1.0))
    adjusted_lens = max(18, min(50, adjusted_lens))
    camera.data.lens = adjusted_lens
    print(f"  カメラレンズ: {original_lens}mm → {adjusted_lens}mm（広角調整）")
    
    camera.data.sensor_height = max(camera.data.sensor_height, 22.0)
    print(f"  カメラセンサー高: {camera.data.sensor_height}mm")

    # ============================================================
    # スケール情報を strategy_config に注入
    # ============================================================
    if strategy_config is None:
        strategy_config = {}
    strategy_config["scale_factor"] = scale_factor
    strategy_config["char_scale"] = char_scale
    strategy_config["cam_scale"] = cam_scale
    strategy_config["cam_start_x"] = cam_start_x
    strategy_config["cam_start_y"] = cam_start_y
    strategy_config["cam_start_z"] = cam_start_z

    # カメラZの最低値保証
    max_char_height_m = 3.0  # デフォルト
    if char_dimensions:
        heights = []
        for dims in char_dimensions.values():
            h = dims.get("height", 0) / 1000.0 if dims.get("height") else 0
            if h > 0:
                heights.append(h)
        if heights:
            max_char_height_m = max(heights)
    min_camera_z = max_char_height_m + 3.0
    strategy_config["min_camera_z"] = min_camera_z
    print(f"  カメラZ最低値保証: {min_camera_z:.1f}m (キャラ高{max_char_height_m:.1f}m + マージン3.0m)")

    # ============================================================
    # フレーム定義
    # ============================================================
    total_frames = 576
    cut1_start = 0
    cut1_end = 576

    print(f"  カット区間: fr{cut1_start}-{cut1_end} (約{(cut1_end - cut1_start + 1)/24:.1f}秒)")

    cut_frames = {
        "cut1_start": cut1_start,
        "cut1_end": cut1_end,
    }

    # ============================================================
    # クォータニオン状態をリセット
    # ============================================================
    from short_game2_cuts import reset_camera_quat_state
    reset_camera_quat_state()

    # ============================================================
    # --- カット1 (fr0-576): 360度一周円弧パンニング + キャラクターズスライド ---
    # ============================================================
    cut1_result = setup_cut1_360(
        camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CharBの半透明化 — short2専用関数で完全に再構築
    _setup_short2_carb_transparency(char_b, end_frame=total_frames, restore_frame=400)
    print(f"  Alpha(carB): fr30で半透明化(1.0→0.35), fr400で不透明化(0.35→1.0) [CONSTANT補間]")

    # ============================================================
    # --- カット1終了地点の状態 ---
    # ============================================================
    print(f"\n=== カット1終了 (fr{total_frames}) 状態 ===")
    print(f"  charA: {char_a_start}")
    print(f"  charB: {char_b_start}")
    print(f"  カメラ: loc={cut1_result['camera_loc']}, rot={cut1_result['camera_rot']}")

    # シーンの終了フレームを設定
    scene.frame_end = total_frames
    print(f"  scene.frame_end={total_frames}")

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print(f"\n=== ゲームキャラクターショート動画v2 アニメーション完了 (total_frames={total_frames}, 約{total_frames/24:.1f}秒) ===")

    from animation_common import CutState
    return CutState(
        car_a_loc=char_a_start,
        car_b_loc=char_b_start,
        camera_loc=cut1_result['camera_loc'],
        camera_rot=cut1_result['camera_rot'],
    )
