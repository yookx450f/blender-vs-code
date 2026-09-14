"""
ShortGame - カット1・カット2 の位置アニメーションモジュール

各カットごとのカメラ・キャラクターの位置キーフレームを設定する。
カッは完全に分離されており、独立して動作する。

フレーム定義 (24fps):
  カット1: fr0-288 (約12秒) — キャラクターが中央へスライド + 円弧パンニング
  カット2A: fr289-456 (7秒) — トップダウンビューへ移動 (イージング) + キャラクターズスライド開始
  カット2B: fr457-624 (7秒) — カメラ復帰 (イージング) + CarB不透明化 + キャラクターズスライド完了

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
    if strategy_config and "camera_pattern" in strategy_config:
        cam_pattern = strategy_config["camera_pattern"]
        cam_start = tuple(cam_pattern["start_position"])
        total_rotation = cam_pattern["total_rotation"]
        print(f"  カメラパターン: {cam_pattern['name']} (start={cam_start})")
    else:
        cam_start = (-3.0, -6.0, 3.5)
        total_rotation = -0.85

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
            zoom_t = (frame - zoom_start_frame) / max(1, zoom_end_frame - zoom_start_frame)
            zoom_factor = 1.0 - 0.35 * zoom_t  # 最大35%ズームイン
            adjusted_radius = arc_radius * zoom_factor
            cam_x = adjusted_radius * math.sin(angle)
            cam_y = adjusted_radius * math.cos(angle)
            cam_z = arc_height * (1.0 - 0.2 * zoom_t)  # 少し下げる
        else:
            cam_x, cam_y, cam_z = get_cam_on_arc(angle)

        cam_pos = (cam_x, cam_y, cam_z)

        # カメラの位置キーフレームを設定（制限付き）
        _set_camera_location_keyframe(camera, frame, cam_pos)

        # カメラは常にターゲットを見るように回転させる
        set_camera_look_at(camera, target)
        _set_rotation_keyframe(camera, frame, camera.rotation_euler)

        final_cam_pos = cam_pos
        final_rot = (camera.rotation_euler.x, camera.rotation_euler.y, camera.rotation_euler.z)

    print(f"  カット1完了: 最終カメラ位置={final_cam_pos}, ターゲット={target}")
    return {
        "camera_loc": final_cam_pos,
        "camera_rot": final_rot,
        "char_a_pos": char_a_end,
        "char_b_pos": char_b_end,
    }


def setup_cut2_phase_a_topdown(camera, char_a, char_b, 
                               char_a_overlap, char_b_overlap,
                               topdown_char_offset=0.6,
                               strategy_config=None, cut_frames=None):
    """
    カット2 フェーズA: トップダウンビューへの移動（イージング適用）

    Returns:
        dict: フェーズA終了時の状態情報 (camera_loc, camera_rot)
    """
    cut2a_start = cut_frames.get("cut2a_start", DEFAULT_CUT_FRAMES["cut2a_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_start"]
    cut2a_end = cut_frames.get("cut2a_end", DEFAULT_CUT_FRAMES["cut2a_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_end"]

    print(f"\n  === カット2 フェーズA: トップダウンビューへ移動 (fr{cut2a_start}-{cut2a_end}) ===")

    # イージング関数の取得
    easing = _get_easing_func(strategy_config)

    # --- カメラのトップダウンへの円弧移動 ---
    start_pos = tuple(camera.location)
    
    # キャラクターの最高部を考慮して、より高い位置から上から見下ろす（トップダウンビュー）
    topdown_target_height = 12.0  # トップダウン用高度
    topdown_radius = 2.5  # ほぼ真上
    
    # トップダウンでの半径と角度を計算
    start_angle_rad = math.atan2(start_pos[0], start_pos[1])
    end_x = topdown_radius * math.sin(start_angle_rad)
    end_y = topdown_radius * math.cos(start_angle_rad)
    
    # 回転: 真上を見るように（X軸で90度回転）
    end_rot = (math.radians(90), 0, 0)

    phase_a_duration = cut2a_end - cut2a_start + 1
    
    # --- カメラキーフレームを8フレーム間隔で設定 ---
    for frame in range(cut2a_start, cut2a_end + 1, 8):
        t = (frame - cut2a_start) / phase_a_duration if phase_a_duration > 0 else 0
        eased_t = easing(t)

        # カメラ位置を補間
        cx = start_pos[0] + (end_x - start_pos[0]) * eased_t
        cy = start_pos[1] + (end_y - start_pos[1]) * eased_t
        cz = start_pos[2] + (topdown_target_height - start_pos[2]) * eased_t

        # カメラの位置を更新
        _set_camera_location_keyframe(camera, frame, (cx, cy, cz))

        # 回転も補間（上を向くように）
        rx = start_pos[0] and camera.rotation_euler.x + (end_rot[0] - camera.rotation_euler.x) * eased_t if False else end_rot[0] * eased_t
        ry = end_rot[1] * eased_t
        rz = end_rot[2] * eased_t
        _set_rotation_keyframe(camera, frame, (rx, ry, rz))

    # 最終フレームを確実に設定
    final_cam_pos_topdown = (end_x, end_y, topdown_target_height)
    _set_camera_location_keyframe(camera, cut2a_end, final_cam_pos_topdown)
    _set_rotation_keyframe(camera, cut2a_end, end_rot)

    # --- キャラクターはフェーズAでもスライドを開始（イージング適用）---
    char_a_slide_start = tuple(char_a_overlap)
    char_b_slide_start = tuple(char_b_overlap)

    # トップダウンではキャラクターを中央から少し離す
    char_a_topdown = (char_a_overlap[0] - topdown_char_offset, char_a_overlap[1], char_a_overlap[2])
    char_b_topdown = (char_b_overlap[0] + topdown_char_offset, char_b_overlap[1], char_b_overlap[2])

    for frame in range(cut2a_start, cut2a_end + 1, 8):
        t = (frame - cut2a_start) / phase_a_duration if phase_a_duration > 0 else 0
        eased_t = easing(t)

        ax = char_a_slide_start[0] + (char_a_topdown[0] - char_a_slide_start[0]) * eased_t
        ay = char_a_slide_start[1] + (char_a_topdown[1] - char_a_slide_start[1]) * eased_t
        _set_location_keyframe(char_a, frame, ax, ay, char_a_overlap[2])

        bx = char_b_slide_start[0] + (char_b_topdown[0] - char_b_slide_start[0]) * eased_t
        by = char_b_slide_start[1] + (char_b_topdown[1] - char_b_slide_start[1]) * eased_t
        _set_location_keyframe(char_b, frame, bx, by, char_b_overlap[2])

    # 最終フレームを確実に設定
    _set_location_keyframe(char_a, cut2a_end, char_a_topdown[0], char_a_topdown[1], char_a_topdown[2])
    _set_location_keyframe(char_b, cut2a_end, char_b_topdown[0], char_b_topdown[1], char_b_topdown[2])

    print(f"  フェーズA完了: カメラ→({end_x:.2f}, {end_y:.2f}, {topdown_target_height}), 回転→{end_rot}")
    return {
        "camera_loc": final_cam_pos_topdown,
        "camera_rot": end_rot,
        "char_a_pos": char_a_topdown,
        "char_b_pos": char_b_topdown,
    }


def setup_cut2_phase_b_camera_return(camera, char_a, char_b,
                                     topdown_camera_pos, topdown_char_a_pos, topdown_char_b_pos,
                                     target_camera_height=3.5, strategy_config=None, cut_frames=None):
    """
    カット2 フェーズB: カメラを元の位置へ復帰（イージング適用）
                 + キャラクターのスライド復帰
                 + CharBの不透明化

    Returns:
        dict: フェーズB終了時の状態情報 (camera_loc, camera_rot)
    """
    cut2b_start = cut_frames.get("cut2b_start", DEFAULT_CUT_FRAMES["cut2b_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_start"]
    cut2b_end = cut_frames.get("cut2b_end", DEFAULT_CUT_FRAMES["cut2b_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_end"]

    print(f"\n  === カット2 フェーズB: カメラ復帰 + キャラクター復帰 (fr{cut2b_start}-{cut2b_end}) ===")

    # イージング関数の取得
    easing = _get_easing_func(strategy_config)

    # --- カメラの元の位置への円弧復帰 ---
    start_pos = tuple(topdown_camera_pos) if topdown_camera_pos else (0, 0, 12.0)
    
    end_angle_rad = math.atan2(start_pos[0], max(0.01, abs(start_pos[1]))) + math.pi  # 反対側へ戻る
    final_radius = 6.0
    end_x = final_radius * math.sin(end_angle_rad)
    end_y = final_radius * math.cos(end_angle_rad)
    end_z = target_camera_height
    
    end_rot = (math.radians(-30), 0, 0)  # 少し下を見る

    phase_b_duration = cut2b_end - cut2b_start + 1

    # キャラクターの最終位置（スライド復帰 = 中央より少し離れる）
    slide_back_x_a = -1.5
    slide_back_x_b = 1.5
    char_a_final = (slide_back_x_a, 0, topdown_char_a_pos[2] if topdown_char_a_pos else 0)
    char_b_final = (slide_back_x_b, 0, topdown_char_b_pos[2] if topdown_char_b_pos else 0)

    # --- カメラ復帰キーフレーム（8フレーム間隔）---
    for frame in range(cut2b_start, cut2b_end + 1, 8):
        t = (frame - cut2b_start) / phase_b_duration if phase_b_duration > 0 else 0
        eased_t = easing(t)

        # カメラ位置の補間（円弧）
        cx = start_pos[0] + (end_x - start_pos[0]) * eased_t
        cy = start_pos[1] + (end_y - start_pos[1]) * eased_t
        cz = start_pos[2] + (end_z - start_pos[2]) * eased_t

        _set_camera_location_keyframe(camera, frame, (cx, cy, cz))

        # 回転も補間
        rx = math.radians(90) + (end_rot[0] - math.radians(90)) * eased_t
        ry = end_rot[1] * eased_t
        rz = end_rot[2] * eased_t
        _set_rotation_keyframe(camera, frame, (rx, ry, rz))

    # 最終フレームを確実に設定
    final_cam_pos_return = (end_x, end_y, end_z)
    _set_camera_location_keyframe(camera, cut2b_end, final_cam_pos_return)
    _set_rotation_keyframe(camera, cut2b_end, end_rot)

    # --- キャラクターのスライド復帰（イージング）---
    char_a_start = tuple(topdown_char_a_pos) if topdown_char_a_pos else (0, 0, 0)
    char_b_start = tuple(topdown_char_b_pos) if topdown_char_b_pos else (0, 0, 0)

    for frame in range(cut2b_start, cut2b_end + 1, 8):
        t = (frame - cut2b_start) / phase_b_duration if phase_b_duration > 0 else 0
        eased_t = easing(t)

        ax = char_a_start[0] + (char_a_final[0] - char_a_start[0]) * eased_t
        _set_location_keyframe(char_a, frame, ax, char_a_final[1], char_a_final[2])

        bx = char_b_start[0] + (char_b_final[0] - char_b_start[0]) * eased_t
        _set_location_keyframe(char_b, frame, bx, char_b_final[1], char_b_final[2])

    # 最終フレームを確実に設定
    _set_location_keyframe(char_a, cut2b_end, char_a_final[0], char_a_final[1], char_a_final[2])
    _set_location_keyframe(char_b, cut2b_end, char_b_final[0], char_b_final[1], char_b_final[2])

    print(f"  フェーズB完了: カメラ→({end_x:.2f}, {end_y:.2f}, {end_z}), キャラA→{char_a_final}, キャラB→{char_b_final}")
    return {
        "camera_loc": final_cam_pos_return,
        "camera_rot": end_rot,
        "char_a_pos": char_a_final,
        "char_b_pos": char_b_final,
    }
