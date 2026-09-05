"""
動物ショート動画 - 初期化・ターゲット設定モジュール

カメラターゲット用Emptyの作成、Track To制約の設定、
カメラレンズの変更など、アニメーション開始前の準備処理をまとめる。

使い方:
    from short_animal_setup import setup_camera_target_and_lens
    result = setup_camera_target_and_lens(scene, camera, car_a, car_b, grounded_z_a)
"""

import math
import bpy
from short_animal_utils import _set_empty_location_keyframe, _get_animal_max_z


def setup_camera_target_and_lens(scene, camera, car_a, car_b, grounded_z_a):
    """
    カメラターゲットとレンズの設定を行う。

    - ターゲットEmptyを作成し、動物A・Bの高さに合わせて配置
    - Track To制約を追加/更新
    - カメラレンズを35mmに設定

    Returns:
        dict: {
            'target_empty': Target Emptyオブジェクト,
            'target_base': ターゲットの基本位置 (x, y, z),
            'target_height': 計算されたターゲット高さ,
            'animal_a_max_z': 動物Aの最大Z座標,
            'animal_b_max_z': 動物Bの最大Z座標,
            'original_lens': 元のレンズ焦距,
            'cam_height': カメラ高さ,
        }
    """
    print("\n  === カメラターゲット・レンズ設定 ===")

    # レンズ焦距設定
    original_lens = camera.data.lens
    camera.data.lens = 35
    print(f"  カメラレンズ: {original_lens}mm → 35mm")

    # カメラの高さを固定（仕様: 円軌道中は100cm）
    CAM_HEIGHT = 1.0

    # カメラのターゲット（動物A・Bの一番高いところ）
    animal_a_max_z = _get_animal_max_z(car_a)
    animal_b_max_z = _get_animal_max_z(car_b)
    target_height = animal_a_max_z if animal_a_max_z > 0 else 1.0
    target_base = (0.0, 0.0, target_height)
    print(f"  カメラターゲット (動物Aの一番高いところ): {target_base}")
    print(f"  動物Bの最大Z: {animal_b_max_z}")

    # --- カメラターゲット用 Empty を作成 ---
    target_empty_name = "CameraTarget"
    if target_empty_name in bpy.data.objects:
        target_empty = bpy.data.objects[target_empty_name]
    else:
        target_empty = bpy.data.objects.new(target_empty_name, None)
        scene.collection.objects.link(target_empty)
    target_empty.location = target_base
    target_empty.rotation_euler = (0.0, 0.0, 0.0)
    print(f"  カメラターゲット Empty '{target_empty_name}' を作成: 位置={target_base}")

    # 既存の Track To 制約を削除
    for constraint in camera.constraints:
        if constraint.type == 'TRACK_TO':
            camera.constraints.remove(constraint)
            print(f"  既存の Track To 制約 '{constraint.name}' を削除")

    # 新しい Track To 制約を追加（ターゲット Empty を追う）
    track_constraint = camera.constraints.new(type='TRACK_TO')
    track_constraint.target = target_empty
    track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    track_constraint.up_axis = 'UP_Y'
    print(f"  Track To 制約 '{track_constraint.name}' を追加（ターゲット={target_empty.name}）")

    return {
        'target_empty': target_empty,
        'target_base': target_base,
        'target_height': target_height,
        'animal_a_max_z': animal_a_max_z,
        'animal_b_max_z': animal_b_max_z,
        'original_lens': original_lens,
        'cam_height': CAM_HEIGHT,
    }


def setup_animal_positions(car_a, car_b, grounded_z_positions):
    """
    動物の中心位置と分離位置を計算する。

    Returns:
        dict: {
            'center_pos_a': carA の中心位置 (x, y, z),
            'center_pos_b': carB の中心位置 (x, y, z),
            'separated_pos_a': carA の分離位置 (x, y, z),
            'separated_pos_b': carB の分離位置 (x, y, z),
            'offset_a': carA の視覚的中心オフセット,
            'offset_b': carB の視覚的中心オフセット,
        }
    """
    from short_animal_utils import get_car_visual_center_offset

    print("\n  === 動物位置計算 ===")

    grounded_z_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    grounded_z_b = grounded_z_positions.get(car_b.name, car_b.location.z)

    print(f"  接地Z: carA={grounded_z_a:.4f}, carB={grounded_z_b:.4f}")

    # 視覚的中心補正を取得
    offset_a = (0.0, 0.0)
    offset_b = (0.0, 0.0)

    try:
        offset_a = get_car_visual_center_offset(car_a)
        offset_b = get_car_visual_center_offset(car_b)
        print(f"  視覚的中心オフセット: carA=({offset_a[0]:.4f}, {offset_a[1]:.4f}), carB=({offset_b[0]:.4f}, {offset_b[1]:.4f})")
    except Exception as e:
        print(f"  ⚠️ オフセット計算エラー: {e} → (0,0)にフォールバック")

    # 位置定義
    center_pos_a = (-offset_a[0], -offset_a[1], grounded_z_a)
    center_pos_b = (-offset_b[0], -offset_b[1], grounded_z_b)

    separated_pos_a = (-1.25 - offset_a[0], -offset_a[1], grounded_z_a)
    separated_pos_b = (1.25 - offset_b[0], -offset_b[1], grounded_z_b)

    print(f"  carA: center={center_pos_a} -> separated={separated_pos_a}")
    print(f"  carB: center={center_pos_b} -> separated={separated_pos_b}")

    return {
        'center_pos_a': center_pos_a,
        'center_pos_b': center_pos_b,
        'separated_pos_a': separated_pos_a,
        'separated_pos_b': separated_pos_b,
        'offset_a': offset_a,
        'offset_b': offset_b,
    }


def setup_target_animation(target_empty, target_base, target_height, animal_a_max_z, animal_b_max_z):
    """
    ターゲットEmptyのアニメーション（カメラの「向き」を制御）を設定。

    仕様に従って、各カットでのターゲットZ座標を変化させる。
      カット1 (fr0-72, 3秒):     正面→動物Aの最高部+0.5mへ視点移動
      カット1-2 (fr72-216, 6秒): 動物Aの最高部→動物Bの最高部へ視点移動（半透明フェーズ）
      カット2 (fr216-360, 6秒):  分離スライド、視点固定（動物A高さの半分を向く）
      カット3 (fr360-960, 25秒): 円軌道1周、動物Aの高さの半分を向く
      カット4 (fr960-1032, 3秒):  正面に戻る、動物Aの高さの半分を向く
    """
    print("\n  === ターゲットEmptyアニメーション設定 ===")

    # フレーム定義（24fps）— 仕様に準拠
    CUT1_START = 0
    CUT1_END = 72
    CUT1_2_START = 72
    CUT1_2_END = 216
    CUT2_START = 216
    CUT2_END = 360
    CUT3_START = 360
    CUT3_END = 960
    CUT4_START = 960
    CUT4_END = 1032

    # カット1: 動物Aの一番高いところー2m（仕様変更）
    animal_a_top_target_z = animal_a_max_z - 2.0

    # カット1-2: 動物Aの最高部→動物Bの最高部（仕様書準拠）
    animal_b_top_target_z = animal_b_max_z

    # カット2/3/4: 動物Aの高さの半分のZ位置を向く（仕様書準拠）
    animal_a_half_z = animal_a_max_z * 0.5

    # カット1: fr0-72, 斜め上20度から动物Aの最高部+0.2mへ視点移動
    # カメラ位置(1, -5, 0.5)、ターゲットXY=(0,0) → 水平距離=sqrt(1^2+5^2)=sqrt(26)≈5.1
    # 斜め上20度: tan(20°)*水平距離 = delta_z
    initial_target_z = 0.5 + math.tan(math.radians(20)) * math.sqrt(1**2 + 5**2)
    _set_empty_location_keyframe(target_empty, CUT1_START, target_base[0], target_base[1], initial_target_z)
    _set_empty_location_keyframe(target_empty, CUT1_END, target_base[0], target_base[1], animal_a_max_z + 0.2)

    # カット1-2: fr72-216, 动物Aの最高部から动物Bの最高部へ視点移動（半透明フェーズ）
    _set_empty_location_keyframe(target_empty, CUT1_2_START, target_base[0], target_base[1], animal_a_top_target_z)
    _set_empty_location_keyframe(target_empty, CUT1_2_END, target_base[0], target_base[1], animal_b_top_target_z)

    # カット2: fr216-360, 分離スライド、視点固定（動物Aの高さの半分を向く - 仕様に準拠）
    _set_empty_location_keyframe(target_empty, CUT2_START, target_base[0], target_base[1], animal_a_half_z)
    _set_empty_location_keyframe(target_empty, CUT2_END, target_base[0], target_base[1], animal_a_half_z)

    # カット3: fr360-960, 円軌道中は動物Aの高さの半分を向く（仕様に準拠）
    _set_empty_location_keyframe(target_empty, CUT3_START, target_base[0], target_base[1], animal_a_half_z)
    _set_empty_location_keyframe(target_empty, CUT3_END, target_base[0], target_base[1], animal_a_half_z)

    # カット4: fr960-1032, 正面に戻り、動物Aの高さの半分を向く
    _set_empty_location_keyframe(target_empty, CUT4_START, target_base[0], target_base[1], animal_a_half_z)
    _set_empty_location_keyframe(target_empty, CUT4_END, target_base[0], target_base[1], animal_a_half_z)

    print(f"  ターゲットZ: {initial_target_z:.2f}→{animal_a_top_target_z:.2f} (fr0-72), {animal_a_top_target_z:.2f}→{animal_b_top_target_z:.2f} (fr72-216), {animal_a_half_z:.2f}固定 (fr216-360), {animal_a_half_z:.2f}固定 (fr360-960), {animal_a_half_z:.2f} (fr960-1032)")
