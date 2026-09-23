"""
ShortGame2 共通ユーティリティモジュール

ゲームキャラクターショート動画v2（縦長9:16、カット1のみ360度一周）で共通して使用される
キーフレーム設定ヘルパー関数を定義。

使い方:
    from short_game2_utils import (
        _set_location_keyframe,
        _set_rotation_keyframe,
        _set_camera_location_keyframe,
        get_character_visual_center_offset,
        clear_animation_data,
    )
"""

import bpy
import math
from mathutils import Vector


# カメラ位置の制限範囲（メートル）
CAMERA_LOCATION_MAX = 15.0


def get_character_visual_center_offset(char_obj):
    """キャラクターのジオメトリから視覚的な中心のオフセットを取得
    
    depsgraph評価のみで計算し、副作用を持たない。
    
    Returns:
        tuple: (offset_x, offset_y) — 視覚的中心をワールド座標(0,0)に配置するための補正値
    """
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = char_obj.evaluated_get(depsgraph)
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


def _clamp_camera_location(x, y, z):
    """カメラの位置を安全な範囲内に制限する
    
    各座標軸を ±CAMERA_LOCATION_MAX 以内にクランプし、
    Z座標は常に正（地面より上）を保証する。
    """
    cx = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, x))
    cy = max(-CAMERA_LOCATION_MAX, min(CAMERA_LOCATION_MAX, y))
    cz = max(0.1, min(CAMERA_LOCATION_MAX, z))  # Zは常に0.1以上
    
    # クランプした値が元の値と大きく異なれば警告（問題の特定用）
    if abs(cx - x) > 1.0 or abs(cy - y) > 1.0 or abs(cz - z) > 1.0:
        print(f"    ⚠ カメラ位置クランプ: ({x:.2f}, {y:.2f}, {z:.2f}) → ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    
    return (cx, cy, cz)


def _set_location_keyframe(obj, frame, x, y, z):
    """キャラクターの位置キーフレームを設定
    
    index=-1（全インデックス）を使用せず、各軸を明示的に指定して
    Blender 5.x のアクションレイヤーシステムとの混同を防ぐ。
    """
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    
    # 各軸を明示的に指定（index=-1はlocationとrotationが混同される原因）
    for i in range(3):
        obj.keyframe_insert(data_path="location", index=i)
    
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_rotation_keyframe(obj, frame, rot):
    """回転キーフレームを設定
    
    各軸を明示的に指定して location との混同を防ぐ。
    """
    if hasattr(rot, 'x'):
        rx, ry, rz = rot.x, rot.y, rot.z
    else:
        rx, ry, rz = rot[0], rot[1], rot[2]
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.rotation_euler = (rx, ry, rz)
    if obj.animation_data is None:
        obj.animation_data_create()
    
    # 各軸を明示的に指定
    for i in range(3):
        obj.keyframe_insert(data_path="rotation_euler", index=i)
    
    _ensure_linear_interpolation_for_object(obj, frame)
    bpy.context.scene.frame_set(current_frame)


def _set_camera_location_keyframe(obj, frame, loc):
    """カメラの位置キーフレームを設定（位置制限付き）
    
    カメラの位置が ±CAMERA_LOCATION_MAX 範囲内に収まるようクランプし、
    Blender 5.x のアクションレイヤーシステムによる異常値の拡散を防止する。
    """
    x, y, z = loc if isinstance(loc, tuple) else (loc.x, loc.y, loc.z)
    
    # 位置を安全な範囲にクランプ
    x, y, z = _clamp_camera_location(x, y, z)
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    obj.location = (x, y, z)
    if obj.animation_data is None:
        obj.animation_data_create()
    
    # locationのみをキーフレームとして挿入（rotationは含めない）
    for i in range(3):
        obj.keyframe_insert(data_path="location", index=i)
    
    _ensure_linear_interpolation_for_object(obj, frame)
    
    # キーフレーム挿入後に位置が維持されているか確認・修正
    if abs(obj.location.x - x) > 0.01 or abs(obj.location.y - y) > 0.01 or abs(obj.location.z - z) > 0.01:
        obj.location = (x, y, z)
    
    bpy.context.scene.frame_set(current_frame)


def _get_action_name_for_object(obj):
    """オブジェクトの名前から推測されるアクション名を返す"""
    return f"{obj.name}アクション"


def _clear_old_actions_for_object(obj):
    """bpy.data.actions からこのオブジェクト関連の旧アクションを全て削除（包含的）"""
    base_name = _get_action_name_for_object(obj)
    removed = []
    
    actions_to_check = list(bpy.data.actions.keys())
    for action_name in actions_to_check:
        # 全ての関連アクションを削除（現在のものも含む。後で再作成するため問題なし）
        if base_name in action_name or obj.name.replace('_', '').replace(' ', '') in action_name.replace('_', '').replace(' ', ''):
            try:
                action = bpy.data.actions.get(action_name)
                if action is not None and action.users <= 1:
                    bpy.data.actions.remove(action)
                    removed.append(action_name)
            except ReferenceError:
                pass
    
    if removed:
        print(f"    {obj.name}: 旧アクション {removed} を削除")


def _clear_animation_data(obj):
    """オブジェクトのアニメーションデータを完全に消去"""
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
