"""
動物ショート動画 - カット1-5 の位置アニメーションモジュール

各カットごとのカメラ・動物の位置キーフレームを設定する。
カットは完全に分離されており、独立して動作する。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。
旧カット1-2 → 新カット1 (fr0-144)
旧カット2 → 新カット2 (fr144-288)
旧カット3 → 新カット3 (fr288-888)
旧カット4 → 新カット4 (fr888-960)

使い方:
    from short_animal_cuts import (
        setup_cut1_transparency_start,
        setup_cut2_separation,
        setup_cut3_orbit,
        setup_cut4_return_front,
    )
"""

import math
from short_animal_utils import (
    _set_location_keyframe,
    _set_camera_location_keyframe,
    _set_camera_location_keyframe_with_easing,
)


# ============================================================
# フレーム定義（24fps）— 全カットで共通
# 【変更】カット1を削除し、72フレーム分ずらした
# 旧: カット1=3秒(72f), カット1-2=6秒(144f), カット2=6秒(144f), カット3=25秒(600f), カット4=3秒(72f)
# 新: カット1=6秒(144f), カット2=6秒(144f), カット3=25秒(600f), カット4=3秒(72f)
# 合計: 40秒 = 960フレーム
# ============================================================
CUT1_START = 0
CUT1_END = 144

CUT2_START = 144
CUT2_END = 288

CUT3_START = 288
CUT3_END = 888

CUT4_START = 888
CUT4_END = 960


def setup_cut1_transparency_start(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed):
    """
    カット1 (fr0-144, 6秒): 半透明化 + 动物重叠状態維持。

    動物Bが半透明(瞬時0.35)になり、动物は重叠したまま不动。
    カメラ位置: X=1m固定、Y:-7→-9渐变、Z:0.5→7渐变（中間点経由）。
    3段階キーフレーム: (1,-7,0.5) → (1,-8,2.75) → (1,-9,7)
    """
    print("\n  === カット1: 半透明化 + Y:-7→-9渐变, Z:0.5→7渐变 (AUTO_CLAMPED) ===")

    # 动物は重叠位置を维持（fr0-fr144で不动）
    _set_location_keyframe(car_a, CUT1_START, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_START, center_pos_b[0], center_pos_b[1], center_pos_b[2])
    _set_location_keyframe(car_a, CUT1_END, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_END, center_pos_b[0], center_pos_b[1], center_pos_b[2])

    # カメラ位置: X=1固定、Y:-7→-9渐变、Z:0.5→7渐变（AUTO_CLAMPEDが自動イージング）
    # 3段階キーフレーム設定
    cam_start = (cam_fixed[0], -7.0, 0.5)              # fr0: (1, -7, 0.5)
    cam_middle = (cam_fixed[0], -8.0, 2.75)            # fr72: (1, -8, 2.75) - 中間点
    cam_end = (cam_fixed[0], -9.0, 7.0)                # fr144: (1, -9, 7.0)

    middle_frame = int((CUT1_START + CUT1_END) / 2)     # fr72

    _set_camera_location_keyframe(camera, CUT1_START, cam_start)
    _set_camera_location_keyframe(camera, middle_frame, cam_middle)
    _set_camera_location_keyframe(camera, CUT1_END, cam_end)

    print(f"  [フレーム {CUT1_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT1_START}-{CUT1_END}] カメラ: (1,-7,0.5)→(1,-8,2.75)→(1,-9,7) (AUTO_CLAMPED自動イージング)")
    print(f"  [フレーム {CUT1_END}] carA={center_pos_a}, carB={center_pos_b} (重叠維持)")


def setup_cut2_separation(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed, cam_height):
    """
    カット2 (fr144-288, 6秒): 动物が横へスライドして2体が並ぶ。

    动物はfr144で重叠（center位置）→ fr288で分離位置に渐变スライド。
    カメラ: X=1m固定、Y=-9固定、Z=7→1.0渐变（AUTO_CLAMPEDで自動イージング）。
    
    fr288終了時、カメラ位置は (1, -9, 1.0) でカット3（円軌道）へ接続。
    """
    print("\n  === カット2: 动物横スライド分离 + カメラZ:7→1.0渐变 (AUTO_CLAMPED) ===")

    # 动物はfr144-288で中心位置→分離位置に渐变スライド（既存のease-in-out維持）
    frames_list = list(range(CUT2_START, CUT2_END + 1, 4))
    for sf in frames_list:
        t = (sf - CUT2_START) / (CUT2_END - CUT2_START)  # 0 → 1
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

    # カメラ: X=1固定、Y=-9固定、Z=7→1.0渐变（AUTO_CLAMPEDが自動イージング）
    cam_start = (1.0, -9.0, 7.0)
    cam_end = (1.0, -9.0, 1.0)
    _set_camera_location_keyframe(camera, CUT2_START, cam_start)
    _set_camera_location_keyframe(camera, CUT2_END, cam_end)

    # fr288終了時、X=1のままで円軌道へ接続（X=0に戻さない）
    final_cam_cut2 = (1.0, -9.0, 1.0)
    _set_camera_location_keyframe(camera, CUT2_END, final_cam_cut2)

    print(f"  [フレーム {CUT2_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT2_END}] carA={separated_pos_a}, carB={separated_pos_b} (スライド分离完了) | カメラZ: 7→1.0, X=1维持")


def setup_cut3_orbit(camera, car_a, car_b, separated_pos_a, separated_pos_b, cam_height):
    """
    カット3 (fr288-888, 25秒): 円軌道カメラで1周。

    両方の動物を視界に入れながら、中心(0,0)を中心として回転。
    动物は分离位置を维持。

    軌道パラメータ:
      - 半径: 9m（新仕様準拠）
      - fr288: カット2終了位置 (1, -9, 1.0) から开始
      - 開始角度: atan2(-9, 1) ≈ -83.7° （X=1で円軌道へ接続）
      - 半径補間: fr288→fr304 で √(1²+9²)≈9.06 から 9 へ渐变移行
      - カメラの向き: ターゲットEmptyが高位（max高さ*0.75）を向く。
    """
    print("\n  === カット3: 円軌道1周（半径9m、25秒、両方視界に）===")

    ORBIT_CENTER = (0.0, 0.0)
    ORBIT_RADIUS = 9.0  # 半径9m（新仕様準拠）
    
    # 開始角度を再計算 - カット2終了位置 (1, -9) から円軌道へ接続
    orbit_start_angle = math.atan2(-9.0, 1.0)  # ≈ -83.7°
    initial_radius = math.sqrt(1.0**2 + 9.0**2)  # ≈ 9.06
    
    # fr288: カット2終了位置から直接接続（X=1維持）
    _set_camera_location_keyframe(camera, CUT3_START, (1.0, -9.0, 1.0))

    # 軌道移行フェーズ: fr288→fr304 で半径を initial_radius → ORBIT_RADIUS へ渐变
    transition_frames = [288, 296, 304]
    for sf in transition_frames:
        if sf == 288:
            continue  # fr288 はすでに設定済み
        t = (sf - 288) / (304 - 288)  # 0 → 1
        radius = initial_radius + (ORBIT_RADIUS - initial_radius) * t
        cam_x = ORBIT_CENTER[0] + radius * math.cos(orbit_start_angle)
        cam_y = ORBIT_CENTER[1] + radius * math.sin(orbit_start_angle)
        _set_camera_location_keyframe(camera, sf, (cam_x, cam_y, 1.0))

    # 通常の軌道キーフレーム（8フレーム間隔、fr304から继续）
    orbit_keyframe_interval = 8
    orbit_keyframes = list(range(312, CUT3_END + 1, orbit_keyframe_interval))
    if orbit_keyframes[-1] != CUT3_END:
        orbit_keyframes.append(CUT3_END)

    num_orbit_segments = len(orbit_keyframes) - 1 if len(orbit_keyframes) > 1 else 1

    for i, frame in enumerate(orbit_keyframes):
        progress = i / num_orbit_segments if num_orbit_segments > 0 else 0
        angle = orbit_start_angle + 2 * math.pi * progress

        cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(angle)
        cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(angle)
        cam_pos = (cam_x, cam_y, 1.0)

        _set_camera_location_keyframe(camera, frame, cam_pos)

        if i % 20 == 0 or i == num_orbit_segments:
            print(f"  [フレーム {frame}] カメラ={cam_pos} (角度={math.degrees(angle):.1f}°)")

    # 动物は分离位置を维持
    _set_location_keyframe(car_a, CUT3_START, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT3_START, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])
    _set_location_keyframe(car_a, CUT3_END, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT3_END, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])

    # 円軌道の最終位置を計算して返す（カット4の起点用）
    final_orbit_angle = orbit_start_angle + 2 * math.pi
    final_cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(final_orbit_angle)
    final_cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(final_orbit_angle)
    final_cam_cut3 = (final_cam_x, final_cam_y, 1.0)

    print(f"  [フレーム {CUT3_END}] 円軌道1周完了（半径9m）")
    print(f"  軌道始点: (1, -9, 1.0), 開始角度={math.degrees(orbit_start_angle):.1f}°")

    return {'final_cam_cut3': final_cam_cut3}


def setup_cut4_return_front(camera, car_a, car_b, separated_pos_a, separated_pos_b, final_cam_cut3, cam_front):
    """
    カット4 (fr888-960, 3秒): カメラはゆっくり正面に戻る、动物は動かさない。

    仕様: 「最後に动物を重ねるのは不要。动物は動かなくていい」
    カメラ位置: (2, -5, cam_height) にAUTO_CLAMPEDで渐变戻る（自動イージングで滑らかに動き出し・停止）。
    """
    print("\n  === カット4: カメラが正面戻る（动物は不动、AUTO_CLAMPED）===")

    # 动物是分离位置を维持（動かさない）
    _set_location_keyframe(car_a, CUT4_START, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT4_START, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])
    _set_location_keyframe(car_a, CUT4_END, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT4_END, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])

    # カメラは正面の位置 (2, -5, cam_height) にAUTO_CLAMPEDで渐变戻る（自動イージング）
    _set_camera_location_keyframe(camera, CUT4_START, final_cam_cut3)
    _set_camera_location_keyframe(camera, CUT4_END, cam_front)

    print(f"  [フレーム {CUT4_START}] carA={separated_pos_a}, carB={separated_pos_b} (不动)")
    print(f"  [フレーム {CUT4_END}] carA={separated_pos_a}, carB={separated_pos_b} (不动) | カメラ={cam_front} (AUTO_CLAMPED自動イージング)")
