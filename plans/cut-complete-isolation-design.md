# カット完全分離設計（固定位置定義方式）

## 概要

各カットの開始/終了位置を固定値として定義し、カット間の連鎖依存を解消する。
これにより、`python run.py 1` で Cut1 のみを再実行しても、Cut2以降に影響しない構造を実現する。

---

## 現状の問題点

### 問題1: カット間の位置継承依存

`animation_settings.py` で、各カットが前のカットの戻り値（`CutState`）を受け取っている。
Cut1の終了位置を変更すると、Cut2以降の開始位置も変わる。

```
Cut1 → CutState(car_a_loc, car_b_loc, ...) → Cut2 → CutState(...) → Cut3 → ...
```

### 問題2: animation_data_clear() の使用

`animation_settings_cut4.py:135-138` と `animation_settings_cut5.py:87-90` で、
車のアニメーションデータを全消去している。これは他のカットのキーフレームも削除する可能性がある。

### 問題3: Emptyオブジェクトの跨カット依存

Cut4で作成する `CarA_TurnPivot` / `CarB_TurnPivot` が Cut5で参照されている。

---

## 設計方針

### 核心: 固定位置定義ファイル + オフセット保存ファイル

```
animation_cut_positions.py  ← 各カットの境界位置を定数で定義
cut_offsets.json           ← Cut1実行時に生成、GLBオフセット結果を保存
```

### アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│              run.py (エントリーポイント)               │
│  python run.py 1  → Cut1のみ実行                     │
│  python run.py 2  → Cut2のみ実行                     │
│  ...                                                 │
│  python run.py all → 全カット独立実行                 │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│         blend_scene_creator.py (シーン作成)           │
│  - GLBインポート、オフセット計算                      │
│  - cut_offsets.json に結果を保存                     │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│         animation_settings.py (統合エントリー)        │
│  - 環境変数 CUT_NUMBER で対象カットを選択             │
│  - 各カットを独立して呼び出し                         │
└──────┬───────┬───────┬───────┬───────┘
       │       │       │       │
   ┌───▼──┐ ┌─▼───┐ ┌─▼───┐ ┌─▼───┐ ┌─▼───┐
   │Cut1  │ │Cut2 │ │Cut3 │ │Cut4 │ │Cut5 │
   │独立  │ │独立 │ │独立 │ │独立 │ │独立 │
   └──────┘ └─────┘ └─────┘ └─────┘ └─────┘
```

---

## 実装ステップ

### ステップ1: 固定位置定義ファイルを作成

**新規ファイル**: `animation_cut_positions.py`

各カットの境界での車の位置・カメラの位置を定数として定義する。

```python
"""
各カットの固定位置定義ファイル

各カットは自分のフレーム範囲内のキーフレームのみを操作し、
前のカットの結果に依存しない。
"""

# Cut1 の開始位置 (frame 0)
# 注意: carAのYオフセット、接地Z値は実行時に決定されるため、
#       cut_offsets.json から読み込む
CUT1_START_FRAME = 0
CUT1_END_FRAME = 696

# Cut2 のフレーム範囲
CUT2_START_FRAME = 696
CUT2_END_FRAME = 1272

# Cut3 のフレーム範囲
CUT3_START_FRAME = 1272
CUT3_END_FRAME = 1632

# Cut4 のフレーム範囲
CUT4_START_FRAME = 1632
CUT4_END_FRAME = 2256

# Cut5 のフレーム範囲
CUT5_START_FRAME = 2256
CUT5_END_FRAME = 2880

# カメラの固定位置（カット境界で）
CAMERA_POSITIONS = {
    "cut1_start": {"loc": (6.5, -6.5, 4.0), "target": (0.0, 0.0, 1.5)},
    "cut1_end":   {"loc": (8.0, 0.0, 2.5), "target": (0.0, 0.0, 1.5)},
    "cut2_end":   {"loc": (0.0, -7.0, 2.5), "target": (0.0, 0.0, 1.5)},
    "cut3_end":   {"loc": (-6.0, -2.0, 0.8), "target": (0.0, 0.0, 1.5)},
    "cut4_end":   {"loc": None, "target": None},  # Cut4は回転中心に依存
    "cut5_end":   {"loc": None, "target": None},  # Cut5はCut4のカメラ位置を継承
}

# オフセットJSONファイルのパス（実行時に生成/読み込み）
OFFSET_FILE = "cut_offsets.json"
```

### ステップ2: cut_offsets.json の生成・読み込みロジックを追加

**修正ファイル**: `blend_scene_creator.py`

Cut1実行時（または初回実行時）に、GLBオフセット計算結果をJSONに保存する。

```json
{
    "offset_a": [0.0, 0.0],
    "offset_b": [0.0, 0.0],
    "grounded_z_a": 0.85,
    "grounded_z_b": 0.92,
    "rear_offset_y": 0.15,
    "car_a_center": [0.0, 0.0, 0.85],
    "car_b_center": [0.0, 0.0, 0.92]
}
```

### ステップ3: animation_settings_cut1.py を修正

**変更点**:
- `clear_object_animation()` をフレーム 0-696 範囲に限定
- オフセット計算結果を `cut_offsets.json` に保存
- `previous_state` の返却は維持する（後方互換性のため）

### ステップ4: animation_settings_cut2.py を修正

**変更点**:
- `previous_state` 引数をオプション化（指定なしの場合は固定位置を使用）
- 車の開始位置を `cut_offsets.json` または固定値から読み込み
- カメラの開始位置を `CAMERA_POSITIONS["cut1_end"]` から読み込み

### ステップ5: animation_settings_cut3.py を修正

**変更点**:
- `previous_state` 引数をオプション化
- 車の開始位置を固定値から読み込み（Cut2終了時と同じ位置）
- カメラの開始位置を `CAMERA_POSITIONS["cut2_end"]` から読み込み

### ステップ6: animation_settings_cut4.py を修正

**変更点**:
- `animation_data_clear()` の使用を廃止
- 代わりに、フレーム範囲限定でキーフレームを操作
- Emptyオブジェクトの作成・削除をCut4内で完結
- Emptyの位置情報を `cut_offsets.json` に保存（Cut5用）

### ステップ7: animation_settings_cut5.py を修正

**変更点**:
- `animation_data_clear()` の使用を廃止
- Emptyオブジェクトが存在しない場合のフォールバック処理を追加
- Cut4の保存データからEmpty位置を読み込む

### ステップ8: animation_settings.py を修正

**変更点**:
- カット連鎖を解消（各カットを独立して呼び出し）
- `previous_state` の受け渡しを廃止、またはオプション化

```python
def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    target_cut = _get_target_cut()
    
    # 各カットを独立して実行（previous_state不要）
    if target_cut in ("all", "1"):
        setup_cut1_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions)
    
    if target_cut in ("all", "2"):
        setup_cut2_animations(scene, camera, imported_cars, car_dimensions=car_dimensions)
    
    if target_cut in ("all", "3"):
        setup_cut3_animations(scene, camera, imported_cars, car_dimensions=car_dimensions)
    
    if target_cut in ("all", "4"):
        setup_cut4_animations(scene, camera, imported_cars, car_dimensions=car_dimensions)
    
    if target_cut in ("all", "5"):
        setup_cut5_animations(scene, camera, imported_cars, car_dimensions=car_dimensions)
```

---

## 変更ファイル一覧

| ファイル | 操作 | 変更内容 |
|---------|------|---------|
| `animation_cut_positions.py` | **新規作成** | 固定位置定義、フレーム範囲定数 |
| `blend_scene_creator.py` | 修正 | オフセットJSON保存ロジック追加 |
| `animation_settings_cut1.py` | 修正 | JSON保存、clear範囲限定 |
| `animation_settings_cut2.py` | 修正 | previous_state不要化 |
| `animation_settings_cut3.py` | 修正 | previous_state不要化 |
| `animation_settings_cut4.py` | 修正 | animation_data_clear除去、Empty独立化 |
| `animation_settings_cut5.py` | 修正 | animation_data_clear除去、Emptyフォールバック |
| `animation_settings.py` | 修正 | カット連鎖解消 |

---

## テスト戦略

1. `python run.py 1` → Cut1のみ実行、cut_offsets.json が生成されることを確認
2. `python run.py 2` → Cut2のみ実行（Cut1を実行せずに）、固定位置から開始することを確認
3. `python run.py 1` → Cut1を修正して再実行、Cut2に影響しないことを確認
4. `python run.py all` → 全カット独立実行、各カットが正しく動作することを確認

---

## リスクと対応

| リスク | 影響 | 対応策 |
|-------|------|--------|
| Cut1のオフセット計算結果が変わる | Cut2以降の開始位置がずれる | cut_offsets.json を明示的に更新するフローを文書化 |
| Emptyオブジェクトが存在しない | Cut5でエラー発生 | フォールバックとして固定位置を使用 |
| animation_data_clear() 除去後のキーフレーム競合 | 予期しないアニメーション発動 | フレーム範囲を厳密に管理、重複キーフレームを回避 |
