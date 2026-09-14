"""
Gallery BGM動画 - 内部用メインスクリプト（Blender内から実行される）
シーンの生成、カメラアニメーションの設定、レンダリングをすべて実行する。
"""

import bpy
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def main():
    print("=" * 60)
    print("Gallery BGM動画 - 一括生成パイプライン")
    print("=" * 60)
    
    # GUIモードチェック（環境変数から）
    use_gui = os.environ.get("GALLERY_GUI_MODE", "0") == "1"
    if use_gui:
        print("[GUIモード] レンダリングはスキップします\n")
    else:
        print("[バックグラウンドモード] 全自動レンダリング実行\n")
    
    # --- Step 1: シーン生成 ---
    print("\n=== Step 1: シーン生成 ===")
    from gallery_scene_creator import create_gallery_scene
    create_gallery_scene()
    
    # --- Step 2: カメラアニメーション・レンダリング設定 ---
    print("\n=== Step 2: アニメーション・レンダリング設定 ===")
    from render_gallery import load_gallery_config, setup_background_black, setup_camera_animation, configure_render_settings
    
    config = load_gallery_config()
    gallery_settings = config.get("gallery", {})
    
    # 背景を真っ黒に
    setup_background_black()
    
    # カメラアニメーション（GUIモード時はフレーム数を200以下に制限）
    setup_camera_animation(gallery_settings, max_frames=200 if use_gui else None)
    
    # レンダリング設定
    configure_render_settings()
    
    # --- Step 3: レンダリング ---
    if not use_gui:
        print("\n=== Step 3: レンダリング実行 ===")
        try:
            bpy.ops.render.render(animation=True)
            print("\n" + "=" * 60)
            print("Gallery BGM動画の生成が完了しました！")
            desktop_path = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
            print(f"出力先: {desktop_path}/gallery_bgm.mp4")
            print("=" * 60)
        except RuntimeError as e:
            if "Could not open file for writing" in str(e):
                print("注意: レンダリングがブロックされました。")
            else:
                raise
    else:
        print("\n=== Step 3: GUIモードのためレンダリングスキップ ===")
        print("Blenderウィンドウでシーンを確認できます。")


if __name__ == "__main__":
    main()
