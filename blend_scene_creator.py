"""
Blenderスタンドアロンスクリプト - コマンドラインから直接実行可能

使い方:
    blender --background --python blend_scene_creator.py
    python run.py
"""

import bpy
import os
import math
import sys
import struct
import json
import time
from mathutils import Vector

# ============================================================
# glTFアドオンを強制的に有効化
# ============================================================
addon_name = "io_scene_gltf2"

try:
    # アドオンが既に有効か確認
    if addon_name not in bpy.context.preferences.addons:
        # アドオンを有効化（ビルトインアドオンとして）
        result = bpy.ops.preferences.addon_enable(module=addon_name)
        if 'FINISHED' in str(result):
            print("glTFアドオンを有効化しました")
        else:
            print(f"glTFアドオンの有効化結果: {result}")
    else:
        print("glTFアドオンは既に有効です")
except Exception as e:
    print(f"glTFアドオンの有効化中にエラーが発生しました: {e}")

# アドオンが完全に登録されるのを待つ
print("glTFオペレーターが利用可能になるのを待機中...")
for i in range(10):
    if hasattr(bpy.ops.wm, 'gltf_import'):
        print(f"glTFオペレーターが見つかりました（{i/10:.1f}秒後）")
        break
    time.sleep(0.5)
else:
    print("警告: glTFオペレーターが見つかりません。代わりにbpy.ops.wm.linkを使用します。")

# ============================================================
# 設定変数（ここを変更して使い回し可能）
# ============================================================
CARS = {
    "carA": {
        "name": "Corolla Cross",
        "glb_path": r"C:\3d\Modly\glb\colloraCross2025.glb",
        "position": (-2.0, 0, 0),
        "color": (0.8, 0.2, 0.2),
        # サイズ（mm）: 全長4460 × 全幅1825 × 全高1620, ホイールベース2640
        "dimensions_mm": {"length": 4460, "width": 1825, "height": 1620},
    },
    "carB": {
        "name": "Land Cruiser",
        "glb_path": r"C:\3d\Modly\glb\colloraCross2026.glb",
        "position": (2.0, 0, 0),
        "color": (0.2, 0.2, 0.8),
        # サイズ（mm）: 全長4950 × 全幅1930 × 全高1875, ホイールベース2850
        "dimensions_mm": {"length": 4950, "width": 1930, "height": 1875},
    },
}
# ============================================================


def clear_scene():
    """シーン内のすべてのメッシュオブジェクトを削除（初期化関数）"""
    # デフォルトの立方体を削除
    if "Cube" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)
    
    # ライトを削除
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT' and obj.name != "KeyLight":
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # カメラを削除（デフォルト以外）
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA' and obj.name != "ComparisonCamera":
            bpy.data.objects.remove(obj, do_unlink=True)
    
    print("シーンクリア完了")


def import_glb_file(file_path):
    """GLBファイルをBlenderにインポートし、メインオブジェクトを返す"""
    if not os.path.exists(file_path):
        print(f"エラー: ファイルが見つかりません - {file_path}")
        return None
    
    # glTFアドオンが有効か確認
    addon_name = "io_scene_gltf2"
    
    if addon_name not in bpy.context.preferences.addons:
        print(f"警告: glTFアドオンが有効になっていません。")
        return None
    
    try:
        # インポート前に存在するオブジェクトのリストを取得
        objects_before = set(bpy.data.objects.keys())
        
        # bpy.ops.import_scene.gltf を使用してインポート
        if not hasattr(bpy.ops.import_scene, 'gltf'):
            print("エラー: bpy.ops.import_scene.gltf が利用できません。")
            return None
        
        print(f"GLBファイルをインポート中: {file_path}")
        result = bpy.ops.import_scene.gltf(filepath=file_path)
        
        if 'FINISHED' not in str(result):
            print(f"インポートが失敗しました: {result}")
            return None
        
        # インポート後に追加された新しいオブジェクトを取得
        objects_after = set(bpy.data.objects.keys())
        new_object_names = objects_after - objects_before
        
        if not new_object_names:
            print("警告: インポートされたオブジェクトが見つかりません")
            return None
        
        # 最初のメッシュオブジェクトを返す
        for obj_name in new_object_names:
            obj = bpy.data.objects[obj_name]
            if obj.type in ('MESH', 'EMPTY'):
                print(f"成功: '{obj.name}' ({obj.type}) をインポートしました")
                return obj
        
        # メッシュもEMPTYもない場合は、最初のオブジェクトを返す
        first_obj = bpy.data.objects[list(new_object_names)[0]]
        print(f"成功: '{first_obj.name}' ({first_obj.type}) をインポートしました")
        return first_obj
        
    except Exception as e:
        print(f"エラー: GLBインポートに失敗しました - {e}")
        import traceback
        traceback.print_exc()
        return None


def create_grid_floor():
    """サイバー空間用の発光グリッド床面を作成する"""
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    grid = bpy.context.active_object
    grid.name = "CyberGrid"
    
    grid_mat_name = "NeonGridMaterial"
    
    if grid_mat_name in bpy.data.materials:
        grid.data.materials.clear()
        grid.data.materials.append(bpy.data.materials[grid_mat_name])
        return grid
    
    grid_mat = bpy.data.materials.new(name=grid_mat_name)
    grid_mat.use_nodes = True
    nodes = grid_mat.node_tree.nodes
    links = grid_mat.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (800, 0)
    
    mix_node = nodes.new(type='ShaderNodeMix')
    mix_node.location = (500, 0)
    mix_node.inputs['Factor'].default_value = 0.4
    
    grid_emission = nodes.new(type='ShaderNodeEmission')
    grid_emission.location = (200, 200)
    grid_emission.inputs['Color'].default_value = (0.0, 1.0, 1.0, 1.0)
    grid_emission.inputs['Strength'].default_value = 5.0
    
    base_emission = nodes.new(type='ShaderNodeEmission')
    base_emission.location = (200, -100)
    base_emission.inputs['Color'].default_value = (0.05, 0.05, 0.15, 1.0)
    base_emission.inputs['Strength'].default_value = 1.0
    
    # Mathノードを使用して加算（Blender 5.2互換）
    math_node = nodes.new(type='ShaderNodeMath')
    math_node.operation = 'ADD'
    math_node.location = (400, 100)
    
    # 定数値を追加（Emission出力の値を使用）
    constant_node = nodes.new(type='ShaderNodeValToRGB')
    constant_node.location = (400, -50)
    
    links.new(base_emission.outputs['Emission'], math_node.inputs[0])
    links.new(grid_emission.outputs['Emission'], math_node.inputs[1])
    links.new(math_node.outputs[0], mix_node.inputs[1])
    links.new(base_emission.outputs['Emission'], mix_node.inputs[2])
    links.new(mix_node.outputs[0], output_node.inputs['Surface'])
    
    grid.data.materials.clear()
    grid.data.materials.append(grid_mat)
    
    print(f"グリッドマテリアル作成完了: {grid_mat_name}")
    return grid


def create_clay_material(name, color):
    """単色クレイモデル用のマテリアルを作成する（Principled BSDFベース）"""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    
    nodes = material.node_tree.nodes
    nodes.clear()
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)
    
    # Principled BSDF ノード（クレイモデル用）
    principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled_node.location = (100, 0)
    # Blender 5.x では 'Base Color'、それ以前は 'Color'
    if 'Base Color' in principled_node.inputs:
        principled_node.inputs['Base Color'].default_value = (*color, 1.0)
    else:
        principled_node.inputs['Color'].default_value = (*color, 1.0)
    principled_node.inputs['Roughness'].default_value = 0.8
    principled_node.inputs['Metallic'].default_value = 0.0
    
    material.node_tree.links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
    
    return material


def setup_transparency_animation(car_object, start_frame, end_frame, start_alpha, end_alpha):
    """車のマテリアル不透明度をアニメーションさせる（EEVEE透過対応）"""
    if car_object is None:
        print(f"エラー: オブジェクトがNoneです")
        return
    
    # マテリアルが存在するか確認
    if len(car_object.data.materials) == 0:
        print(f"警告: {car_object.name} にマテリアルが設定されていません")
        return
    
    material = car_object.data.materials[0]
    
    # ノードベースのマテリアルでない場合はスキップ
    if not material.use_nodes:
        print(f"警告: {material.name} はノードベースではありません")
        return
    
    # EEVEEで透過が正しくブレンドされるよう、ブレンドモードを 'BLEND' に設定
    material.blend_method = 'BLEND'
    print(f"{car_object.name} のマテリアルブレンドモードを BLEND に設定しました")
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    # Principled BSDF ノードを検索
    principled_node = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_node = node
            break
    
    if principled_node is None:
        print(f"警告: {material.name} にPrincipled BSDFノードが見つかりません")
        return
    
    # Alpha入力が存在するか確認（Blender 4.0+ では 'Alpha'、それ以前は 'Specular Tint' の下）
    if 'Alpha' in principled_node.inputs:
        alpha_input = principled_node.inputs['Alpha']
        
        # スタートフレームでセット
        car_object.location = car_object.location  # 何もしないが更新を強制
        alpha_input.default_value = start_alpha
        alpha_input.keyframe_insert(data_path="default_value", frame=start_frame)
        
        # エンドフレームでセット
        alpha_input.default_value = end_alpha
        alpha_input.keyframe_insert(data_path="default_value", frame=end_frame)
        
        print(f"不透明度アニメーション設定: {car_object.name} ({start_frame}-{end_frame}) Alpha: {start_alpha}→{end_alpha}")
    else:
        # Alpha入力が存在しない場合は、Base ColorのAlpha成分を操作する代替方法
        # ただし、これはキーフレームが効かない可能性があるため注意が必要
        print(f"警告: {material.name} にAlpha入力が見つかりません。Base Colorでの透過制御を試みます...")
        
        # Base Colorの入力を取得（Blender 5.x）
        if 'Base Color' in principled_node.inputs:
            base_color = principled_node.inputs['Base Color']
            
            # スタートフレーム - color パラメータが必要
            # ここではデフォルトの赤色を使用
            start_color = (1.0, 0.2, 0.2)  # 赤
            base_color.default_value = (*start_color, start_alpha)
            base_color.keyframe_insert(data_path="default_value", frame=start_frame)
            
            # エンドフレーム
            base_color.default_value = (*start_color, end_alpha)
            base_color.keyframe_insert(data_path="default_value", frame=end_frame)
            
            print(f"Base Colorアニメーション設定: {car_object.name} ({start_frame}-{end_frame})")
        else:
            print(f"エラー: Base Color入力も存在しません。透過アニメーションを実行できません。")


def setup_camera_animation(camera, start_frame, end_frame, start_location, end_location, start_rotation, end_rotation):
    """カメラの位置と回転をアニメーションさせる"""
    if camera is None:
        print("エラー: カメラがシーンに設定されていません")
        return
    
    # スタートフレームでセット
    camera.location = start_location
    camera.rotation_euler = start_rotation
    camera.keyframe_insert(data_path="location", frame=start_frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    
    # エンドフレームでセット
    camera.location = end_location
    camera.rotation_euler = end_rotation
    camera.keyframe_insert(data_path="location", frame=end_frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    
    print(f"カメラアニメーション設定: {camera.name} ({start_frame}-{end_frame})")
    print(f"  - スタート位置: {start_location}, 回転: {[round(e, 3) for e in start_rotation]}")
    print(f"  - エンド位置: {end_location}, 回転: {[round(e, 3) for e in end_rotation]}")


def create_placeholder_car(key, color, location):
    """GLBファイルがない場合のプレースホルダー車（円柱ベース）"""
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.8, depth=2.5, location=location)
    body = bpy.context.active_object
    body.name = f"{key}_body"
    body.rotation_euler = (0, 0, math.pi / 2)
    
    mat_name = f"clay_{key}"
    clay_material = create_clay_material(mat_name, color)
    body.data.materials.clear()
    body.data.materials.append(clay_material)
    
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.6, location=(location[0] + 0.3, location[1] + 0.5, location[2] + 0.8))
    cabin = bpy.context.active_object
    cabin.name = f"{key}_cabin"
    cabin.scale = (1.2, 0.7, 0.8)
    
    cabin_mat_name = f"clay_{key}_cabin"
    cabin_material = create_clay_material(cabin_mat_name, color)
    cabin.data.materials.clear()
    cabin.data.materials.append(cabin_material)
    
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    cabin.select_set(True)
    bpy.ops.object.join()
    
    print(f"プレースホルダー車作成: {body.name} at {location}")
    return body


def scale_object_to_dimensions(obj, target_length_mm, target_width_mm, target_height_mm):
    """オブジェクトを指定した寸法（mm）にスケールする"""
    # 現在のサイズを取得（Blender単位: メートル）
    current_x = abs(obj.dimensions.x)
    current_y = abs(obj.dimensions.y)
    current_z = abs(obj.dimensions.z)
    
    # mmをBlender単位（メートル）に変換
    target_length_m = target_length_mm / 1000.0
    target_width_m = target_width_mm / 1000.0
    target_height_m = target_height_mm / 1000.0
    
    # スケール係数を計算（全長→Y軸、全幅→X軸、全高→Z軸）
    if current_x > 0:
        scale_x = target_width_m / current_x   # 全幅をX軸に適用
    else:
        scale_x = 1.0
    
    if current_y > 0:
        scale_y = target_length_m / current_y  # 全長をY軸に適用
    else:
        scale_y = 1.0
    
    if current_z > 0:
        scale_z = target_height_m / current_z  # 全高をZ軸に適用
    else:
        scale_z = 1.0
    
    # スケールを適用
    obj.scale = (scale_x, scale_y, scale_z)
    
    print(f"スケール適用: {obj.name} -> ({scale_x:.3f}, {scale_y:.3f}, {scale_z:.3f})")
    return obj


def auto_ground_car(car_object):
    """オブジェクトのバウンディングボックスから最低点を計算し、Z=0.0 に接地するオフセットを適用"""
    # オブジェクトとシーンを完全に更新
    car_object.update_tag()
    car_object.data.update_tag()
    bpy.context.view_layer.update()
    
    # ローカル座標系のバウンディングボックスを取得（ワールド空間に変換済み）
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"警告: {car_object.name} のバウンディングボックスが取得できません")
        return 0.0
    
    # 8隅のローカル座標
    corners_local = [Vector(corner) for corner in local_bounds]
    
    # ワールド座標に変換（行列適用）
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    # Z軸の最小値（一番低い位置）を取得
    min_z = min(corner.z for corner in corners_world)
    
    # 接地オフセットを計算（最低点を Z=0.0 に合わせる）
    offset_z = -min_z
    
    # オブジェクトのZ位置にオフセットを適用
    car_object.location.z += offset_z
    
    print(f"自動接地: {car_object.name} -> ズオフセット: {offset_z:.4f}, 新 Z 位置: {car_object.location.z:.4f}")
    
    # グローバル変数に保存（アニメーションで再利用）
    grounded_z_positions[car_object.name] = car_object.location.z
    
    return offset_z

# 追加：バウンディングボックスの最小Z値を返す関数
def get_car_ground_offset(car_object):
    """車の接地オフセットを計算する（デバッグ用）"""
    car_object.update_tag()
    car_object.data.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        return 0.0
    
    corners_local = [Vector(corner) for corner in local_bounds]
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    min_z = min(corner.z for corner in corners_world)
    offset_z = -min_z
    
    print(f"  接地オフセット: {offset_z:.4f}, 最低点 Z={min_z:.4f}")
    return offset_z

# 追加：バウンディングボックスの最小Z値を返す関数
def get_car_ground_offset(car_object):
    """車の接地オフセットを計算する（デバッグ用）"""
    car_object.update_tag()
    car_object.data.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        return 0.0
    
    corners_local = [Vector(corner) for corner in local_bounds]
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    min_z = min(corner.z for corner in corners_world)
    offset_z = -min_z
    
    print(f"  接地オフセット: {offset_z:.4f}, 最低点 Z={min_z:.4f}")
    return offset_z

# 追加：バウンディングボックスの最小Z値を返す関数
def get_car_ground_offset(car_object):
    """車の接地オフセットを計算する（デバッグ用）"""
    car_object.update_tag()
    car_object.data.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        return 0.0
    
    corners_local = [Vector(corner) for corner in local_bounds]
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    min_z = min(corner.z for corner in corners_world)
    offset_z = -min_z
    
    print(f"  接地オフセット: {offset_z:.4f}, 最低点 Z={min_z:.4f}")
    return offset_z

# 追加：バウンディングボックスの最小Z値を返す関数
def get_car_ground_offset(car_object):
    """車の接地オフセットを計算する（デバッグ用）"""
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        return 0.0
    
    corners_local = [Vector(corner) for corner in local_bounds]
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    min_z = min(corner.z for corner in corners_world)
    offset_z = -min_z
    
    print(f"  接地オフセット: {offset_z:.4f}, 最低点 Z={min_z:.4f}")
    return offset_z

# 追加：バウンディングボックスの最小Z値を返す関数
def get_car_ground_offset(car_object):
    """車の接地オフセットを計算する（デバッグ用）"""
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        return 0.0
    
    corners_local = [Vector(corner) for corner in local_bounds]
    corners_world = [car_object.matrix_world @ corner for corner in corners_local]
    
    min_z = min(corner.z for corner in corners_world)
    offset_z = -min_z
    
    print(f"  接地オフセット: {offset_z:.4f}, 最低点 Z={min_z:.4f}")
    return offset_z


def setup_car(key, car_data, imported_object):
    """車の設定（位置、名前、マテリアル、サイズ）を適用"""
    if imported_object is None:
        return None
    
    imported_object.name = f"{key}_{car_data['name']}"
    imported_object.data.name = f"{key}_{car_data['name']}.Mesh"
    
    # サイズ指定がある場合はスケール適用
    if 'dimensions_mm' in car_data:
        dims = car_data['dimensions_mm']
        scale_object_to_dimensions(
            imported_object,
            dims.get('length', 4460),
            dims.get('width', 1825),
            dims.get('height', 1620)
        )
    
    # 初期位置を設定（後で接地処理で調整される）
    initial_location = list(car_data['position'])  # tuple を list に変換
    imported_object.location = initial_location
    
    # オブジェクトの原点を幾何中心に設定
    bpy.context.view_layer.objects.active = imported_object
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
    
    # 自動接地処理：バウンディングボックスから最低点を計算して Z=0.0 に合わせる
    auto_ground_car(imported_object)
    
    mat_name = f"clay_{key}_{car_data['name']}"
    clay_material = create_clay_material(mat_name, car_data['color'])
    
    if len(imported_object.data.materials) == 0:
        imported_object.data.materials.append(clay_material)
    else:
        imported_object.data.materials[0] = clay_material
    
    return imported_object

# グローバル変数として接地後のZ位置を保存
grounded_z_positions = {}


def setup_camera_and_lighting():
    """カメラとライティングを設定する"""
    scene = bpy.context.scene
    
    # 既存のカメラを削除（ComparisonCamera以外）
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA' and obj.name != "ComparisonCamera":
            bpy.data.objects.remove(obj, do_unlink=True)
    
    bpy.ops.object.camera_add(location=(5, -5, 3))
    camera = bpy.context.active_object
    camera.name = "ComparisonCamera"
    scene.camera = camera
    
    target_location = (0.0, 0.0, 0.0)
    # カメラからターゲットへの方向を計算
    dx = target_location[0] - camera.location[0]
    dy = target_location[1] - camera.location[1]
    dz = target_location[2] - camera.location[2]
    # Y軸周りの回転（水平方向）
    yaw = math.atan2(dx, dy)
    # X軸周りの回転（垂直方向）
    pitch = math.atan2(dz, math.sqrt(dx*dx + dy*dy))
    camera.rotation_euler = (pitch, 0.0, -yaw)
    
    bpy.ops.object.light_add(type='AREA', location=(3, -3, 5))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 100
    key_light.data.size = 3
    
    bpy.ops.object.light_add(type='AREA', location=(-3, 3, 4))
    sub_light = bpy.context.active_object
    sub_light.name = "SubLight"
    sub_light.data.energy = 50
    sub_light.data.size = 2
    
    bpy.ops.object.light_add(type='SPOT', location=(0, 5, 3))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 80
    rim_light.data.spot_size = 1.2
    
    print(f"カメラを設定しました: {camera.name}")
    print(f"  - 位置: {camera.location}")
    
    return camera


def setup_world_background():
    """世界背景を黒に設定する"""
    world = bpy.data.worlds["World"]
    world.node_tree.nodes["Background"].inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    world.node_tree.nodes["Background"].inputs['Strength'].default_value = 0.0
    print("世界背景を黒に設定しました")


# ============================================================
# アニメーション設定関数（ステップ2）
# ============================================================
def setup_car_animation(car_object, start_frame, end_frame, start_x, end_x):
    """車の位置アニメーションを設定"""
    # X位置のキーフレームを設定
    car_object.location = (start_x, 0.0, 0.0)
    car_object.keyframe_insert(data_path="location", frame=start_frame)
    
    car_object.location = (end_x, 0.0, 0.0)
    car_object.keyframe_insert(data_path="location", frame=end_frame)
    
    print(f"アニメーション設定: {car_object.name} ({start_frame}-{end_frame}フレーム)")


def apply_clay_material_to_object(object_name, color_rgb):
    """指定されたオブジェクトにクレイマテリアルを適用"""
    if object_name not in bpy.data.objects:
        print(f"警告: オブジェクト '{object_name}' が見つかりません")
        return
    
    obj = bpy.data.objects[object_name]
    
    # マテリアル名（重複防止）
    mat_name = f"clay_{object_name}"
    
    if mat_name not in bpy.data.materials:
        # 新しいクレイマテリアルを作成
        material = create_clay_material(mat_name, color_rgb)
    else:
        material = bpy.data.materials[mat_name]
    
    # オブジェクトにマテリアルを適用
    if len(obj.data.materials) == 0:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material
    
    print(f"マテリアル適用完了: {object_name} -> {mat_name}")


# ============================================================
# ビューポートシェーディング設定（ステップ3）
# ============================================================
def setup_viewport_shading(shading_type='MATERIAL'):
    """3Dビューポートのシェーディングモードを設定"""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    # シェーディングモードを設定（MATERIAL, RENDER, TEXTURED など）
                    space.shading.type = shading_type
    print(f"ビューポートシェーディングを {shading_type} モードに設定しました")


# ============================================================
# メイン処理
# ============================================================
def main():
    print("=" * 50)
    print("3Dシーン作成パイプライン開始")
    print("=" * 50)
    
    # シーンをクリア
    clear_scene()
    
    # グリッド床面を作成
    grid = create_grid_floor()
    print(f"グリッド床面を作成しました: {grid.name}")
    
    # 世界背景を設定
    setup_world_background()
    
    # GLBファイルをインポート
    imported_cars = {}
    
    for key, car_data in CARS.items():
        print(f"\n--- {key} ({car_data['name']}) を読み込み中: {car_data['glb_path']} ---")
        
        glb_path = car_data['glb_path']
        
        if not os.path.exists(glb_path):
            print(f"エラー: GLBファイルが見つかりません - {glb_path}")
            print("GLBファイルがない場合はシーンを作成できません。処理を停止します。")
            sys.exit(1)
        
        imported_object = import_glb_file(glb_path)
        
        if imported_object is None:
            print(f"エラー: GLBインポートに失敗しました - {glb_path}")
            print("GLBファイルが破損しているか、形式が正しくありません。処理を停止します。")
            sys.exit(1)
        
        setup_car(key, car_data, imported_object)
        imported_cars[key] = imported_object
        print(f"成功: '{imported_object.name}' をインポートしました")
        print(f"  - 位置: {imported_object.location}")
    
    # 結果を表示
    print("\n=== インポート結果 ===")
    for key, obj in imported_cars.items():
        print(f"{key}: {obj.name} at {obj.location}")
    
    # カメラとライティングを設定
    camera = setup_camera_and_lighting()
    
    # =============================================
    # アニメーション設定（ステップ2）
    # =============================================
    print("\n=== アニメーション設定を開始 ===")
    
    # シーンフレーム範囲を設定
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = 120
    scene.render.fps = 24
    print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end} (fps={scene.render.fps})")
    
    # 車のアニメーション設定（キーフレーム）
    for key, car_data in CARS.items():
        # 車オブジェクトを取得
        car_obj = imported_cars.get(key)
        if not car_obj:
            print(f"警告: {key} の車オブジェクトが見つかりません")
            continue
        
        # 接地後のZ位置を保持（アニメーションでも維持）
        grounded_z = grounded_z_positions.get(car_obj.name, 0.0)
        
        # 0フレーム：初期位置に出現
        car_obj.location = (car_data['position'][0], 0.0, grounded_z)
        car_obj.keyframe_insert(data_path="location", frame=0)
        
        # 30フレーム：初期位置を維持（キーフレーム）
        car_obj.location = (car_data['position'][0], 0.0, grounded_z)
        car_obj.keyframe_insert(data_path="location", frame=30)
        
        # 90フレーム：中央に到達
        car_obj.location = (0.0, 0.0, grounded_z)
        car_obj.keyframe_insert(data_path="location", frame=90)
        
        # 120フレーム：中央を維持（キーフレーム）
        car_obj.location = (0.0, 0.0, grounded_z)
        car_obj.keyframe_insert(data_path="location", frame=120)
        
        print(f"アニメーション設定完了: {car_obj.name}")
    
    # =============================================
    # 新しい演出：半透明化アニメーション（フレーム30-90）
    # =============================================
    print("\n=== 半透明化アニメーションを設定 ===")
    
    # 両車のマテリアルに不透明度アニメーションを追加
    for key, car_obj in imported_cars.items():
        setup_transparency_animation(car_obj, 30, 90, 1.0, 0.4)
    
    print("半透明化アニメーション設定完了")
    
    # =============================================
    # 新しい演出：カメラ移動アニメーション（フレーム90-120）
    # =============================================
    print("\n=== カメラ移動アニメーションを設定 ===")
    
    # 初期カメラ位置と回転を取得
    camera = scene.camera
    if camera is None:
        print("エラー: カメラが設定されていません")
    else:
        start_location = list(camera.location)
        start_rotation = list(camera.rotation_euler)
        
        # 真上からの俯瞰アングル（X軸回転90度、Z軸位置10m）
        end_location = (0.0, 0.0, 10.0)
        end_rotation = [math.radians(90), 0.0, 0.0]  # X軸を90度回転
        
        setup_camera_animation(camera, 90, 120, start_location, end_location, start_rotation, end_rotation)
    
    print("カメラ移動アニメーション設定完了")
    
    # マテリアルの再適用（確認用）
    for key, car_data in CARS.items():
        apply_clay_material_to_object(imported_cars[key].name, car_data['color'])
    
    print("\n=== アニメーション設定完了 ===")
    
    # =============================================
    # ビューポートシェーディング設定（ステップ3）
    # =============================================
    print("\n=== ビューポートシェーディングを設定 ===")
    setup_viewport_shading()  # デフォルト: MATERIAL モード
    
    print("\n" + "=" * 50)
    print("シーン作成完了！")
    print("=" * 50)
    
    return imported_cars


# スクリプトとして実行された場合
if __name__ == "__main__":
    result = main()
    
    # シーン作成後にBlenderを自動終了しない（ウィンドウを開いたまま）
