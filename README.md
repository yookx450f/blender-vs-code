# blender-vs-code

## 概要

BlenderのVS Code拡張機能に依存せず、コマンドラインから直接Blenderを起動して3Dシーンを作成するシステムです。

## ファイル構成

- [`blend_scene_creator.py`](blend_scene_creator.py) - メインのシーン作成スクリプト
- [`run.py`](run.py) - Blenderを起動するラッパースクリプト
- [`import bpy.py`](import bpy.py) - VS Code拡張機能経由用のスクリプト（旧版）

## 使い方

### 1. run.py を使う場合（推奨）

```bash
# デフォルト: GUIモードでBlenderを開き、スクリプト実行後もウィンドウを開いたままにする
python run.py

# バックグラウンドモード: スクリプト完了後にBlenderが自動終了する
python run.py --background

# レンダーのみ実行
python run.py --render

# 別スクリプトを実行
python run.py --script <パス>
```

### 2. 直接Blenderを起動する場合

#### GUIモード（ウィンドウを開いたまま）
```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --addons io_scene_gltf2 --python blend_scene_creator.py
```

#### バックグラウンドモード（ウィンドウを閉じる）
```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --addons io_scene_gltf2 --python blend_scene_creator.py
```

### 3. スクリプトのカスタマイズ

[`blend_scene_creator.py`](blend_scene_creator.py) の `CARS` 辞書を変更して車種情報を更新:

```python
CARS = {
    "carA": {
        "name": "Car Name",
        "glb_path": r"C:\path\to\your\car.glb",
        "position": (-2.0, 0, 0),
        "color": (0.8, 0.2, 0.2),
    },
    ...
}
```

## Blenderウィンドウの制御について

### 重要な仕組み

Blenderは以下の2つのモードで動作します：

| モード | フラグ | ウィンドウの状態 | 用途 |
|--------|--------|------------------|------|
| GUIモード | なし | スクリプト完了後も開いたまま | 目視確認、手動調整、動画書き出し |
| バックグラウンドモード | `--background` | スクリプト完了後に自動終了 | 自動化、バッチ処理 |

### デフォルトはGUIモード

[`run.py`](run.py) のデフォルト動作はGUIモードです。これにより：

1. スクリプトが走り終わった後の3D空間を直接目視で確認できる
2. カメラアングルを手動で調整できる
3. 動画書き出しなどの操作を人間が行える

バックグラウンドモードが必要な場合のみ `--background` フラグを追加してください。

### スクリプトの自動終了について

[`blend_scene_creator.py`](blend_scene_creator.py) の末尾には `sys.exit(0)` がありません。これにより、スクリプトが正常に完了してもBlenderプロセスは終了せず、ウィンドウが開いたままになります。

## 環境設定

- Blender 5.2+
- Windows 10/11
- Python 3.8+
