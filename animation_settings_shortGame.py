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

使い方:
    from animation_settings_shortGame import setup_shortGame_animations
    setup_shortGame_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions)
"""

import bpy
from animation_common import _setup_transparency_keyframe_animation, _add_transparency_keyframe_existing, _force_constant_interpolation_car_b_alpha, _setup_short2_carb_transparency
from short_game_utils import get_character_visual_center_offset, clear_animation_data
from short_game_cuts import (
    setup_cut1_overlap,
    setup_cut2_phase_a_topdown,
    setup_cut2_phase_b_camera_return,
)


def setup_shortGame_animations(scene, camera, imported_chars, rear_offset_y, grounded_z_positions, strategy_config=None):
    """
    ゲームキャラクターショート動画のアニメーションをオーケストレーション（フレーム 0-624）

    カット1 (fr0-288): キャラクターが中央へスライド + 円弧パンニング
    カット2 (fr289-624): トップダウン→カメラ復帰→キャラクターズスライド復帰（同時進行、イージング適用）

    Parameters:
        scene: bpy.context.scene
        camera: カメラオブジェクト
        imported_chars: {key: char_object} の辞書 (gameA, gameB)
        rear_offset_y: リア端揃え用の Y オフセット値
        grounded_z_positions: {object_name: z_value} 接地後の Z 位置を保存する辞書
        strategy_config: バリエーション設定辞書（オプション。None時は既存動作）

    Returns:
        CutState: 最終状態情報
    """
    print(f"\n=== ゲームキャラクターショート動画 アニメーション設定を開始 (total_frames=624, 約26秒) ===")

    # ============================================================
    # 前提計算：キャラクターの位置・接地 Z を準備
    # ============================================================
    char_a = imported_chars.get("gameA")
    char_b = imported_chars.get("gameB")

    if not char_a or not char_b:
        print("エラー: gameA または gameB が見つかりません")
        return None

    grounded_z_a = grounded_z_positions.get(char_a.name, char_a.location.z)
    grounded_z_b = grounded_z_positions.get(char_b.name, char_b.location.z)

    print(f"  接地Z: gameA={grounded_z_a:.4f}, gameB={grounded_z_b:.4f}")
    print(f"  rear_offset_y={rear_offset_y:.4f}")

    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)

    try:
        offset_a = get_character_visual_center_offset(char_a)
        offset_b = get_character_visual_center_offset(char_b)
        print(f"  視覚的中心オフセット: gameA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), gameB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")

    # ============================================================
    # キャラクターのターゲット位置を定義
    # ============================================================
    char_a_start = (-1.25, rear_offset_y, grounded_z_a)
    char_b_start = (1.25, 0.0, grounded_z_b)
    char_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
    char_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)

    print(f"  gameA: start={char_a_start} -> end={char_a_end}")
    print(f"  gameB: start={char_b_start} -> end={char_b_end}")

    # カメラのターゲット（キャラクターの中心付近）
    target = (0.0, 0.0, 1.0)

    # Track To コンストレイントを無効化（直接回転制御）
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            constraint.mute = True
            print(f"  Track To コンストレイント '{constraint.name}' を無効化")

    # アニメーションデータを完全にクリア（前回実行の残骸を削除）
    print("  アニメーションデータのクリーンアップ...")
    clear_animation_data([camera, char_a, char_b])

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
    # --- カット1 (fr0-cut1_end): 円弧パンニング + キャラクターズスライド ---
    # ============================================================
    cut1_result = setup_cut1_overlap(
        camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CharBの半透明化 — short2専用関数で完全に再構築（CONSTANT補間で瞬時切り替え）
    # ルール2: 透明度対象キャラクターを全高が大きいキャラに設定する
    transparency_target = "gameB"  # デフォルト
    if strategy_config and "transparency_target" in strategy_config:
        transparency_target = strategy_config["transparency_target"]
        print(f"  半透明化対象キャラクター: {transparency_target} (全高比較)")

    target_char = char_b if transparency_target == "gameB" else char_a

    # キーフレームの位置をフェーズB開始に合わせて調整
    alpha_restore_frame = actual_cut2b_start  # フェーズB開始で不透明化
    _setup_short2_carb_transparency(target_char, end_frame=total_frames, restore_frame=alpha_restore_frame)
    print(f"  Alpha({transparency_target}): fr30で半透明化(1.0→0.35), fr{alpha_restore_frame}で不透明化(0.35→1.0) [CONSTANT補間]")

    # ============================================================
    # --- カット2 フェーズA: トップダウンビュー + キャラクターズスライド開始 ---
    # ============================================================
    cut1_final_cam = cut1_result['camera_loc']
    setup_cut2_phase_a_topdown(
        camera, char_a, char_b, char_a_end, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # CharBはフェーズA中半透明状態を維持（alpha=0.35のままで良い）

    # ============================================================
    # --- カット2 フェーズB: カメラ復帰 + 不透明化 + キャラクターズスライド完了 ---
    # ============================================================
    cut2_result = setup_cut2_phase_b_camera_return(
        camera, char_a, char_b, char_a_end, char_b_end,
        strategy_config=strategy_config,
        cut_frames=cut_frames
    )

    # ============================================================
    # --- カット2終了地点の状態 ---
    # ============================================================
    print(f"\n=== カット2終了 (fr{total_frames}) 状態 ===")
    print(f"  gameA: {char_a_start}")
    print(f"  gameB: {char_b_start}")
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
