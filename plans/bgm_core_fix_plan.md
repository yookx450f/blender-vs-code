# bgm_core.py 修正計画（最終版）

## 概要
ユーザーのフィードバックに基づき、2つの問題を修正する。

## 問題と修正内容

### 1. カメラアニメーションを無効化 (setup_camera_animation)
**現在**: カメラY位置が車の動きに追従している  
**修正**: 関数内を `pass` に変更 (空操作)

```python
def setup_camera_animation(cam_obj, fps, total_frames, start_y, end_y):
    # カメラは固定位置なので、アニメーションは設定しない
    pass
```

### 2. 車名ラベルの位置・配置を変更 (create_name_label)
**現在**: 車の上部 (`top_z + 0.5`) に配置。親として car_obj に設定。  
**修正**: 車の前方2m、床面上(Z=0.01m)、上向き。車に追従するため親設定維持。

```python
def create_name_label(car_obj, car_name):
    """車名の3Dテキストを床面・車の前方に配置 (車に追従)"""
    from mathutils import Matrix
    car_obj.update_tag(); bpy.context.view_layer.update()
    _m, _n = _emission_mat('emission_bgm', (1.0, 0.95, 0.75, 1.0), 6.0)
    fd = _bold_font()
    bpy.ops.object.text_add(location=(0,0,0))
    tobj = bpy.context.active_object
    tobj.name = 'Label_' + car_name
    tobj.data.body = car_name
    tobj.data.size = 0.3
    tobj.data.extrude = 0.02
    tobj.data.align_x = 'CENTER'
    tobj.data.align_y = 'CENTER'
    if fd: tobj.data.font = fd
    # X軸で90度回転して上を向く
    rx = Matrix.Rotation(math.pi / 2, 4, 'X')
    # 親の車に対する相対位置: 前方(Y=-2m)、高さ(Z=0.01m)
    tx = Matrix.Translation((0, -2.0, 0.01))
    tobj.matrix_world = tx @ rx
    tobj.parent = car_obj  # 追従させる
    tobj.data.materials.clear()
    tobj.data.materials.append(_m)
    return tobj
```

## 実装手順 (Codeモードで実施)

1. `bgm_core.py` の `setup_camera_animation` を空操作に変更
2. `bgm_core.py` の `create_name_label` を床面・前方配置 + X軸90度回転に修正
3. GUI動作テスト