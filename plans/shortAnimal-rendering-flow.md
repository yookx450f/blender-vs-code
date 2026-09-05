# shortAnimal レンダリングフロー仕様書

## 概要
動物ショート動画（shortAnimal）の自動レンダリングパイプラインの完全なフローを記述したドキュメントです。
動画の長さを変更しても確実に最後までレンダリングされるように設計されています。

---

## 1. システム構成

### 主要ファイル
| ファイル | 役割 |
|----------|------|
| [`run.py`](run.py) | エントリポイント。Blenderを起動し、環境変数でカット番号・フレーム範囲を渡す |
| [`blend_scene_creator.py`](blend_scene_creator.py) | Blender内で実行。GLBインポート→シーン構築→アニメーション設定→レンダリング設定 |
| [`animation_settings_shortAnimal.py`](animation_settings_shortAnimal.py) | shortAnimal用のアニメーションキーフレームを設定 |
| [`render_animation.py`](render_animation.py) | 自動レンダリング用スクリプト。--renderフラグ時に実行される |

---

## 2. レンダリングフロー

### ステップ1: run.py から Blender を起動
```bash
python run.py shortAnimal          # GUIモード（シーン作成のみ）
python run.py shortAnimal --render # バックグラウンドレンダリングモード（MP4出力）
```

### ステップ2: 環境変数を渡す
[`run.py`](run.py:103-108) で以下の環境変数セット:
- `CUT_NUMBER`: "shortAnimal"
- `FRAME_START`: 0
- `FRAME_END`: 624（仕様書に基づく総フレーム数）
- `SHORT2_EXTRA_FRAMES`: 0
- `CUT5_EXTRA_FRAMES`: 0

### ステップ3: blend_scene_creator.py が実行される
1. **シーンクリア**: `clear_scene()` で古いオブジェクトを削除
2. **グリッド床面作成**: `create_grid_floor(10.0, 10.0)` 
3. **GLBインポート**: GLBファイルを読み込み、動物モデルを配置
4. **Z軸回転適用**: DBの `rotation_direction` を再帰的に全子メッシュに適用
5. **アニメーション設定**: [`setup_shortAnimal_animations()`](animation_settings_shortAnimal.py) でキーフレームを設定
6. **scene.frame_end 設定**: 総フレーム数(624)をシーンに明示的に設定
7. **レンダリング設定**: EEVEE+FFMPEGでMP4出力準備

### ステップ4: render_animation.py がレンダリングを実行
（`--render`フラグ時のみ）
1. 全オブジェクトのキーフレームから最終フレームを検出
2. `scene.frame_end` が足りない場合は補正
3. `bpy.ops.render.render(animation=True)` でMP4を出力

---

## 3. フレーム数の自動補償メカニズム

### 問題
動画の設定を変更すると、`scene.frame_end`が古い値のままで途中で終了する。

### 解決策
3層の補償仕組み:

| レイヤー | ファイル | メカニズム |
|----------|----------|------------|
| **第1層** | [`run.py`](run.py:43) | CUTS辞書で `end=624` をハードコード |
| **第2層** | [`blend_scene_creator.py`](blend_scene_creator.py:1544) | `scene.frame_end = SHORT_ANIMAL_TOTAL_FRAMES` で明示設定 |
| **第3層** | [`render_animation.py`](render_animation.py:47-59) | キーフレームから最終フレームを検出して補正 |

### 使い方
動画の長さを変更する場合は:
1. [`animation_settings_shortAnimal.py`](animation_settings_shortAnimal.py) の `total_frames` デフォルト値を更新
2. [`run.py`](run.py:43) の CUTS辞書の `end` を更新
3. 第3層の自動補償が働いて、万全なレンダリングが行われる

---

## 4. Z軸回転の処理仕様

### 問題
GLBモデルは複数の子メッシュを含むため、親オブジェクトのみに回転を適用しても効果が出ない。

### 解決策
[`blend_scene_creator.py`](blend_scene_creator.py:1395) で再帰的に全メッシュデータにZ軸回転を適用:
```python
def rotate_mesh_data_recursive(obj):
    if obj.type == 'MESH' and obj.data is not None:
        # メッシュ頂点をZ軸回転
    for child in obj.children:
        rotate_mesh_data_recursive(child)  # 子オブジェクトも再帰処理
```

### DB設定
`animals`テーブルの `rotation_direction` カラムに角度を保存:
- `0`: 正面
- `90`: 右向きのモデルなど、GLBの向きに合わせて調整

---

## 5. shortAnimal アニメーションタイムライン

| カット | フレーム | 時間 | 内容 |
|--------|----------|------|------|
| カット1 | fr0-12 | 0.5秒 | 重叠状態、すべて不透明、カメラ正面→動物A最高ポイント |
| カット2 | fr12-36 | 1秒 | 重叠維持、動物B半透明(0.35) |
| カット3 | fr36-60 | 1.5秒 | 横向きスライド分離、不透明化、カメラ静止 |
| カット4 | fr60-540 | 20秒 | 半径9m円軌道1周（両方を視界に） |
| カット5 | fr540-624 | 3秒 | ゆっくり重叠、B半透明、カメラは正面に戻る |

**合計: 624フレーム (約26秒 @24fps)**

---

## 6. Alpha（透明度）アニメーション

動物Bの透明度は[`animation_settings_shortAnimal.py`](animation_settings_shortAnimal.py) のドライバー式で制御:
```python
alpha_expr = (
    "1.0 if frame < 12 else"           # カット1: 不透明
    " 1.0 - 0.65 * clamp((frame - 12) / 24.0, 0.0, 1.0) if frame < 36 else"  # カット2: 半透明遷移
    " 1.0 if frame < 540 else"        # カット3-4: 不透明
    " 1.0 - 0.65 * clamp((frame - 540) / 84.0, 0.0, 1.0)"  # カット5: 半透明遷移
)
```

---

## 7. テスト手順

### GUIモードで確認
```bash
python run.py shortAnimal
# → Blenderが起動。タイムラインで624フレームまでキーフレームがあるか確認
```

### バックグラウンドレンダリング
```bash
python run.py shortAnimal --render
# → Desktop/shortAnimal_overlap.mp4 が出力される（約26秒）
```

---

## 8. テンプレート構造

上部の変数定義を書き換えるだけで別の動物比較動画に流用可能:

| パラメータ | 設定場所 | 変更方法 |
|------------|----------|----------|
| 動物A/動物Bの選択 | `animals_config.json` | id を変更 |
| 動物の色 | `animals_config.json` | color配列を変更 |
| GLBファイルパス | DB animalsテーブル | glb_filenameを更新 |
| 動画総フレーム数 | [`animation_settings_shortAnimal.py`](animation_settings_shortAnimal.py:125) | total_framesデフォルト値変更 |
| カット時間配分 | [`animation_settings_shortAnimal.py`](animation_settings_shortAnimal.py:210-227) | CUT*_START/CUT*_END を調整 |
