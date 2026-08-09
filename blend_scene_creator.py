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
    },
    "carB": {
        "name": "Land Cruiser",
        "glb_path": r"C:\3d\Modly\glb\colloraCross2026.glb",
        "position": (2.0, 0, 0),
        "color": (0.2, 0.2, 0.8),
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
    
    print("\n" + "=" * 50)
    print("シーン作成完了！")
    print("=" * 50)
    
    return imported_cars


# スクリプトとして実行された場合
if __name__ == "__main__":
    result = main()
    # シーン作成後にBlenderを自動終了しない（ウィンドウを開いたまま）
