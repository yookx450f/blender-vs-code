"""
Short2 - カット1・カット2 の位置アニメーションモジュール

各カットごとのカメラ・車の位置キーフレームを設定する。
カッは完全に分離されており、独立して動作する。

フレーム定義 (24fps):
  カット1: fr0-288 (約12秒) — 車が中央へスライド + 円弧パンニング
  カット2A: fr289-456 (7秒) — トップダウンビューへ移動 (イージング) + 車スライド開始
  カット2B: fr457-624 (7秒) — カメラ復帰 (イージング) + CarB不透明化 + 車スライド完了

使い方:
    from short2_cuts import (
        setup_cut1_overlap,
        setup_cut2_phase_a_topdown,
        setup_cut2_phase_b_camera_return,
    )
"""

import math
from animation_common import set_camera_look_at
from short2_utils import (
    _set_location_keyframe,
    _set_rotation_keyframe,
    _set_camera_location_keyframe,
)


# ============================================================
# フレーム定義（24fps）— 全カットで共通
# ============================================================
CUT1_START = 0
CUT1_END = 288

CUT2A_START = 289
CUT2A_END = 456  # 7秒 (168フレーム)

CUT2B_START = 457
CUT2B_END = 624  # 7秒 (168フレーム)


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


def setup_cut1_overlap(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, strategy_config=None):
    """
    カット1 (fr0-288, 約12秒): 車が中央へスライド + 円弧パンニング。

    CarA: (-1.25, rear_offset_y) → 中央集合位置
    CarB: (1.25, 0.0) → 中央集合位置
    カメラ: バリエーション設定に基づく円弧パンニング
     
    Returns:
        dict: カット1終了時の状態情報 (camera_loc, camera_rot)
    """
    print("\n  === カット1: 車中央スライド + 円弧パンニング (fr0-288) ===")

    # --- 車のアニメーション ---
    # フレーム 0: スタート位置
    _set_location_keyframe(car_a, CUT1_START, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, CUT1_START, car_b_start[0], car_b_start[1], car_b_start[2])

    # フレーム 120: 中央集合完了（5秒かけてスライド）
    _set_location_keyframe(car_a, 120, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, 120, car_b_end[0], car_b_end[1], car_b_end[2])

    # フレーム 144: 中央位置維持
    _set_location_keyframe(car_a, 144, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, 144, car_b_end[0], car_b_end[1], car_b_end[2])

    # フレーム 168-288: 中央位置維持（1秒ごと）
    keyframe_interval = 24
    for frame in range(168, CUT1_END + 1, keyframe_interval):
        _set_location_keyframe(car_a, frame, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, frame, car_b_end[0], car_b_end[1], car_b_end[2])

    # カット1終了フレームも確実に設定
    if CUT1_END not in range(168, CUT1_END + 1, keyframe_interval):
        _set_location_keyframe(car_a, CUT1_END, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, CUT1_END, car_b_end[0], car_b_end[1], car_b_end[2])

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
    total_rotation = total_rotation * (CUT1_END / 144)

    def get_cam_on_arc(angle):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        return (x, y, arc_height)

    target = (0.0, 0.0, 1.0)

    cut1_keyframes = list(range(CUT1_START, CUT1_END + 1, keyframe_interval))
    if cut1_keyframes[-1] != CUT1_END:
        cut1_keyframes.append(CUT1_END)
    num_segments = len(cut1_keyframes) - 1

    for i, frame in enumerate(cut1_keyframes):
        progress = i / num_segments if num_segments > 0 else 0
        angle = start_angle + total_rotation * progress
        cam_pos = get_cam_on_arc(angle)
        set_camera_look_at(camera, cam_pos, target)
        rot = camera.rotation_euler.copy()
        _set_camera_location_keyframe(camera, frame, cam_pos)
        _set_rotation_keyframe(camera, frame, rot)

    # 最終カメラ位置を計算
    final_angle = start_angle + total_rotation
    final_cam = get_cam_on_arc(final_angle)
    set_camera_look_at(camera, final_cam, target)
    final_rot = camera.rotation_euler.copy()

    # ============================================================
    # A案: カット1終盤にカメラズームインを追加（fr264-fr288）
    # 視聴者が「止まった」と感じないよう、緩やかな動きを追加
    # ============================================================
    zoom_start_frame = 264
    zoom_end_frame = CUT1_END  # 288
    zoom_frames = list(range(zoom_start_frame, zoom_end_frame + 1, 12))  # 0.5秒ごと
    if zoom_frames[-1] != zoom_end_frame:
        zoom_frames.append(zoom_end_frame)
    
    # カメラを徐々に近づける（半径を80%まで縮小）
    for i, frame in enumerate(zoom_frames):
        progress = i / (len(zoom_frames) - 1) if len(zoom_frames) > 1 else 0
        current_radius = arc_radius * (1.0 - 0.2 * progress)  # 100% → 80%
        angle_at_frame = start_angle + total_rotation * ((frame - CUT1_START) / CUT1_END)
        x = current_radius * math.sin(angle_at_frame)
        y = current_radius * math.cos(angle_at_frame)
        cam_pos_zoom = (x, y, arc_height * (1.0 - 0.15 * progress))  # 높이는 100% → 85%
        set_camera_look_at(camera, cam_pos_zoom, target)
        rot_zoom = camera.rotation_euler.copy()
        _set_camera_location_keyframe(camera, frame, cam_pos_zoom)
        _set_rotation_keyframe(camera, frame, rot_zoom)
    
    # fr288에서도 최종 위치 업데이트
    final_cam_zoomed = zoom_frames and (zoom_frames[-1] == zoom_end_frame) and cam_pos_zoom or final_cam
    if zoom_frames:
        final_cam = zoom_frames and cam_pos_zoom or final_cam
    
    print(f"  [fr{zoom_start_frame}-{zoom_end_frame}] 카메라 줌인 추가 (반경 100%→80%)")
    print(f"  [fr{CUT1_START}-{CUT1_END}] carA: {car_a_start} → {car_a_end}")
    print(f"  [fr{CUT1_START}-{CUT1_END}] carB: {car_b_start} → {car_b_end}")
    print(f"  [fr{CUT1_END}] カメラパンニング完了: {math.degrees(total_rotation):.1f}°回転")

    return {
        'camera_loc': final_cam,
        'camera_rot': (final_rot.x, final_rot.y, final_rot.z),
    }


def _interpolate_car_position(start_pos, end_pos, progress):
    """車の位置を補間するヘルパー関数"""
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    z = start_pos[2] + (end_pos[2] - start_pos[2]) * progress
    return (x, y, z)


def setup_cut2_phase_a_topdown(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, cut1_final_cam, strategy_config=None):
    """
    カット2 フェーズA (fr289-456, 7秒): トップダウンビューへ移動 + 車は中央で静止。

    カメラ: カット1終了位置 → バリエーション設定に基づくトップダウン位置
    車: 中央集合位置で静止（フェーズBでスライド開始）
    
    Parameters:
        car_a_start: CarAのカット1開始位置（戻す先）
        car_a_end: CarAの中央集合位置（現在の位置）
        car_b_start: CarBのカット1開始位置（戻す先）
        car_b_end: CarBの中央集合位置（現在の位置）
        strategy_config: バリエーション設定辞書（オプション）

    Returns:
        dict: フェーズA終了時のカメラ情報
    """
    print("\n  === カット2 フェーズA: トップダウンビューへ移動 + 車中央静止 (fr289-456, イージング) ===")

    # バリエーション設定からトップダウン位置を取得
    if strategy_config and "topdown_variation" in strategy_config:
        top_down_pos = tuple(strategy_config["topdown_variation"]["position"])
        print(f"  トップダウン変形: {strategy_config['topdown_variation']['name']} → {top_down_pos}")
    else:
        top_down_pos = (0.0, 0.0, 8.0)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 24

    # カメラのキーフレーム
    phase_a_frames = list(range(CUT2A_START, CUT2A_END + 1, keyframe_interval))
    if phase_a_frames[-1] != CUT2A_END:
        phase_a_frames.append(CUT2A_END)
    num_segments = len(phase_a_frames) - 1

    for i, frame in enumerate(phase_a_frames):
        # カメラの補間（イージング適用）
        raw_progress = i / num_segments if num_segments > 0 else 0
        cam_progress = ease_func(raw_progress)
        cam_x = cut1_final_cam[0] + (top_down_pos[0] - cut1_final_cam[0]) * cam_progress
        cam_y = cut1_final_cam[1] + (top_down_pos[1] - cut1_final_cam[1]) * cam_progress
        cam_z = cut1_final_cam[2] + (top_down_pos[2] - cut1_final_cam[2]) * cam_progress
        cam_pos = (cam_x, cam_y, cam_z)
        set_camera_look_at(camera, cam_pos, target)
        rot = camera.rotation_euler.copy()
        _set_camera_location_keyframe(camera, frame, cam_pos)
        _set_rotation_keyframe(camera, frame, rot)

        # 車は中央集合位置で静止（重なったまま）
        _set_location_keyframe(car_a, frame, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, frame, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"  [fr{CUT2A_START}-{CUT2A_END}] カメラ: {cut1_final_cam} → {top_down_pos}")
    print(f"  車: 中央集合位置で静止（フェーズBでスライド開始）")

    return {'camera_loc': top_down_pos}


def setup_cut2_phase_b_camera_return(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, strategy_config=None):
    """
    カット2 フェーズB (fr457-624, 7秒): カメラ開始位置へ復帰 + CarB不透明化 + 車スライド。

    カメラ: トップダウン位置 → バリエーション設定に基づく復帰位置
    車: 中央集合位置からカット1開始位置へスライド開始 → fr624で到達
    
    Parameters:
        car_a_start: CarAのカット1開始位置（戻す先）
        car_a_end: CarAの中央集合位置（現在の位置）
        car_b_start: CarBのカット1開始位置（戻す先）
        car_b_end: CarBの中央集合位置（現在の位置）
        strategy_config: バリエーション設定辞書（オプション）
    
    Returns:
        dict: フェーズB終了時のカメラ情報
    """
    print("\n  === カット2 フェーズB: カメラ開始位置へ復帰 + 車スライド (fr457-624, イージング) ===")

    # バリエーション設定から復帰カメラ位置を取得
    if strategy_config and "camera_pattern" in strategy_config:
        cam_return_pos = tuple(strategy_config["camera_pattern"]["start_position"])
        print(f"  カメラ復帰先: {cam_return_pos}")
    else:
        cam_return_pos = (-3.0, -6.0, 3.5)

    # トップダウン位置もバリエーションから取得
    if strategy_config and "topdown_variation" in strategy_config:
        top_down_pos = tuple(strategy_config["topdown_variation"]["position"])
    else:
        top_down_pos = (0.0, 0.0, 8.0)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 24

    # 車のスライドはフェーズBのみで進行 (fr457-fr624 = 168フレーム = 7秒)
    total_slide_frames = CUT2B_END - CUT2B_START + 1

    phase_b_frames = list(range(CUT2B_START, CUT2B_END + 1, keyframe_interval))
    if phase_b_frames[-1] != CUT2B_END:
        phase_b_frames.append(CUT2B_END)
    num_segments = len(phase_b_frames) - 1

    for i, frame in enumerate(phase_b_frames):
        # カメラの補間（イージング適用）
        raw_progress = i / num_segments if num_segments > 0 else 0
        cam_progress = ease_func(raw_progress)
        cam_x = top_down_pos[0] + (cam_return_pos[0] - top_down_pos[0]) * cam_progress
        cam_y = top_down_pos[1] + (cam_return_pos[1] - top_down_pos[1]) * cam_progress
        cam_z = top_down_pos[2] + (cam_return_pos[2] - top_down_pos[2]) * cam_progress
        cam_pos = (cam_x, cam_y, cam_z)
        set_camera_look_at(camera, cam_pos, target)
        rot = camera.rotation_euler.copy()
        _set_camera_location_keyframe(camera, frame, cam_pos)
        _set_rotation_keyframe(camera, frame, rot)

        # 車のスライド進行度 (フェーズB fr457-fr624 に対する位置)（イージング適用）
        raw_car_progress = (frame - CUT2B_START) / total_slide_frames
        car_progress = ease_func(raw_car_progress)
        
        car_a_pos = _interpolate_car_position(car_a_end, car_a_start, car_progress)
        car_b_pos = _interpolate_car_position(car_b_end, car_b_start, car_progress)
        
        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # 終了フレームを確実に設定（車が完全にスタート位置に戻っていることを保証）
    _set_location_keyframe(car_a, CUT2B_END, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, CUT2B_END, car_b_start[0], car_b_start[1], car_b_start[2])

    # 最終カメラ位置を設定
    set_camera_look_at(camera, cam_return_pos, target)
    final_rot = camera.rotation_euler.copy()

    print(f"  [fr{CUT2B_START}-{CUT2B_END}] カメラ: {top_down_pos} → {cam_return_pos}")
    print(f"  車: スライド完了 → carA={car_a_start}, carB={car_b_start}")

    return {
        'camera_loc': cam_return_pos,
        'camera_rot': (final_rot.x, final_rot.y, final_rot.z),
    }
