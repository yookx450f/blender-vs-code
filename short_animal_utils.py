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
    )
"""

import bpy
from mathutils import Vector


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
    """カメラの位置キーフレームを設定"""
    x, y, z = loc if isinstance(loc, tuple) else (loc.x, loc.y, loc.z)

    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
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


def _get_animal_max_z(animal_obj):
    """動物オブジェクトの最大Z座標を取得"""
    animal_obj.update_tag()
    bpy.context.view_layer.update()
    bounds = [Vector(b) for b in animal_obj.bound_box]
    corners_world = [animal_obj.matrix_world @ corner for corner in bounds]
    return max(c.z for c in corners_world)
