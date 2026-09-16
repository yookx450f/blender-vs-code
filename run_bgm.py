"""
作业BGM动画 - 実行用ランチャー

用法:
    python run_bgm.py              # GUIモードでシーン確認
    python run_bgm.py --render     # MP4レンダリング実行
    python run_bgm.py --car_id 5   # 車種IDを指定して実行
    python run_bgm.py --car_id 2,5,8 --render  # 複数車ID指定（カンマ区切り、最大10台）＋レンダリング
                                   # → 複数の Blender を並列起動して同時レンダリング
"""
import subprocess, sys, os, tempfile, multiprocessing

BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "bgm_main.py")

def _render_single_car(args):
    """
    プロセスプールで呼び出されるレンダリング関数。
    引数: (use_render, car_id)
    戻り値: (car_id, success_bool)
    """
    use_render, car_id = args
    
    if not os.path.exists(MAIN_SCRIPT):
        return (car_id, False, f"スクリプトが見つかりません - {MAIN_SCRIPT}")
    if not os.path.exists(BLENDER_PATH):
        return (car_id, False, f"Blenderが見つかりません - {BLENDER_PATH}")

    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2"]
    if use_render:
        cmd.extend(["--background"])

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    if SCRIPT_DIR not in existing:
        env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + existing

    env["BGM_CAR_ID"] = car_id
    env["BGM_OUTPUT_SUFFIX"] = f"_{car_id}"
    if use_render:
        env["BGM_RENDER"] = "1"

    cmd.extend(["--python", MAIN_SCRIPT])

    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
        if result.returncode == 0:
            return (car_id, True, "成功")
        else:
            return (car_id, False, f"return code: {result.returncode}")
    except Exception as e:
        return (car_id, False, str(e))

# winget でインストールされた ffmpeg のパス（PATH更新が反映されないため直接指定）
_FFMPEG_CANDIDATES = [
    r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe",
    "ffmpeg",  # PATH に通っている場合用フォールバック
]

def _find_ffmpeg():
    for path in _FFMPEG_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None

def concat_mp4_files(mp4_paths, output_path):
    """ffmpeg で個別MP4ファイルを結合する"""
    ffmpeg_exe = _find_ffmpeg()
    if not ffmpeg_exe:
        print("  ffmpeg がインストールされていません")
        return False
    
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    for p in mp4_paths:
        tmp.write(f"file '{p}'\n")
    tmp.close()

    cmd = [
        ffmpeg_exe, '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', tmp.name,
        '-c:v', 'copy',
        '-c:a', 'copy',
        output_path
    ]

    print(f"ffmpeg 結合コマンド: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR)
        os.unlink(tmp.name)
        if result.returncode == 0:
            return True
        else:
            print("  ffmpeg 結合に失敗しました（個別MP4は出力されています）")
            return False
    except FileNotFoundError:
        os.unlink(tmp.name)
        print("  ffmpeg がインストールされている必要があります。個別MP4ファイルが出力されています。")
        return False
    except Exception as e:
        try: os.unlink(tmp.name)
        except: pass
        print(f"  ffmpeg エラー: {e}")
        return False

def run_single_car_gui(use_render=False, car_id=None):
    """GUIモード用（単一車、順次実行）"""
    if not os.path.exists(MAIN_SCRIPT):
        print(f"エラー: スクリプトが見つかりません - {MAIN_SCRIPT}")
        return False
    if not os.path.exists(BLENDER_PATH):
        print(f"エラー: Blenderが見つかりません - {BLENDER_PATH}")
        return False

    cmd = [BLENDER_PATH, "--addons", "io_scene_gltf2"]
    if use_render:
        cmd.extend(["--background"])
    else:
        print("GUIモード（Blenderウィンドウでシーン確認）")

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    if SCRIPT_DIR not in existing:
        env["PYTHONPATH"] = SCRIPT_DIR + os.pathsep + existing

    if car_id is not None:
        env["BGM_CAR_ID"] = car_id
        env["BGM_OUTPUT_SUFFIX"] = f"_{car_id}"
        print(f"車種ID指定: {car_id}")
    if use_render:
        env["BGM_RENDER"] = "1"

    cmd.extend(["--python", MAIN_SCRIPT])

    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, env=env)
        if result.returncode == 0:
            return True
        else:
            print(f"エラー (return code: {result.returncode})")
            return False
    except Exception as e:
        print(f"エラー: {e}")
        return False

def main():
    use_render = "--render" in sys.argv
    car_ids = []

    if "--car_id" in sys.argv:
        idx = sys.argv.index("--car_id")
        if idx + 1 < len(sys.argv):
            car_ids_str = sys.argv[idx + 1]
            car_ids = [cid.strip() for cid in car_ids_str.split(",") if cid.strip()]
        else:
            print("エラー: --car_id の後に車種IDを指定してください")
            sys.exit(1)
    else:
        # --car_id が指定されていない場合はGUIモード（単一処理）
        success = run_single_car_gui(use_render=use_render, car_id=None)
        sys.exit(0 if success else 1)

    # 最大10台制限
    if len(car_ids) > 10:
        print("エラー: 車種IDは最大10台まで指定可能です")
        sys.exit(1)

    if len(car_ids) == 0:
        print("エラー: 有効な車種IDが指定されていません")
        sys.exit(1)

    print("=" * 60)
    print(f"作业BGM動画 - 複数車一括生成 ({len(car_ids)}台)")
    print(f"対象車ID: {', '.join(car_ids)}")
    print("=" * 60)

    if use_render:
        print("レンダリングモード（バックグラウンド実行）")

    desktop = os.path.expanduser("~").replace("\\", "/") + "/Desktop"

    if len(car_ids) >= 2 and use_render:
        # --- 並列レンダリングモード ---
        cpu_count = multiprocessing.cpu_count()
        # BlenderはCPU/GPUを多く消費するため、コア数の半分（最大4）を並列数に設定
        max_workers = min(max(2, cpu_count // 2), 4)
        print(f"\n並列レンダリング開始 (最大 {max_workers} プロセス同時起動)")

        from concurrent.futures import ProcessPoolExecutor, as_completed

        tasks = [(use_render, cid) for cid in car_ids]
        success_paths = []
        failed_ids = []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_render_single_car, task): cid for task, cid in zip(tasks, car_ids)}
            
            completed = 0
            for future in as_completed(futures):
                cid = futures[future]
                completed += 1
                try:
                    car_id_result, success, msg = future.result()
                    if success:
                        mp4_path = f"{desktop}/bgm_output_{car_id_result}.mp4"
                        success_paths.append(mp4_path)
                        print(f"  [{completed}/{len(car_ids)}] ✓ 車種ID {car_id_result} 完了 → {mp4_path}")
                    else:
                        failed_ids.append(car_id_result)
                        print(f"  [{completed}/{len(car_ids)}] ✗ 車種ID {car_id_result} 失敗 ({msg})")
                except Exception as e:
                    failed_ids.append(cid)
                    print(f"  [{completed}/{len(car_ids)}] ✗ 車種ID {cid} エラー ({e})")

    else:
        # --- 順次実行モード（1台 or GUIモード） ---
        success_paths = []
        failed_ids = []

        for i, cid in enumerate(car_ids, 1):
            print(f"\n[{i}/{len(car_ids)}] 車種ID {cid} を処理中...")
            if run_single_car_gui(use_render=use_render, car_id=cid):
                mp4_path = f"{desktop}/bgm_output_{cid}.mp4"
                success_paths.append(mp4_path)
                print(f"  成功: {mp4_path}")
            else:
                failed_ids.append(cid)
                print(f"  失敗: 車種ID {cid}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("処理結果サマリー")
    print("=" * 60)
    print(f"成功: {len(success_paths)}台 / {len(car_ids)}台")

    all_success = True
    if failed_ids:
        all_success = False
        print(f"失敗車ID: {', '.join(failed_ids)}")

    # ffmpeg で結合（成功したファイルのみ）
    # ★ffmpeg実行を無効化している場合、下の条件の前に False and を追加
    if False and len(success_paths) >= 2 and use_render:
        output_all = f"{desktop}/bgm_all_output.mp4"
        print(f"\nffmpeg で全ファイルを結合中... → {output_all}")
        concat_mp4_files(success_paths, output_all)
        print(f"結合完了: {output_all}")
    elif len(success_paths) == 1 and use_render:
        print(f"出力先: {success_paths[0]}")
    else:
        if not use_render:
            print(f"出力先: {desktop}/bgm_output.mp4")

    print("\n完了!")
    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
