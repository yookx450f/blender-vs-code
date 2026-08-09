"""
Blenderをコマンドライン経由で起動してスクリプトを実行するラッパースクリプト

使い方:
    python run.py              # デフォルトのシーンを作成（ウィンドウを開いたまま）
    python run.py --view       # レンダー後にビューポートを開く
    python run.py --render     # レンダーのみ実行して終了
    python run.py --background # バックグラウンドモードで実行（ウィンドウを閉じる）
"""

import subprocess
import sys
import os
import argparse

# Blenderの実行ファイルパス
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 現在のディレクトリにあるスクリプトのパス
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "blend_scene_creator.py")


def run_blender(scene_script=None, view=False, render_only=False, background=False):
    """Blenderをコマンドラインから起動してスクリプトを実行する"""
    
    if scene_script is None:
        scene_script = MAIN_SCRIPT
    
    if not os.path.exists(scene_script):
        print(f"エラー: スクリプトが見つかりません - {scene_script}")
        return False
    
    if not os.path.exists(BLENDER_PATH):
        print(f"エラー: Blenderが見つかりません - {BLENDER_PATH}")
        print("パスが正しいか確認してください。")
        return False
    
    # glTFアドオンを有効にするために、--addonsフラグで明示的に有効化
    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2", "--python", scene_script]
    
    if background:
        # バックグラウンドモード: ウィンドウを開かず、スクリプト完了後に自動終了
        cmd.insert(1, "--background")
        print("バックグラウンドモードでBlenderを起動します（スクリプト実行後、ウィンドウが閉じます）")
    else:
        # GUIモード: ウィンドウを開いたまま、スクリプト実行後も操作可能
        print("GUIモードでBlenderを起動します（スクリプト実行後もウィンドウが開いたままになります）")
    
    if render_only:
        cmd.extend(["--render-output", "//output/"])
        print("レンダーモードを有効にしました")
    
    print(f"Blenderを起動します...")
    print(f"コマンド: {' '.join(cmd)}")
    print("-" * 50)
    print("GLBファイルをインポートするには、glTF 2.0 formatアドオンが有効になっている必要があります。")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print("-" * 50)
            print("Blenderのスクリプト実行が完了しました。")
            if not background:
                print("注意: Blenderウィンドウは開いたままです。必要に応じて手動で閉じてください。")
        else:
            print("-" * 50)
            print(f"Blenderの実行中にエラーが発生しました (終了コード: {result.returncode})")
        return result.returncode == 0
    except Exception as e:
        print(f"エラー: Blenderの実行に失敗しました - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Blenderを起動して3Dシーンを作成する")
    parser.add_argument("--script", type=str, help="実行するPythonスクリプトのパス")
    parser.add_argument("--view", action="store_true", help="ビューポートを開く")
    parser.add_argument("--render", action="store_true", help="レンダーのみ実行")
    parser.add_argument("--background", action="store_true", help="バックグラウンドモードで実行（ウィンドウを閉じる）")
    
    args = parser.parse_args()
    
    success = run_blender(
        scene_script=args.script,
        view=args.view,
        render_only=args.render,
        background=args.background
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
