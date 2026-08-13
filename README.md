# blender-vs-code

## 概要

BlenderのVS Code拡張機能に依存せず、コマンドラインから直接Blenderを起動して3Dシーンを作成するシステムです。

2台の車の比較アニメーションを4つのカットに分割し、各カットを独立したBlenderプロセスで実行することで、アニメーションデータの干渉を防ぎます。

## アーキテクチャ

### カット構成

| カット | フレーム範囲 | シーン内容 |
|--------|-------------|-----------|
| カット1 | 0-648 | シーン1-4（斜め上視点→トップビュー→Z軸回転→サイドビュー） |
| カット2 | 648-1224 | シーン5-7（全長差表示→正面ビュー→横幅差表示） |
| カット3 | 1224-1584 | シーン8-9（左側低位置→最低地上高差表示） |
| カット4 | 1584-1992 | シーン10-11（横並び移動→最小回転半径アニメーション） |

### カット独立実行方式

各カットは独立したBlenderプロセスで実行され、個別の`.blend`ファイルを生成します。これにより、後続カットのオブジェクトが累積して画面が偏移する問題を解消しています。

```
python run.py all
  ↓
┌─────────────────────────────────────────┐
│ カット1 → cut1_scene.blend             │
│ カット2 → cut2_scene.blend             │
│ カット3 → cut3_scene.blend             │
│ カット4 → cut4_scene.blend             │
└─────────────────────────────────────────┘
  ↓
python merge_cuts.py (レンダリング合成)
```

## ファイル構成

### メインスクリプト
- [`blend_scene_creator.py`](blend_scene_creator.py) - シーン作成のメインスクリプト
- [`run.py`](run.py) - Blenderを起動するラッパースクリプト
- [`merge_cuts.py`](merge_cuts.py) - 各カットのレンダリング合成用スクリプト

### アニメーション設定
- [`animation_common.py`](animation_common.py) - 共通関数・`CutState`クラス
- [`animation_settings_cut1.py`](animation_settings_cut1.py) - カット1（シーン1-4）
- [`animation_settings_cut2.py`](animation_settings_cut2.py) - カット2（シーン5-7）
- [`animation_settings_cut3.py`](animation_settings_cut3.py) - カット3（シーン8-9）
- [`animation_settings_cut4.py`](animation_settings_cut4.py) - カット4（シーン10-11）
- [`animation_settings.py`](animation_settings.py) - 統合モジュール

### 設定ファイル
- [`cars_config.json`](cars_config.json) - 車種のGLBパス・寸法情報
- [`cars_config_template.json`](cars_config_template.json) - 設定ファイルのテンプレート

## 使い方

### 1. 全カットを独立実行（推奨）

```bash
python run.py all
```

各カットを別プロセスで実行し、`cut1_scene.blend` 〜 `cut4_scene.blend` を生成します。

### 2. 個別カットを実行

```bash
python run.py 1  # カット1のみ（フレーム0-648）
python run.py 2  # カット2のみ（フレーム648-1224）
python run.py 3  # カット3のみ（フレーム1224-1584）
python run.py 4  # カット4のみ（フレーム1584-1992）
```

### 3. レンダリング合成

```bash
# 各カットをレンダリングし、ffmpegで1つのMP4に合成
python merge_cuts.py

# レンダリングのみ（合成は行わない）
python merge_cuts.py --render-only
```

### 4. Blender GUIで直接確認

```bash
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" cut1_scene.blend
```

## 車の設定を変更する

[`cars_config.json`](cars_config.json) を編集して車種情報を更新します：

```json
{
  "carA": {
    "name": "Corolla Cross 2025",
    "glb_path": "C:\\path\\to\\car.glb",
    "color": [0.8, 0.2, 0.2],
    "dimensions_mm": {
      "length": 4455,
      "width": 1825,
      "height": 1620,
      "ground_clearance": 160,
      "turning_radius": 5200
    }
  }
}
```

## 環境設定

- Blender 5.2+
- Windows 10/11
- Python 3.8+
- ffmpeg（レンダリング合成用）

## 参考ドキュメント

- [`plans/cut-independent-file-design.md`](plans/cut-independent-file-design.md) - カット独立ファイル保存方式の設計
- [`plans/cut-isolation-redesign.md`](plans/cut-isolation-redesign.md) - カット完全分離のリデザイン計画
