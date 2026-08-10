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


def run_blender(scene_script=None, render_only=False):
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
    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2"]
    
    if render_only:
        # バックグラウンドモードでアニメーションレンダリング実行
        cmd.extend(["--background"])
        cmd.extend(["--python", scene_script])
        cmd.extend(["--render-output", "//output/"])
        # レンダリング用スクリプトを追加（シーン作成後にレンダリングを実行）
        render_script = os.path.join(SCRIPT_DIR, "render_animation.py")
        if not os.path.exists(render_script):
            create_render_script(render_script)
        cmd.extend(["--python", render_script])
        print("アニメーションレンダリングモード（EEVEE、バックグラウンド実行）")
    else:
        # GUIモード: ウィンドウを開いたまま、スクリプト実行後も操作可能
        cmd.extend(["--python", scene_script])
        print("GUIモードでBlenderを起動します（シーン作成のみ、自動レンダリングは行いません）")
    
    print(f"Blenderを起動します...")
    print(f"コマンド: {' '.join(cmd)}")
    print("-" * 50)
    print("GLBファイルをインポートするには、glTF 2.0 formatアドオンが有効になっている必要があります。")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print("-" * 50)
            print("Blenderのスクリプト実行が完了しました。")
            if not render_only:
                print("注意: Blenderウィンドウは開いたままです。必要に応じて手動で閉じてください。")
        else:
            print("-" * 50)
            print(f"Blenderの実行中にエラーが発生しました (終了コード: {result.returncode})")
        return result.returncode == 0
    except Exception as e:
        print(f"エラー: Blenderの実行に失敗しました - {e}")
        return False


def create_render_script(path):
    """アニメーションレンダリング用スクリプトを作成"""
    script_content = '''import bpy

# アニメーションレンダリングを実行（EEVEE）
print("=== アニメーションレンダリング開始 (EEVEE) ===")
bpy.ops.render.render(animation=True)
print("アニメーションレンダリング完了！")
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(script_content)


def convert_png_sequence_to_mp4(input_pattern, output_path, fps=24):
    """PNGシーケンスをffmpegでmp4に変換する"""
    import shutil
    
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("警告: ffmpeg がシステムにインストールされていません。")
        print("PNGシーケンスのまま出力されます。")
        return False
    
    cmd = [
        ffmpeg_path,
        "-y",  # 上書き許可
        "-framerate", str(fps),
        "-i", input_pattern,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",  # 偶数サイズにパディング
        output_path
    ]
    
    print(f"PNGシーケンスをmp4に変換中...")
    print(f"コマンド: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"変換完了: {output_path}")
            return True
        else:
            print(f"ffmpeg変換エラー: {result.stderr}")
            return False
    except Exception as e:
        print(f"ffmpeg実行エラー: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Blenderを起動して3Dシーンを作成する")
    parser.add_argument("--script", type=str, help="実行するPythonスクリプトのパス")
    parser.add_argument("--render", action="store_true",
                        help="アニメーションレンダリングを実行（EEVEE、PNGシーケンス出力＋mp4変換）")
    
    args = parser.parse_args()
    
    success = run_blender(
        scene_script=args.script,
        render_only=args.render
    )
    
    # PNGシーケンスをmp4に変換（--render オプションの場合のみ）
    if success and args.render:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        png_pattern = os.path.join(desktop_path, "car_comparison.mp4.%04d.png")
        mp4_output = os.path.join(desktop_path, "car_comparison.mp4")
        
        print("\n=== PNGシーケンスをmp4に変換 ===")
        convert_png_sequence_to_mp4(png_pattern, mp4_output, fps=24)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
