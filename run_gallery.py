"""
Gallery BGM動画 - 一括実行ラッパー（Blenderをコマンドライン経由で起動）

使い方:
    python run_gallery.py              # ギャラリーBGM動画を全自動生成
"""

import subprocess
import sys
import os

# Blenderの実行ファイルパス
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 現在のディレクトリにあるスクリプトのパス
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GALLERY_SCRIPT = os.path.join(SCRIPT_DIR, "gallery_main.py")


def run_gui_mode():
    """GUIモードが指定されているかをチェック"""
    return "--gui" in sys.argv


def run_gallery():
    """ギャラリーBGM動画をBlenderで実行"""
    print("=" * 60)
    print("Gallery BGM動画 - Blenderラッパー")
    print("=" * 60)
    
    if not os.path.exists(BLENDER_PATH):
        print(f"エラー: Blenderが見つかりません - {BLENDER_PATH}")
        sys.exit(1)
    
    # GUIモードかバックグラウンドモードでコマンドを分ける
    use_gui = run_gui_mode()
    
    # 環境変数でGUIモードを伝える
    env = os.environ.copy()
    env["GALLERY_GUI_MODE"] = "1" if use_gui else "0"
    
    if use_gui:
        cmd = [BLENDER_PATH, "--factory-startup", "--python", GALLERY_SCRIPT]
        print(f"\nGUIモードでBlenderを実行中...")
        print("(Blenderウィンドウが起動します)")
    else:
        cmd = [BLENDER_PATH, "--background", "--python", GALLERY_SCRIPT]
        print(f"\nバックグラウンドモードでBlenderを実行中...")
    print(f"コマンド: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
        result = subprocess.run(cmd, cwd=SCRIPT_DIR)
        
        if result.returncode != 0:
            print(f"\nエラー: Blenderの実行が失敗しました (return code: {result.returncode})")
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("Gallery BGM動画の生成が完了しました！")
        desktop_path = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
        print(f"出力先: {desktop_path}/gallery_bgm.mp4")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n実行を中断しました")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_gallery()
