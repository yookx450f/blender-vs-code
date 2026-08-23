"""
Blenderスタンドアロンスクリプト - コマンドラインから直接実行可能

使い方:
    blender --background --python blend_scene_creator.py
    python run.py
"""

import bpy
import csv
import os
import math
import sys
import struct
import json
import time
import sqlite3
from mathutils import Vector, Matrix

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

def load_cars_db():
    """SQLiteデータベース (cars.db) から車種マスターデータを辞書として読み込む"""
    db_path = os.path.join(SCRIPT_DIR, "cars.db")
    
    if not os.path.exists(db_path):
        print(f"エラー: 車種データベースが見つかりません - {db_path}")
        print("python manage_cars.py import-csv cars.csv でインポートしてください。")
        sys.exit(1)
    
    cars_db = {}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cars")
        
        for row in cursor.fetchall():
            car_id = str(row["id"])
            # Widthはミラー未包含のため、mirror_offset_mm × 2 を加算して3Dスケールに使用する
            # mirror_offset_mm が設定されていない場合はデフォルト100mm（両側200mm）を使用
            # ただしテキスト表示には生値を使用するため、width_rawを別途保持する
            width_raw = row["width"]
            try:
                mirror_offset = row["mirror_offset_mm"]
            except (KeyError, IndexError):
                mirror_offset = 100  # デフォルト値
            cars_db[car_id] = {
                "name": row["name"],
                "glb_filename": row["glb_filename"],
                "length": row["length"],
                "width": width_raw + (mirror_offset * 2),
                "width_raw": width_raw,
                "height": row["height"],
                "ground_clearance": row["ground_clearance"],
                "turning_radius": row["turning_radius"],
                "acceleration_0_to_100": row["acceleration_0_to_100"],
                "rotation_direction": row["rotation_direction"]
            }
        
        conn.close()
        print(f"車種マスターDBを読み込みました: {db_path} ({len(cars_db)} 車種)")
    except Exception as e:
        print(f"エラー: cars.db の読み込みに失敗しました - {e}")
        sys.exit(1)
    
    return cars_db


def load_cars_config():
    """cars_config.json + cars.db を結合して車の設定辞書を返す
    
    JSONでは carA/carB に id, color, position のみを指定し、
    寸法データは DBからidで自動的に取得・結合する。
    戻り値の構造は従来と同じ（後方互換性維持）。
    """
    config_path = os.path.join(SCRIPT_DIR, "cars_config.json")
    
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイルが見つかりません - {config_path}")
        print("cars_config.json を作成してください。")
        sys.exit(1)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # DBから車種マスターデータを取得
        cars_db = load_cars_db()
        
        # GLBディレクトリの取得（JSONのグローバル設定）
        glb_dir = config.get("glb_dir", "")
        
        # carA/carB ごとにCSVデータを結合
        merged = {}
        for key in ["carA", "carB"]:
            if key not in config:
                continue
            
            car_cfg = config[key]
            car_id = car_cfg.get("id", "")
            
            if car_id not in cars_db:
                print(f"エラー: DBに車種ID '{car_id}' が見つかりません")
                print(f"  利用可能なID: {', '.join(cars_db.keys())}")
                sys.exit(1)
            
            csv_data = cars_db[car_id]
            merged[key] = {
                "name": csv_data["name"],
                "glb_path": os.path.join(glb_dir, csv_data["glb_filename"]),
                "position": tuple(car_cfg.get("position", [0.0, 0.0, 0])),
                "color": tuple(car_cfg.get("color", [0.5, 0.5, 0.5])),
                "dimensions_mm": {
                    "length": csv_data["length"],
                    "width": csv_data["width"],
                    "width_raw": csv_data.get("width_raw", csv_data["width"]),
                    "height": csv_data["height"],
                    "ground_clearance": csv_data["ground_clearance"],
                    "turning_radius": csv_data["turning_radius"]
                },
                "acceleration_0_to_100_km_h": csv_data["acceleration_0_to_100"],
                "rotation_z_degrees": csv_data["rotation_direction"]
            }
        
        print(f"設定ファイルを読み込みました: {config_path}")
        for key, car_data in merged.items():
            dims = car_data.get("dimensions_mm", {})
            print(f"  - {key}: {car_data['name']} (ID: {config[key].get('id', '?')})")
            print(f"    GLBパス: {car_data['glb_path']}")
            print(f"    寸法: 全長{dims.get('length', '?')}mm × 全幅{dims.get('width', '?')}mm × 全高{dims.get('height', '?')}mm")
        
        return merged
    
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
    """シーン内のすべてのオブジェクトを削除（初期化関数）"""
    # 全オブジェクトを一括削除（KeyLightとComparisonCamera以外）
    objects_to_keep = {"KeyLight", "ComparisonCamera"}
    for obj in list(bpy.data.objects):
        if obj.name not in objects_to_keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # 不要なマテリアルもクリーンアップ
    for mat in list(bpy.data.materials):
        if "clay_" in mat.name or "emission_label" in mat.name or "NeonGrid" in mat.name:
            bpy.data.materials.remove(mat)
    
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

def _apply_clay_to_all_meshes(obj, clay_material):
    """オブジェクトとその全子オブジェクトのメッシュにクレイマテリアルを強制適用
    GLBインポート時の元マテリアル（透明など）を完全に上書きする。
    """
    if obj is None:
        return
    
    # 自身がMESHの場合、全スロットをクレイマテリアルに置換
    if obj.type == 'MESH' and obj.data is not None:
        obj.data.materials.clear()
        obj.data.materials.append(clay_material)
    
    # 子オブジェクトも再帰的に処理
    for child in obj.children:
        _apply_clay_to_all_meshes(child, clay_material)


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
        adjusted_color = (0.0, 0.7, 1.0)  # 鮮明な青色
    
    mat_name = f"clay_{key}_{car_data['name']}"
    clay_material = create_clay_material(mat_name, adjusted_color)
    
    # ★重要: 親オブジェクトと全子メッシュのマテリアルをすべてクレイマテリアルに置換
    # GLBインポート時の元マテリアル（透明設定など）を完全に上書きする
    _apply_clay_to_all_meshes(imported_object, clay_material)
    print(f"  マテリアルを全メッシュに適用: {mat_name}")
    
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
    key_light.data.shadow_soft_size = 1.0
    # 照射距離を無限に設定（Distance=0）
    key_light.data.use_shadow = True
    if hasattr(key_light.data, 'distance'):
        key_light.data.distance = 0  # 0=無限
    if hasattr(key_light.data, 'use_custom_distance'):
        key_light.data.use_custom_distance = False
    
    # SubLightもカメラに合わせて拡大
    bpy.ops.object.light_add(type='AREA', location=(-8.5*0.6, 8.5*0.6, 6))
    sub_light = bpy.context.active_object
    sub_light.name = "SubLight"
    sub_light.data.energy = 800  # さらに明るさを抑える
    sub_light.data.size = 2
    sub_light.data.shadow_soft_size = 1.0
    if hasattr(sub_light.data, 'distance'):
        sub_light.data.distance = 0  # 0=無限
    if hasattr(sub_light.data, 'use_custom_distance'):
        sub_light.data.use_custom_distance = False
    
    # RimLightもカメラに合わせて拡大
    bpy.ops.object.light_add(type='SPOT', location=(0, 7*1.7, 5))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 800  # さらに明るさを抑える
    rim_light.data.spot_size = 1.2
    if hasattr(rim_light.data, 'distance'):
        rim_light.data.distance = 0  # 0=無限
    if hasattr(rim_light.data, 'use_custom_distance'):
        rim_light.data.use_custom_distance = False
    
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
def create_glowing_text_label_short2(car_key, car_object, text_content, color_rgb):
    """short2用: 車の上方前方に配置され、フロント方向を向く発光3Dテキストラベル
    
    CarA は上側（X負方向寄り）、CarB は下側（X正方向寄り）に配置。
    テキストは車のフロント方向（+Y）を向く。
    """
    if car_object is None:
        print(f"エラー: {car_key} の車オブジェクトがNoneです")
        return
    
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.active_object
    text_obj.name = f"label_{car_key}"
    
    text_obj.data.body = text_content
    text_obj.data.size = 0.35
    text_obj.scale = (1.0, 1.0, 1.0)
    
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"警告: {car_object.name} のバウンディングボックスが取得できません")
        return
    
    local_corners = [Vector(corner) for corner in local_bounds]
    local_center_x = (min(c.x for c in local_corners) + max(c.x for c in local_corners)) / 2.0
    local_max_z = max(c.z for c in local_corners)
    local_max_y = max(c.y for c in local_corners)
    
    text_y = local_max_y + 0.3
    
    # Z位置: CarAは少し低く、CarBは上面より高く
    if car_key == "carA":
        text_z = local_max_z + 0.25   # CarAはもう少し下げる
    else:
        text_z = local_max_z + 0.5
    
    # X座標は車の中心と揃える
    text_x = local_center_x
    
    text_obj.location = (text_x, text_y, text_z)
    # テキストを上方向（+Z）に向けることで、カメラから水平に読めるようにする
    text_obj.rotation_euler = (math.pi / 2, 0, 0)
    
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
        adjusted_color = color_rgb
        if car_key == "carB" and color_rgb[2] > color_rgb[0]:
            adjusted_color = (0.0, 0.7, 1.0)
        emission_node.inputs['Color'].default_value = (*adjusted_color, 1.0)
        emission_node.inputs['Strength'].default_value = 5.0
        links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
    
    text_obj.data.materials.clear()
    text_obj.data.materials.append(emission_mat)
    text_obj.parent = car_object
    
    print(f"3Dテキストラベル作成完了 (short2): {text_obj.name} -> '{text_content}' (上方配置, ペアレント: {car_object.name})")


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
    
    # バウンディングボックスから車の寸法を計算（ワールド座標系）
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"警告: {car_object.name} のバウンディングボックスが取得できません")
        return
    
    # ワールド座標でバウンディングボックスの隅を取得
    corners_world = [car_object.matrix_world @ Vector(corner) for corner in local_bounds]
    
    world_min_x = min(c.x for c in corners_world)
    world_max_x = max(c.x for c in corners_world)
    world_min_y = min(c.y for c in corners_world)  # リア端（後部）のY座標
    world_max_y = max(c.y for c in corners_world)  # フロント端（前部）のY座標

    world_car_width_x = world_max_x - world_min_x   # ワールド座標でのX幅
    world_car_length_y = world_max_y - world_min_y  # ワールド座標でのY長さ

    # 車のワールド寸法に比例した動的オフセットを計算
    # 全長が長い車ほどテキストを大きく離し、短い車ほど近くに配置
    x_margin_world = world_car_width_x * 0.3   # 車幅の30%分外側に配置
    y_margin_world = world_car_length_y * 0.15 + 0.3  # 全長の15% + 固定0.3m

    # X位置: 車の左端から外側に配置（ワールド座標）
    text_x_world = world_min_x - x_margin_world

    # Y位置: リア端から後ろに配置（ワールド座標）
    text_y_world = world_min_y - y_margin_world

    # まず一時的な位置に設定（ペアレント用）
    text_obj.location = (0, 0, 0)

    print(f"  テキストの目標ワールド座標: X={text_x_world:.3f}, Y={text_y_world:.3f} (ワールド車幅={world_car_width_x:.3f}m, ワールド全長={world_car_length_y:.3f}m)")
    
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
            adjusted_color = (0.0, 0.7, 1.0)  # 鮮明な青色
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
    
    # ペアレント設定後、ワールド座標で目標位置に直接配置
    # matrix_world を直接設定することで、車のスケール変換の影響を受けない
    text_obj.matrix_world = Matrix.Translation((text_x_world, text_y_world, 0.02))
    
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
        
        # メッシュデータを直接回転（スケール/origin_setの影響を受けない）
        rotation_z = car_data.get("rotation_z_degrees", 0)
        if rotation_z != 0:
            import bmesh
            mesh = imported_object.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            rot_angle = math.radians(rotation_z)
            rot_matrix = Matrix.Rotation(rot_angle, 3, 'Z')
            for vert in bm.verts:
                vert.co.rotate(rot_matrix)
            bm.to_mesh(mesh)
            bm.free()
            mesh.update(calc_edges=True)
            bpy.context.view_layer.update()
            print(f"  メッシュ回転: Z軸 {rotation_z}度 を適用")
        
        setup_car(key, car_data, imported_object)
        imported_cars[key] = imported_object
        print(f"成功: '{imported_object.name}' をインポートしました")
        print(f"  - 位置: {imported_object.location}")
    
    # ============================================================
    # 新しい演出：後端を揃えて全長差を可視化（左右配置版）
    # バウンディングボックスから実際の後端Y座標を測定して揃える
    # ============================================================
    
    def get_rear_end_y(car_obj):
        """バウンディングボックスから後端（Y最大）のワールド座標を取得"""
        bounds = [Vector(b) for b in car_obj.bound_box]
        corners_world = [car_obj.matrix_world @ corner for corner in bounds]
        return max(c.y for c in corners_world)
    
    def get_car_length_from_bbox(car_obj):
        """バウンディングボックスから車の全長（Y方向の長さ）を取得"""
        bounds = [Vector(b) for b in car_obj.bound_box]
        corners_world = [car_obj.matrix_world @ corner for corner in bounds]
        min_y = min(c.y for c in corners_world)
        max_y = max(c.y for c in corners_world)
        return max_y - min_y
    
    # 初期位置は左右に配置（X軸方向）かつ後端を揃える
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")
    
    if car_a and car_b:
        # 接地後のZ位置を取得
        grounded_z_a = grounded_z_positions.get(car_a.name, 0.0)
        grounded_z_b = grounded_z_positions.get(car_b.name, 0.0)
        
        # carB (Land Cruiser) を基準位置に配置
        car_b.location = (1.25, 0.0, grounded_z_b)
        rear_y_b = get_rear_end_y(car_b)
        
        # carAを一時的に基準位置に配置して後端Yを測定
        car_a.location = (-1.25, 0.0, grounded_z_a)
        rear_y_a = get_rear_end_y(car_a)
        
        # 後端を揃えるためのYオフセットを計算
        # carAの後端が carBの後端と一致するように調整
        rear_offset_y = rear_y_b - rear_y_a
        
        # carAの最終位置を設定
        car_a.location = (-1.25, rear_offset_y, grounded_z_a)
        
        # バウンディングボックスから測定した実際の全長を表示
        length_a_m = get_car_length_from_bbox(car_a)
        length_b_m = get_car_length_from_bbox(car_b)
        
        print(f"バウンディングボックスから後端Y座標を測定: carA={rear_y_a:.4f}m, carB={rear_y_b:.4f}m")
        print(f"後端揃えオフセット: offset_Y={rear_offset_y:.4f}m")
        print(f"実際の全長: carA={length_a_m*1000:.0f}mm, carB={length_b_m*1000:.0f}mm")
        print(f"初期位置を設定（後端揃え、Z=接地後）：carA={car_a.location}, carB={car_b.location}")
    
    # 結果を表示
    print("\n=== インポート結果 ===")
    for key, obj in imported_cars.items():
        print(f"{key}: {obj.name} at {obj.location}")
    
    # カメラとライティングを設定
    camera = setup_camera_and_lighting()
    
    # =============================================
    # オフセットデータをJSONに保存（カット分離用）
    # =============================================
    import sys
    if SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    from animation_cut_positions import save_offsets

    if car_a and car_b:
        offset_data = {
            "offset_a": [round(car_a.location.x, 4), round(car_a.location.y, 4)],
            "offset_b": [round(car_b.location.x, 4), round(car_b.location.y, 4)],
            "grounded_z_a": round(grounded_z_a, 4),
            "grounded_z_b": round(grounded_z_b, 4),
            "rear_offset_y": round(rear_offset_y, 4),
            "car_a_center": [round(car_a.location.x, 4), round(car_a.location.y, 4), round(car_a.location.z, 4)],
            "car_b_center": [round(car_b.location.x, 4), round(car_b.location.y, 4), round(car_b.location.z, 4)]
        }
        save_offsets(offset_data)
        print(f"オフセットデータを保存しました: cut_offsets.json")

    # =============================================
    # アニメーション設定（フレーム順・別モジュールから呼び出し）
    # =============================================
    if SCRIPT_DIR not in sys.path:
        sys.path.insert(0, SCRIPT_DIR)
    
    scene = bpy.context.scene
    
    # ショート動画モードの場合は独立したアニメーション設定を使用
    if CUT_NUMBER == "short":
        from animation_settings_short import setup_short_animations
        setup_short_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions)
    elif CUT_NUMBER == "short2":
        from animation_settings_short2 import setup_short2_animations
        setup_short2_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions)
    else:
        from animation_settings import setup_all_animations
        
        # 車の寸法情報を抽出（全長差・横幅差・最低地上高差計算用）
        car_dimensions = {}
        for key, car_data in CARS.items():
            dims = car_data.get("dimensions_mm", {})
            car_dimensions[key] = {
                "length": dims.get("length", 0),
                "width": dims.get("width", 0),
                "width_raw": dims.get("width_raw", dims.get("width", 0)),
                "height": dims.get("height", 0),
                "ground_clearance": dims.get("ground_clearance", 0),
                "turning_radius": dims.get("turning_radius", 0),
            }
            # 0-100km/h 加速時間（秒）を取得
            accel = car_data.get("acceleration_0_to_100_km_h")
            if accel:
                car_dimensions[key]["acceleration_0_to_100_km_h"] = accel
            # 車の色を取得（比較テキストの数字の色に使用）
            color = car_data.get("color", (1.0, 1.0, 1.0))
            car_dimensions[key]["color"] = color
        
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
        if CUT_NUMBER == "short2":
            create_glowing_text_label_short2(key, car_obj, text_content, color_rgb)
        else:
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
    
    desktop_path = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
    
    # カット番号に応じてファイル名を設定
    if CUT_NUMBER == "short":
        output_filename = "short_overlap.mp4"
    elif CUT_NUMBER == "short2":
        output_filename = "short2_overlap.mp4"
    elif CUT_NUMBER in ("1", "2", "3", "4", "4b", "5"):
        output_filename = f"cut{CUT_NUMBER}.mp4"
    else:
        output_filename = "mp4.mp4"
    
    output_filepath = f"{desktop_path}/{output_filename}"
    scene.render.filepath = output_filepath
    
    # ファイル拡張子の自動付与を無効化
    scene.render.use_file_extension = False
    
    # レンダーエンジンを EEVEE に設定
    scene.render.engine = 'BLENDER_EEVEE'
    
    # EEVEEのレイトレーシングを有効化（Blender 5.x 対応）
    try:
        scene.eevee.use_gi = True
    except AttributeError:
        pass  # Blender 5.x では use_gi が廃止されている
    scene.eevee.use_raytracing = True
    print("EEVEEレイトレーシングを有効化しました")
    
    # 解像度設定（ショート動画は縦長9:16）
    if CUT_NUMBER in ("short", "short2"):
        scene.render.resolution_x = 1080
        scene.render.resolution_y = 1920
        scene.render.resolution_percentage = 100
        print("解像度: 1080x1920 (縦長9:16)")
    else:
        # デフォルトの横長設定を維持（1920x1080）
        print(f"解像度: {scene.render.resolution_x}x{scene.render.resolution_y} (デフォルト)")
    
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
    print(f"  file_extension: {scene.render.file_extension}")
    print(f"  use_file_extension: {scene.render.use_file_extension}")
    
    print("\n" + "=" * 50)
    print("シーン作成完了！")
    print("=" * 50)
    
    # シーンを.blendファイルとして保存（Blenderで開けるように）
    # カット番号に応じてファイル名を切り替え（各カット独立保存用）
    if CUT_NUMBER == "short":
        blend_output_path = os.path.join(SCRIPT_DIR, "short_scene.blend")
    elif CUT_NUMBER == "short2":
        blend_output_path = os.path.join(SCRIPT_DIR, "short2_scene.blend")
    elif CUT_NUMBER in ("1", "2", "3", "4", "4b", "5"):
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
