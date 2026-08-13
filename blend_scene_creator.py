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
# グローバル変数（内部用 - 通常は変更不要）
# ============================================================
grounded_z_positions = {}  # 接地後のZ位置を保存する辞書

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
# ★ 車の設定は cars_config.json で管理しています ★
# ============================================================
# GLBファイルパスや寸法を変更する場合は、cars_config.json を編集してください。
# このスクリプトは起動時に自動的に読み込みます。
# ============================================================

def load_cars_config():
    """cars_config.json から車の設定を読み込む"""
    config_path = os.path.join(SCRIPT_DIR, "cars_config.json")
    
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイルが見つかりません - {config_path}")
        print("cars_config.json を作成してください。")
        sys.exit(1)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # JSONのリスト形式をタプルに変換（position, color）
        for key in config:
            if "position" in config[key]:
                config[key]["position"] = tuple(config[key]["position"])
            if "color" in config[key]:
                config[key]["color"] = tuple(config[key]["color"])
        
        print(f"設定ファイルを読み込みました: {config_path}")
        for key, car_data in config.items():
            dims = car_data.get("dimensions_mm", {})
            print(f"  - {key}: {car_data['name']}")
            print(f"    GLBパス: {car_data['glb_path']}")
            print(f"    寸法: 全長{dims.get('length', '?')}mm × 全幅{dims.get('width', '?')}mm × 全高{dims.get('height', '?')}mm")
        
        return config
    
    except json.JSONDecodeError as e:
        print(f"エラー: cars_config.json の形式が正しくありません - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 設定ファイルの読み込みに失敗しました - {e}")
        sys.exit(1)


# ============================================================
# シーン初期化・インポート関数群
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


# ============================================================
# マテリアル・床面作成関数群
# ============================================================
def create_grid_floor():
    """サイバー空間用の発光グリッド床面を作成する（1M間隔のネオン線）"""
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
    
    # 既存ノードをすべて削除
    for node in nodes:
        nodes.remove(node)
    
    # Output Material ノード
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (1000, 0)
    
    # ColorRamp ノード（線と背景を分離）
    color_ramp = nodes.new(type='ShaderNodeValToRGB')
    color_ramp.location = (600, 0)
    
    # ColorRamp の要素を設定：小数部分が0に近い位置（整数座標）で線を表示
    # X - FLOOR(X) の結果は 0〜1 の範囲。0に近い=整数座標=グリッド線
    color_ramp.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)  # 白（発光強度MAX）
    color_ramp.color_ramp.elements[0].position = 0.0
    
    color_ramp.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)  # 完全な黒（発光なし）
    color_ramp.color_ramp.elements[1].position = 0.03  # 線幅をさらに細く調整
    
    # Emission ノード（ネオン発光）- Colorは固定、StrengthをColorRampで制御
    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.location = (850, 0)
    emission_node.inputs['Color'].default_value = (0.0, 1.0, 1.0, 1.0)  # シアンブルー（固定）
    emission_node.inputs['Strength'].default_value = 6.0  # 基準強度（ColorRampで制御される）
    
    # Math ノード群：正弦波ベースで正確な1M間隔グリッドを計算
    # X座標からグリッド線を抽出
    separate_xyz_x = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_xyz_x.location = (250, 150)
    
    math_floor_x = nodes.new(type='ShaderNodeMath')
    math_floor_x.operation = 'FLOOR'
    math_floor_x.location = (400, 200)
    
    math_subtract_x = nodes.new(type='ShaderNodeMath')
    math_subtract_x.operation = 'SUBTRACT'
    math_subtract_x.location = (550, 180)
    
    # Y座標からグリッド線を抽出
    separate_xyz_y = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_xyz_y.location = (250, -150)
    
    math_floor_y = nodes.new(type='ShaderNodeMath')
    math_floor_y.operation = 'FLOOR'
    math_floor_y.location = (400, -200)
    
    math_subtract_y = nodes.new(type='ShaderNodeMath')
    math_subtract_y.operation = 'SUBTRACT'
    math_subtract_y.location = (550, -180)
    
    # XとYのグリッド線を組み合わせる（最小値で両方の線を表示）
    math_min_xy = nodes.new(type='ShaderNodeMath')
    math_min_xy.operation = 'MINIMUM'
    math_min_xy.location = (700, 0)
    
    # Mapping ノード（グリッド間隔を正確に制御）
    mapping_node = nodes.new(type='ShaderNodeMapping')
    mapping_node.location = (50, 0)
    # Scale を (1, 1, 1) に設定 → ワールド座標で正確に1m四方のグリッド間隔
    mapping_node.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    
    # Texture Coordinate ノード（Generated を使用）
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-200, 0)
    
    # ノード接続：Texture Coordinate (Object) → SeparateXYZ/Math → ColorRamp → Emission → Output
    # Object座標を使用することで、ワールド座標で正確に1M間隔のグリッドを表示
    links.new(tex_coord.outputs['Object'], mapping_node.inputs['Vector'])
    
    # X軸のグリッド線計算
    links.new(mapping_node.outputs['Vector'], separate_xyz_x.inputs['Vector'])
    links.new(separate_xyz_x.outputs['X'], math_floor_x.inputs[0])
    links.new(math_floor_x.outputs[0], math_subtract_x.inputs[1])  # FLOOR(X) を引数として使用
    links.new(separate_xyz_x.outputs['X'], math_subtract_x.inputs[0])  # X - FLOOR(X) で小数部分を取得
    
    # Y軸のグリッド線計算
    links.new(mapping_node.outputs['Vector'], separate_xyz_y.inputs['Vector'])
    links.new(separate_xyz_y.outputs['Y'], math_floor_y.inputs[0])
    links.new(math_floor_y.outputs[0], math_subtract_y.inputs[1])  # FLOOR(Y) を引数として使用
    links.new(separate_xyz_y.outputs['Y'], math_subtract_y.inputs[0])  # Y - FLOOR(Y) で小数部分を取得
    
    # XとYのグリッド線を組み合わせ（MINIMUMで両方の線を表示）
    links.new(math_subtract_x.outputs[0], math_min_xy.inputs[0])
    links.new(math_subtract_y.outputs[0], math_min_xy.inputs[1])
    
    # ColorRamp で閾値処理して発光強度を制御（Colorは固定のシアンブルー）
    links.new(math_min_xy.outputs[0], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], emission_node.inputs['Strength'])  # Strengthに接続
    links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
    
    grid.data.materials.clear()
    grid.data.materials.append(grid_mat)
    
    print(f"グリッドマテリアル作成完了: {grid_mat_name}")
    print("  - グリッド間隔: 1.0m四方（正確）")
    print("  - 線色: シアンブルー (RGB: 0, 1, 1)")
    print("  - 発光強度: 6.0")
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


# ============================================================
# 車の設定・配置関数群（スケール・接地・マテリアル適用）
# ============================================================
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
    
    # 青い車の場合、より鮮明な青色に補正（JSONは変更しない）
    adjusted_color = car_data['color']
    if key == "carB" and car_data['color'][2] > car_data['color'][0]:  # 青成分が強い場合
        adjusted_color = (0.1, 0.4, 1.0)  # より鮮明な青色
    
    mat_name = f"clay_{key}_{car_data['name']}"
    clay_material = create_clay_material(mat_name, adjusted_color)
    
    if len(imported_object.data.materials) == 0:
        imported_object.data.materials.append(clay_material)
    else:
        imported_object.data.materials[0] = clay_material
    
    return imported_object

# ============================================================
# カメラ・ライティング設定関数群
# ============================================================
def setup_camera_and_lighting():
    """カメラとライティングを設定する"""
    scene = bpy.context.scene
    
    # 既存のカメラを削除（ComparisonCamera以外）
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA' and obj.name != "ComparisonCamera":
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # カメラを作成 - 初期位置を1.7倍に拡大（2台の車が画面にゆとりを持って収まるように）
    camera_location = (6.5, -6.5, 4.0)  # 修正前より少し遠く（元の位置の約1.3倍）
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.active_object
    camera.name = "ComparisonCamera"
    scene.camera = camera
    
    # 視野角を広げてより広い範囲が映るように（24mm相当）
    camera.data.lens = 24
    print(f"カメラの焦点距離を {camera.data.lens}mm に設定しました")
    
    # カメラの初期回転を設定（車の中心を見る）
    target_location = (0.0, 0.0, 1.5)  # 車の中心付近を見つめる
    dx = target_location[0] - camera.location[0]
    dy = target_location[1] - camera.location[1]
    dz = target_location[2] - camera.location[2]
    yaw = math.atan2(dx, dy)
    pitch = math.atan2(dz, math.sqrt(dx*dx + dy*dy))
    camera.rotation_euler = (pitch, 0.0, -yaw)
    
    # ライトもカメラの位置に合わせて調整（より広い照明範囲に）
    # カメラ位置 (8.5, -8.5, 4.5) から見た相対位置を維持しつつ1.7倍に拡大
    # ライトもカメラの位置に合わせて調整（より広い照明範囲に）
    # カメラ位置 (8.5, -8.5, 4.5) から見た相対位置を維持しつつ1.7倍に拡大
    bpy.ops.object.light_add(type='AREA', location=(8.5*0.6, -8.5*0.6, 7))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 800  # さらに明るさを抑える
    key_light.data.size = 3
    
    # SubLightもカメラに合わせて拡大
    bpy.ops.object.light_add(type='AREA', location=(-8.5*0.6, 8.5*0.6, 6))
    sub_light = bpy.context.active_object
    sub_light.name = "SubLight"
    sub_light.data.energy = 800  # さらに明るさを抑える
    sub_light.data.size = 2
    
    # RimLightもカメラに合わせて拡大
    bpy.ops.object.light_add(type='SPOT', location=(0, 7*1.7, 5))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 800  # さらに明るさを抑える
    rim_light.data.spot_size = 1.2
    
    print(f"カメラを設定しました: {camera.name}")
    print(f"  - 位置: {camera.location}")
    
    return camera


def setup_world_background():
    """世界背景を完全な漆黒（真っ黒）に設定する"""
    world = bpy.data.worlds["World"]
    # RGBすべてゼロで完全な黒、アルファ1.0
    world.node_tree.nodes["Background"].inputs['Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    # Strengthを0.0に設定して完全に暗闇にする
    world.node_tree.nodes["Background"].inputs['Strength'].default_value = 0.0
    print("世界背景を完全な漆黒（真っ黒）に設定しました")


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


# ============================================================
# 車の配置・整列関数群（リア端揃え）
# ============================================================
def align_cars_by_rear_simple(car_a, car_b):
    """2台の車のリア（後部）端をピッタリ揃える（シンプル版：左右配置用）"""
    # オブジェクトを完全に更新
    car_a.update_tag()
    car_a.data.update_tag()
    bpy.context.view_layer.update()
    car_b.update_tag()
    car_b.data.update_tag()
    bpy.context.view_layer.update()
    
    # ローカルバウンディングボックスを取得してワールド座標に変換
    local_bounds_a = car_a.bound_box
    corners_world_a = [car_a.matrix_world @ Vector(corner) for corner in local_bounds_a]
    local_bounds_b = car_b.bound_box
    corners_world_b = [car_b.matrix_world @ Vector(corner) for corner in local_bounds_b]
    
    # 車の前後方向の軸を判定（XまたはY）
    x_range_a = max(c.x for c in corners_world_a) - min(c.x for c in corners_world_a)
    y_range_a = max(c.y for c in corners_world_a) - min(c.y for c in corners_world_a)
    x_range_b = max(c.x for c in corners_world_b) - min(c.x for c in corners_world_b)
    y_range_b = max(c.y for c in corners_world_b) - min(c.y for c in corners_world_b)
    
    # 最も長い軸を前後方向とする
    if x_range_a >= y_range_a and x_range_b >= y_range_b:
        axis = 'x'
        print("車の前後方向：X軸")
    else:
        axis = 'y'
        print("車の前後方向：Y軸")
    
    # リア端の座標を取得（最小値）
    if axis == 'x':
        car_a_rear = min(c.x for c in corners_world_a)
        car_b_rear = min(c.x for c in corners_world_b)
    else:
        car_a_rear = min(c.y for c in corners_world_a)
        car_b_rear = min(c.y for c in corners_world_b)
    
    # オフセットを計算（carBがcarAより後ろにある場合、carAを前にずらす）
    offset = car_b_rear - car_a_rear
    print(f"リア端オフセット計算：{car_a.name}={car_a_rear:.4f}, {car_b.name}={car_b_rear:.4f} -> オフセット={offset:.4f}")
    
    return offset, axis


def setup_car_animation_aligned_simple(car_object, start_frame, end_frame, start_x, end_x, rear_offset, rear_axis):
    """リア端を揃えた位置へのアニメーションを設定（シンプル版）"""
    # 初期位置：リアオフセット分だけずらす
    if rear_axis == 'x':
        car_object.location = (start_x + rear_offset, 0.0, 0.0)
    else:
        car_object.location = (0.0, start_x + rear_offset, 0.0)
    car_object.keyframe_insert(data_path="location", frame=start_frame)
    
    # エンド位置：リア端がピッタリ揃う位置（オフセットなし）
    if rear_axis == 'x':
        car_object.location = (end_x, 0.0, 0.0)
    else:
        car_object.location = (0.0, end_x, 0.0)
    car_object.keyframe_insert(data_path="location", frame=end_frame)
    
    print(f"リア揃えアニメーション設定：{car_object.name} ({start_frame}-{end_frame}フレーム)")


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
# 3Dテキストラベル作成関数（ステップ4）
# ============================================================
def create_glowing_text_label(car_key, car_object, text_content, color_rgb):
    """車の足元に発光する3Dテキストラベルを作成し、車にペアレント設定"""
    if car_object is None:
        print(f"エラー: {car_key} の車オブジェクトがNoneです")
        return
    
    # テキストオブジェクトを生成（一時的な位置）
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.active_object
    text_obj.name = f"label_{car_key}"
    
    # JSONから取得した車種名を設定
    text_obj.data.body = text_content
    
    # テキストのサイズ設定（画面で読みやすい大きさに調整）
    text_obj.data.size = 0.35         # フォントサイズ（70%に縮小）
    text_obj.scale = (1.0, 1.0, 1.0)  # スケール
    
    # バウンディングボックスから車のフロント端を計算
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"警告: {car_object.name} のバウンディングボックスが取得できません")
        return
    
    corners_world = [car_object.matrix_world @ Vector(corner) for corner in local_bounds]
    
    # バウンディングボックスから車の中心と幅を計算（Y軸中央配置）
    min_x = min(c.x for c in corners_world)
    max_x = max(c.x for c in corners_world)
    min_y = min(c.y for c in corners_world)  # リア端（後部）のY座標

    # X軸の半幅を計算（ローカル座標系）
    half_width_x = (max_x - min_x) / 2.0

    # テキストを車のY軸中央、車体のすぐ横に配置（ローカル座標系）
    # carAは左側（X=-）、carBは右側（X=+）なので、それぞれ外側に配置
    if car_key == "carA":
        text_x_offset = -half_width_x - 0.15  # 車体の左側のすぐ横
    else:
        text_x_offset = -half_width_x - 0.15   # 車体の中央

    # テキストを車のリア端より後ろに配置（Y負方向）
    # carBの文字を上に（Y正方向へ）移動してcarAに近づける
    if car_key == "carA":
        text_y_offset = min_y - 0.2   # リア端からさらに後ろに0.5m
    else:
        text_y_offset = min_y + 0.3   # carBはもう少し上に（リア端から0.3m）
    text_obj.location = (text_x_offset, text_y_offset, 0.05)
    
    # Emissionマテリアルを作成（車の色と同じRGB）
    mat_name = f"emission_label_{car_key}"
    if mat_name in bpy.data.materials:
        emission_mat = bpy.data.materials[mat_name]
    else:
        emission_mat = bpy.data.materials.new(name=mat_name)
        emission_mat.use_nodes = True
        
        nodes = emission_mat.node_tree.nodes
        links = emission_mat.node_tree.links
        nodes.clear()
        
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (400, 0)
        
        emission_node = nodes.new(type='ShaderNodeEmission')
        emission_node.location = (100, 0)
        # 車の色と同じRGBを使用（アルファ=1.0）
        # 青い車の場合、より鮮明な青色に補正
        adjusted_color = color_rgb
        if car_key == "carB" and color_rgb[2] > color_rgb[0]:  # 青成分が強い場合
            adjusted_color = (0.1, 0.4, 1.0)  # より鮮明な青色
        emission_node.inputs['Color'].default_value = (*adjusted_color, 1.0)
        # ネオン風発光の強度
        emission_node.inputs['Strength'].default_value = 5.0
        
        links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
    
    # テキストにマテリアルを適用
    text_obj.data.materials.clear()
    text_obj.data.materials.append(emission_mat)
    
    # ★重要: テキストを車にペアレント設定（親子関係）
    # これにより、車のアニメーション中にテキストが自動で追従する
    text_obj.parent = car_object
    
    print(f"3Dテキストラベル作成完了: {text_obj.name} -> '{text_content}' (ペアレント: {car_object.name})")


# ============================================================
# メイン処理
# ============================================================
# カット番号とフレーム範囲の取得（環境変数から）
CUT_NUMBER = os.environ.get("CUT_NUMBER", "all")
FRAME_START_OVERRIDE = int(os.environ.get("FRAME_START", "-1"))
FRAME_END_OVERRIDE = int(os.environ.get("FRAME_END", "-1"))


def main():
    print("=" * 50)
    print("3Dシーン作成パイプライン開始")
    print("=" * 50)

    # カット情報の表示
    if CUT_NUMBER != "all":
        print(f"\n=== カットモード: {CUT_NUMBER} ===")
        if FRAME_START_OVERRIDE >= 0 and FRAME_END_OVERRIDE >= 0:
            print(f"フレーム範囲: {FRAME_START_OVERRIDE}-{FRAME_END_OVERRIDE}")
    
    # cars_config.json から車の設定を読み込む
    CARS = load_cars_config()
    
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
    
    # ============================================================
    # 新しい演出：リア端を揃えて全長差を可視化（左右配置版）
    # ============================================================
    
    # 初期位置は左右に配置（X軸方向）かつリア端を揃える - 全長の差から計算
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")
    
    if car_a and car_b:
        # 両車の全長（mm）を取得し、メートルに変換
        length_a_mm = CARS["carA"]["dimensions_mm"].get("length", 4460)
        length_b_mm = CARS["carB"]["dimensions_mm"].get("length", 4890)
        length_a_m = length_a_mm / 1000.0
        length_b_m = length_b_mm / 1000.0
        
        # 全長の差を計算（フロント端揃え用のYオフセット）
        # CarB (Land Cruiser) が CarA (Corolla Cross) より長いので、
        # フロント端を揃えるには CarA を Y正方向にずらす必要がある
        rear_offset_y = (length_b_m - length_a_m)
        
        print(f"全長差からフロント端揃えオフセットを計算: carA={length_a_mm}mm, carB={length_b_mm}mm -> offset_Y={rear_offset_y:.4f}m")
        
        # 接地後のZ位置を取得
        grounded_z_a = grounded_z_positions.get(car_a.name, 0.0)
        grounded_z_b = grounded_z_positions.get(car_b.name, 0.0)
        
        # carB (Land Cruiser): Vector(1.25, 0.0, Z) - Y座標=0.0（基準）、X=1.25m（右側）
        car_b.location = (1.25, 0.0, grounded_z_b)
        # carA: Vector(-1.25, +rear_offset_y, Z) - Y座標を全長差で調整してフロント端を揃える、X=-1.25m（左側）
        car_a.location = (-1.25, rear_offset_y, grounded_z_a)
        
        print(f"初期位置を設定（計算値、Z=接地後）：carA={car_a.location}, carB={car_b.location}")
    
    # 結果を表示
    print("\n=== インポート結果 ===")
    for key, obj in imported_cars.items():
        print(f"{key}: {obj.name} at {obj.location}")
    
    # カメラとライティングを設定
    camera = setup_camera_and_lighting()
    
    # =============================================
    # アニメーション設定（フレーム順・別モジュールから呼び出し）
    # =============================================
    import sys
    if SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    from animation_settings import setup_all_animations
    
    # 車の寸法情報を抽出（全長差・横幅差・最低地上高差計算用）
    car_dimensions = {}
    for key, car_data in CARS.items():
        dims = car_data.get("dimensions_mm", {})
        car_dimensions[key] = {
            "length": dims.get("length", 0),
            "width": dims.get("width", 0),
            "height": dims.get("height", 0),
            "ground_clearance": dims.get("ground_clearance", 0),
            "turning_radius": dims.get("turning_radius", 0),
        }
    
    scene = bpy.context.scene
    setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions)

    # カット番号に応じたフレーム範囲を適用
    if FRAME_START_OVERRIDE >= 0 and FRAME_END_OVERRIDE >= 0:
        original_end = scene.frame_end
        scene.frame_start = FRAME_START_OVERRIDE
        scene.frame_end = FRAME_END_OVERRIDE
        print(f"\n=== カット{CUT_NUMBER}のフレーム範囲を適用 ===")
        print(f"元のフレーム範囲: 0-{original_end}")
        print(f"現在のフレーム範囲: {scene.frame_start}-{scene.frame_end}")
    
    # マテリアルの再適用は行わない（アニメーション設定でCarBの半透明化キーフレームが上書きされるため）
    
    # =============================================
    # ステップ4: 3Dテキストラベル生成
    # =============================================
    print("\n=== 3Dテキストラベルを設定 ===")
    
    for key, car_data in CARS.items():
        car_obj = imported_cars.get(key)
        if not car_obj:
            continue
        
        # JSONから車種名と色を取得
        text_content = car_data["name"]
        color_rgb = car_data["color"]
        
        # 発光テキストを作成（ペアレント設定含む）
        create_glowing_text_label(key, car_obj, text_content, color_rgb)
    
    print("3Dテキストラベル設定完了")
    
    # =============================================
    # ビューポートシェーディング設定（ステップ3）
    # =============================================
    print("\n=== ビューポートシェーディングを設定 ===")
    setup_viewport_shading()  # デフォルト: MATERIAL モード
    
    # =============================================
    # レンダリング出力設定（FFMPEG動画直接出力）
    # =============================================
    print("\n=== レンダリング出力設定 ===")
    
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    output_filepath = os.path.join(desktop_path, "mp4")
    scene.render.filepath = output_filepath
    
    # レンダーエンジンを EEVEE に設定
    scene.render.engine = 'BLENDER_EEVEE'
    
    # EEVEEのレイトレーシングを有効化（Blender 5.x 対応）
    try:
        scene.eevee.use_gi = True
    except AttributeError:
        pass  # Blender 5.x では use_gi が廃止されている
    scene.eevee.use_raytracing = True
    print("EEVEEレイトレーシングを有効化しました")
    
    # FFMPEGで直接動画出力（メディアタイプ=動画）
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.image_settings.color_mode = 'RGB'
    
    # FFMPEG設定（H.264コーデック、MP4コンテナ）
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    
    print(f"出力フォーマット: MP4 (FFMPEG / H.264)")
    print(f"レンダーエンジン: EEVEE")
    print(f"保存先: {output_filepath}.mp4")
    
    print("\n" + "=" * 50)
    print("シーン作成完了！")
    print("=" * 50)
    
    # シーンを.blendファイルとして保存（Blenderで開けるように）
    # カット番号に応じてファイル名を切り替え（各カット独立保存用）
    if CUT_NUMBER in ("1", "2", "3", "4"):
        blend_output_path = os.path.join(SCRIPT_DIR, f"cut{CUT_NUMBER}_scene.blend")
    else:
        blend_output_path = os.path.join(SCRIPT_DIR, "car_comparison_scene.blend")
    bpy.ops.wm.save_mainfile(filepath=blend_output_path)
    print(f"シーンを保存しました: {blend_output_path}")
    
    # 注意: 自動レンダリングは行いません。Blender GUIで手動レンダリングしてください。
    # または --render オプションを使用してコマンドラインからレンダリングを実行できます。
    print("\nシーンが作成されました。Blender GUIで確認・編集できます。")
    print("アニメーションレンダリングを実行するには:")
    print("  - Blender GUI: レンダー > アニメーションのレンダー (Ctrl+F12)")
    print("  - コマンドライン: python run.py --render")
    
    return imported_cars


# スクリプトディレクトリのパス（保存用）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()


# スクリプトとして実行された場合
if __name__ == "__main__":
    result = main()
    
    # シーン作成後にBlenderを自動終了しない（ウィンドウを開いたまま）
