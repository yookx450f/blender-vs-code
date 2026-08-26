"""
Blenderをコマンドライン経由で起動してスクリプトを実行するラッパースクリプト

使い方:
    python run.py              # 全カット（それぞれ独立プロセスで実行）
    python run.py 1            # カット1のみ（シーン1-4、フレーム0-696）
    python run.py 2            # カット2のみ（シーン5-7、フレーム696-1272）
    python run.py 3            # カット3のみ（シーン8-9、フレーム912-1128）
    python run.py 4            # カット4のみ（シーン10-14、フレーム1512-2256）
    python run.py 4b           # カット4bのみ（カメラ回転カット、フレーム2256-3024）
    python run.py 5            # カット5のみ（シーン13-14、フレーム3024-3648）
    python run.py short        # ショート動画（縦長9:16、車重なりカット、フレーム0-240）
    python run.py short2       # ショート動画v2（縦長9:16、キーフレーム半透明、フレーム0-240）
    python run.py --render     # 全カットをレンダリング合成してMP4出力
"""

import subprocess
import sys
import os
import random
import argparse

# Blenderの実行ファイルパス
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# カット定義（フレーム範囲）
# 【改訂: カット1短縮】各カットのフレームが120ずつずれた
CUTS = {
    "all": {"start": 0, "end": 3360, "label": "全カット（シーン1-14＋カメラ回転）"},
    "1": {"start": 0, "end": 576, "label": "カット1（シーン1-4）"},
    "2": {"start": 576, "end": 912, "label": "カット2（シーン5-7）"},  # 【改訂】カット2短縮 (24秒→14秒)
    "3": {"start": 912, "end": 1128, "label": "カット3（シーン8-9）"},  # 【改訂】カット3さらに短縮 (15秒→9秒)
    "4": {"start": 1512, "end": 2256, "label": "カット4（シーン10-14）"},  # 【修正】終了フレームを2256に（シーン14:車が左右スライドまで含む）
    "4b": {"start": 2136, "end": 2904, "label": "カット4b（カメラ回転カット）"},
    "5": {"start": 2904, "end": 3528, "label": "カット5（シーン13-14）"},
    "short": {"start": 0, "end": 240, "label": "ショート動画（縦長9:16、車重なりカット）"},
    "short2": {"start": 0, "end": 240, "label": "ショート動画v2（縦長9:16、キーフレーム半透明）"},
}

# 現在のディレクトリにあるスクリプトのパス
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "blend_scene_creator.py")


def run_single_cut(cut_number):
    """単一カットをBlenderで実行し、個別の.blendファイルを生成する"""
    cut_info = CUTS.get(cut_number)
    if not cut_info:
        print(f"エラー: 無効なカット番号 '{cut_number}' です。")
        return False

    frame_start = cut_info["start"]
    frame_end = cut_info["end"]
    cut_label = cut_info["label"]

    # short2の場合、ランダム延長を追加（+0〜48フレーム = +0〜2秒）
    extra_frames = 0
    if cut_number == "short2":
        extra_frames = random.randint(0, 48)
        frame_end = frame_start + 240 + extra_frames
        print(f"\n{'='*60}")
        print(f"=== カット{cut_number}実行: {cut_label} ===")
        print(f"ランダム延長: +{extra_frames}フレーム (+{extra_frames/24:.1f}秒)")
        print(f"フレーム範囲: {frame_start}-{frame_end} ({(frame_end - frame_start)/24:.1f}秒)")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"=== カット{cut_number}実行: {cut_label} ===")
        print(f"フレーム範囲: {frame_start}-{frame_end}")
        print(f"{'='*60}")

    if not os.path.exists(MAIN_SCRIPT):
        print(f"エラー: スクリプトが見つかりません - {MAIN_SCRIPT}")
        return False

    if not os.path.exists(BLENDER_PATH):
        print(f"エラー: Blenderが見つかりません - {BLENDER_PATH}")
        return False

    # glTFアドオンを有効にするコマンド
    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2", "--python", MAIN_SCRIPT]

    # 環境変数でカット番号とフレーム範囲を渡す
    env = os.environ.copy()
    env["CUT_NUMBER"] = cut_number
    env["FRAME_START"] = str(frame_start)
    env["FRAME_END"] = str(frame_end)
    env["SHORT2_EXTRA_FRAMES"] = str(extra_frames)

    print(f"Blenderを起動します...")
    print(f"コマンド: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, env=env)
        if result.returncode == 0:
            blend_file = os.path.join(SCRIPT_DIR, f"cut{cut_number}_scene.blend")
            if os.path.exists(blend_file):
                print(f"✓ cut{cut_number}_scene.blend が生成されました")
            return True
        else:
            print(f"✗ カット{cut_number}の実行に失敗しました (終了コード: {result.returncode})")
            return False
    except Exception as e:
        print(f"エラー: Blenderの実行に失敗しました - {e}")
        return False


def run_all_cuts_independent():
    """全カットを独立プロセスで実行し、個別の.blendファイルを生成する"""
    print("\n" + "="*60)
    print("全カット独立実行モード")
    print("各カットを別プロセスで実行し、個別の.blendファイルを生成します")
    print("="*60)

    results = {}
    for cut in ["1", "2", "3", "4", "4b", "5"]:
        success = run_single_cut(cut)
        results[cut] = success
        if not success:
            print(f"\n⚠ カット{cut}でエラーが発生しました。続行します...")

    # 結果サマリー
    print("\n" + "="*60)
    print("実行結果サマリー")
    print("="*60)
    all_success = True
    for cut, success in results.items():
        status = "✓ 成功" if success else "✗ 失敗"
        print(f"  カット{cut}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\n全カットの.blendファイルを生成しました。")
        print("確認方法:")
        for cut in ["1", "2", "3", "4", "4b", "5"]:
            print(f"  - cut{cut}_scene.blend をBlenderで開いて確認")
        print("\nレンダリング合成するには: python run.py --render")
    else:
        print("\n一部のカットで失敗しました。個別に再実行してください。")

    return all_success


def run_blender(scene_script=None, render_only=False, cut_number="all"):
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

    # "all"モードは独立プロセスで実行
    if cut_number == "all" and not render_only:
        return run_all_cuts_independent()

    # 単一カット実行
    cut_info = CUTS.get(cut_number)
    if not cut_info:
        print(f"エラー: 無効なカット番号 '{cut_number}' です。使用可能な値: all, 1, 2, 3, 4, 4b, 5")
        return False

    frame_start = cut_info["start"]
    frame_end = cut_info["end"]
    cut_label = cut_info["label"]

    # short2の場合、ランダム延長を追加（+0〜48フレーム = +0〜2秒）
    extra_frames = 0
    if cut_number == "short2":
        extra_frames = random.randint(0, 48)
        frame_end = frame_start + 240 + extra_frames

    print(f"=== カット選択: {cut_label} ===")
    if cut_number == "short2":
        print(f"ランダム延長: +{extra_frames}フレーム (+{extra_frames/24:.1f}秒)")
    print(f"フレーム範囲: {frame_start}-{frame_end}")

    # glTFアドオンを有効にするために、--addonsフラグで明示的に有効化
    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2"]

    if render_only:
        # バックグラウンドモードでアニメーションレンダリング実行
        cmd.extend(["--background"])
        cmd.extend(["--python", scene_script])
        # --render-output は削除（blend_scene_creator.py で出力パスを設定しているため）
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

    # カット番号とフレーム範囲を環境変数として渡す
    env = os.environ.copy()
    env["CUT_NUMBER"] = cut_number
    env["FRAME_START"] = str(frame_start)
    env["FRAME_END"] = str(frame_end)
    env["SHORT2_EXTRA_FRAMES"] = str(extra_frames)

    print(f"Blenderを起動します...")
    print(f"コマンド: {' '.join(cmd)}")
    print("-" * 50)
    print("GLBファイルをインポートするには、glTF 2.0 formatアドオンが有効になっている必要があります。")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, env=env)
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


def main():
    parser = argparse.ArgumentParser(description="Blenderを起動して3Dシーンを作成する")
    parser.add_argument("cut", nargs="?", default="all", type=str,
                        help="実行するカット番号 (all=全カット独立実行, 1/2/3/4/4b/5=各カット, short=縦長ショート動画)")
    parser.add_argument("--script", type=str, help="実行するPythonスクリプトのパス")
    parser.add_argument("--render", action="store_true",
                        help="アニメーションレンダリングを実行（EEVEE、FFMPEGで直接MP4出力）")

    args = parser.parse_args()

    # カット番号の検証
    if args.cut not in CUTS:
        print(f"エラー: 無効なカット番号 '{args.cut}' です。")
        print(f"使用可能な値: all, 1, 2, 3, 4, 4b, 5, short")
        sys.exit(1)

    success = run_blender(
        scene_script=args.script,
        render_only=args.render,
        cut_number=args.cut
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
