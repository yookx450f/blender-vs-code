"""
作业BGM动画 - 実行用ランチャー

用法:
    python run_bgm.py              # GUIモードでシーン確認
    python run_bgm.py --render     # MP4レンダリング実行
"""
import subprocess, sys, os

BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "bgm_main.py")

def run(use_render=False):
    if not os.path.exists(MAIN_SCRIPT):
        print(f"エラー: スクリプトが見つかりません - {MAIN_SCRIPT}")
        return False
    if not os.path.exists(BLENDER_PATH):
        print(f"エラー: Blenderが見つかりません - {BLENDER_PATH}")
        return False

    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2"]
    if use_render:
        cmd.extend(["--background"])
        print("レンダリングモード（バックグラウンド実行）")
    else:
        print("GUIモード（Blenderウィンドウでシーン確認）")

    cmd.extend(["--python", MAIN_SCRIPT])
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    if SCRIPT_DIR not in existing:
        env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + existing

    print(f"コマンド: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
        if result.returncode == 0:
            print("\n完了!")
            desktop = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
            print(f"出力先: {desktop}/bgm_output.mp4")
            return True
        else:
            print(f"\nエラー (return code: {result.returncode})")
            return False
    except Exception as e:
        print(f"エラー: {e}")
        return False

if __name__ == "__main__":
    use_render = "--render" in sys.argv
    success = run(use_render=use_render)
    sys.exit(0 if success else 1)
