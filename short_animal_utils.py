"""
動物ショート動画用ユーティリティモジュール

animation_settings_shortAnimal.py から抽出した共通ツール関数群。
キーフレーム設定、視覚的中心計算、アニメーション補間制御などを提供する。

使い方:
    from short_animal_utils import (
        get_car_visual_center_offset,
        _set_location_keyframe,
        _set_empty_location_keyframe,
        _set_camera_location_keyframe,
        _get_animal_max_z,
        generate_easing_frames,
        _set_camera_location_keyframe_with_easing,
        _calculate_animal_scale_factor,
    )
"""

import bpy
from mathutils import Vector


# ============================================================
# イージング関数（密集キーフレーム法用）
# ============================================================

def ease_in_quad(t):
    """クイッティ・イン — 始動を緩やかにする"""
    return t * t


def ease_out_quad(t):
    """クイッティ・アウト — 停止を緩やかにする"""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t):
    """クイッティ・インアウト — 始動と停止の両方を緩やかにする"""
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - (-2 * t + 2) ** 2 / 2


def ease_in_cubic(t):
    """カーブ・イン — より強い始動緩和"""
    return t * t * t


def ease_out_cubic(t):
    """カーブ・アウト — より強い停止緩和"""
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    """カーブ・インアウト — 始動と停止の両方をより強く緩やかにする"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - (-2 * t + 2) ** 3 / 2


# デフォルトで使用するイージング関数（三次系でより滑らかな加減速）
DEFAULT_EASE_IN = ease_in_cubic
DEFAULT_EASE_OUT = ease_out_cubic
DEFAULT_EASE_IN_OUT = ease_in_out_cubic


def generate_easing_frames(start_frame, end_frame, num_frames=12, ease_type="in_out"):
    """
    イージングに従ってキーフレームの位置を生成する。
    
    開始・終了付近でフレームが密集し、中間で間隔が広がる。
    
    Parameters:
        start_frame: 開始フレーム番号
        end_frame: 終了フレーム番号
        num_frames: 生成するキーフレームの数（デフォルト12）
        ease_type: "in" | "out" | "in_out" — イージングの種類
    
    Returns:
        list: ソートされたフレーム番号のリスト
    """
    if ease_type == "in":
        ease_func = DEFAULT_EASE_IN
    elif ease_type == "out":
        ease_func = DEFAULT_EASE_OUT
    else:
        ease_func = DEFAULT_EASE_IN_OUT
    
    total_duration = end_frame - start_frame
    frames = []
    
    for i in range(num_frames):
        t = i / (num_frames - 1) if num_frames > 1 else 0.5
        eased_t = ease_func(t)
        frame = start_frame + int(eased_t * total_duration)
        frames.append(frame)
    
    # 重複を除去してソート
    frames = sorted(set(frames))
    
    # 開始・終了フレームを保証
    if frames[0] != start_frame:
        frames.insert(0, start_frame)
    if frames[-1] != end_frame:
        frames.append(end_frame)
    
    return frames


def _interpolate_position(start_pos, end_pos, t):
    """2つの位置を線形補間する"""
    x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
    y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
    z = start_pos[2] + (end_pos[2] - start_pos[2]) * t
    return (x, y, z)


def _set_camera_location_keyframe_with_easing(
    camera,
    start_frame,
    end_frame,
    start_pos,
    end_pos,
    num_frames=32,
    ease_type="in_out"
):
    """
    イージング付きでカメラの位置キーフレームを設定する。
    
    密集キーフレーム法により、始動と停止を滑らかにする。
    
    Parameters:
        camera: カメラオブジェクト
        start_frame: 開始フレーム番号
        end_frame: 終了フレーム番号
        start_pos: 開始位置 (x, y, z)
        end_pos: 終了位置 (x, y, z)
        num_frames: 生成するキーフレームの数（多いほど滑らか）
        ease_type: "in" | "out" | "in_out" — イージングの種類
    """
    frames = generate_easing_frames(start_frame, end_frame, num_frames, ease_type)
    
    for frame in frames:
        t = (frame - start_frame) / (end_frame - start_frame) if end_frame != start_frame else 0
        pos = _interpolate_position(start_pos, end_pos, t)
        _set_camera_location_keyframe(camera, frame, pos)


# ============================================================
# 既存のユーティリティ関数
# ============================================================

def get_car_visual_center_offset(car_obj):
    """動物のジオメトリから視覚的な中心のオフセットを取得

    GLBモデルのオブジェクト原点が視覚的中心と一致しない場合、
    ジオメトリ頂点から直接計算して補正値を返す。

    Returns:
        tuple: (offset_x, offset_y) — 視覚的中心をワールド座標(0,0)に配置するための補正値
    """
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = car_obj.evaluated_get(depsgraph)
    me_eval = obj_eval.to_mesh()

    if not me_eval or len(me_eval.vertices) == 0:
        obj_eval.to_mesh_clear()
        return (0.0, 0.0)

    mat_world = obj_eval.matrix_world
    verts_world = [mat_world @ Vector(vert.co) for vert in me_eval.vertices]

    min_x = min(v.x for v in verts_world)
    max_x = max(v.x for v in verts_world)
    min_y = min(v.y for v in verts_world)
    max_y = max(v.y for v in verts_world)

    visual_center_x = (min_x + max_x) / 2.0
    visual_center_y = (min_y + max_y) / 2.0

    obj_eval.to_mesh_clear()

    world_origin = obj_eval.matrix_world.to_translation()
    offset_x = visual_center_x - world_origin.x
    offset_y = visual_center_y - world_origin.y

    return (offset_x, offset_y)


def _set_location_keyframe(obj, frame, x, y, z):
    """動物の位置キーフレームを設定"""
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_empty_location_keyframe(obj, frame, x, y, z):
    """Emptyの位置キーフレームを設定"""
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_camera_location_keyframe(obj, frame, loc):
    """
    カメラの位置キーフレームを設定
    
    AUTO_CLAMPED ハンドルを維持して、Blender の自動イージングを有効にする。
    LINEAR にしないことで、カット間で滑らかな始動・停止が実現される。
    """
    x, y, z = loc if isinstance(loc, tuple) else (loc.x, loc.y, loc.z)

    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    # AUTO_CLAMPEDを維持して滑らかな補間を有効にする（LINEARにしない）
    _ensure_autoclamped_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _ensure_linear_interpolation_for_object(obj, frame):
    """指定オブジェクトのF-CurveキーフレームのインターポレーションをLINEARに設定"""
    if not obj.animation_data or not obj.animation_data.action:
        return

    action = obj.animation_data.action

    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
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
                            for kf in fc.keyframe_points:
                                if abs(kf.co.x - frame) < 0.1:
                                    kf.interpolation = 'LINEAR'


def _ensure_autoclamped_interpolation_for_object(obj, frame):
    """
    指定オブジェクトのF-CurveキーフレームのハンドルをAUTO_CLAMPEDに設定
    Blender の自動イージングを有効にし、滑らかな始動・停止を実現する。
    """
    if not obj.animation_data or not obj.animation_data.action:
        return

    action = obj.animation_data.action

    if hasattr(action, 'fcurves'):
        for fc in action.fcurves:
            for kf in fc.keyframe_points:
                if abs(kf.co.x - frame) < 0.1:
                    kf.handle_left_type = 'AUTO_CLAMPED'
                    kf.handle_right_type = 'AUTO_CLAMPED'
        return

    if hasattr(action, 'layers'):
        for layer in action.layers:
            for strip in layer.strips:
                if strip.type == 'KEYFRAME':
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kf in fc.keyframe_points:
                                if abs(kf.co.x - frame) < 0.1:
                                    kf.handle_left_type = 'AUTO_CLAMPED'
                                    kf.handle_right_type = 'AUTO_CLAMPED'


def _get_animal_max_z(animal_obj):
    """動物オブジェクトの最大Z座標を取得"""
    animal_obj.update_tag()
    bpy.context.view_layer.update()
    bounds = [Vector(b) for b in animal_obj.bound_box]
    corners_world = [animal_obj.matrix_world @ corner for corner in bounds]
    return max(c.z for c in corners_world)


# ============================================================
# 動的スケーリング — 動物の寸法からカメラ位置・軌道半径などを自動調整
# Short2 (animation_settings_short2.py) の _calculate_scale_factor を参考に設計
#
# 【再調整】中小型動物でも寄るように基準サイズを上げて補正係数を下げる
# ============================================================

def _calculate_animal_scale_factor(animal_dimensions):
    """
    動物の寸法からスケール倍率を計算する。

    基準サイズ(2.5m)に対して、両動物の最大寸法の大きい方を比較し、
    スケール係数を算出。範囲は 0.5〜3.0 でクリップする。

    【設計思想】
    - 中小型動物（犬・猫・熊など ~1-2m）は補正されないor微弱に補正される
    - 大型動物（馬・シカ ~2-3m）では適度に遠ざかる
    - 超大型動物（キリン・象 ~4m+）で強く遠ざかる

    動物には全長データがない場合もあるので、height のみを基準にし、
    length があれば max(height, length) を使用する。

    Parameters:
        animal_dimensions: {key: {"length": mm値, "height": mm値}} の辞書 (None時はデフォルト1.0)

    Returns:
        float: スケール倍率 (デフォルト=1.0)
    """
    if not animal_dimensions:
        return 1.0

    base_size_m = 2.5  # 基準サイズ（中小型動物〜中型動物の境界）

    # 両動物の最大寸法をメートルで取得
    max_dims_m = []
    for key, dims in animal_dimensions.items():
        length_m = dims.get("length", 0) / 1000.0 if dims.get("length") else 0
        height_m = dims.get("height", 0) / 1000.0 if dims.get("height") else 0
        # length と height の両方があれば大きい方を、なければ height を使用
        max_dim_m = max(length_m, height_m) if length_m > 0 else height_m
        if max_dim_m > 0:
            max_dims_m.append(max_dim_m)

    if not max_dims_m:
        return 1.0

    # 両者のうち最大寸法の大きい方を基準に計算
    largest_dim_m = max(max_dims_m)
    scale_factor = largest_dim_m / base_size_m

    # クリップ範囲 0.5 〜 3.0 （小型動物〜超大型動物をカバー）
    # 中小型動物では 1.0 に近い値を保ち、カメラが寄ったままになる
    scale_factor = max(0.5, min(3.0, scale_factor))

    print(f"  スケール倍率計算: 最大寸法={largest_dim_m:.2f}m / 基準={base_size_m:.1f}m -> scale_factor={scale_factor:.2f}")
    return scale_factor
