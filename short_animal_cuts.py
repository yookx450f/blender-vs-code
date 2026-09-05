"""
動物ショート動画 - カット1-5 の位置アニメーションモジュール

各カットごとのカメラ・動物の位置キーフレームを設定する。
カットは完全に分離されており、独立して動作する。

使い方:
    from short_animal_cuts import (
        setup_cut1_overlap,
        setup_cut2_transparency_start,
        setup_cut3_separation,
        setup_cut4_orbit,
        setup_cut5_return_front,
    )
"""

import math
from short_animal_utils import (
    _set_location_keyframe,
    _set_camera_location_keyframe,
)


# ============================================================
# フレーム定義（24fps）— 全カットで共通
# 仕様: カット1=3秒(72f), カット1-2=6秒(144f), カット2=6秒(144f), カット3=25秒(600f), カット4=3秒(72f)
# 合計: 43秒 = 1032フレーム
# ============================================================
CUT1_START = 0
CUT1_END = 72

CUT2_START = 72
CUT2_END = 216

CUT3_START = 216
CUT3_END = 360

CUT4_START = 360
CUT4_END = 960

CUT5_START = 960
CUT5_END = 1032


def setup_cut1_overlap(camera, car_a, car_b, center_pos_a, center_pos_b, cam_fixed):
    """
    カット1 (fr0-72, 3秒): 重叠状態、動物はすべて不透明。

    カメラ位置 X:1m Y:-5m Z:0.5m で静止。
    動物A・B は中心で重叠した状態で固定。
    """
    print("\n  === カット1: 重叠状態（すべて不透明）===")

    # 动物は重叠位置に固定
    _set_location_keyframe(car_a, CUT1_START, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_START, center_pos_b[0], center_pos_b[1], center_pos_b[2])
    _set_location_keyframe(car_a, CUT1_END, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_END, center_pos_b[0], center_pos_b[1], center_pos_b[2])

    # カメラ位置を固定 (1, -5, 0.5)
    _set_camera_location_keyframe(camera, CUT1_START, cam_fixed)
    _set_camera_location_keyframe(camera, CUT1_END, cam_fixed)

    print(f"  [フレーム {CUT1_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT1_END}] carA={center_pos_a}, carB={center_pos_b} (重叠维持)")


def setup_cut2_transparency_start(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed):
    """
    カット1-2 (fr72-216, 6秒): 半透明化 + 动物重叠状態維持。

    動物Bが半透明(瞬時0.35)になり、动物は重叠したまま不动。
    カメラ位置: X=1m固定、Y=-5→-6渐变、Z=0.5→7渐变。
    """
    print("\n  === カット1-2: 半透明化 + Y:-5→-6渐变, Z:0.5→7渐变 ===")

    # 动物は重叠位置を维持（fr72-fr216で不动）
    _set_location_keyframe(car_a, CUT2_START, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT2_START, center_pos_b[0], center_pos_b[1], center_pos_b[2])
    _set_location_keyframe(car_a, CUT2_END, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT2_END, center_pos_b[0], center_pos_b[1], center_pos_b[2])

    # カメラ位置: Y座標を -5m → -6m に平滑、Z=0.5→7渐变
    cam_start = (cam_fixed[0], -5.0, 0.5)
    _set_camera_location_keyframe(camera, CUT2_START, cam_start)
    
    # fr144: Y=-5→-6 の中間点、Z=0.5→7 の中間点 (6秒間の中間フレーム)
    cam_mid = (cam_fixed[0], -5.5, 2.75)
    _set_camera_location_keyframe(camera, 144, cam_mid)
    
    # fr216でY=-6m、Z=7mに到達（カット2接続位置）
    cam_end = (cam_fixed[0], -6.0, 7.0)
    _set_camera_location_keyframe(camera, CUT2_END, cam_end)

    print(f"  [フレーム {CUT2_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム 144] カメラY=-5.5m, Z=2.75m (平滑移動中)")
    print(f"  [フレーム {CUT2_END}] carA={center_pos_a}, carB={center_pos_b} (重叠維持) | カメラ: Y-5→-6, Z:0.5→7")


def setup_cut3_separation(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed, cam_height):
    """
    カット2 (fr216-360, 6秒): 动物が横へスライドして2体が並ぶ。

    动物はfr216で重叠（center位置）→ fr360で分離位置に渐变スライド。
    カメラ: X=1m固定、Y=-6固定、Z=7→cam_height渐变（6秒かけて下がる）。
    
    fr360終了時、カメラ位置は (1, -6, cam_height) でカット3（円軌道）へ接続。
    """
    print("\n  === カット2: 动物横スライド分离 + カメラZ:7→cam_height渐变 ===")

    # 动物はfr216-360で中心位置→分離位置に渐变スライド
    frames_list = list(range(CUT3_START, CUT3_END + 1, 4))
    for sf in frames_list:
        t = (sf - CUT3_START) / (CUT3_END - CUT3_START)  # 0 → 1
        # ease-in-out
        ease = 3 * t * t - 2 * t * t * t
        # carA: center → separated
        a_x = center_pos_a[0] + (separated_pos_a[0] - center_pos_a[0]) * ease
        a_y = center_pos_a[1] + (separated_pos_a[1] - center_pos_a[1]) * ease
        _set_location_keyframe(car_a, sf, a_x, a_y, center_pos_a[2])
        # carB: center → separated
        b_x = center_pos_b[0] + (separated_pos_b[0] - center_pos_b[0]) * ease
        b_y = center_pos_b[1] + (separated_pos_b[1] - center_pos_b[1]) * ease
        _set_location_keyframe(car_b, sf, b_x, b_y, center_pos_b[2])

    # カメラ: X=1固定、Y=-6固定、Z=7→cam_height渐变（全程）
    for sf in frames_list:
        t = (sf - CUT3_START) / (CUT3_END - CUT3_START)  # 0 → 1
        cam_x = 1.0
        cam_y = -6.0
        z_interp = 7.0 + (cam_height - 7.0) * t
        _set_camera_location_keyframe(camera, sf, (cam_x, cam_y, z_interp))

    # fr360終了時、X=1のままで円軌道へ接続（X=0に戻さない）
    final_cam_cut3 = (1.0, -6.0, cam_height)
    _set_camera_location_keyframe(camera, CUT3_END, final_cam_cut3)

    print(f"  [フレーム {CUT3_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT3_END}] carA={separated_pos_a}, carB={separated_pos_b} (スライド分离完了) | カメラZ: 7→{cam_height}, X=1維持")


def setup_cut4_orbit(camera, car_a, car_b, separated_pos_a, separated_pos_b, cam_height):
    """
    カット3 (fr360-960, 25秒): 円軌道カメラで1周。

    両方の動物を視界に入れながら、中心(0,0)を中心として回転。
    動物は分離位置を维持。

    軌道パラメータ:
      - 半径: 6.2m（キリンの頭が見切れないように拡大）
      - fr360: カット2終了位置 (1, -6, cam_height) から开始
      - 開始角度: atan2(-6, 1) ≈ -80.5° （X=1で円軌道へ接続）
      - 半径補間: fr360→fr376 で √(1²+6²)≈6.08 から 6.2 へ渐变移行
      - カメラの向き: ターゲットEmptyが動物Aの高さの半分を向く（short_animal_setup.pyで設定）。
    """
    print("\n  === カット3: 円軌道1周（半径6.2m、25秒、両方視界に）===")

    ORBIT_CENTER = (0.0, 0.0)
    ORBIT_RADIUS = 6.2  # 半径6.2m（キリンがより見えるように拡大）
    
    # 開始角度を再計算 - カット2終了位置 (1, -6) から円軌道へ接続
    orbit_start_angle = math.atan2(-6.0, 1.0)  # ≈ -80.5°
    initial_radius = math.sqrt(1.0**2 + 6.0**2)  # ≈ 6.083
    
    # fr360: カット2終了位置から直接接続（X=1維持）
    _set_camera_location_keyframe(camera, CUT4_START, (1.0, -6.0, cam_height))

    # 軌道移行フェーズ: fr360→fr376 で半径を initial_radius → ORBIT_RADIUS へ渐变
    transition_frames = [360, 368, 376]
    for sf in transition_frames:
        if sf == 360:
            continue  # fr360 はすでに設定済み
        t = (sf - 360) / (376 - 360)  # 0 → 1
        radius = initial_radius + (ORBIT_RADIUS - initial_radius) * t
        cam_x = ORBIT_CENTER[0] + radius * math.cos(orbit_start_angle)
        cam_y = ORBIT_CENTER[1] + radius * math.sin(orbit_start_angle)
        _set_camera_location_keyframe(camera, sf, (cam_x, cam_y, cam_height))

    # 通常の軌道キーフレーム（8フレーム間隔、fr376から继续）
    orbit_keyframe_interval = 8
    orbit_keyframes = list(range(384, CUT4_END + 1, orbit_keyframe_interval))
    if orbit_keyframes[-1] != CUT4_END:
        orbit_keyframes.append(CUT4_END)

    num_orbit_segments = len(orbit_keyframes) - 1 if len(orbit_keyframes) > 1 else 1

    for i, frame in enumerate(orbit_keyframes):
        progress = i / num_orbit_segments if num_orbit_segments > 0 else 0
        angle = orbit_start_angle + 2 * math.pi * progress

        cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(angle)
        cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(angle)
        cam_pos = (cam_x, cam_y, cam_height)

        _set_camera_location_keyframe(camera, frame, cam_pos)

        if i % 20 == 0 or i == num_orbit_segments:
            print(f"  [フレーム {frame}] カメラ={cam_pos} (角度={math.degrees(angle):.1f}°)")

    # 動物は分離位置を维持
    _set_location_keyframe(car_a, CUT4_START, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT4_START, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])
    _set_location_keyframe(car_a, CUT4_END, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT4_END, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])

    # 円軌道の最終位置を計算して返す（カット5の起点用）
    final_orbit_angle = orbit_start_angle + 2 * math.pi
    final_cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(final_orbit_angle)
    final_cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(final_orbit_angle)
    final_cam_cut4 = (final_cam_x, final_cam_y, cam_height)

    print(f"  [フレーム {CUT4_END}] 円軌道1周完了（半径6.2m）")
    print(f"  軌道始点: (1, -6, {cam_height}), 開始角度={math.degrees(orbit_start_angle):.1f}°")

    return {'final_cam_cut4': final_cam_cut4}


def setup_cut5_return_front(camera, car_a, car_b, separated_pos_a, separated_pos_b, final_cam_cut4, cam_front):
    """
    カット4 (fr960-1032, 3秒): カメラはゆっくり正面に戻る、动物は動かさない。

    仕様: 「最後に动物を重ねるのは不要。动物は動かなくていい」
    カメラ位置: (2, -5, cam_height) に渐变戻る
    """
    print("\n  === カット4: カメラが正面戻る（动物は不动）===")

    # 动物是分离位置を维持（動かさない）
    _set_location_keyframe(car_a, CUT5_START, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT5_START, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])
    _set_location_keyframe(car_a, CUT5_END, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT5_END, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])

    # カメラは正面の位置 (2, -5, cam_height) に渐变戻る
    _set_camera_location_keyframe(camera, CUT5_START, final_cam_cut4)
    _set_camera_location_keyframe(camera, CUT5_END, cam_front)

    print(f"  [フレーム {CUT5_START}] carA={separated_pos_a}, carB={separated_pos_b} (不动)")
    print(f"  [フレーム {CUT5_END}] carA={separated_pos_a}, carB={separated_pos_b} (不动) | カメラ={cam_front}")
