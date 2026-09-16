"""
動物ショート動画 - 初期化・ターゲット設定モジュール

カメラターゲット用Emptyの作成、Track To制約の設定、
カメラレンズの変更など、アニメーション開始前の準備処理をまとめる。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。
【2026-09-08 変更】カット4を削除し、カット3を27秒・1.1周に拡張。

【動的スケーリング】
    動物の寸法に基づいて、カメラ距離・レンズ・分離間隔を自動調整する。
    大きな動物ほど、カメラを遠ざけ・広角にし・間隔を広げる。

使い方:
    from short_animal_setup import setup_camera_target_and_lens
    result = setup_camera_target_and_lens(scene, camera, car_a, car_b, grounded_z_a, cam_scale=1.0)
"""

import math
import bpy
from short_animal_utils import _set_empty_location_keyframe, _get_animal_max_z


def setup_camera_target_and_lens(scene, camera, car_a, car_b, grounded_z_a, cam_scale=1.0):
    """
    カメラターゲットとレンズの設定を行う。

    - ターゲットEmptyを作成し、動物A・Bの高さに合わせて配置
    - Track To制約を追加/更新
    - カメラレンズをスケール係数に応じて動的に設定（巨大動物ほど広角）
    - カメラ高さをスケール係数で調整

    Parameters:
        scene: Blenderシーン
        camera: カメラオブジェクト
        car_a: 動物Aのオブジェクト
        car_b: 動物Bのオブジェクト
        grounded_z_a: 動物Aの接地Z座標
        cam_scale: スケール係数（デフォルト1.0）

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

    # レンズ焦距設定 — cam_scaleに応じて調整（巨大動物ほど広角）
    original_lens = camera.data.lens
    adjusted_lens = round(35 * min(cam_scale, 2.0))
    adjusted_lens = max(24, min(85, adjusted_lens))  # 広角〜望遠の範囲に収める
    camera.data.lens = adjusted_lens
    print(f"  カメラレンズ: {original_lens}mm -> {adjusted_lens}mm（スケール調整）")

    # カメラの高さをスケール係数で動的に設定
    CAM_HEIGHT = 1.0 * min(cam_scale, 2.0)

    # カメラのターゲット（動物A・Bの一番高いところ）
    animal_a_max_z = _get_animal_max_z(car_a)
    animal_b_max_z = _get_animal_max_z(car_b)
    target_height = animal_a_max_z if animal_a_max_z > 0 else 1.0
    target_base = (0.0, 0.0, target_height)
    print(f"  カメラターゲット (動物Aの一番高いところ): {target_base}")
    print(f"  動物Bの最大Z: {animal_b_max_z}")
    print(f"  カメラ高さ: {CAM_HEIGHT:.2f}m（スケール調整）")

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


def setup_animal_positions(car_a, car_b, grounded_z_positions, sep_scale=1.0):
    """
    動物の中心位置と分離位置を計算する。

    Parameters:
        car_a: 動物Aのオブジェクト
        car_b: 動物Bのオブジェクト
        grounded_z_positions: 接地Z座標の辞書
        sep_scale: 分離間隔のスケーリング係数（デフォルト1.0）

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
        print(f"  警告: オフセット計算エラー: {e} -> (0,0)にフォールバック")

    # 位置定義 — 分離間隔をスケール係数で調整
    half_separation = 0.9 * sep_scale

    center_pos_a = (-offset_a[0], -offset_a[1], grounded_z_a)
    center_pos_b = (-offset_b[0], -offset_b[1], grounded_z_b)

    separated_pos_a = (-half_separation - offset_a[0], -offset_a[1], grounded_z_a)
    separated_pos_b = (half_separation - offset_b[0], -offset_b[1], grounded_z_b)

    print(f"  carA: center={center_pos_a} -> separated={separated_pos_a}")
    print(f"  carB: center={center_pos_b} -> separated={separated_pos_b}")
    print(f"  分離間隔: ±{half_separation:.2f}m（スケール調整）")

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
    视点は高めに保ち、カット間で连续な过渡を行う（ジャンプ禁止）。

    【変更】カット1 (fr0-72) が削除されたため、fr0から直接半透明フェーズへ移行。
    【変更】カット4を削除し、カット3を27秒・1.1周に拡張。

      カット1 (fr0-144, 6秒):    動物Bの最高部→max(A,B)*0.75へ视点移动（半透明フェーズ）
      カット2 (fr144-288, 6秒): 分离スライド、max(A,B)*0.75を维持（高位化完了）
      カット3 (fr288-936, 27秒): 円軌道1.1周、max(动物A,B)*0.75を向く（高位维持）
    """
    print("\n  === ターゲットEmptyアニメーション設定 ===")

    # フレーム定義（24fps）— 【変更】カット1削除で72フレーム分ずらし、カット4削除
    CUT1_START = 0
    CUT1_END = 144
    CUT2_START = 144
    CUT2_END = 288
    CUT3_START = 288
    CUT3_END = 936

    # 两动物の最大高さ（视点高めで见切れ防止）
    max_animal_z = max(animal_a_max_z, animal_b_max_z)
    high_target_z = max_animal_z * 0.75  # 高位ターゲット（max高さの75%）

    # カット1: fr0-144, 動物Bの最高部からmax(A,B)*0.75へ视点移动（半透明フェーズ）
    # カット1が削除されたため、fr0から动物Bの最高部を開始値とする
    _set_empty_location_keyframe(target_empty, CUT1_START, target_base[0], target_base[1], animal_b_max_z)
    _set_empty_location_keyframe(target_empty, CUT1_END, target_base[0], target_base[1], high_target_z)

    # カット2: fr144-288, 分离スライド、max(A,B)*0.75を维持（高位化完了）
    _set_empty_location_keyframe(target_empty, CUT2_START, target_base[0], target_base[1], high_target_z)
    _set_empty_location_keyframe(target_empty, CUT2_END, target_base[0], target_base[1], high_target_z)

    # カット3: fr288-936, 円軌道中は高位を维持（见切れ防止）
    _set_empty_location_keyframe(target_empty, CUT3_START, target_base[0], target_base[1], high_target_z)
    _set_empty_location_keyframe(target_empty, CUT3_END, target_base[0], target_base[1], high_target_z)

    print(f"  ターゲットZ: {animal_b_max_z:.2f}固定 (fr0), {animal_b_max_z:.2f}->{high_target_z:.2f} (fr0-144), {high_target_z:.2f}固定 (fr144-288), {high_target_z:.2f}固定 (fr288-936)")
