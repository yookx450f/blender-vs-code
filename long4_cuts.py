"""
Long4 - カメラ円弧等速360°一周 + 新車アニメーション モジュール（横長16:9）

fr0-total_framesで、カメラは円弧上をZサイン波で360°一周し、起始位置へ戻る。
車のアニメーション：分離→中央スライド→半透明→不透明化→分離位置へスライド。

総フレーム数はランダムに 576-672 の範囲で変動（約24-28秒）。
すべてのフレーム位置は total_frames に対する割合で計算される。

使い方の例:
    from long4_cuts import setup_arc_full_circle, reset_camera_quat_state
"""

import bpy
import math
from animation_common import set_camera_look_at, _set_camera_keyframe
from short2_utils import (
    _set_location_keyframe,
    _set_rotation_keyframe,
    _set_camera_location_keyframe,
)


# カメラ位置の制限範囲（メートル）
CAMERA_LOCATION_MAX = 12.0

# 前回のカメラクォータニオンを保持（符号統一用）
_last_camera_quat = None

def reset_camera_quat_state():
    """_last_camera_quat をリセット（各実行开始时に呼ぶ）"""
    global _last_camera_quat
    _last_camera_quat = None


def _set_camera_keyframes_to_linear(cam, frame):
    """カメラの location + rotation_quaternion キーフレームを LINEAR に設定"""
    if not cam.animation_data or not cam.animation_data.action:
        return

    action = cam.animation_data.action

    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            if 'location' in fc.data_path or 'rotation_quaternion' in fc.data_path:
                for kf in fc.keyframe_points:
                    if abs(kf.co.x - frame) < 0.1:
                        kf.interpolation = 'LINEAR'
        return

    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type == 'KEYFRAME':
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            if 'location' in fc.data_path or 'rotation_quaternion' in fc.data_path:
                                for kf in fc.keyframe_points:
                                    if abs(kf.co.x - frame) < 0.1:
                                        kf.interpolation = 'LINEAR'


def _clamp_camera_location(x, y, z):
    """カメラの位置を安全な範囲内に制限する"""
    cx = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, x))
    cy = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, y))
    cz = max(0.1, min(CAMERA_LOCATION_MAX, z))

    if abs(cx - x) > 1.0 or abs(cy - y) > 1.0 or abs(cz - z) > 1.0:
        print(f"    ⚠ カメラ位置クランプ: ({x:.2f}, {y:.2f}, {z:.2f}) -> ({cx:.2f}, {cy:.2f}, {cz:.2f})")

    return (cx, cy, cz)


def _set_camera_position_and_rotation_keyframe(cam, target_name, frame, cam_pos, tgt_pos):
    """LookAt計算でカメラの向きを直接設定してキーフレーム記録する"""
    from mathutils import Vector

    global _last_camera_quat

    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)

    # カメラ位置を安全な範囲にクランプ
    clamped_pos = _clamp_camera_location(cam_pos[0], cam_pos[1], cam_pos[2])

    # CameraTargetの位置を設定
    if target_name in bpy.data.objects:
        tgt = bpy.data.objects[target_name]
        tgt.location = (tgt_pos[0], tgt_pos[1], tgt_pos[2])

    # カメラの位置を設定（クランプ後の値を使用）
    cam.location = Vector(clamped_pos)

    # LookAt計算: カメラの-Z軸がtargetを向くように回転quaternionを算出
    camera_loc = Vector(clamped_pos)
    target_loc = Vector(tgt_pos)
    direction = target_loc - camera_loc

    if direction.length < 0.001:
        pass
    else:
        track_quat = direction.normalized().to_track_quat('-Z', 'Y')

        # quaternion符号統一
        if _last_camera_quat is not None:
            dot = track_quat.dot(_last_camera_quat)
            if dot < 0:
                track_quat = -track_quat

        _last_camera_quat = track_quat.copy()

        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = track_quat

    # キーフレームとして記録
    if cam.animation_data is None:
        cam.animation_data_create()

    for i in range(3):
        cam.keyframe_insert(data_path="location", index=i)

    for i in range(4):
        cam.keyframe_insert(data_path="rotation_quaternion", index=i)

    _set_camera_keyframes_to_linear(cam, frame)

    bpy.context.scene.frame_set(current_frame)


def _interpolate_car_position(start_pos, end_pos, progress):
    """車の位置を補間するヘルパー関数"""
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    z = start_pos[2] + (end_pos[2] - start_pos[2]) * progress
    return (x, y, z)


def _get_easing_func(strategy_config=None):
    """イージング関数を取得（車のスライド用）"""
    def _ease_in_out_cubic(t):
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            return 1.0 - (-2.0 * t + 2.0)**3 / 2.0
    return _ease_in_out_cubic


def setup_arc_full_circle(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, strategy_config=None, total_frames=624):
    """
    fr0-fr{total_frames}全体: カメラ円弧等速360°一周 + 新車アニメーション（横長版）。

    カメラ: 起始角度から負方向に360°一周（等速・LINEAR補間）。
            Z座標はサイン波 (fr0=z_min → fr{total_frames/2}=z_max → fr{total_frames}=z_min)。

    車: 新しいアニメーションロジック
      fr0-slide_end: 左右分離→中央へスライド（イージング付き）
      fade_out_phase1_start-fade_out_phase1_end: 透明度段階1 (Alpha 1.0→0.5)
      fade_out_phase2_end: 透明度段階2 (Alpha 0.5→0.4)
      restore_phase1_start-restore_phase1_end: 不透明化段階1 (Alpha 0.4→0.5)
      restore_phase2_end: 不透明化段階2 (Alpha 0.5→1.0)
      slide_start_frame-slide_out_end: 不透明で中央→左右分離位置へゆっくりスライド

    各フレーム位置は total_frames に対する割合で計算される（624を基準）。

    Parameters:
        camera: カメラオブジェクト
        car_a, car_b: 車のオブジェクト
        car_a_start, car_b_start: 車の開始位置（左右に開いた位置）
        car_a_end, car_b_end: 車の終了位置（中央集合位置）
        strategy_config: スケール情報を含む辞書
        total_frames: 総フレーム数（デフォルト624、ランダム化可能。約24-28秒）

    Returns:
        dict: 終了時の状態情報 (camera_loc, camera_rot)
    """
    print(f"\n=== Long4 アニメーション: カメラ円弧等速360°一周（fr{total_frames}完了）+ 新車アニメーション (fr0-{total_frames}) ===")

    # ============================================================
    # --- カメラ: fr0-fr{total_frames} で等速360°一周 ---
    # ============================================================
    if strategy_config and "camera_pattern" in strategy_config:
        cam_pattern = strategy_config["camera_pattern"]
        cam_start = tuple(cam_pattern["start_position"])
    else:
        cam_start_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cam_start_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cam_start_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_start = (cam_start_x, cam_start_y, cam_start_z)

    arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
    arc_radius = min(arc_radius, CAMERA_LOCATION_MAX)
    arc_height = cam_start[2]
    start_angle = math.atan2(cam_start[0], cam_start[1])

    print(f"  円弧パラメータ: radius={arc_radius:.2f}, height={arc_height:.2f}")
    print(f"  起始角度: {math.degrees(start_angle):.1f}°")
    print(f"  回転方向: 負方向（時計回り）, 一周 = -360°")

    # Z高さパラメータ
    z_min = 1.2   # 開始/終了位置のZ高さ
    z_max = 10.0  # 180°地点の最大Z高さ
    z_amplitude = z_max - z_min  # 8.8m

    def get_cam_on_arc(angle, progress):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        # Z高さ: 最初の1秒(fr0-fr24)はZ=z_min固定、fr25以降はサイン波
        fixed_z_progress = 24.0 / total_frames if total_frames > 0 else 0.0385
        if progress <= fixed_z_progress:
            z = z_min
        else:
            # fr25以降: サイン波にスムーズにつなげる（progressをシフト）
            shifted_progress = (progress - fixed_z_progress) / (1.0 - fixed_z_progress)
            z = z_min + z_amplitude * math.sin(shifted_progress * math.pi)
        return (x, y, z)

    target = (0.0, 0.0, 1.0)
    keyframe_interval_cam = 1  # カメラはフレームごとに設定（滑らかな円弧）
    keyframe_interval_car = 12  # 車は0.5秒ごとで十分

    all_cam_frames = list(range(0, total_frames + 1, keyframe_interval_cam))
    if all_cam_frames[-1] != total_frames:
        all_cam_frames.append(total_frames)

    rotation_end_frame = total_frames  # fr{total_frames}で360°完了
    for frame in all_cam_frames:
        progress = frame / rotation_end_frame if rotation_end_frame > 0 else 0
        # 負方向に360°一周（-2π）
        angle = start_angle - (2 * math.pi * progress)
        cam_pos = get_cam_on_arc(angle, progress)

        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

    final_cam_pos = get_cam_on_arc(start_angle - 2 * math.pi, 1.0)
    print(f"  [fr0-{total_frames}] カメラ: {cam_start} → {final_cam_pos} (等速360°一周、Z={z_min:.1f}→{z_max:.1f}→{z_min:.1f})")

    # ============================================================
    # --- 車: total_framesに対する割合でフレーム位置を計算 ---
    # ============================================================
    # 基準フレーム数624に対する割合で各フェーズの開始・終了フレームを計算
    BASE_FRAMES = 624  # 基準となる総フレーム数（横長版=約26秒）

    slide_to_center_end = int(total_frames * 72 / BASE_FRAMES)       # 中央へスライド完了（short4の36×2）
    fade_out_phase1_start = int(total_frames * 80 / BASE_FRAMES)   # 半透明化第一阶段開始（透明度用）
    fade_out_phase1_end = int(total_frames * 96 / BASE_FRAMES)     # Alpha=0.5（透明度用）
    fade_out_phase2_end = int(total_frames * 112 / BASE_FRAMES)    # Alpha=0.4（透明度用）
    restore_phase1_start = int(total_frames * 360 / BASE_FRAMES)   # 不透明化第一阶段開始（透明度用）
    restore_phase1_end = int(total_frames * 384 / BASE_FRAMES)     # Alpha=0.5（透明度用）
    restore_phase2_end = int(total_frames * 408 / BASE_FRAMES)     # Alpha=1.0（透明度用）
    slide_start_frame = int(total_frames * 409 / BASE_FRAMES)      # 中央→分離位置へスライド開始
    slide_out_end = total_frames                                   # 分離位置で終了

    print(f"  フレーム配置 (total_frames={total_frames}): slide_in~fr{slide_to_center_end}, "
          f"半透明化fr{fade_out_phase1_start}-{fade_out_phase2_end}, "
          f"不透明化fr{restore_phase1_start}-{restore_phase2_end}, "
          f"slide_out fr{slide_start_frame}-{slide_out_end}")

    ease_func = _get_easing_func(strategy_config)

    # fr0: 開始位置で左右に分離
    _set_location_keyframe(car_a, 0, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, 0, car_b_start[0], car_b_start[1], car_b_start[2])

    print(f"  [fr0] 開始位置で分離: carA={car_a_start}, carB={car_b_start}")

    # fr0-slide_to_center_end: 分離→中央へスライド（イージング付き）
    for frame in range(1, slide_to_center_end + 1, keyframe_interval_car):
        raw_progress = max(0, (frame - 0) / slide_to_center_end)
        progress = ease_func(raw_progress)

        car_a_pos = _interpolate_car_position(car_a_start, car_a_end, progress)
        car_b_pos = _interpolate_car_position(car_b_start, car_b_end, progress)

        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # slide_to_center_end: 中央で重なり（スライド完了）
    _set_location_keyframe(car_a, slide_to_center_end, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, slide_to_center_end, car_b_end[0], car_b_end[1], car_b_end[2])
    print(f"  [fr{slide_to_center_end}] 中央スライド完了: carA={car_a_end}, carB={car_b_end}")

    # 中央位置で静止（透明度変化は animation_settings_long4.py / animation_common.py で処理）
    for frame in range(slide_to_center_end + keyframe_interval_car, slide_start_frame, keyframe_interval_car):
        _set_location_keyframe(car_a, frame, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, frame, car_b_end[0], car_b_end[1], car_b_end[2])
    print(f"  [fr{slide_to_center_end}-{slide_start_frame-1}] 中央位置で静止（半透明→不透明化）")

    # slide_start_frame-slide_out_end: 中央→分離位置へゆっくりスライド（イージング付き）
    slide_frames_count = slide_out_end - slide_start_frame + 1
    for frame in range(slide_start_frame, slide_out_end + 1, keyframe_interval_car):
        raw_progress = max(0, (frame - slide_start_frame) / slide_frames_count)
        progress = ease_func(raw_progress)

        car_a_pos = _interpolate_car_position(car_a_end, car_a_start, progress)
        car_b_pos = _interpolate_car_position(car_b_end, car_b_start, progress)

        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # fr{total_frames}: 分離位置で終了（確実に設定）
    _set_location_keyframe(car_a, total_frames, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, total_frames, car_b_start[0], car_b_start[1], car_b_start[2])
    print(f"  [fr{slide_start_frame}-{total_frames}] 中央→分離位置へスライド（不透明、約{slide_frames_count/24:.1f}秒）")

    return {
        'camera_loc': final_cam_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }
