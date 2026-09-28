"""
Short2 - カット1・カット2 の位置アニメーションモジュール

各カットごとのカメラ・車の位置キーフレームを設定する。
カットは完全に分離されており、独立して動作する。

フレーム定義 (24fps):
  カット1: fr0-120 (約5秒) — 車が中央へスライド + 円弧パンニング
  カット2A: fr121-240 (5秒) — トップダウンビューへ移動 (イージング、ゆっくり滑らかに) + 車スライド開始
  カット2B: fr241-324 (3.5秒) — カメラ復帰 (イージング) + CarB不透明化 + 車スライド完了

使い方:
    from short2_cuts import (
        setup_cut1_overlap,
        setup_cut2_phase_a_topdown,
        setup_cut2_phase_b_camera_return,
    )
"""

import bpy
import math
from animation_common import set_camera_look_at, _set_camera_keyframe
from short2_utils import (
    _set_location_keyframe,
    _set_rotation_keyframe,
    _set_camera_location_keyframe,
)


# ============================================================
# デフォルトフレーム定義（24fps）— バックアップ用
# ============================================================
DEFAULT_CUT_FRAMES = {
    "cut1_start": 0,
    "cut1_end": 120,   # カット1を5秒に短縮 (fr0-120)
    "cut2a_start": 121,
    "cut2a_end": 204,  # フェーズA: 3.5秒 (84フレーム)
    "cut2b_start": 205,
    "cut2b_end": 288,  # フェーズB: 3.5秒 (84フレーム) → 全体12秒
}

# カメラ位置の制限範囲（メートル）
# short2_utils.py と統一値を使用
# ※2026-09-27: カメラ飛翔防止のため 15.0→12.0 に変更
CAMERA_LOCATION_MAX = 12.0


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


def setup_cut1_overlap(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, strategy_config=None, cut_frames=None):
    """
    カット1: 車のスライドアニメーション + 円弧パンニング。

    新しい流れ (fr=cut1_start を 0 とする前提):
      fr0:       2台が中央で重なり (carBは半透明)
      fr1-24(1秒): 各自の開始位置へスライド
      fr30:     carB不透明化 (透明度アニメーション側で制御)
      fr31-48(1秒): 再度中央へスライドして重なり
      fr48-cut1_end: 中央位置維持

    カメラ: バリエーション設定に基づく円弧パンニング（変更なし）

    Parameters:
        cut_frames: dict with keys cut1_start, cut1_end (None時はデフォルト値を使用)

    Returns:
        dict: カット1終了時の状態情報 (camera_loc, camera_rot)
    """
    # フレーム値を取得（引数がなければデフォルトを使用）
    cut1_start = cut_frames.get("cut1_start", DEFAULT_CUT_FRAMES["cut1_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_start"]
    cut1_end = cut_frames.get("cut1_end", DEFAULT_CUT_FRAMES["cut1_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut1_end"]

    print(f"\n  === カット1: 車中央スライド + 円弧パンニング (fr{cut1_start}-{cut1_end}) ===")

    # --- 車のアニメーション ---
    # 新しい流れ:
    #   fr0:       中央で重なり (car_a_end / car_b_end)
    #   fr0→fr24(1秒): 開始位置へスライド (car_a_start / car_b_start)
    #   fr30:     開始位置維持 (carB不透明化は透明度側で制御)
    #   fr30→fr66(1.5秒): 中央へスライド (car_a_end / car_b_end)
    #   fr67-cut1_end: 中央位置維持 (carBは半透明 Alpha=0.35)

    slide_out_end = cut1_start + 24       # fr24: スライドアウト完了
    stay_frame = cut1_start + 30          # fr30: 不透明化 (開始位置維持)
    slide_in_end = cut1_start + 66        # fr66: 中央へスライド完了 (1.5秒)

    # fr0: 中央で重なり
    _set_location_keyframe(car_a, cut1_start, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, cut1_start, car_b_end[0], car_b_end[1], car_b_end[2])

    # fr24: 各自の開始位置へスライド完了
    _set_location_keyframe(car_a, slide_out_end, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, slide_out_end, car_b_start[0], car_b_start[1], car_b_start[2])

    # fr30: 開始位置維持 (不透明化タイミング)
    _set_location_keyframe(car_a, stay_frame, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, stay_frame, car_b_start[0], car_b_start[1], car_b_start[2])

    # fr48: 中央へスライド完了
    _set_location_keyframe(car_a, slide_in_end, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, slide_in_end, car_b_end[0], car_b_end[1], car_b_end[2])

    # 位置維持キーフレーム（0.5秒ごと - 補間の階段状を緩和）
    keyframe_interval = 12
    maintain_start = slide_in_end + keyframe_interval
    for frame in range(maintain_start, cut1_end + 1, keyframe_interval):
        _set_location_keyframe(car_a, frame, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, frame, car_b_end[0], car_b_end[1], car_b_end[2])

    # カット1終了フレームも確実に設定
    _set_location_keyframe(car_a, cut1_end, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, cut1_end, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"  [fr{cut1_start}] 中央重なり: carA={car_a_end}, carB={car_b_end}")
    print(f"  [fr{slide_out_end}] スライドアウト完了: carA={car_a_start}, carB={car_b_start}")
    print(f"  [fr{stay_frame}] 開始位置維持 (不透明化タイミング)")
    print(f"  [fr{slide_in_end}] 中央スライドイン完了: carA={car_a_end}, carB={car_b_end}")

    # --- カメラ円弧パンニング（バリエーション設定適用） ---
    if strategy_config and "camera_pattern" in strategy_config:
        cam_pattern = strategy_config["camera_pattern"]
        cam_start = tuple(cam_pattern["start_position"])
        total_rotation = cam_pattern["total_rotation"]
        print(f"  カメラパターン: {cam_pattern['name']} (start={cam_start})")
    else:
        # スケール適用済みのカメラ起始位置を使用（strategy_configから取得）
        cam_start_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cam_start_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cam_start_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_start = (cam_start_x, cam_start_y, cam_start_z)
        total_rotation = -1.7

    arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
    # ※2026-09-27: 巨大車両でカメラが遠くなりすぎないように半径に上限を追加
    arc_radius = min(arc_radius, CAMERA_LOCATION_MAX)
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
    # Zを一定に保つ（ズームイン廃止）
    # ============================================================

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

        # Zを一定に保つ（ズームイン廃止）
        cam_pos = get_cam_on_arc(angle)

        # カメラの位置+回転を直接キーフレーム記録（Phase A/Bと同じ方式に統一）
        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

        final_cam_pos = cam_pos
        final_rot = camera.rotation_quaternion.copy()

    print(f"  [fr{cut1_start}-{cut1_end}] carA: {car_a_start} → {car_a_end}")
    print(f"  [fr{cut1_start}-{cut1_end}] carB: {car_b_start} → {car_b_end}")
    print(f"  [fr{cut1_end}] カメラパンニング完了: {math.degrees(total_rotation_scaled):.1f}°回転")

    return {
        'camera_loc': final_cam_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }


def _clamp_camera_z(cam_z, min_z):
    """
    カメラのZ位置を最低値でクリップ（車との干渉防止）。
    
    Parameters:
        cam_z: 補間後のカメラZ座標
        min_z: 許可される最低Z値（車の全高 + 安全マージン）
    
    Returns:
        float: クリップされたZ座標
    """
    return max(cam_z, min_z)


def _interpolate_car_position(start_pos, end_pos, progress):
    """車の位置を補間するヘルパー関数"""
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
    z = start_pos[2] + (end_pos[2] - start_pos[2]) * progress
    return (x, y, z)


def _clamp_camera_location(x, y, z):
    """カメラの位置を安全な範囲内に制限する
    
    各座標軸を ±CAMERA_LOCATION_MAX (±12.0m) 以内にクランプし、
    Z座標は常に正（地面より上）を保証する。
    
    ※2026-09-27: CAMERA_LOCATION_MAX を 15.0→12.0 に変更 (short2_utils.py と統一)
    """
    cx = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, x))
    cy = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, y))
    cz = max(0.1, min(CAMERA_LOCATION_MAX, z))
    
    if abs(cx - x) > 1.0 or abs(cy - y) > 1.0 or abs(cz - z) > 1.0:
        print(f"    ⚠ カメラ位置クランプ: ({x:.2f}, {y:.2f}, {z:.2f}) → ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    
    return (cx, cy, cz)


# 前回のカメラクォータニオンを保持（符号統一用）
_last_camera_quat = None

def reset_camera_quat_state():
    """_last_camera_quat をリセット（各実行开始时に呼ぶ）"""
    global _last_camera_quat
    _last_camera_quat = None

def _set_camera_keyframes_to_linear(cam, frame):
    """カメラの location + rotation_quaternion キーフレームを LINEAR に設定
    
    quaternion符号は _last_camera_quat で統一済みなので、
    LINEAR補間で最短経路が保証される。
    rotationもLINEARにすることで、locationとのinterpolationを統一し、
    不揃いな動き（直線+曲線の混在）による「ぼよん感」を解消する。
    """
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


def _set_camera_position_and_rotation_keyframe(cam, target_name, frame, cam_pos, tgt_pos):
    """LookAt計算でカメラの向きを直接設定してキーフレーム記録する
    
    修正点 (2026-09-18):
      1. カメラ位置を ±15m にクランプ（飛び防止）
      2. rotation_euler → rotation_quaternion でジンバルロックを回避
      3. quaternion 符号統一で最短経路補間を保証（Fix7）
    
    Track To constraintの有効/無効に関係なく動作する。
    mathutils.Vector.to_track_quat() を使用し、カメラの-Z軸がtargetを向くように回転を算出。
    """
    from mathutils import Vector
    
    global _last_camera_quat
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    
    # カメラ位置を安全な範囲にクランプ（修正1）
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
        # カメラとtargetが重なっている場合は回転を変更しない
        pass
    else:
        # to_track_quat(direction, 'TRACK_axis', 'UP_axis')
        # Blenderのカメラ: 進行方向=-Z, 上向き=+Y
        track_quat = direction.normalized().to_track_quat('-Z', 'Y')
        
        # Fix7: quaternion符号統一 — 前回のクォータニオンとのinner productが負なら符号反転
        # q と -q は同じ回転だが、補間の経路が逆側になる。最短経路を保証するために符号を合わせる
        if _last_camera_quat is not None:
            dot = track_quat.dot(_last_camera_quat)
            if dot < 0:
                track_quat = -track_quat
        
        _last_camera_quat = track_quat.copy()
        
        # rotation_modeをQUATERNIONに切り替え（ジンバルロック回避）
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = track_quat
    
    # キーフレームとして記録
    if cam.animation_data is None:
        cam.animation_data_create()
    
    for i in range(3):
        cam.keyframe_insert(data_path="location", index=i)
    
    # rotation_quaternionでキーフレーム（rotation_eulerの代わりに）
    for i in range(4):
        cam.keyframe_insert(data_path="rotation_quaternion", index=i)
    
    # location + rotation_quaternion の両方をLINEARに設定
    _set_camera_keyframes_to_linear(cam, frame)
    
    bpy.context.scene.frame_set(current_frame)


def setup_cut2_phase_a_topdown(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, cut1_final_cam, strategy_config=None, cut_frames=None):
    """
    カット2 フェーズA: トップダウンビューへ移動 + 車は中央で静止。

    カメラ: カット1終了位置 → バリエーション設定に基づくトップダウン位置
    車: 中央集合位置で静止（フェーズBでスライド開始）

    Parameters:
        cut1_final_cam: カット1終了時のカメラ位置 (x, y, z)
        cut_frames: dict with keys cut2a_start, cut2a_end (None時はデフォルト値を使用)

    Returns:
        dict: フェーズA終了時のカメラ情報
    """
    # フレーム値を取得
    cut2a_start = cut_frames.get("cut2a_start", DEFAULT_CUT_FRAMES["cut2a_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_start"]
    cut2a_end = cut_frames.get("cut2a_end", DEFAULT_CUT_FRAMES["cut2a_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2a_end"]

    print(f"\n  === カット2 フェーズA: トップダウンビューへ移動 + 車中央静止 (fr{cut2a_start}-{cut2a_end}, イージング) ===")

    # バリエーション設定からトップダウン位置を取得
    if strategy_config and "topdown_variation" in strategy_config:
        top_down_pos = tuple(strategy_config["topdown_variation"]["position"])
        print(f"  トップダウン変形: {strategy_config['topdown_variation']['name']} → {top_down_pos}")
    else:
        # スケール適用済みのトップダウン高さを使用（strategy_configから取得）
        topdown_height = strategy_config.get("topdown_height", 8.0) if strategy_config else 8.0
        top_down_pos = (0.0, 0.0, topdown_height)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    # カメラZの最低値保証（車の全高 + 安全マージン）
    min_camera_z = strategy_config.get("min_camera_z", 4.0) if strategy_config else 4.0

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 6  # 0.25秒ごとで補間をより滑らかに

    # cut2a_startで明確なカメラキーフレームを設定（カット1からの連続性を保証）
    _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", cut2a_start, cut1_final_cam, target)

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
        # Zの最低値を保証（車との干渉防止）
        cam_z = _clamp_camera_z(cam_z, min_camera_z)
        cam_pos = (cam_x, cam_y, cam_z)
        # Track Toがミュートされているので、位置+回転を直接キーフレーム記録
        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

        # 車は中央集合位置で静止（重なったまま）
        _set_location_keyframe(car_a, frame, car_a_end[0], car_a_end[1], car_a_end[2])
        _set_location_keyframe(car_b, frame, car_b_end[0], car_b_end[1], car_b_end[2])

    print(f"  [fr{cut2a_start}-{cut2a_end}] カメラ: {cut1_final_cam} → {top_down_pos}")
    print(f"  車: 中央集合位置で静止（フェーズBでスライド開始）")

    return {'camera_loc': top_down_pos}


def setup_cut2_phase_b_camera_return(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, strategy_config=None, cut_frames=None):
    """
    カット2 フェーズB: カメラ復帰 + 車スライド（二段階）。

    フェーズB前半 (fr205-fr287):
      カメラ: トップダウン → 復帰位置
      車: 中央集合位置 → 開始位置へスライド
    フェーズB後半 (fr288-fr324, ~1.5秒):
      カメラ: 固定（復帰位置維持）
      車: 開始位置 → 中央へスライド回来り

    Parameters:
        strategy_config: バリエーション設定辞書（オプション）
        cut_frames: dict with keys cut2b_start, cut2b_end (None時はデフォルト値を使用)

    Returns:
        dict: フェーズB終了時のカメラ情報
    """
    # フレーム値を取得
    cut2b_start = cut_frames.get("cut2b_start", DEFAULT_CUT_FRAMES["cut2b_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_start"]
    cut2b_end = cut_frames.get("cut2b_end", DEFAULT_CUT_FRAMES["cut2b_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_end"]

    print(f"\n  === カット2 フェーズB: カメラ開始位置へ復帰 + 車スライド (fr{cut2b_start}-{cut2b_end}, イージング) ===")

    # バリエーション設定から復帰カメラ位置を取得
    if strategy_config and "camera_pattern" in strategy_config:
        cam_return_pos = tuple(strategy_config["camera_pattern"]["start_position"])
        print(f"  カメラ復帰先: {cam_return_pos}")
    else:
        # スケール適用済みのカメラ起始位置を使用（strategy_configから取得）
        cam_start_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cam_start_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cam_start_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_return_pos = (cam_start_x, cam_start_y, cam_start_z)

    # トップダウン位置もバリエーションから取得
    if strategy_config and "topdown_variation" in strategy_config:
        top_down_pos = tuple(strategy_config["topdown_variation"]["position"])
    else:
        # スケール適用済みのトップダウン高さを使用（strategy_configから取得）
        topdown_height = strategy_config.get("topdown_height", 8.0) if strategy_config else 8.0
        top_down_pos = (0.0, 0.0, topdown_height)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    # カメラZの最低値保証（車の全高 + 安全マージン）
    min_camera_z = strategy_config.get("min_camera_z", 4.0) if strategy_config else 4.0

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 6  # 0.25秒ごとで補間をより滑らかに

    # フェーズB後半: 最後の1.5秒（36フレーム）は車を中央へスライド回来り
    slide_back_frames = 36  # 1.5秒
    phase_b_slide_end = cut2b_end - slide_back_frames

    # --- フェーズB前半: カメラ復帰 + 車→開始位置へスライド (fr205-fr288) ---
    total_slide_frames_a = phase_b_slide_end - cut2b_start + 1

    phase_b_a_frames = list(range(cut2b_start, phase_b_slide_end + 1, keyframe_interval))
    if not phase_b_a_frames or phase_b_a_frames[-1] != phase_b_slide_end:
        phase_b_a_frames.append(phase_b_slide_end)
    num_segments_a = len(phase_b_a_frames) - 1

    for i, frame in enumerate(phase_b_a_frames):
        # カメラの補間（イージング適用）
        raw_progress = i / num_segments_a if num_segments_a > 0 else 0
        cam_progress = ease_func(raw_progress)
        cam_x = top_down_pos[0] + (cam_return_pos[0] - top_down_pos[0]) * cam_progress
        cam_y = top_down_pos[1] + (cam_return_pos[1] - top_down_pos[1]) * cam_progress
        cam_z = top_down_pos[2] + (cam_return_pos[2] - top_down_pos[2]) * cam_progress
        cam_z = _clamp_camera_z(cam_z, min_camera_z)
        cam_pos = (cam_x, cam_y, cam_z)
        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

        # 車のスライド進行度（中央→開始位置へ）
        raw_car_progress = max(0, (frame - cut2b_start) / total_slide_frames_a)
        car_progress = ease_func(raw_car_progress)

        car_a_pos = _interpolate_car_position(car_a_end, car_a_start, car_progress)
        car_b_pos = _interpolate_car_position(car_b_end, car_b_start, car_progress)

        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # 前半終了時に車が開始位置に到達していることを保証
    _set_location_keyframe(car_a, phase_b_slide_end, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, phase_b_slide_end, car_b_start[0], car_b_start[1], car_b_start[2])

    # --- フェーズB後半: カメラ固定 + 車→中央へスライド回来り (fr289-fr324) ---
    slide_back_frames_list = list(range(phase_b_slide_end, cut2b_end + 1, keyframe_interval))
    if not slide_back_frames_list or slide_back_frames_list[-1] != cut2b_end:
        slide_back_frames_list.append(cut2b_end)
    num_segments_b = len(slide_back_frames_list) - 1

    for i, frame in enumerate(slide_back_frames_list):
        # カメラは固定（復帰位置維持）
        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_return_pos, target)

        # 車のスライド進行度（開始位置→中央へ回来り、イージング適用）
        raw_car_progress = max(0, (frame - phase_b_slide_end) / slide_back_frames)
        car_progress = ease_func(raw_car_progress)

        car_a_pos = _interpolate_car_position(car_a_start, car_a_end, car_progress)
        car_b_pos = _interpolate_car_position(car_b_start, car_b_end, car_progress)

        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # 終了フレームを確実に設定（車が中央に到達していることを保証）
    _set_location_keyframe(car_a, cut2b_end, car_a_end[0], car_a_end[1], car_a_end[2])
    _set_location_keyframe(car_b, cut2b_end, car_b_end[0], car_b_end[1], car_b_end[2])

    # 最終カメラ位置を設定（キーフレームはループで設定済み）
    camera.location = (cam_return_pos[0], cam_return_pos[1], cam_return_pos[2])

    print(f"  [fr{cut2b_start}-{phase_b_slide_end}] カメラ: {top_down_pos} → {cam_return_pos} + 車: 中央→開始位置へ")
    print(f"  [fr{phase_b_slide_end+1}-{cut2b_end}] カメラ固定 + 車: 開始位置→中央へスライド回来り (1.5秒)")
    print(f"  車: スライド完了 → carA={car_a_start}, carB={car_b_start}")

    return {
        'camera_loc': cam_return_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }


def setup_cut2_arc_return(camera, car_a, car_b, car_a_start, car_a_end, car_b_start, car_b_end, cut1_final_cam, strategy_config=None, cut_frames=None):
    """
    カット2 (arc return): カット1終了位置から起始位置へ同じ円弧で水平に逆戻り + 車のスライド復帰。

    カメラ: カット1の円弧を終了点から起点へ逆方向で戻る（Zは一定、水平移動）
    車: 中央集合位置からカット1開始位置へゆっくりスライド

    Parameters:
        cut1_final_cam: カット1終了時のカメラ位置 (x, y, z)
        strategy_config: バリエーション設定辞書（オプション）
        cut_frames: dict with keys cut2b_start, cut2b_end (None時はデフォルト値を使用)

    Returns:
        dict: カット2終了時のカメラ情報
    """
    # フレーム値を取得
    cut2b_start = cut_frames.get("cut2b_start", DEFAULT_CUT_FRAMES["cut2b_start"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_start"]
    cut2b_end = cut_frames.get("cut2b_end", DEFAULT_CUT_FRAMES["cut2b_end"]) if cut_frames else DEFAULT_CUT_FRAMES["cut2b_end"]

    print(f"\n  === カット2 (arc return): 円弧逆戻り + 車スライド復帰 (fr{cut2b_start}-{cut2b_end}, イージング) ===")

    # 起始カメラ位置を取得
    if strategy_config and "camera_pattern" in strategy_config:
        cam_start_pos = tuple(strategy_config["camera_pattern"]["start_position"])
    else:
        cam_start_x = strategy_config.get("cam_start_x", -3.0) if strategy_config else -3.0
        cam_start_y = strategy_config.get("cam_start_y", -6.0) if strategy_config else -6.0
        cam_start_z = strategy_config.get("cam_start_z", 3.5) if strategy_config else 3.5
        cam_start_pos = (cam_start_x, cam_start_y, cam_start_z)

    # イージング関数の取得
    ease_func = _get_easing_func(strategy_config)

    target = (0.0, 0.0, 1.0)
    keyframe_interval = 12  # 0.5秒ごと

    # --- 円弧パラメータを起始位置から再計算 ---
    arc_radius = math.sqrt(cam_start_pos[0]**2 + cam_start_pos[1]**2)
    # ※2026-09-27: 巨大車両でカメラが遠くなりすぎないように半径に上限を追加
    arc_radius = min(arc_radius, CAMERA_LOCATION_MAX)
    arc_height = cam_start_pos[2]

    start_angle = math.atan2(cam_start_pos[0], cam_start_pos[1])

    # total_rotation を復元（カット1と同じ回転量）
    total_rotation_raw = strategy_config.get("camera_pattern", {}).get("total_rotation", -0.85) if strategy_config else -0.85
    cut1_start_frame = cut_frames.get("cut1_start", 0) if cut_frames else 0
    cut1_end_frame = cut_frames.get("cut1_end", 288) if cut_frames else 288
    cut1_length = cut1_end_frame - cut1_start_frame + 1
    total_rotation_scaled = total_rotation_raw * (cut1_length / 144)

    print(f"  円弧パラメータ: radius={arc_radius:.2f}, height={arc_height:.2f}")
    print(f"  カット1の回転量: {math.degrees(total_rotation_scaled):.1f}°")
    print(f"  start_angle={math.degrees(start_angle):.1f}°, end_angle_cut1={math.degrees(start_angle + total_rotation_scaled):.1f}°")
    print(f"  カット2: {math.degrees(start_angle + total_rotation_scaled):.1f}° → {math.degrees(start_angle):.1f}° (逆回転)")

    def get_cam_on_arc(angle):
        x = arc_radius * math.sin(angle)
        y = arc_radius * math.cos(angle)
        return (x, y, arc_height)

    # カメラ開始キーフレーム（cut1終了位置から連続）
    _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", cut2b_start, cut1_final_cam, target)

    # フレームリストを生成
    phase_frames = list(range(cut2b_start, cut2b_end + 1, keyframe_interval))
    if phase_frames[-1] != cut2b_end:
        phase_frames.append(cut2b_end)
    num_segments = len(phase_frames) - 1

    for i, frame in enumerate(phase_frames):
        # イージング適用した進行度
        raw_progress = i / num_segments if num_segments > 0 else 0
        progress = ease_func(raw_progress)

        # カメラ: カット1と同じ方式で逆回転
        # カット1: start_angle → start_angle + total_rotation (progress 0→1)
        # カット2: start_angle + total_rotation → start_angle (progress 1→0)
        cam_angle = start_angle + total_rotation_scaled * (1 - progress)
        cam_pos = get_cam_on_arc(cam_angle)

        _set_camera_position_and_rotation_keyframe(camera, "CameraTarget", frame, cam_pos, target)

        # 車: 中央集合位置 → 各自の開始位置へスライド（元の位置に戻す、イージング適用）
        # CarA → CarAの元位置, CarB → CarBの元位置
        car_a_pos = _interpolate_car_position(car_a_end, car_a_start, progress)
        car_b_pos = _interpolate_car_position(car_b_end, car_b_start, progress)

        _set_location_keyframe(car_a, frame, car_a_pos[0], car_a_pos[1], car_a_pos[2])
        _set_location_keyframe(car_b, frame, car_b_pos[0], car_b_pos[1], car_b_pos[2])

    # 終了フレームを確実に設定（各自の開始位置へ戻る）
    _set_location_keyframe(car_a, cut2b_end, car_a_start[0], car_a_start[1], car_a_start[2])
    _set_location_keyframe(car_b, cut2b_end, car_b_start[0], car_b_start[1], car_b_start[2])

    # 最終カメラ位置を設定（起始位置）
    final_cam_pos = get_cam_on_arc(start_angle)
    camera.location = (final_cam_pos[0], final_cam_pos[1], final_cam_pos[2])

    print(f"  [fr{cut2b_start}-{cut2b_end}] カメラ: {cut1_final_cam} → {final_cam_pos} (円弧逆戻り)")
    print(f"  車: スライド完了（元の位置へ）→ carA={car_a_start}, carB={car_b_start}")

    return {
        'camera_loc': final_cam_pos,
        'camera_rot': camera.rotation_euler.copy(),
    }
