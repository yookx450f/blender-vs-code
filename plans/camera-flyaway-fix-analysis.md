# カメラ飛翔問題 分析・修正方針書

**作成日**: 2026-09-27  
**ステータス**: 修正方針策定中  
**対象モジュール**: `animation_settings_short2.py`, `short2_cuts.py`, `short2_utils.py`

---

## 1. 現在の症状

Blenderのスクリーンショットで確認:
- カメラ位置: **(15m, 15m, 15m)** — `_clamp_camera_location()` の上限値に到達
- フレーム: 139/312（カット1途中）
- 車は中央に小さく表示され、カメラが過度に遠い位置にある

---

## 2. 根本原因の特定

### 問題A: 動的スケーリングの上限値が大きすぎる

[`animation_settings_short2.py`](animation_settings_short2.py) で計算されるスケール値:

| パラメータ | 式 | scale_factor=4.0時の最大値 |
|-----------|-----|--------------------------|
| `cam_scale` | `scale_factor * 1.5` | **6.0** |
| `cam_start_x` | `-3.0 * cam_scale` | **-18.0m** |
| `cam_start_y` | `-6.0 * cam_scale` | **-36.0m** ⚠️ |
| `cam_start_z` | `3.5 * min(cam_scale, 2.0)` | 7.0m (上限あり) |

特に `cam_start_y` は最大 **-36.0m** に到達可能。これはクランプ値 ±15m の2.4倍。

### 問題B: カメラパターン適用と直接計算の制限が異なる

```
# L217-227: camera_pattern のスケール適用 (上限 min(cam_scale, 1.5))
scaled_sp = (sp[0] * min(cam_scale, 1.5), ...)

# L108-110: cam_start_x/y の計算 (上限なし!)
cam_start_x = -3.0 * cam_scale   # max -18.0
cam_start_y = -6.0 * cam_scale   # max -36.0
```

L217-227では camera_pattern にスケール適用時に `min(cam_scale, 1.5)` の上限があるが、L108-110の direct計算には制限がない。この値は L194-196 で strategy_configに注入され、camera_pattern が未設定時のフォールバックとして使用される。

### 問題C: クランプ関数の重複・値の不一致

| モジュール | CAMERA_LOCATION_MAX | 場所 |
|-----------|-------------------|------|
| `short2_utils.py` | **12.0** | L25 |
| `short2_cuts.py` | **15.0** | L200 |

現在の `_set_camera_position_and_rotation_keyframe()` は `short2_cuts.py` 内の `_clamp_camera_location()` (L200, MAX=15.0) を使用している。スクリーンショットのカメラ位置が (15m, 15m, 15m) になっていることから、このクランプ値に到達していることが確認できた。

### 問題D: 円弧計算での半径过大

[`short2_cuts.py:120`](short2_cuts.py:120):
```python
arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
```

`cam_start_y = -36.0m` の場合、`arc_radius ≈ 36.1m` になる。この半径で円弧パンニングを行うと、当然 ±15m を超える位置にカメラが移動する。

---

## 3. 修正方針

### 修正1: カメラ距離の絶対上限を厳格化 ⭐ 最重要

**対象**: [`animation_settings_short2.py`](animation_settings_short2.py) L104-116

動的スケーリング時に計算される各値に明らかな上限を追加:

```python
# 現在のコード
cam_scale = scale_factor * 1.5            # 最大 6.0 に
cam_start_x = -3.0 * cam_scale            # 最大 -18.0m
cam_start_y = -6.0 * cam_scale            # 最大 -36.0m

# → 修正後 (提案)
cam_scale = min(scale_factor * 1.5, 2.0)           # 上限 2.0 に固定
cam_start_x = max(-10.0, -3.0 * cam_scale)         # Xは ±10m に制限
cam_start_y = max(-10.0, -6.0 * cam_scale)         # Yも ±10m に制限
cam_start_z = min(3.5 * cam_scale, 7.0)            # Zの上限を維持
```

巨大車両ではカメラを遠ざけるより、レンズのFOV調整で対応する。

### 修正2: クランプ値の一貫性

**対象**: `short2_utils.py` L25, `short2_cuts.py` L200

```python
# short2_utils.py: CAMERA_LOCATION_MAX = 12.0
# short2_cuts.py:  CAMERA_LOCATION_MAX = 15.0

# → 統一値に (提案)
CAMERA_LOCATION_MAX = 12.0
```

### 修正3: レンズ補正の強化

**対象**: [`animation_settings_short2.py`](animation_settings_short2.py) L180-184

巨大車両ではカメラを近づけすぎない代わりに、レンズをより広角にして画面に収める:

```python
# 現在のコード
adjusted_lens = round(35 * min(cam_scale, 1.5))  # max 52mm

# → 修正後 (提案)
if scale_factor > 2.0:
    adjusted_lens = max(24, round(35 / min(scale_factor, 3.0)))  # 広角化
else:
    adjusted_lens = round(35 * min(cam_scale, 1.5))
adjusted_lens = max(24, min(85, adjusted_lens))
```

### 修正4: 円弧半径の制限

**対象**: [`short2_cuts.py`](short2_cuts.py) L120

```python
arc_radius = math.sqrt(cam_start[0]**2 + cam_start[1]**2)
arc_radius = min(arc_radius, 10.0)  # 半径に上限を追加
```

---

## 4. リスク評価

| 修正項目 | リスク | 備考 |
|---------|-------|------|
| 修正1: スケーリング上限値変更 | **中** | 既存の巨大車両動画に影響する可能性。テスト必要 |
| 修正2: クランプ値統一 | **低** | より厳しくなるが、飛翔防止に寄与 |
| 修正3: レンズ補正強化 | **低** | FOV調整は可視的に自然に見える |
| 修正4: 円弧半径制限 | **中** | 極端なケースのみ影響 |

---

## 5. テスト計画

1. 標準サイズの車両 (scale_factor ≈ 1.0) で動作確認
2. 大型SUV (scale_factor ≈ 1.5) で動作確認
3. 巨大トラック (scale_factor ≈ 3.0+) で動作確認
4. カメラ位置が ±12m に収まっていることをログで確認

---

## 6. 関連ファイル

| ファイル | 変更箇所 |
|---------|---------|
| [`animation_settings_short2.py`](animation_settings_short2.py) | L104-116, L180-184 |
| [`short2_cuts.py`](short2_cuts.py) | L120, L200 |
| [`short2_utils.py`](short2_utils.py) | L25 |
