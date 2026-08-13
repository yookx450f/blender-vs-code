"""
カット独立ファイルのレンダリング合成スクリプト

各カットの.blendファイルを個別にレンダリングし、ffmpegで1つのMP4に合成する。

使い方:
    python merge_cuts.py              # 全カットをレンダリングして合成
    python merge_cuts.py --render-only # レンダリングのみ（合成は行わない）
"""

import subprocess
import sys
import os
import glob

# Blenderの実行ファイルパス
BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"

# 現在のディレクトリ
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# カット定義（フレーム範囲）
CUTS = {
    "1": {"start": 0, "end": 648, "label": "カット1（シーン1-4）"},
    "2": {"start": 648, "end": 1224, "label": "カット2（シーン5-7）"},
    "3": {"start": 1224, "end": 1584, "label": "カット3（シーン8-9）"},
    "4": {"start": 1584, "end": 1992, "label": "カット4（シーン10-11）"},
}


def render_single_cut(cut_number, output_dir):
    """単一カットの.blendファイルをレンダリングする"""
    blend_file = os.path.join(SCRIPT_DIR, f"cut{cut_number}_scene.blend")

    if not os.path.exists(blend_file):
        print(f"  ✗ ファイルが見つかりません: {blend_file}")
        return False

    if not os.path.exists(BLENDER_PATH):
        print(f"  ✗ Blenderが見つかりません: {BLENDER_PATH}")
        return False

    # 出力ディレクトリを作成
    cut_output_dir = os.path.join(output_dir, f"cut{cut_number}")
    os.makedirs(cut_output_dir, exist_ok=True)

    # Blenderのバックグラウンドレンダリングコマンド
    cmd = [
        BLENDER_PATH,
        "--background",
        blend_file,
        "--addons", "io_scene_gltf2",
        "--animation",
        "--output", os.path.join(cut_output_dir, "frame_%04d"),
        "--frame-start", str(CUTS[cut_number]["start"]),
        "--frame-end", str(CUTS[cut_number]["end"]),
        "-f", "ANIM"  # アニメーションレンダリング実行
    ]

    print(f"  レンダリング中: カット{cut_number}")
    print(f"  コマンド: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ カット{cut_number}のレンダリングが完了しました")
            return True
        else:
            print(f"  ✗ カット{cut_number}のレンダリングに失敗しました")
            if result.stderr:
                print(f"  エラー: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ レンダリング実行エラー: {e}")
        return False


def render_cut_to_video(cut_number, output_dir):
    """単一カットをMP4動画としてレンダリングする（BlenderのFFMPEG出力を使用）"""
    blend_file = os.path.join(SCRIPT_DIR, f"cut{cut_number}_scene.blend")

    if not os.path.exists(blend_file):
        print(f"  ✗ ファイルが見つかりません: {blend_file}")
        return False

    if not os.path.exists(BLENDER_PATH):
        print(f"  ✗ Blenderが見つかりません: {BLENDER_PATH}")
        return False

    # 出力動画ファイルパス
    output_video = os.path.join(output_dir, f"cut{cut_number}_render.mp4")

    # Blenderのバックグラウンドレンダリングコマンド（FFMPEG直接出力）
    cmd = [
        BLENDER_PATH,
        "--background",
        blend_file,
        "--addons", "io_scene_gltf2",
        "--animation",
        "--output", output_video,
        "--frame-start", str(CUTS[cut_number]["start"]),
        "--frame-end", str(CUTS[cut_number]["end"]),
        "-f", "ANIM"  # アニメーションレンダリング実行
    ]

    print(f"  レンダリング中: カット{cut_number} → {output_video}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            if os.path.exists(output_video):
                print(f"  ✓ カット{cut_number}の動画が生成されました")
                return True
            else:
                print(f"  ✗ 出力ファイルが生成されていません")
                return False
        else:
            print(f"  ✗ カット{cut_number}のレンダリングに失敗しました")
            if result.stderr:
                print(f"  エラー: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ レンダリング実行エラー: {e}")
        return False


def merge_videos_with_ffmpeg(output_dir, final_output_path):
    """ffmpegで各カットの動画を1つに合成する"""
    # 各カットの動画ファイルを確認
    video_files = []
    for cut in ["1", "2", "3", "4"]:
        video_file = os.path.join(output_dir, f"cut{cut}_render.mp4")
        if os.path.exists(video_file):
            video_files.append(video_file)
        else:
            print(f"  ✗ 動画ファイルが見つかりません: {video_file}")
            return False

    # ffmpegのconcatフィルタ用入力リストを作成
    concat_list_path = os.path.join(output_dir, "concat_list.txt")
    with open(concat_list_path, 'w', encoding='utf-8') as f:
        for vf in video_files:
            # ffmpegのconcat demuxerは絶対パスを必要とする
            f.write(f"file '{os.path.abspath(vf)}'\n")

    # ffmpegコマンドで動画を連結
    cmd = [
        "ffmpeg",
        "-y",  # 出力ファイルを上書き
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",  # リエンコードなしでコピー
        final_output_path
    ]

    print(f"\n  動画を合成中...")
    print(f"  コマンド: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            if os.path.exists(final_output_path):
                print(f"  ✓ 合成動画が生成されました: {final_output_path}")
                return True
            else:
                print(f"  ✗ 出力ファイルが生成されていません")
                return False
        else:
            print(f"  ✗ ffmpeg合成に失敗しました")
            if result.stderr:
                print(f"  エラー: {result.stderr[:200]}")
            return False
    except FileNotFoundError:
        print("  ✗ ffmpeg がインストールされていません。")
        print("  https://ffmpeg.org/download.html からダウンロードしてください。")
        return False
    except Exception as e:
        print(f"  ✗ ffmpeg実行エラー: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="カット独立ファイルのレンダリング合成")
    parser.add_argument("--render-only", action="store_true",
                        help="レンダリングのみ実行（合成は行わない）")
    parser.add_argument("--output", type=str, default=None,
                        help="出力ディレクトリ（デフォルト: ./render_output）")

    args = parser.parse_args()

    # 出力ディレクトリ
    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(SCRIPT_DIR, "render_output")
    os.makedirs(output_dir, exist_ok=True)

    print("="*60)
    print("カット独立ファイル レンダリング合成")
    print("="*60)

    # 各カットをレンダリング
    print("\n--- 各カットのレンダリング ---")
    render_results = {}
    for cut in ["1", "2", "3", "4"]:
        success = render_cut_to_video(cut, output_dir)
        render_results[cut] = success

    # レンダリング結果サマリー
    print("\n--- レンダリング結果 ---")
    all_rendered = True
    for cut, success in render_results.items():
        status = "✓ 成功" if success else "✗ 失敗"
        print(f"  カット{cut}: {status}")
        if not success:
            all_rendered = False

    if not all_rendered:
        print("\n✗ 一部のカットのレンダリングに失敗しました。")
        sys.exit(1)

    if args.render_only:
        print("\n✓ レンダリングのみ実行モードです。合成はスキップします。")
        print(f"出力ディレクトリ: {output_dir}")
        return

    # 動画を合成
    final_output_path = os.path.join(output_dir, "final_animation.mp4")
    print("\n--- 動画合成 ---")
    merge_success = merge_videos_with_ffmpeg(output_dir, final_output_path)

    if merge_success:
        print(f"\n{'='*60}")
        print(f"✓ 全処理完了!")
        print(f"最終出力: {final_output_path}")
        print(f"{'='*60}")
    else:
        print(f"\n✗ 動画合成に失敗しました。")
        print(f"個別のレンダリングファイルは {output_dir} に保存されています。")
        sys.exit(1)


if __name__ == "__main__":
    main()
