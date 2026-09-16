"""
Gallery BGM動画 - シーン生成スクリプト
Blenderでギャラリー展示風の車配置シーンを作成する。

使い方:
    blender --background --python gallery_scene_creator.py
"""

import bpy
import bmesh
import os
import json
import sys
import time
import math
from mathutils import Vector, Matrix

# スクリプトディレクトリの設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def load_gallery_config():
    """gallery_bgm_config.json を読み込んで戻す"""
    config_path = os.path.join(SCRIPT_DIR, "gallery_bgm_config.json")
    
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイルが見つかりません - {config_path}")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    glb_dir = config.get("glb_dir", "")
    gallery_settings = config.get("gallery", {})
    cars_list = config.get("cars", [])
    
    print(f"Gallery設定を読み込みました: {len(cars_list)} 台")
    print(f"  GLBディレクトリ: {glb_dir}")
    print(f"  グリッド長さ: {gallery_settings.get('grid_length', 100)}m")
    print(f"  車間隔: {gallery_settings.get('car_spacing', 10)}m")
    
    return glb_dir, gallery_settings, cars_list


def clear_scene():
    """シーン内のすべてのオブジェクトを削除（初期化関数）"""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    
    # マテリアルもクリーンアップ
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    
    print("シーンクリア完了")


def enable_gltf_addon():
    """glTFアドオンを有効化"""
    addon_name = "io_scene_gltf2"
    try:
        if addon_name not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=addon_name)
            print("glTFアドオンを有効化しました")
        else:
            print("glTFアドオンは既に有効です")
    except Exception as e:
        print(f"glTFアドオンの有効化中にエラー: {e}")


def import_glb_file(file_path):
    """GLBファイルをインポートし、メインオブジェクトを返す
    
    Short2と同様に、シンプルにインポートのみを行う。
    回転はメッシュ頂点レベルで後から適用する。
    """
    if not os.path.exists(file_path):
        print(f"警告: ファイルが見つかりません - {file_path}")
        return None
    
    try:
        objects_before = set(bpy.data.objects.keys())
        
        result = bpy.ops.import_scene.gltf(filepath=file_path)
        
        if 'FINISHED' not in str(result):
            print(f"インポート失敗: {result}")
            return None
        
        objects_after = set(bpy.data.objects.keys())
        new_objects = objects_after - objects_before
        
        if not new_objects:
            print("警告: インポートされたオブジェクトが見つかりません")
            return None
        
        # 親オブジェクトを取得
        parent_obj = None
        for obj_name in new_objects:
            obj = bpy.data.objects[obj_name]
            if not obj.parent:
                parent_obj = obj
                break
        
        if not parent_obj:
            first_obj = list(new_objects)[0]
            parent_obj = bpy.data.objects[first_obj]
        
        return parent_obj
        
    except Exception as e:
        print(f"エラー: GLBインポート失敗 - {e}")
        return None


def create_clay_material(name):
    """グレーのクレイモデル用のマテリアルを作成"""
    mat_name = f"clay_{name}"
    
    if mat_name in bpy.data.materials:
        return bpy.data.materials[mat_name]
    
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # ノードをクリア
    nodes.clear()
    
    # Principled BSDF ノード（グレー）
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.65, 0.65, 0.65, 1.0)  # ミディアムグレー（博物館展示風）
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.0
    
    # Output ノード
    output = nodes.new("ShaderNodeOutputMaterial")
    
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    
    return mat


def create_grid_floor(grid_length=100):
    """発光グリッド床面を作成（既存のcreate_grid_floorと同じノード構成を使用）"""
    y_half_length = grid_length / 2.0
    x_half_width = 100.0  # X方向も100m（±100m＝全長200m）に拡張
    
    plane_size = y_half_length * 2
    bpy.ops.mesh.primitive_plane_add(size=plane_size, location=(0, 0, 0))
    grid = bpy.context.active_object
    grid.name = "CyberGrid"
    
    _target_local_x_half = float(x_half_width)
    mesh_data = grid.data
    bm = bmesh.new()
    bm.from_mesh(mesh_data)
    max_abs_x = max((abs(v.co.x) for v in bm.verts), default=0.0) or 1e-9
    if abs(max_abs_x - _target_local_x_half) > 1e-6:
        fx = _target_local_x_half / max_abs_x
        for v in bm.verts:
            v.co.x *= fx
        bm.to_mesh(mesh_data)
    mesh_data.update(calc_edges=True)
    bm.free()
    
    grid.scale = (1.0, 1.0, 1.0)
    
    # グリッドマテリアル（既存コードと同じ構成）
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
    
    # Output Material ノード
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (1200, 0)
    
    # ColorRamp (横線用)
    color_ramp_h = nodes.new(type='ShaderNodeValToRGB')
    color_ramp_h.location = (800, -100)
    color_ramp_h.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp_h.color_ramp.elements[0].position = 0.0
    color_ramp_h.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    color_ramp_h.color_ramp.elements[1].position = 0.04
    
    # ColorRamp (縦線用)
    color_ramp_v = nodes.new(type='ShaderNodeValToRGB')
    color_ramp_v.location = (800, 100)
    color_ramp_v.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    color_ramp_v.color_ramp.elements[0].position = 0.0
    color_ramp_v.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    color_ramp_v.color_ramp.elements[1].position = 0.04
    
    # Emission ノード
    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.location = (1050, 0)
    emission_node.inputs['Color'].default_value = (0.0, 1.0, 1.0, 1.0)
    emission_node.inputs['Strength'].default_value = 6.0
    
    # X座標処理
    separate_xyz_x = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_xyz_x.location = (250, 150)
    
    math_floor_x = nodes.new(type='ShaderNodeMath')
    math_floor_x.operation = 'FLOOR'
    math_floor_x.location = (400, 200)
    
    math_subtract_x = nodes.new(type='ShaderNodeMath')
    math_subtract_x.operation = 'SUBTRACT'
    math_subtract_x.location = (550, 180)
    
    # Y座標処理
    separate_xyz_y = nodes.new(type='ShaderNodeSeparateXYZ')
    separate_xyz_y.location = (250, -150)
    
    math_floor_y = nodes.new(type='ShaderNodeMath')
    math_floor_y.operation = 'FLOOR'
    math_floor_y.location = (400, -200)
    
    math_subtract_y = nodes.new(type='ShaderNodeMath')
    math_subtract_y.operation = 'SUBTRACT'
    math_subtract_y.location = (550, -180)
    
    # MAXimum ノード
    math_max_hv = nodes.new(type='ShaderNodeMath')
    math_max_hv.operation = 'MAXIMUM'
    math_max_hv.location = (1000, 0)
    
    # Mapping ノード
    mapping_node = nodes.new(type='ShaderNodeMapping')
    mapping_node.location = (50, 0)
    mapping_node.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    
    # Texture Coordinate ノード
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-200, 0)
    
    # 接続: Object → Mapping → SeparateXYZ/Math → ColorRamp → MAXimum → Emission → Output
    links.new(tex_coord.outputs['Object'], mapping_node.inputs['Vector'])
    
    links.new(mapping_node.outputs['Vector'], separate_xyz_x.inputs['Vector'])
    links.new(separate_xyz_x.outputs['X'], math_floor_x.inputs[0])
    links.new(math_floor_x.outputs[0], math_subtract_x.inputs[1])
    links.new(separate_xyz_x.outputs['X'], math_subtract_x.inputs[0])
    links.new(math_subtract_x.outputs[0], color_ramp_v.inputs['Fac'])
    
    links.new(mapping_node.outputs['Vector'], separate_xyz_y.inputs['Vector'])
    links.new(separate_xyz_y.outputs['Y'], math_floor_y.inputs[0])
    links.new(math_floor_y.outputs[0], math_subtract_y.inputs[1])
    links.new(separate_xyz_y.outputs['Y'], math_subtract_y.inputs[0])
    links.new(math_subtract_y.outputs[0], color_ramp_h.inputs['Fac'])
    
    links.new(color_ramp_h.outputs['Color'], math_max_hv.inputs[0])
    links.new(color_ramp_v.outputs['Color'], math_max_hv.inputs[1])
    links.new(math_max_hv.outputs[0], emission_node.inputs['Strength'])
    links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
    
    grid.data.materials.clear()
    grid.data.materials.append(grid_mat)
    
    print(f"グリッド床を作成完了 (X±{x_half_width:.0f}m / Y±{y_half_length:.0f}m)")
    return grid


def setup_lighting():
    """博物館展示風のソフトライティングを設定"""
    # キーライト（主光）- SUNライト、やや強めに照射して陰影を強調
    key_light = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light_object = bpy.data.objects.new("KeyLightObject", key_light)
    key_light_object.location = (5, -5, 10)
    key_light_object.rotation_euler = (math.radians(45), 0, math.radians(45))
    key_light.energy = 0.588  # さらに30%暗くして（0.84→0.588）
    bpy.context.collection.objects.link(key_light_object)
    
    # フィラーライト（補助光）- SUNライト、左側からやや弱く補う（陰を強調するため）
    fill_light = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light_object = bpy.data.objects.new("FillLightObject", fill_light)
    fill_light_object.location = (-5, 5, 8)
    fill_light_object.rotation_euler = (math.radians(60), 0, math.radians(-45))
    fill_light.energy = 0.7
    bpy.context.collection.objects.link(fill_light_object)
    
    # バックライト（輪郭光）- SUNライト、後方から縁取りを強調
    back_light = bpy.data.lights.new(name="BackLight", type='SUN')
    back_light_object = bpy.data.objects.new("BackLightObject", back_light)
    back_light_object.location = (0, 10, 5)
    back_light_object.rotation_euler = (math.radians(30), math.radians(-45), 0)
    back_light.energy = 1.5
    bpy.context.collection.objects.link(back_light_object)
    
    print("ライティング設定完了（博物館展示風）")


def position_car_on_side(car_config, gallery_settings):
    """車の配置位置を計算（Blender座標: Y軸=前後方向）"""
    side = car_config["side"]
    index = car_config["index"]
    
    spacing = gallery_settings.get("car_spacing", 10)
    aisle_half_width = gallery_settings.get("aisle_width", 4) / 2.0
    offset_from_aisle = 3.0  # 通路から3m離れて配置
    
    z_pos = index * spacing
    
    if side == "left":
        x_pos = -(aisle_half_width + offset_from_aisle)
    else:
        x_pos = (aisle_half_width + offset_from_aisle)
    
    return x_pos, z_pos


def _apply_clay_recursive(obj, clay_material):
    """再帰的に全子オブジェクトのメッシュにクレイマテリアルを適用"""
    if obj.type == 'MESH':
        if not obj.data.materials:
            obj.data.materials.append(clay_material)
        else:
            obj.data.materials[0] = clay_material
    
    for child in obj.children:
        _apply_clay_recursive(child, clay_material)


def apply_clay_material_to_meshes(root_obj):
    """インポートしたモデルの全メッシュにグレーのクレイマテリアルを適用"""
    mat = create_clay_material(root_obj.name)
    _apply_clay_recursive(root_obj, mat)
    print(f"  {root_obj.name}: クレイマテリアルを適用完了")


def apply_rotation_to_car(obj, rotation_z_deg=90):
    """車の回転をメッシュ頂点レベルで適用（Short2と同じ方式）
    
    bmeshを使用して各メッシュの頂点を直接Z軸回転させる。
    オブジェクトレベルの回転ではなく、メッシュデータ自体を変形する。
    これによりクォータニオン回転モードの影響を受けない。
    """
    if rotation_z_deg == 0:
        return
    
    rot_angle = math.radians(rotation_z_deg)
    
    def rotate_mesh_data_recursive(mesh_obj):
        """オブジェクトとその全子オブジェクトのメッシュデータをZ軸回転"""
        if mesh_obj.type == 'MESH' and mesh_obj.data is not None:
            mesh = mesh_obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            rot_matrix = Matrix.Rotation(rot_angle, 3, 'Z')
            for vert in bm.verts:
                vert.co.rotate(rot_matrix)
            bm.to_mesh(mesh)
            bm.free()
            mesh.update(calc_edges=True)
        
        for child in mesh_obj.children:
            rotate_mesh_data_recursive(child)
    
    rotate_mesh_data_recursive(obj)
    bpy.context.view_layer.update()
    print(f"  メッシュ回転: Z軸 {rotation_z_deg}度 を再帰的に全メッシュに適用")


def auto_ground_car(car_object):
    """オブジェクトのバウンディングボックスから最低点を計算し、Z=0.0 に接地するオフセットを適用"""
    # シーンを更新してバウンディングボックスを再計算
    car_object.update_tag()
    bpy.context.view_layer.update()
    
    local_bounds = car_object.bound_box
    if not local_bounds:
        print(f"  警告: {car_object.name} のバウンディングボックスが取得できません")
        return
    
    # ローカル座標 → ワールド座標に変換
    corners_world = [car_object.matrix_world @ Vector(corner) for corner in local_bounds]
    
    # Z軸の最小値（一番低い位置）を取得
    min_z = min(corner.z for corner in corners_world)
    
    # 接地オフセットを計算（最低点を Z=0.0 に合わせる）
    offset_z = -min_z
    car_object.location.z += offset_z
    
    print(f"  自動接地: {car_object.name} -> オフセット Z={offset_z:.3f}")


def create_name_label(car_config, position):
    """床面に車名を表示（3Dテキスト）"""
    name = car_config["name"]
    x_pos, z_pos = position
    
    # テキストオブジェクトを作成（既存コードと同じ方法）
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.active_object
    text_obj.name = f"Label_{name}"
    
    text_obj.data.body = name
    text_obj.data.size = 0.3
    text_obj.data.extrude = 0.005
    text_obj.data.align_x = 'CENTER'
    text_obj.data.align_y = 'CENTER'
    
    # テキストを車の手前に配置（通路側）
    label_offset = 2.5  # 車から少し離して配置
    if car_config["side"] == "left":
        label_x = x_pos + label_offset
    else:
        label_x = x_pos - label_offset
    
    text_obj.location = (label_x, 0.01, z_pos)
    
    # テキストを上方向（+Z）に向ける
    text_obj.rotation_euler = (math.pi / 2, 0, 0)
    
    # テキストマテリアル（発光）
    if "EmissionText" in bpy.data.materials:
        text_mat = bpy.data.materials["EmissionText"]
    else:
        text_mat = bpy.data.materials.new(name="EmissionText")
        text_mat.use_nodes = True
        nodes = text_mat.node_tree.nodes
        links = text_mat.node_tree.links
        nodes.clear()
        
        emission = nodes.new(type='ShaderNodeEmission')
        emission.inputs["Color"].default_value = (0.0, 1.0, 1.0, 1.0)  # シアン
        emission.inputs["Strength"].default_value = 3.0
        
        output = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(emission.outputs["Emission"], output.inputs["Surface"])
    
    text_obj.data.materials.clear()
    text_obj.data.materials.append(text_mat)


def create_gallery_scene():
    """ギャラリーシーンを生成するメイン関数"""
    # シーン初期化
    clear_scene()
    enable_gltf_addon()
    
    # 設定ファイル読み込み
    glb_dir, gallery_settings, cars_list = load_gallery_config()
    
    # グリッド床を作成
    grid_length = gallery_settings.get("grid_length", 100)
    create_grid_floor(grid_length)
    print(f"グリッド床を作成しました ({grid_length}m)")
    
    # ライティング設定
    setup_lighting()
    
    # 車を読み込み・配置
    for car_config in cars_list:
        car_name = car_config["name"]
        glb_filename = car_config["glb_filename"]
        glb_path = os.path.join(glb_dir, glb_filename)
        
        print(f"\n車をインポート中: {car_name}")
        
        # GLBインポート
        car_obj = import_glb_file(glb_path)
        if car_obj is None:
            print(f"  スkip: {car_name} (ファイル読み込み失敗)")
            continue
        
        # オブジェクト名を設定
        obj_group_name = f"Car_{car_config['id']}_{car_name}"
        if isinstance(car_obj, bpy.types.Object):
            car_obj.name = obj_group_name
        
        # 配置位置を計算
        x_pos, z_pos = position_car_on_side(car_config, gallery_settings)
        
        # クレイマテリアルを適用
        apply_clay_material_to_meshes(car_obj)
        
        # ★メッシュ頂点レベルで回転（Short2と同じ方式）
        rotation_z = car_config.get("rotation_z", 90)
        apply_rotation_to_car(car_obj, rotation_z)
        
        # 位置を設定
        car_obj.location.x = x_pos
        car_obj.location.y = z_pos  # Y=奥行き方向
        
        # 自動接地補正（車のモデルが床に埋まらないようにする）
        auto_ground_car(car_obj)
        
        # 床面に車名を表示
        create_name_label(car_config, (x_pos, z_pos))
        
        print(f"  配置完了: ({x_pos}, {z_pos})")
    
    # カメラを設定
    setup_camera(gallery_settings)
    
    print("\n=== シーン生成完了 ===")


def setup_camera(gallery_settings):
    """ギャラリー用カメラを設定"""
    # デフォルトカメラを削除して新規作成
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    camera = bpy.data.cameras.new(name="GalleryCamera")
    camera_object = bpy.data.objects.new("GalleryCamera", camera)
    
    # カメラ設定
    camera.sensor_fit = 'AUTO'
    camera.clip_start = 0.1
    camera.clip_end = 200
    
    scene = bpy.context.scene
    scene.camera = camera_object
    
    # レンダリング設定
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.engine = 'BLENDER_EEVEE'
    
    # フレームレート設定
    scene.render.fps = 30
    
    # EEVEE設定（Blender 5.2 対応）
    try:
        scene.eevee.use_raytracing = True
    except AttributeError:
        pass
    
    print("カメラ設定完了 (1920x1080, 30FPS)")


if __name__ == "__main__":
    create_gallery_scene()
