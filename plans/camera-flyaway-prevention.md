# カメラ飛翔問題対策ドキュメント

**作成日**: 2026-09-11  
**ステータス**: 有効  
**対象モジュール**: `animation_common.py`, `short2_utils.py`, `short2_cuts.py`, `blend_scene_creator.py`

---

## 1. 問題の概要

Short2（およびショート動画系）の実行時に、カメラが期待された軌道から外れて異常な位置に飛んでしまう現象。

### 症状
| 項目 | 正常値 | 異常時の値 | 
|------|--------|-----------|
| カメラZ座標 | 3.0-5.0m (円弧) / 8.0m (トップダウン) | 5.5m など中途半端な値 |
| 回転X | ±45°以内 | 65°以上、ジンバルロック領域 |
| カメラ位置 | 円弧軌道上 | 軌道外のランダム位置 |

### 発生条件
- Short2 のフェーズA (トップダウン移動中) または フェーズB (カメラ復帰中) で発生しやすい
- バリエーション設定で `total_frames` が変動し、フレーム境界がシフトしたとき
- Blenderのタイムラインで特定のフレーム(例: fr271)を確認している際に目立つ

---

## 2. 根本原因の分類

### 原因A: ジンバルロック (HIGH PRIORITY)

**場所**: [`set_camera_look_at()`](animation_common.py:95)  
**現象**: カメラがトップダウン位置 `(0, 0, 8)` に近づくと、方向ベクトルが-Z軸に接近し、`rotation_euler` の変換でX軸回転が暴走する

```
方向ベクトル = ターゲット - カメラ位置
カメラが真上(0,0,8)に近づく → 方向ベクトル ≈ (0, 0, -7) → X回転 → π/2 に接近
quat.to_euler() の変換でジンバルロック発症 → 回転値が±180°など異常値になる
```

**現在の対策**: 
- `|dx| < 0.01 AND |dy| < 0.01` の場合のみ特別処理 (L107)
- X軸回転の上限 ±1.4ラジアン (~80°) に制限 (L116-118)

**不十分理由**:
- 補間の中間地点 (例: Z=5.5m で方向ベクトル=(1, -1, -4.5)) では特別処理が効かない
- X軸の制限値 1.4 ラジアンは tight すぎず、ジンバルロックの境界で切り捨てられた回転が残る

### 原因B: keyframe_insert のタイミングミス (MEDIUM PRIORITY)

**場所**: [`short2_utils.py`](short2_utils.py:82) の `_set_rotation_keyframe()`  
**現象**: `keyframe_insert()` は現在のオブジェクトの値を記録するが、`rotation_euler` を設定してからキーフレームを挿入していないと、前回の値が記録される

**歴史**: 試行#4 (2026-08-13) で発見。[`plans/scene1-slide-animation-fix.md`](plans/scene1-slide-animation-fix.md:360) に記録済み。

**ステータス**: 現在のコードでは修正済み (`rotation_euler` を設定してから `keyframe_insert`)。ただし、新コード追加時に再発しないよう注意が必要。

### 原因C: clear_scene() でカメラの回転データが残存 (MEDIUM PRIORITY)

**場所**: [`blend_scene_creator.py:306`](blend_scene_creator.py:306)  
**現象**: `clear_scene()` は ComparisonCamera を保持対象 (`objects_to_keep`) にしているが、カメラの `rotation_euler` や `animation_data` はクリアされていない

```python
# 現在の clear_scene():
objects_to_keep = {"KeyLight", "ComparisonCamera"}  # Cameraは削除されない
for obj in list(bpy.data.objects):
    if obj.name not in objects_to_keep:
        bpy.data.objects.remove(obj, do_unlink=True)
# → カメラの回転状態が残ったままになる
```

**影響**: 前回のShort2実行で設定されたキーフレームやrotation_eulerが次回に引き継がれる

### 原因D: キーフレーム間隔が広い (LOW PRIORITY)

**場所**: [`short2_cuts.py`](short2_cuts.py:95) - `keyframe_interval = 24`  
**現象**: 24フレーム(1秒)ごとのキーフレーム設定では、Blender 5.x の interpolation で急な移動区間の補間が不安定になる

**影響**: カメラの位置は正しく設定されていても、中間フレームで値が暴走する可能性

---

## 3. 修正履歴

| 日付 | 問題 | 修正内容 | 参照 |
|------|------|---------|------|
| 2026-08-13 | keyframe_insert が正しい値を記録しない | obj.location/rotation_euler を keyframe_insert 前に設定 | [`plans/scene1-slide-animation-fix.md`](plans/scene1-slide-animation-fix.md:397) |
| 2026-08-13 | Blender 5.x で fcurves が存在しない | レイヤー化アクションAPIに対応 | same |
| 2026-09-xx | ジンバルロックでカメラが飛ぶ | set_camera_look_at の安全域を拡張 (L107-118) | `animation_common.py` |

---

## 4. チェックリスト (修正時に必ず確認)

### カメラアニメーションを追加/修正する前に

- [ ] **ジンバルロック检查**: `set_camera_look_at()` の方向ベクトルが真上(-Z)に近づかないか確認
- [ ] **keyframe_insert前の値設定**: `obj.rotation_euler = rot` を `keyframe_insert` より前に呼んでいるか
- [ ] **クリア処理の確認**: 前回のキーフレームが残っていないか確認 (`clear_animation_data` が呼ばれているか)
- [ ] **カメラ位置の安全域**: Z座標が 0.5m-10m の範囲内か確認。超える場合は `_clamp_camera_location()` を通す
- [ ] **キーフレーム間隔**: カメラ回転の変化が激しい区間は 12フレーム以下の間隔を使用
- [ ] **Track To制約の状態**: Track To がミュートされているか確認 (`constraint.mute = True`)

### Blenderでテストした後

- [ ] タイムラインを全フレーム再生し、カメラが軌道から外れていないか目視確認
- [ ] フレーム0, 終了フレームの両方でカメラ位置/回転が正しい値か確認
- [ ] トップダウン直前・直後 (Z=6-8m 付近) のフレームでX回転が ±45°以内か確認

---

## 5. 推奨修正 (未実装分)

### 修正1: set_camera_look_at() を matrix_world ベースに書き換え (HIGH PRIORITY)

**問題**: `rotation_euler` 経由の設定はジンバルロックの根本解決にならない

**方針**:
```python
def set_camera_look_at(cam, loc, tgt):
    """カメラを指定位置に配置し、ターゲット方向に向ける (matrix_world方式)"""
    cam.location = loc
    direction = Vector(tgt) - Vector(loc)
    
    # カメラの-Z軸がtargetを向くようにLookAt行列を構築
    # Blenderのカメラは-Zが進行方向、+Yが上向き
    z_axis = -direction.normalized()
    up = Vector((0, 0, 1))
    
    if abs(z_axis.dot(up)) > 0.99:
        # 真上/真下のケース: X軸を向くベクトルを使用
        right = Vector((1, 0, 0)).cross(z_axis).normalized()
    else:
        right = up.cross(z_axis).normalized()
    
    y_axis = z_axis.cross(right).normalized()
    
    # 変換行列を構築 (Blenderの座標系: X=右, Y=奥, Z=上)
    rotation_matrix = Matrix([
        (right.x, right.y, right.z, 0),
        (y_axis.x, y_axis.y, y_axis.z, 0),
        (z_axis.x, z_axis.y, z_axis.z, 0),
        (0, 0, 0, 1)
    ])
    
    cam.matrix_world = Matrix.Translation(loc) @ rotation_matrix
```

**利点**:
- ジンバルロックを完全に回避 (オイラー角を使用しない)
- 真上/真下付近も安定して動作
- カメラの進行方向(-Z軸)が常にターゲットを指す

### 修正2: clear_scene() でカメラのrotation_eulerをリセット (MEDIUM PRIORITY)

**追加コード**:
```python
def clear_scene():
    # ... 既存処理 ...
    
    # ComparisonCamera の状態もリセット
    if "ComparisonCamera" in bpy.data.objects:
        camera = bpy.data.objects["ComparisonCamera"]
        camera.rotation_euler = (0.0, 0.0, 0.0)
        if camera.animation_data:
            camera.animation_data_clear()
```

### 修正3: キーフレーム間隔の短縮 (LOW PRIORITY)

`short2_cuts.py` の `keyframe_interval = 24` を `keyframe_interval = 12` に変更。

---

## 6. 関連ファイル

| ファイル | 役割 | 確認すべき箇所 |
|---------|------|---------------|
| [`animation_common.py`](animation_common.py) | `set_camera_look_at()` - カメラ注視関数 | L95-119 ジンバルロック対策 |
| [`short2_utils.py`](short2_utils.py) | `_set_rotation_keyframe()`, `_set_camera_location_keyframe()` | L102-153 キーフレーム設定 |
| [`short2_cuts.py`](short2_cuts.py) | カット1/2のカメラアニメーション | L95 キーフレーム間隔 |
| [`blend_scene_creator.py`](blend_scene_creator.py) | `clear_scene()` - シーン初期化 | L306 ComparisonCameraの保持処理 |
| [`animation_settings_short2.py`](animation_settings_short2.py) | Short2全体のオーケストレーション | L98-99 アニメーションクリア処理 |

---

## 7. トラブルシューティング

### 症状: カメラがZ=5-6mの中途半端な位置にある
**確認**: 
1. 現在フレームがフェーズA中 (トップダウン移動途中) かフェーズB中 (復帰途中) か
2. バリエーション設定で `total_frames` が変動しているか
3. `set_camera_look_at()` の回転値が異常か

### 症状: カメラのX回転が ±60°以上
**確認**:
1. ジンバルロック対策が有効か (L116-118)
2. カメラ位置とターゲットの距離が短すぎないか
3. `direction.to_track_quat()` の結果を確認

### 症状: 同じシード値で毎回同じ異常位置
**確認**:
1. バリエーション設定の `camera_pattern` が極端な値になっていないか
2. TOPDOWN_VARIATIONS で Z=5.0 の `low_topdown` が選択されていないか
3. `arc_radius` の計算で 0 に近づいていないか

---

**更新履歴**:
- 2026-09-11: 初版作成 (Short2カメラ飛翔問題を契機に)
