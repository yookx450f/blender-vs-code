"""
作业BGM动画 - メイン実行スクリプト
blender --background --python bgm_main.py で実行。
"""
import bpy, os, sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import os as _os
_car_id_env = _os.environ.get("BGM_CAR_ID")
if _car_id_env is not None:
    print(f"環境変数 BGM_CAR_ID から車種IDを読み込み: {_car_id_env}")

from bgm_config import GLB_DIRECTORY, FPS, DURATION_SECONDS, TOTAL_FRAMES, START_Y, END_Y

# 環境変数が設定されていればそれを優先、そうでなければ bgm_config.py の CAR_ID を使用
import bgm_config
CAR_ID = _car_id_env if _car_id_env is not None else bgm_config.CAR_ID
from bgm_core import (get_car_info, clear_scene, enable_gltf_addon, import_glb_file,
    apply_clay_material_to_meshes, apply_rotation_to_car, auto_ground_car, scale_car_to_dimensions,
    create_grid_floor, setup_lighting, setup_black_world, create_name_label,
    setup_camera, setup_car_animation, setup_camera_animation, setup_render)

def main():
    print("=" * 60)
    print("作业BGM動画 - 生成パイプライン")
    print("=" * 60)

    # Step 1: 初期化
    print("\n[Step 1] シーン初期化")
    clear_scene()
    enable_gltf_addon()
    setup_black_world()

    # Step 2: グリッド床
    print("\n[Step 2] グリッド床作成")
    create_grid_floor(100)

    # Step 3: ライティング
    print("\n[Step 3] ライティング設定")
    setup_lighting()

    # Step 4: 車型情報取得・GLBインポート
    print("\n[Step 4] 車インポート")
    car_info = get_car_info(CAR_ID)
    if not car_info:
        print(f"エラー: 車型ID {CAR_ID} が見つかりません")
        return
    car_name = car_info.get('name', 'Unknown')
    glb_file = car_info.get('glb_filename', '')
    rot_dir = int(car_info.get('rotation_direction', 0))
    glb_path = os.path.join(GLB_DIRECTORY, glb_file)
    print(f"  車型: {car_name}")
    print(f"  GLB: {glb_path}")

    car_obj = import_glb_file(glb_path)
    if not car_obj:
        print(f"エラー: GLBインポート失敗 - {glb_file}")
        return
    car_obj.name = "Car_" + car_name

    # ★実寸法に合わせてスケールを適用 (Short2と同様)
    print("\n[Step 4.5] スケール調整")
    scale_car_to_dimensions(car_obj, car_info)

    # クレイマテリアル適用
    apply_clay_material_to_meshes(car_obj)
    apply_rotation_to_car(car_obj, rot_dir)
    auto_ground_car(car_obj)

    # 車の位置を(0, 0)に固定
    car_obj.location.x = 0.0
    car_obj.location.y = 0.0

    print(f"  初期位置: ({car_obj.location.x}, {car_obj.location.y}, {car_obj.location.z})")

    # 車の全長を取得（カメラスライド範囲に使用）
    car_length_m = float(car_info.get('length', 4800)) / 1000.0
    print(f"  車全長: {car_length_m}m")

    # Step 5: カメラ設定 (車の全長を渡す)
    print("\n[Step 5] カメラ設定")
    cam_obj = setup_camera(car_length_m)

    # Step 6: 車名ラベル
    print("\n[Step 6] 車名ラベル作成")
    create_name_label(car_obj, car_name)

    # Step 7: アニメーション設定（カメラのみスライド）
    print(f"\n[Step 7] アニメーション設定 ({TOTAL_FRAMES}フレーム)")
    setup_car_animation(car_obj, FPS, TOTAL_FRAMES, START_Y, END_Y)
    setup_camera_animation(cam_obj, car_length_m, FPS, TOTAL_FRAMES, margin=3.0)

    # Step 8: レンダリング設定
    print("\n[Step 8] レンダリング設定")
    setup_render(FPS, TOTAL_FRAMES)
    scene = bpy.context.scene
    print(f"  フレーム範囲: {scene.frame_start}-{scene.frame_end}")
    print(f"  出力先: {scene.render.filepath}.mp4")

    # 環境変数でレンダリングモードなら実際のレンダリングを実行
    import os as _os2
    if _os2.environ.get("BGM_RENDER"):
        print("\n[Step 9] レンダリング実行中...")
        bpy.ops.render.render(animation=True)
        print(f"  レンダリング完了 → {scene.render.filepath}.mp4")

    print("\n" + "=" * 60)
    print("シーン生成完了！")
    print("=" * 60)

if __name__ == "__main__":
    main()
