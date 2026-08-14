# シーン1 - 両車後端揃え修正

## 日付
2026-08-14

## 問題概要

シーン1（フレーム0-96）でCarAとCarBが中央に集合する際、両車の後端（Y軸正方向側）が一致せず、視覚的にズレが生じていた。

### 原因
- `blend_scene_creator.py` の `rear_offset_y` 計算が「前端揃え」のロジックになっていた
- `animation_settings_cut1.py` の `car_a_end` / `car_b_end` 計算でY座標に視覚的中心オフセットを引いていたため、後端揃えが崩れていた
- `cars_config.json` の全長値とGLBモデルの実際のバウンディングボックス寸法が一致していなかった

## 解決策

### 1. `blend_scene_creator.py` - 後端Y座標測定関数追加

バウンディングボックスから実際の後端（Y最大）ワールド座標を測定し、それに基づいて `rear_offset_y` を計算するように変更。

```python
def get_rear_end_y(car_obj):
    """バウンディングボックスから後端（Y最大）のワールド座標を取得"""
    bounds = [Vector(b) for b in car_obj.bound_box]
    corners_world = [car_obj.matrix_world @ corner for corner in bounds]
    return max(c.y for c in corners_world)

# carBを基準(Y=0.0)に配置後、後端Yを取得
car_b.location = (1.25, 0.0, grounded_z_b)
rear_y_b = get_rear_end_y(car_b)

# carAを一時的に基準位置に配置して後端Yを測定
car_a.location = (-1.25, 0.0, grounded_z_a)
rear_y_a = get_rear_end_y(car_a)

# 後端を揃えるためのYオフセットを計算
rear_offset_y = rear_y_b - rear_y_a
```

### 2. `animation_settings_cut1.py` - Y座標の後端揃え維持

`car_a_end` / `car_b_end` のY座標計算から視覚的中心オフセット（`offset_a[1]` / `offset_b[1]`）を削除し、`rear_offset_y` をそのまま使用するように変更。

```python
# 修正前
car_a_end = (0.0 - offset_a[0], rear_offset_y - offset_a[1], grounded_z_a)
car_b_end = (0.0 - offset_b[0], 0.0 - offset_b[1], grounded_z_b)

# 修正後（X方向のオフセット補正は維持）
car_a_end = (0.0 - offset_a[0], rear_offset_y, grounded_z_a)
car_b_end = (0.0 - offset_b[0], 0.0, grounded_z_b)
```

### 3. `cars_config.json` - 全長値更新

carBの全長をバウンディングボックス測定値に合わせ、4925mm → 4926mm に更新。

## 影響範囲

- カット1のみが直接修正対象
- カット2以降は `CutState` を通じて cut1 の最終位置を自動継承するため、追加修正不要
- テキストラベルは車にペアレント設定されているため、自動追従する

## 検証方法

1. `python run.py 1` を実行
2. Blenderでフレーム96に移動
3. トップビューから両車の後端（Y軸正方向側）が一致していることを確認
