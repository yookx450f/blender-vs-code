"""
Debug script for text positioning issue in scenes 5-6
This script will be run by Blender to print debug information
"""

import bpy
from mathutils import Vector

def main():
    print("\n" + "="*80)
    print("DEBUG: TEXT POSITIONING ISSUE - SCENES 5-6")
    print("="*80)
    
    # テキストコンテナのデバッグ情報取得
    text_container_name = "LengthDiff_Container_Scene5"
    
    if text_container_name in bpy.data.objects:
        container = bpy.data.objects[text_container_name]
        
        print("\n=== TEXT CONTAINER DEBUG INFO ===")
        print(f"Object Name: {container.name}")
        print(f"Location (world): {container.location}")
        print(f"Rotation Euler: {container.rotation_euler}")
        print(f"Rotation Quaternion: {container.rotation_quaternion}")
        print(f"Parent: {container.parent.name if container.parent else 'None'}")
        print(f"Children Count: {len(container.children)}")
        
        # 子オブジェクトの位置も確認
        for child in container.children:
            if child.type == 'MESH':
                print(f"Child '{child.name}' location: {child.location}")
        
        # カメラと車の位置情報も取得
        camera = bpy.data.objects.get("Camera")
        car_a = bpy.data.objects.get("carA")
        car_b = bpy.data.objects.get("carB")
        
        if camera:
            print("\n=== CAMERA POSITION ===")
            print(f"Location: {camera.location}")
            print(f"Rotation Euler: {camera.rotation_euler}")
        
        if car_a:
            print("\n=== CAR A POSITION ===")
            print(f"Location: {car_a.location}")
            bounds = [tuple(b) for b in car_a.bound_box]
            world_bounds = [car_a.matrix_world @ Vector(b) for b in bounds]
            max_z = max(p.z for p in world_bounds)
            min_z = min(p.z for p in world_bounds)
            print(f"Max Z height: {max_z}")
            print(f"Min Z height: {min_z}")
        
        if car_b:
            print("\n=== CAR B POSITION ===")
            print(f"Location: {car_b.location}")
            bounds = [tuple(b) for b in car_b.bound_box]
            world_bounds = [car_b.matrix_world @ Vector(b) for b in bounds]
            max_z = max(p.z for p in world_bounds)
            min_z = min(p.z for p in world_bounds)
            print(f"Max Z height: {max_z}")
            print(f"Min Z height: {min_z}")
        
        # 地面の位置も確認
        floor = bpy.data.objects.get("Grid_Floor")
        if floor:
            print("\n=== FLOOR POSITION ===")
            print(f"Location: {floor.location}")
        
        # コンテナが地面にあるかチェック
        container_z = container.location.z
        car_a_min_z = min_z if car_a else 0
        car_b_min_z = min_z if car_b else 0
        
        print("\n=== POSITION ANALYSIS ===")
        print(f"Container Z: {container_z}")
        print(f"Car A Min Z: {car_a_min_z}")
        print(f"Car B Min Z: {car_b_min_z}")
        
        # 地面からの高さを計算（コンテナのZ座標が車の最小Zより高いか）
        if car_a and container_z > car_a_min_z + 0.1:
            print("✓ Container is above Car A minimum height")
        else:
            print("✗ Container appears to be at or below ground level relative to Car A")
        
        if car_b and container_z > car_b_min_z + 0.1:
            print("✓ Container is above Car B minimum height")
        else:
            print("✗ Container appears to be at or below ground level relative to Car B")
        
    else:
        print(f"ERROR: Text container '{text_container_name}' not found in scene!")
    
    # シーン全体のオブジェクトリストも取得
    print("\n=== ALL OBJECTS IN SCENE ===")
    for obj in bpy.data.objects:
        if obj.type == 'MESH' or obj.type == 'EMPTY':
            print(f"{obj.name} ({obj.type}): location={obj.location}, rotation={obj.rotation_euler}")
    
    print("\n" + "="*80)
    print("END DEBUG INFO")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
