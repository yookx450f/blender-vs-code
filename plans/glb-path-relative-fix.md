# GLBパス相対化修正計画

## 概要
`C:\3d\Modly\glb` を参照している箇所を、プロジェクト内の `./glb` などの相対パスに変更する。

## 修正対象ファイル一覧

### JSON設定ファイル (3ファイル)

| ファイル | 変更前 | 変更後 |
|---|---|---|
| `cars_config.json` | `"glb_dir": "C:\\\\3d\\\\Modly\\\\glb"` | `"glb_dir": "./glb"` |
| `animals_config.json` | `"glb_dir": "C:\\\\3d\\\\Modly\\\\animal_glb"` | `"glb_dir": "./animal_glb"` |
| `games_config.json` | `"glb_dir": "C:/3d/Modly/game_glb"` | `"glb_dir": "./game_glb"` |

### Pythonファイル (4ファイル)

| ファイル | 行番号 | 変更内容 |
|---|---|---|
| `bgm_config.py` | L2 | `GLB_DIRECTORY` をスクリプトディレクトリからの相対パスに変更 |
| `comparison_manager.py` | L444, L876 | 固定文字列 `C:\3d\Modly\glb` を `os.path.join(os.path.dirname(__file__), "glb")` に変更 |
| `blend_scene_creator.py` | L854 | `human.glb` パスを `./animal_glb/human.glb` の相対パスに変更 |
| `import bpy.py` | L20, L26 | 直接指定 glb_path を相対パスに変更（テスト用） |

## 実装手順

1. JSONファイル3つを修正 (`write_to_file`)
2. `bgm_config.py` の GLB_DIRECTORY を修正
3. `comparison_manager.py` の固定パス×2箇所を修正
4. `blend_scene_creator.py` の human.glb パスを修正
5. `import bpy.py` の glb_path を修正（任意）
6. 動作テスト

## メリット
- プロジェクトの移植性向上（他のPCでもそのまま利用可能）
- GLBファイルの管理が一元化される
- Gitでのバージョン管理が容易になる
