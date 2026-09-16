"""
ShortGame - カット1・カット2 の位置アニメーションモジュール

各カットごとのカメラ・キャラクターの位置キーフレームを設定する。
カッは完全に分離されており、独立して動作する。

フレーム定義 (24fps):
  カット1: fr0-288 (約12秒) — キャラクターが中央へスライド + 円弧パンニング
  カット2A: fr289-456 (7秒) — トップダウンビューへ移動 (イージング) + キャラクターズスライド開始
  カット2B: fr457-624 (7秒) — カメラ復帰 (イージング) + CharB不透明化 + キャラクターズスライド完了

使い方:
    from short_game_cuts import (
        setup_cut1_overlap,
        setup_cut2_phase_a_topdown,
        setup_cut2_phase_b_camera_return,
    )
"""

import math
from animation_common import set_camera_look_at, _set_camera_keyframe
from short_game_utils import (
    _set_location_keyframe,
    _set_rotation_keyframe,
    _set_camera_location_keyframe,
)


# ============================================================
# デフォルトフレーム定義（24fps）— バックアップ用
# ============================================================
DEFAULT_CUT_FRAMES = {
    "cut1_start": 0,
    "cut1_end": 288,
    "cut2a_start": 289,
    "cut2a_end": 456,
    "cut2b_start": 457,
    "cut2b_end": 624,
}


def _get_easing_func(strategy_config=None):
    """
    strategy_config からイージング関数を取得。
    未設定時はデフォルトの cubic を返す。
    """
    if strategy_config and "easing_function" in strategy_config:
        try:
            from short2_variations import get_easing_function
            return get_easing_function(strategy_config["easing_function"])
        except Exception:
            pass
    # デフォルト: cubic
    def _ease_in_out_cubic(t):
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            return 1.0 - (-2.0 * t + 2.0)**3 / 2.0
    return _ease_in_out_cubic


def setup_cut1_overlap(camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end, strategy_config=None, cut_frames=None):
    """
    カット1: キャラクターが中央へスライド + 円弧パンニング。

    CharA: (-1.25, rear_offset_y) → 中央集合位置
    CharB: (1.25, 0.0) → 中央集合位置
    カメラ: バリエーション設定に基づく円弧パンニング

    Parameters:
        cut_frames: dict with keys cut1_start, cut1_end (None時はデフォルト値を使用)

    Returns:
        dict: カット1終了時の状態情報 (camera_loc, camera_rot)
    """
    # フレーム値を取得（引数がなければデフォルトを使用）
    cut1_start = cut_frames.get("cut1_start", DEFAULT_CUT_FRAMES["cut1_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_start"]
    cut1_end = cut_frames.get("cut1_end", DEFAULT_CUT_FRAMES["cut1_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_end"]

    print(f"\n  === カット1: キャラクター中央スライド + 円弧パンニング (fr{cut1_start}-{cut1_end}) ===")

    # --- キャラクターのアニメーション ---
    # フレーム 0: スタート位置
    _set_location_keyframe(char_a, cut1_start, char_a_start[0], char_a_start[1], char_a_start[2])
    _set_location_keyframe(char_b, cut1_start, char_b_start[0], char_b_start[1], char_b_start[2])

    # 中央集合完了フレーム（cut1_end の約42%地点 = 5秒相当）
    slide_end_frame = cut1_start + int((cut1_end - cut1_start) * 0.42)

    # フレーム slide_end_frame: 中央集合完了
    _set_location_keyframe(char_a, slide_end_frame, char_a_end[0], char_a_end[1], char_a_end[2])
    _set_location_keyframe(char_b, slide_end_frame, char_b_end[0], char_b_end[1], char_b_end[2])

    # 位置維持キーフレーム（1秒ごと）
    keyframe_interval = 24
    maintain_start = slide_end_frame + keyframe_interval
    for frame in range(maintain_start, cut1_end + 1, keyframe_interval):
        _set_location_keyframe(char_a, frame, char_a_end[0], char_a_end[1], char_a_end[2])
        _set_location_keyframe(char_b, frame, char_b_end[0], char_b_end[1], char_b_end[2])

    # カット1終了フレームも確実に設定
    _set_location_keyframe(char_a, cut1_end, char_a_end[0], char_a_end[1], char_a_end[2])
    _set_location_keyframe(char_b, cut1_end, char_b_end[0], char_b_end[1], char_b_end[2])

    # --- カメラ円弧パンニング（バリエーション設定適用） ---
    # 動的スケーリング: strategy_config からスケール情報を取得
    scale_factor = 1.0
    cam_scale_val = 1.0
    if strategy_config and "scale_factor" in strategy_config:
        scale_factor = strategy_config["scale_factor"]
    if strategy_config and "cam_scale" in strategy_config:
        cam_scale_val = strategy_config["cam_scale"]

    if strategy_config and "camera_pattern" in strategy_config:
        cam_pattern = strategy_config["camera_pattern"]
        # raw位置にcam_scaleを適用（デフォルトパスと同じスケーリングルール）
        raw_pos = cam_pattern["start_position"]
        cam_start_x = raw_pos[0] * cam_scale_val
        cam_start_y = raw_pos[1] * cam_scale_val
        cam_start_z = raw_pos[2] * min(cam_scale_val, 2.0)  # Z軸は2.0でクリップ（デフォルトと同等）
        cam_start = (cam_start_x, cam_start_y, cam_start_z)
        total_rotation = cam_pattern["total_rotation"]
        print(f"  カメラパターン: {cam_pattern['name']} (raw={raw_pos}, scaled={cam_start})")
    else:
        # スケール適用後のデフォルトカメラ位置
        cam_start_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cam_start_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cam_start_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_start = (cam_start_x, cam_start_y, cam_start_z)
        total_rotation = -0.85
        print(f"  デフォルトカメラ位置（スケール{scale_factor:.2f}適用）: {cam_start}")

    arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
    arc_height = cam_start[2]
    start_angle = math.atan2(cam_start[0], cam_start[1])

    # 総回転量をカット1の長さに応じてスケーリング（デフォルト144フレーム分の倍率）
    cut1_length = cut1_end - cut1_start + 1
    total_rotation_scaled = total_rotation * (cut1_length / 144)

    def get_cam_on_arc(angle):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        return (x, y, arc_height)

    target = (0.0, 0.0, 1.0)

    # ============================================================
    # 統合カメラキーフレーム生成（angleはフレーム位置ベースで計算）
    # ============================================================
    zoom_start_frame = cut1_start + int(cut1_length * 0.85)
    zoom_end_frame = cut1_end

    # すべてのキーフレームを24フレームごとに一様に配置
    all_keyframes = list(range(cut1_start, cut1_end + 1, keyframe_interval))
    if all_keyframes[-1] != cut1_end:
        all_keyframes.append(cut1_end)

    final_cam_pos = None
    final_rot = None

    for frame in all_keyframes:
        # 角度: フレーム位置ベースで計算（index順序に依存せずスムーズ）
        frame_progress = (frame - cut1_start) / cut1_length if cut1_length > 0 else 0
        angle = start_angle + total_rotation_scaled * frame_progress

        # ズーム区間内か判定
        if zoom_start_frame <= frame <= zoom_end_frame:
            zoom_progress = (frame - zoom_start_frame) / (zoom_end_frame - zoom_start_frame + 1)
            current_radius = arc_radius * (1.0 - 0.2 * zoom_progress)
            current_height = arc_height * (1.0 - 0.15 * zoom_progress)
            x = current_radius * math.sin(angle)
            y = current_radius * math.cos(angle)
            cam_pos = (x, y, current_height)
        else:
            cam_pos = get_cam_on_arc(angle)

        # matrix_world→quaternionでキーフレーム設定（ジンバルロック回避）
        _set_camera_keyframe(camera, frame, cam_pos, target)

        final_cam_pos = cam_pos
        final_rot = camera.rotation_quaternion.copy()

    if zoom_start_frame <= cut1_end:
        print(f"  [fr{zoom_start_frame}-{zoom_end_frame}] カメラズームイン追加 (半径100%→80%)")

    print(f"  [fr{cut1_start}-{cut1_end}] charA: {char_a_start} → {char_a_end}")
    print(f"  [fr{cut1_start}-{cut1_end}] charB: {char_b_start} → {char_b_end}")
    print(f"  [fr{cut1_end}] カメラパンニング完了: {math.degrees(total_rotation_scaled):.1f}°回転")

    return {
        'camera_loc': final_cam_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }


def _interpolate_char_position(start_pos, end_pos, progress):
    """キャラクターの位置を補間するヘルパー関数"""
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    z = start_pos[2] + (end_pos[2] - start_pos[2]) * progress
    return (x, y, z)


def setup_cut2_phase_a_topdown(camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end, cut1_final_cam, strategy_config=None, cut_frames=None):
    """
    カット2 フェーズA: トップダウンビューへ移動 + キャラクターは中央で静止。

    カメラ: カット1終了位置 → バリエーション設定に基づくトップダウン位置
    キャラクター: 中央集合位置で静止（フェーズBでスライド開始）

    Parameters:
        cut1_final_cam: カット1終了時のカメラ位置 (x, y, z)
        cut_frames: dict with keys cut2a_start, cut2a_end (None時はデフォルト値を使用)

    Returns:
        dict: フェーズA終了時のカメラ情報
    """
    # フレーム値を取得
    cut2a_start = cut_frames.get("cut2a_start", DEFAULT_CUT_FRAMES["cut2a_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_start"]
    cut2a_end = cut_frames.get("cut2a_end", DEFAULT_CUT_FRAMES["cut2a_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_end"]

    print(f"\n  === カット2 フェーズA: トップダウンビューへ移動 + キャラクター中央静止 (fr{cut2a_start}-{cut2a_end}, イージング) ===")

    # バリエーション設定からトップダウン位置を取得（cam_scale適用）
    cam_scale_td = strategy_config.get("cam_scale", 1.0) if strategy_config else 1.0
    if strategy_config and "topdown_variation" in strategy_config:
        raw_td = strategy_config["topdown_variation"]["position"]
        # raw位置にcam_scaleを適用
        top_down_pos = (raw_td[0] * cam_scale_td, raw_td[1] * cam_scale_td, raw_td[2] * cam_scale_td)
        print(f"  トップダウン変形: {strategy_config['topdown_variation']['name']} → raw={raw_td}, scaled={top_down_pos}")
    else:
        # スケール適用後のデフォルトトップダウン位置
        td_z = strategy_config.get("topdown_height", 8.0) if strategy_config else 8.0
        top_down_pos = (0.0, 0.0, td_z)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 8  # 24→8に狭めてカメラ回転を滑らかに

    # cut2a_startで明確なカメラキーフレームを設定（前回の残骸とのgapを防止）
    _set_camera_keyframe(camera, cut2a_start, cut1_final_cam, target)

    # カメラのキーフレーム
    phase_a_frames = list(range(cut2a_start, cut2a_end + 1, keyframe_interval))
    if phase_a_frames[-1] != cut2a_end:
        phase_a_frames.append(cut2a_end)
    num_segments = len(phase_a_frames) - 1

    for i, frame in enumerate(phase_a_frames):
        # カメラの補間（イージング適用）
        raw_progress = i / num_segments if num_segments > 0 else 0
        cam_progress = ease_func(raw_progress)
        cam_x = cut1_final_cam[0] + (top_down_pos[0] - cut1_final_cam[0]) * cam_progress
        cam_y = cut1_final_cam[1] + (top_down_pos[1] - cut1_final_cam[1]) * cam_progress
        cam_z = cut1_final_cam[2] + (top_down_pos[2] - cut1_final_cam[2]) * cam_progress
        cam_pos = (cam_x, cam_y, cam_z)
        # matrix_world→quaternionでキーフレーム設定（ジンバルロック回避）
        _set_camera_keyframe(camera, frame, cam_pos, target)

        # キャラクターは中央集合位置で静止（重なったまま）
        _set_location_keyframe(char_a, frame, char_a_end[0], char_a_end[1], char_a_end[2])
        _set_location_keyframe(char_b, frame, char_b_end[0], char_b_end[1], char_b_end[2])

    print(f"  [fr{cut2a_start}-{cut2a_end}] カメラ: {cut1_final_cam} → {top_down_pos}")
    print(f"  キャラクター: 中央集合位置で静止（フェーズBでスライド開始）")

    return {'camera_loc': top_down_pos}


def setup_cut2_phase_b_camera_return(camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end, strategy_config=None, cut_frames=None):
    """
    カット2 フェーズB: カメラ開始位置へ復帰 + CharB不透明化 + キャラクターズスライド。

    カメラ: トップダウン位置 → バリエーション設定に基づく復帰位置
    キャラクター: 中央集合位置からカット1開始位置へスライド開始 → cut2b_endで到達

    Parameters:
        strategy_config: バリエーション設定辞書（オプション）
        cut_frames: dict with keys cut2b_start, cut2b_end (None時はデフォルト値を使用)

    Returns:
        dict: フェーズB終了時のカメラ情報
    """
    # フレーム値を取得
    cut2b_start = cut_frames.get("cut2b_start", DEFAULT_CUT_FRAMES["cut2b_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_start"]
    cut2b_end = cut_frames.get("cut2b_end", DEFAULT_CUT_FRAMES["cut2b_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_end"]

    print(f"\n  === カット2 フェーズB: カメラ開始位置へ復帰 + キャラクターズスライド (fr{cut2b_start}-{cut2b_end}, イージング) ===")

    # バリエーション設定から復帰カメラ位置を取得（cam_scale適用）
    cam_scale_b = strategy_config.get("cam_scale", 1.0) if strategy_config else 1.0
    if strategy_config and "camera_pattern" in strategy_config:
        raw_return = strategy_config["camera_pattern"]["start_position"]
        cam_return_x = raw_return[0] * cam_scale_b
        cam_return_y = raw_return[1] * cam_scale_b
        cam_return_z = raw_return[2] * min(cam_scale_b, 2.0)
        cam_return_pos = (cam_return_x, cam_return_y, cam_return_z)
        print(f"  カメラ復帰先: raw={raw_return}, scaled={cam_return_pos}")
    else:
        # スケール適用後のデフォルトカメラ復帰位置
        cr_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cr_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cr_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_return_pos = (cr_x, cr_y, cr_z)

    # トップダウン位置もバリエーションから取得（cam_scale適用）
    if strategy_config and "topdown_variation" in strategy_config:
        raw_td_b = strategy_config["topdown_variation"]["position"]
        top_down_pos = (raw_td_b[0] * cam_scale_b, raw_td_b[1] * cam_scale_b, raw_td_b[2] * cam_scale_b)
    else:
        td_z = strategy_config.get("topdown_height", 8.0) if strategy_config else 8.0
        top_down_pos = (0.0, 0.0, td_z)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 8  # 24→8に狭めてカメラ回転を滑らかに

    # キャラクターのスライドはフェーズBのみで進行
    total_slide_frames = cut2b_end - cut2b_start + 1

    phase_b_frames = list(range(cut2b_start, cut2b_end + 1, keyframe_interval))
    if phase_b_frames[-1] != cut2b_end:
        phase_b_frames.append(cut2b_end)
    num_segments = len(phase_b_frames) - 1

    for i, frame in enumerate(phase_b_frames):
        # カメラの補間（イージング適用）
        raw_progress = i / num_segments if num_segments > 0 else 0
        cam_progress = ease_func(raw_progress)
        cam_x = top_down_pos[0] + (cam_return_pos[0] - top_down_pos[0]) * cam_progress
        cam_y = top_down_pos[1] + (cam_return_pos[1] - top_down_pos[1]) * cam_progress
        cam_z = top_down_pos[2] + (cam_return_pos[2] - top_down_pos[2]) * cam_progress
        cam_pos = (cam_x, cam_y, cam_z)
        # matrix_world→quaternionでキーフレーム設定（ジンバルロック回避）
        _set_camera_keyframe(camera, frame, cam_pos, target)

        # キャラクターのスライド進行度（イージング適用）
        raw_char_progress = (frame - cut2b_start) / total_slide_frames
        char_progress = ease_func(raw_char_progress)

        char_a_pos = _interpolate_char_position(char_a_end, char_a_start, char_progress)
        char_b_pos = _interpolate_char_position(char_b_end, char_b_start, char_progress)

        _set_location_keyframe(char_a, frame, char_a_pos[0], char_a_pos[1], char_a_pos[2])
        _set_location_keyframe(char_b, frame, char_b_pos[0], char_b_pos[1], char_b_pos[2])

    # 終了フレームを確実に設定（キャラクターが完全にスタート位置に戻っていることを保証）
    _set_location_keyframe(char_a, cut2b_end, char_a_start[0], char_a_start[1], char_a_start[2])
    _set_location_keyframe(char_b, cut2b_end, char_b_start[0], char_b_start[1], char_b_start[2])

    # 最終カメラ位置を設定（キーフレームはループで設定済み）
    set_camera_look_at(camera, cam_return_pos, target)

    print(f"  [fr{cut2b_start}-{cut2b_end}] カメラ: {top_down_pos} → {cam_return_pos}")
    print(f"  キャラクター: スライド完了 → charA={char_a_start}, charB={char_b_start}")

    return {
        'camera_loc': cam_return_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }
