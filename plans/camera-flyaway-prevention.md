# カメラ飛翔問題対策ドキュメント

**作成日**: 2026-09-11
**最終更新**: 2026-09-18
**ステータス**: 有効 (2026-09-18修正済み)
**対象モジュール**: `animation_common.py`, `short2_utils.py`, `short2_cuts.py`, `blend_scene_creator.py`, `animation_settings_short2.py`

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

### 原因E: CameraTarget の animation_data がクリアされない (HIGH PRIORITY) ⭐ 2026-09-18修正

**場所**: [`animation_settings_short2.py`](animation_settings_short2.py:168)
**現象**: `clear_animation_data([camera, car_a, car_b])` では CameraTarget は対象外。前回の `_set_camera_keyframe()` で設定された CameraTarget の位置キーフレームが次回に引き継がれる

```
Short2実行 → _set_camera_keyframe() で CameraTarget にlocationキーフレーム设定
次実行   → clear_animation_data([camera, car_a, car_b]) はCameraTargetをクリアしない
結果     → CameraTargetの古いキーフレームが残り、カメラ位置を暴走させる
```

**ステータス**: ✅ 2026-09-18 に修正済み。[`animation_settings_short2.py`](animation_settings_short2.py:170) に CameraTarget の animation_data クリア処理を追加。

### 原因F: Track To constraint が強制再有効化される (HIGH PRIORITY) ⭐ 2026-09-18修正

**場所**: [`animation_common.py:142`](animation_common.py:142)
**現象**: `_ensure_camera_tracks_target()` で `track_constraint.mute = False` に強制。Short2側で `constraint.mute = True` を設定しても、`_set_camera_keyframe()` 呼び出しですぐに再有効化される

```
animation_settings_short2.py: constraint.mute = True (無効化)
short2_cuts.py: _set_camera_keyframe() を呼び出し
animation_common.py: _ensure_camera_tracks_target() で mute = False (再有効化！)
→ CameraTargetの残骸キーフレームに従ってカメラが暴走
```

**ステータス**: ✅ 2026-09-18 に修正済み。[`animation_common.py`](animation_common.py:142) で mute 状態を尊重するよう変更。

### 原因G: カメラが補間で過度に遠方へ移動 (MEDIUM PRIORITY) ⭐ 2026-09-18修正

**場所**: [`animation_common.py:179`](animation_common.py:179) の `_set_camera_keyframe()`
**現象**: トップダウンフェーズでカメラが Z=8m に移動し、その後復帰する補間の途中で「車の中心から過度に遠い位置」を経由することがある。特に fr287 付近で車全体が画面の中央に小さく映ってしまう

```
fr287 (補間中) → カメラ位置: 補間で車が小さすぎる
正常値        → カメラ距離: 5-8m
異常時の値    → カメラ距離: 10m以上、車はピンと見えた
```

**ステータス**: ✅ 2026-09-18 に一時的な距離制限 (最大10m / 最小5m) を追加したが、**これは補間パスを歪める原因となったため削除**。根本的な解決策として原因Hのアプローチに変更。

### 原因H: Short2のPhase A/Bでrotation_eulerキーフレームが設定されない (HIGH PRIORITY) ⭐ 2026-09-18修正

**場所**: [`short2_cuts.py`](short2_cuts.py:193) の `setup_cut2_phase_a_topdown()` / `setup_cut2_phase_b_camera_return()`
**現象**: Track To constraintがミュートされている状態で `_set_camera_keyframe()` を呼んでいても、カメラの回転キーフレームは記録されない。その結果、補間でrotation_eulerが前回の値のまま残っており、CameraTargetのキーフレームと整合性が取れていない

```
Short2: constraint.mute = True (Track To無効)
Phase A/B: _set_camera_keyframe() → 位置のみキーフレーム化（回転は記録しない）
→ カメラの向きが更新されず、前回のrotation_eulerが残ったままになる
→ Track Toが無効なのでカメラはどこにも向かず、補間で暴走する
```

**ステータス**: ✅ 2026-09-18 に修正済み。以下の修正を実施:
1. `_set_camera_position_and_rotation_keyframe()` を追加 (LookAt計算方式)
2. Short2全体 (Cut1 + Phase A + Phase B) で統一して使用
3. カメラ制御方式の統一化により、切り替え時のカクつきも解消

### 原因I: Cut1とPhase A/Bでカメラ制御方式が異なる (MEDIUM PRIORITY) ⭐ 2026-09-18修正

**場所**: [`short2_cuts.py`](short2_cuts.py)
**現象**: Cut1では `_set_camera_keyframe()` (Track To依存)、Phase A/Bでは直接rotation_eulerキーフレーム。制御方式の不一致で切り替え時にカクつきが発生

**ステータス**: ✅ 2026-09-18 に修正済み。Cut1も `_set_camera_position_and_rotation_keyframe()` に変更し、Short2全体で統一

---

## 3. 修正履歴

| 日付 | 問題 | 修正内容 | 参照 |
|------|------|---------|------|
| 2026-08-13 | keyframe_insert が正しい値を記録しない | obj.location/rotation_euler を keyframe_insert 前に設定 | [`plans/scene1-slide-animation-fix.md`](plans/scene1-slide-animation-fix.md:397) |
| 2026-08-13 | Blender 5.x で fcurves が存在しない | レイヤー化アクションAPIに対応 | same |
| 2026-09-xx | ジンバルロックでカメラが飛ぶ | set_camera_look_at の安全域を拡張 (L107-118) | `animation_common.py` |
| **2026-09-18** | **CameraTargetのanimation_dataが残骸として残る** | `animation_settings_short2.py` にCameraTargetクリア処理を追加 | [`animation_settings_short2.py`](animation_settings_short2.py:170) |
| **2026-09-18** | **Track To constraintが強制再有効化される** | `_ensure_camera_tracks_target()` でmute状態を尊重するよう変更 | [`animation_common.py`](animation_common.py:142) |
| **2026-09-18** | **clear_scene()でCameraTargetが生き残り** | `objects_to_keep`からComparisonCamera,CameraTargetを除外。毎回再作成方式に | [`blend_scene_creator.py`](blend_scene_creator.py:423) |
| **2026-09-18** | **補間でカメラが過度に遠方へ移動 (fr287)** | `_set_camera_keyframe()` に最大距離10m / 最小5mの制限を追加 → **削除** (補間パスを歪めるため) | [`animation_common.py`](animation_common.py:179) |
| **2026-09-18** | **Short2でrotation_eulerキーフレーム未設定 + カメラ制御方式不統一** | LookAt計算方式の `_set_camera_position_and_rotation_keyframe()` を実装し、Short2全体に統一適用 | [`short2_cuts.py`](short2_cuts.py:194) |

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

### ✅ 修正1: clear_scene() で ComparisonCamera/CameraTarget を削除 ⭐ 2026-09-18完了

**ステータス**: ✅ 完了

`objects_to_keep` から `ComparisonCamera` と `CameraTarget` を除外し、毎回新しいカメラを作成する方式に変更。これにより前回の回転状態やキーフレームが完全にクリアされる。

### 修正2: set_camera_look_at() を matrix_world ベースに書き換え (HIGH PRIORITY)

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
- 2026-09-18: **CameraTarget残骸問題とconstraint再有効化問題を修正**。3ファイルに渡り一貫性のある修正を適用 ([`animation_settings_short2.py`](animation_settings_short2.py), [`animation_common.py`](animation_common.py), [`blend_scene_creator.py`](blend_scene_creator.py))
- 2026-09-18: **距離制限の削除とPhase A/Bのrotation_eulerキーフレーム追加**。距离制限 (5m-10m) は補間パスを歪めるため削除。代わりに、Short2のPhase A/Bで直接rotation_eulerキーフレームを記録する `_set_camera_position_and_rotation_keyframe()` を実装 ([`short2_cuts.py`](short2_cuts.py), [`animation_common.py`](animation_common.py))
