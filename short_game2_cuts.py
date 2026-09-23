"""
ShortGame2 - カット1 の位置アニメーションモジュール

キャラクターが中央に集合し、カメラが360度一周するシンプルな構成。
カットのみで、カット2は使用しない。

フレーム定義 (24fps):
  カット1: fr0-576 (24秒) — キャラクター中央スライド + カメラ360度円弧パンニング
  
  - fr0-120 (5秒): キャラクターが両側から中央へスライド
  - fr0-576 (24秒): カメラがキャラクター周りを360度一周

使い方:
    from short_game2_cuts import setup_cut1_360
"""

import bpy
import math
from animation_common import set_camera_look_at, _set_camera_keyframe
from short_game2_utils import (
    _set_location_keyframe,
    _set_rotation_keyframe,
    _set_camera_location_keyframe,
)


# ============================================================
# デフォルトフレーム定義（24fps）
# ============================================================
DEFAULT_CUT_FRAMES = {
    "cut1_start": 0,
    "cut1_end": 576,
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


def _clamp_camera_location(x, y, z):
    """カメラの位置を安全な範囲内に制限する"""
    CAMERA_LOCATION_MAX = 30.0
    cx = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, x))
    cy = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, y))
    cz = max(0.1, min(CAMERA_LOCATION_MAX, z))
    
    if abs(cx - x) > 1.0 or abs(cy - y) > 1.0 or abs(cz - z) > 1.0:
        print(f"    ⚠ カメラ位置クランプ: ({x:.2f}, {y:.2f}, {z:.2f}) → ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    
    return (cx, cy, cz)


# 前回のカメラクォータニオンを保持（符号統一用）
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


def reset_camera_quat_state():
    """_last_camera_quat をリセット"""
    global _last_camera_quat
    _last_camera_quat = None


def _set_camera_position_and_rotation_keyframe(cam, target_name, frame, cam_pos, tgt_pos):
    """LookAt計算でカメラの向きを直接設定してキーフレーム記録する
    
    rotation_euler → rotation_quaternion でジンバルロックを回避。
    quaternion 符号統一で最短経路補間を保証。
    """
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


def setup_cut1_360(camera, char_a, char_b, char_a_start, char_a_end, char_b_start, char_b_end, strategy_config=None, cut_frames=None):
    """
    カット1: キャラクターが中央へスライド + カメラが360度一周。

    CharA: char_a_start → 中央集合位置
    CharB: char_b_start → 中央集合位置
    カメラ: 起始位置から始めてキャラクター周りを360度円弧パンニング（一周）

    Parameters:
        cut_frames: dict with keys cut1_start, cut1_end (None時はデフォルト値を使用)

    Returns:
        dict: カット1終了時の状態情報 (camera_loc, camera_rot)
    """
    # フレーム値を取得
    cut1_start = cut_frames.get("cut1_start", DEFAULT_CUT_FRAMES["cut1_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_start"]
    cut1_end = cut_frames.get("cut1_end", DEFAULT_CUT_FRAMES["cut1_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_end"]

    print(f"\n  === カット1: キャラクター中央スライド + カメラ360度一周 (fr{cut1_start}-{cut1_end}) ===")

    # --- キャラクターのアニメーション ---
    # フレーム 0: スタート位置
    _set_location_keyframe(char_a, cut1_start, char_a_start[0], char_a_start[1], char_a_start[2])
    _set_location_keyframe(char_b, cut1_start, char_b_start[0], char_b_start[1], char_b_start[2])

    # 中央集合完了フレーム（cut1_end の約20%地点 = 5秒相当）
    slide_end_frame = cut1_start + int((cut1_end - cut1_start) * 0.20)

    # フレーム slide_end_frame: 中央集合完了
    _set_location_keyframe(char_a, slide_end_frame, char_a_end[0], char_a_end[1], char_a_end[2])
    _set_location_keyframe(char_b, slide_end_frame, char_b_end[0], char_b_end[1], char_b_end[2])

    # 位置維持キーフレーム（fr115-fr400まで - 補間の階段状を緩和）
    keyframe_interval = 12
    maintain_start = slide_end_frame + keyframe_interval
    for frame in range(maintain_start, 400 + 1, keyframe_interval):
        _set_location_keyframe(char_a, frame, char_a_end[0], char_a_end[1], char_a_end[2])
        _set_location_keyframe(char_b, frame, char_b_end[0], char_b_end[1], char_b_end[2])

    # fr400: 中央位置でキーフレーム（スライド開始点）
    _set_location_keyframe(char_a, 400, char_a_end[0], char_a_end[1], char_a_end[2])
    _set_location_keyframe(char_b, 400, char_b_end[0], char_b_end[1], char_b_end[2])

    # fr500: 元の開始位置へスライド復帰
    _set_location_keyframe(char_a, 500, char_a_start[0], char_a_start[1], char_a_start[2])
    _set_location_keyframe(char_b, 500, char_b_start[0], char_b_start[1], char_b_start[2])

    # fr500-fr576: 開始位置で維持（12フレーム間隔）
    for frame in range(500 + keyframe_interval, cut1_end + 1, keyframe_interval):
        _set_location_keyframe(char_a, frame, char_a_start[0], char_a_start[1], char_a_start[2])
        _set_location_keyframe(char_b, frame, char_b_start[0], char_b_start[1], char_b_start[2])

    # カット1終了フレームも確実に設定（開始位置を維持）
    _set_location_keyframe(char_a, cut1_end, char_a_start[0], char_a_start[1], char_a_start[2])
    _set_location_keyframe(char_b, cut1_end, char_b_start[0], char_b_start[1], char_b_start[2])

    # --- カメラ360度円弧パンニング ---
    # 動的スケーリング: strategy_config からスケール情報を取得
    scale_factor = 1.0
    cam_scale_val = 1.0
    if strategy_config and "scale_factor" in strategy_config:
        scale_factor = strategy_config["scale_factor"]
    if strategy_config and "cam_scale" in strategy_config:
        cam_scale_val = strategy_config["cam_scale"]

    # カメラ起始位置を取得（strategy_config から、なければデフォルト）
    cam_start_x = strategy_config.get("cam_start_x", -4.5) if strategy_config else -4.5
    cam_start_y = strategy_config.get("cam_start_y", -8.0) if strategy_config else -8.0
    cam_start_z = strategy_config.get("cam_start_z", 4.5) if strategy_config else 4.5
    cam_start = (cam_start_x, cam_start_y, cam_start_z)

    # 360度一周の回転量（-2π ラジアン）
    total_rotation = -math.tau
    print(f"  カメラ360度円弧パンニング: start={cam_start}, rotation={math.degrees(total_rotation):.0f}°")

    arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
    # arc_radius の安全上限
    CAMERA_LOCATION_MAX = 30.0
    max_safe_radius = CAMERA_LOCATION_MAX * 0.8
    if arc_radius > max_safe_radius:
        print(f"    ⚠ arc_radius({arc_radius:.1f}m)が安全上限({max_safe_radius}m)を超えたため制限しています")
        arc_radius = max_safe_radius
    arc_height = cam_start[2]
    start_angle = math.atan2(cam_start[0], cam_start[1])

    def get_cam_on_arc(angle):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        return (x, y, arc_height)

    target = (0.0, 0.0, 1.0)

    # すべてのキーフレームを24フレームごとに一様に配置
    all_keyframes = list(range(cut1_start, cut1_end + 1, keyframe_interval))
    if all_keyframes[-1] != cut1_end:
        all_keyframes.append(cut1_end)

    final_cam_pos = None
    final_rot = None

    for frame in all_keyframes:
        # 角度: フレーム位置ベースで計算（360度一周）
        cut1_length = cut1_end - cut1_start + 1
        frame_progress = (frame - cut1_start) / cut1_length if cut1_length > 0 else 0
        angle = start_angle + total_rotation * frame_progress

        cam_pos = get_cam_on_arc(angle)

        # カメラの位置+回転を直接キーフレーム記録（LookAt計算方式）
        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

        final_cam_pos = cam_pos
        final_rot = camera.rotation_quaternion.copy()

    print(f"  [fr{cut1_start}-115] charA: {char_a_start} → {char_a_end}")
    print(f"  [fr{cut1_start}-115] charB: {char_b_start} → {char_b_end}")
    print(f"  [fr400-500] charA: {char_a_end} → {char_a_start}")
    print(f"  [fr400-500] charB: {char_b_end} → {char_b_start}")
    print(f"  [fr{cut1_start}-{cut1_end}] カメラ360度一周完了")

    return {
        'camera_loc': final_cam_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }
