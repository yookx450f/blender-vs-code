"""
ステップ1-4: 2台のGLBファイルをBlenderにインポートするベースコード
.clinerules.txtのルールに基づいて作成

使い方:
1. CARS 辞書の変数を書き換えて車種情報を変更
2. BlenderのPythonコンソールまたはテキストエディタで実行
"""

import bpy
import os
import math

# ============================================================
# 設定変数（ここを変更して使い回し可能）
# ============================================================
CARS = {
    "carA": {
        "name": "Corolla Cross",
        "glb_path": r"C:\3d\Modly\glb\colloraCross2025.glb",
        "position": (-2.0, 0, 0),
        "color": (0.8, 0.2, 0.2),
    },
    "carB": {
        "name": "Target Car",
        "glb_path": r"C:\3d\Modly\glb\colloraCross2026.glb",
        "position": (2.0, 0, 0),
        "color": (0.2, 0.2, 0.8),
    },
}
# ============================================================


def clear_scene():
    """シーン内のすべてのメッシュオブジェクトを削除（初期化関数）"""
    bpy.ops.object.select_all(action='DESELECT')
    scene = bpy.context.scene
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    for obj in mesh_objects:
        obj.select_set(True)
        scene.view_layers[0].objects.active = obj
    if mesh_objects:
        bpy.ops.object.delete()
    lights = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
    for obj in lights:
        obj.select_set(True)
    if lights:
        bpy.ops.object.delete()
    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
    for obj in cameras:
        obj.select_set(True)
    if cameras:
        bpy.ops.object.delete()
    print("シーンクリア完了")


def import_glb_file(file_path):
    """GLBファイルをBlenderにインポートし、メインオブジェクトを返す"""
    if not os.path.exists(file_path):
        print(f"エラー: ファイルが見つかりません - {file_path}")
        return None
    try:
        bpy.ops.wm.gltf_import(filepath=file_path)
    except Exception as e:
        print(f"エラー: GLBインポートに失敗しました - {e}")
        return None
    main_object = bpy.context.active_object
    if main_object is None:
        print("エラー: オブジェクトが正常にインポートされませんでした")
        return None
    return main_object


def create_grid_floor():
    """サイバー空間用の発光グリッド床面を作成する"""
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.01))
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
    mix_node.inputs['Fac'].default_value = 0.4
    
    grid_emission = nodes.new(type='ShaderNodeEmission')
    grid_emission.location = (200, 200)
    grid_emission.inputs['Color'].default_value = (0.0, 1.0, 1.0, 1.0)
    grid_emission.inputs['Strength'].default_value = 5.0
    
    base_emission = nodes.new(type='ShaderNodeEmission')
    base_emission.location = (200, -100)
    base_emission.inputs['Color'].default_value = (0.05, 0.05, 0.15, 1.0)
    base_emission.inputs['Strength'].default_value = 1.0
    
    add_node = nodes.new(type='ShaderNodeAdd')
    add_node.location = (400, 100)
    
    links.new(base_emission.outputs['Emission'], add_node.inputs[0])
    links.new(grid_emission.outputs['Emission'], add_node.inputs[1])
    links.new(add_node.outputs[0], mix_node.inputs[1])
    links.new(base_emission.outputs['Emission'], mix_node.inputs[2])
    links.new(mix_node.outputs[0], output_node.inputs['Surface'])
    
    grid.data.materials.clear()
    grid.data.materials.append(grid_mat)
    
    print(f"グリッドマテリアル作成完了: {grid_mat_name}")
    return grid


def create_clay_material(name, color):
    """単色クレイモデル用のマテリアルを作成する"""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    
    nodes = material.node_tree.nodes
    nodes.clear()
    
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)
    
    emission_node = nodes.new(type='ShaderNodeEmission')
    emission_node.location = (100, 0)
    emission_node.inputs['Color'].default_value = (*color, 1.0)
    emission_node.inputs['Strength'].default_value = 0.3
    
    material.node_tree.links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
    
    return material


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
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    cabin.select_set(True)
    bpy.ops.object.join()
    
    print(f"プレースホルダー車作成: {body.name} at {location}")
    return body


def setup_car(key, car_data, imported_object):
    """車の設定（位置、名前、マテリアル）を適用"""
    if imported_object is None:
        return None
    
    imported_object.name = f"{key}_{car_data['name']}"
    imported_object.data.name = f"{key}_{car_data['name']}.Mesh"
    imported_object.location = car_data['position']
    
    bpy.context.view_layer.objects.active = imported_object
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
    
    mat_name = f"clay_{key}_{car_data['name']}"
    clay_material = create_clay_material(mat_name, car_data['color'])
    
    if len(imported_object.data.materials) == 0:
        imported_object.data.materials.append(clay_material)
    else:
        imported_object.data.materials[0] = clay_material
    
    return imported_object


def setup_camera_and_lighting():
    """カメラとライティングを設定する"""
    scene = bpy.context.scene
    
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and obj.name != "ComparisonCamera":
            obj.select_set(True)
    bpy.ops.object.delete()
    
    bpy.ops.object.camera_add(location=(5, -5, 3))
    camera = bpy.context.active_object
    camera.name = "ComparisonCamera"
    scene.camera = camera
    
    target_location = (0, 0, 0)
    direction = target_location - camera.location
    rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    camera.rotation_euler = rotation_euler
    
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


# ============================================================
# メイン処理
# ============================================================
if __name__ == "__main__":
    clear_scene()
    
    grid = create_grid_floor()
    print(f"グリッド床面を作成しました: {grid.name}")
    
    imported_cars = {}
    
    for key, car_data in CARS.items():
        print(f"\n--- {key} ({car_data['name']}) を読み込み中: {car_data['glb_path']} ---")
        
        glb_path = car_data['glb_path']
        
        if os.path.exists(glb_path):
            imported_object = import_glb_file(glb_path)
            
            if imported_object:
                setup_car(key, car_data, imported_object)
                imported_cars[key] = imported_object
                print(f"成功: '{imported_object.name}' をインポートしました")
                print(f"  - 位置: {imported_object.location}")
            else:
                print(f"警告: GLBインポートに失敗、プレースホルダーを使用します")
                placeholder = create_placeholder_car(key, car_data['color'], car_data['position'])
                imported_cars[key] = placeholder
        else:
            print(f"警告: ファイルが見つかりません - {glb_path}")
            print(f"  -> プレースホルダー車を作成します")
            placeholder = create_placeholder_car(key, car_data['color'], car_data['position'])
            imported_cars[key] = placeholder
        
        car_data['imported'] = True
    
    print("\n=== インポート結果 ===")
    for key, obj in imported_cars.items():
        print(f"{key}: {obj.name} at {obj.location}")
    
    carA = imported_cars.get("carA")
    carB = imported_cars.get("carB")
    
    if carA and carB:
        print("\n準備完了: 'carA' と 'carB' 変数としてオブジェクトが利用可能です")
    else:
        print("\n一部の車のインポートに失敗しました。パスを確認してください。")
    
    camera = setup_camera_and_lighting()
