# カット完全分離再設計計画

## 現状の問題

### 依存関係構造（修正前）
```
Cut1 → returns {car_a_end, car_b_end, loc_phase4, rot_phase4, grounded_z_a, grounded_z_b}
         ↓
Cut2 → takes cut1_result → returns {car_a_end, car_b_end, loc_scene7_end, rot_scene7_end}
         ↓
Cut3 → takes cut2_result → returns {car_a_end, car_b_end, loc_scene8_end, rot_scene8_end}
         ↓
Cut4 → takes cut3_result → animation_data_clear() ← 全アニメーションデータを消去！！！
```

**問題点**:
1. Cut4の `animation_data_clear()` が前面のカットのキーフレームをすべて消去
2. 各カットが同じオブジェクトの animation_data を共有しているため、後続処理が前面に影響
3. オフセット計算に副作用（transform_apply）がある

---

## 再設計方針

### 統一されたインターフェース

各カットは以下の形式でデータをやり取りする:

```python
# 入力: 前のカットの最終状態（位置情報のみ）
previous_state = {
    'car_a_loc': (x, y, z),   # CarAの最終位置
    'car_b_loc': (x, y, z),   # CarBの最終位置
    'camera_loc': (x, y, z),  # カメラの最終位置
    'camera_rot': (x, y, z),  # カメラの最終回転
}

# 出力: このカットの最終状態（位置情報のみ）
return {
    'car_a_loc': (x, y, z),
    'car_b_loc': (x, y, z),
    'camera_loc': (x, y, z),
    'camera_rot': (x, y, z),
}
```

### 各カットのフレーム範囲管理

| カット | フレーム範囲 | シーン | 管理責任 |
|--------|-------------|--------|---------|
| Cut1 | 0-648 | 1-4 | この範囲のキーフレームのみ作成・管理 |
| Cut2 | 648-1224 | 5-7 | この範囲のキーフレームのみ作成・管理 |
| Cut3 | 1224-1584 | 8-9 | この範囲のキーフレームのみ作成・管理 |
| Cut4 | 1584-1992 | 10-11 | この範囲のキーフレームのみ作成・管理 |

### 分離ルール

1. **各カットは自分のフレーム範囲内のキーフレームのみを操作する**
2. **前のカットの最終位置のみを継承（変数共有なし）**
3. **animation_data_clear() は使用しない**
4. **オフセット計算に副作用を持たせない**

---

## 実装計画

### 段階1: 統一インターフェースの定義

`CutState` クラスまたは辞書形式で、カット間のデータ受け渡しを標準化する。

```python
# animation_common.py に追加
class CutState:
    """カット間の状態継承用データ構造"""
    def __init__(self, car_a_loc, car_b_loc, camera_loc, camera_rot):
        self.car_a_loc = car_a_loc
        self.car_b_loc = car_b_loc
        self.camera_loc = camera_loc
        self.camera_rot = camera_rot
```

### 段階2: 各カットの再設計

#### Cut1 (animation_settings_cut1.py)
- **変更点**: 
  - `clear_object_animation()` を削除（初回実行なので不要）
  - 戻り値を統一形式に変更
- **フレーム範囲**: 0-648

#### Cut2 (animation_settings_cut2.py)
- **変更点**:
  - 前のカットの最終位置のみを受け取る
  - フレーム648で開始位置キーフレームを設定
  - 戻り値を統一形式に変更
- **フレーム範囲**: 648-1224

#### Cut3 (animation_settings_cut3.py)
- **変更点**:
  - 前のカットの最終位置のみを受け取る
  - フレーム1224で開始位置キーフレームを設定
  - 戻り値を統一形式に変更
- **フレーム範囲**: 1224-1584

#### Cut4 (animation_settings_cut4.py)
- **変更点**:
  - `animation_data_clear()` を**完全に削除**
  - 前のカットの最終位置のみを受け取る
  - フレーム1584で開始位置キーフレームを設定
  - Empty親設定は維持するが、車のアニメーションデータには触れない
- **フレーム範囲**: 1584-1992

### 段階3: animation_settings.py の再設計

```python
def setup_all_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    # カット1を実行
    state1 = setup_cut1_animations(...)
    
    # カット2を実行（カット1の最終状態のみを継承）
    state2 = setup_cut2_animations(previous_state=state1, ...)
    
    # カット3を実行（カット2の最終状態のみを継承）
    state3 = setup_cut3_animations(previous_state=state2, ...)
    
    # カット4を実行（カット3の最終状態のみを継承）
    setup_cut4_animations(previous_state=state3, ...)
```

---

## 影響分析

### 変更が必要なファイル
| ファイル | 変更内容 | 影響度 |
|---------|---------|-------|
| `animation_settings.py` | 呼び出し方を統一形式に変更 | 中 |
| `animation_settings_cut1.py` | 戻り値形式変更、clear削除 | 小 |
| `animation_settings_cut2.py` | パラメータ変更、戻り値形式変更 | 大 |
| `animation_settings_cut3.py` | パラメータ変更、戻り値形式変更 | 大 |
| `animation_settings_cut4.py` | animation_data_clear削除、パラメータ変更 | 大 |

### リスク
1. Cut2-4のキーフレーム設定ロジックが既存の cutX_result に依存している部分がある → すべて書き換えが必要
2. Cut4のEmpty親設定は車の親子関係を変更するため、慎重にテストが必要

---

## テスト戦略

1. `python run.py 1` → Cut1のみ動作確認
2. `python run.py 2` → Cut1+Cut2動作確認
3. `python run.py 3` → Cut1+Cut2+Cut3動作確認
4. `python run.py 4` → 全カット動作確認
5. `python run.py all` → 全カット統合テスト
