"""
Short2 共通ユーティリティモジュール

ショート動画v2（カット1・カット2）で共通して使用される
キーフレーム設定ヘルパー関数を定義。

使い方:
    from short2_utils import (
        _set_location_keyframe,
        _set_rotation_keyframe,
        _set_camera_location_keyframe,
        get_car_visual_center_offset,
        clear_animation_data,
    )
"""

import bpy
import math
from mathutils import Vector


def get_car_visual_center_offset(car_obj):
    """車のジオメトリから視覚的な中心のオフセットを取得
    
    depsgraph評価のみで計算し、副作用を持たない。
    
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
    """車の位置キーフレームを設定"""
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="location", index=-1)
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_rotation_keyframe(obj, frame, rot):
    """回転キーフレームを設定"""
    if hasattr(rot, 'x'):
        rx, ry, rz = rot.x, rot.y, rot.z
    else:
        rx, ry, rz = rot[0], rot[1], rot[2]
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.rotation_euler = (rx, ry, rz)
    if obj.animation_data is None:
        obj.animation_data_create()
    obj.keyframe_insert(data_path="rotation_euler", index=-1)
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


def _get_action_name_for_object(obj):
    """オブジェクトの名前から推測されるアクション名を返す"""
    # Blender 5.x ではデフォルトで "{object.name}アクション" という名前になる
    return f"{obj.name}アクション"


def _clear_old_actions_for_object(obj):
    """bpy.data.actions からこのオブジェクト関連の旧アクションを削除"""
    base_name = _get_action_name_for_object(obj)
    removed = []
    # 現在のアニメーションデータが参照しているアクションは削除しない
    current_action_name = None
    if obj.animation_data and obj.animation_data.action:
        current_action_name = obj.animation_data.action.name
    
    actions_to_check = list(bpy.data.actions.keys())
    for action_name in actions_to_check:
        if base_name in action_name and action_name != current_action_name:
            # ユーザー参照数を確認（0なら安全に削除可能）
            try:
                action = bpy.data.actions.get(action_name)
                if action is not None and action.users == 0:
                    bpy.data.actions.remove(action)
                    removed.append(action_name)
            except ReferenceError:
                pass
    
    if removed:
        print(f"    {obj.name}: 旧アクション {removed} を削除")


def _clear_animation_data(obj):
    """オブジェクトのアニメーションデータを完全に消去"""
    # まず関連する旧アクションを bpy.data.actions から削除
    _clear_old_actions_for_object(obj)
    
    if obj.animation_data:
        obj.animation_data_clear()
        print(f"    {obj.name} のアニメーションデータをクリア")
    else:
        print(f"    {obj.name} にアニメーションデータなし")


def clear_animation_data(objects):
    """指定されたオブジェクトリストのアニメーションデータを完全に消去"""
    if not objects:
        return
    for obj in objects:
        _clear_animation_data(obj)
    print("    アニメーションデータのクリーンアップ完了")


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
