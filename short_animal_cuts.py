"""
動物ショート動画 - カット1-3 の位置アニメーションモジュール

各カットごとのカメラ・動物の位置キーフレームを設定する。
カットは完全に分離されており、独立して動作する。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。
旧カット1-2 → 新カット1 (fr0-144)
旧カット2 → 新カット2 (fr144-288)
旧カット3 → 新カット3 (fr288-936)

【2026-09-08 変更】カメラのY位置を全カットで-11固定、カット3の軌道半径を11mに変更。

【2026-09-08 変更】カット4を削除し、カット3を27秒・1.1周に拡張。

【動的スケーリング】
    動物の寸法に基づいて、カメラY位置・円軌道半径・Z高度を自動調整する。

使い方:
    from short_animal_cuts import (
        setup_cut1_transparency_start,
        setup_cut2_separation,
        setup_cut3_orbit,
    )
"""

import math
from short_animal_utils import (
    _set_location_keyframe,
    _set_camera_location_keyframe,
    _set_camera_location_keyframe_with_easing,
)

# イージング関数（短形動画v2のバリエーションモジュールから取得、失敗時はデフォルト使用）
try:
    from short_animal_variations import get_easing_function
except ImportError:
    def _ease_cubic(t):
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            return 1.0 - (-2.0 * t + 2.0)**3 / 2.0
    def get_easing_function(name):
        return _ease_cubic


# ============================================================
# フレーム定義（24fps）— 全カットで共通
# 【変更】カット1を削除し、72フレーム分ずらした
# 【変更】カット4を削除し、カット3を27秒(648f)に拡張
# 新: カット1=6秒(144f), カット2=6秒(144f), カット3=27秒(648f)
# 合計: 39秒 = 936フレーム
# ============================================================
CUT1_START = 0
CUT1_END = 144

CUT2_START = 144
CUT2_END = 288

CUT3_START = 288
CUT3_END = 936  # 27秒 = 648フレーム (旧: 888, カット4削除で延長)


def setup_cut1_transparency_start(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed, scale_params=None):
    """
    カット1 (fr0-144, 6秒): 半透明化 + 动物重叠状態維持。

    動物Bが半透明(瞬時0.35)になり、动物は重叠したまま不动。
    カメラ位置: X=1m固定、Yをスケール係数で調整、Zをスケール係数で調整。
    3段階キーフレームで平滑移動。

    Parameters:
        camera: カメラオブジェクト
        car_a: 動物Aのオブジェクト
        car_b: 動物Bのオブジェクト
        center_pos_a: 動物Aの中心位置
        center_pos_b: 動物Bの中心位置
        separated_pos_a: 動物Aの分離位置
        separated_pos_b: 動物Bの分離位置
        cam_fixed: 固定カメラ位置 (X, Y_base, Z_ref) の参照値
        scale_params: スケールパラメータ辞書 (オプション)
            - cam_scale: カメラ距離用スケール係数
            - min_camera_z: カメラZの最低値保証
    """
    print("\n  === カット1: 半透明化 + Y=-11固定, Z:0.5->7渐变 (AUTO_CLAMPED) ===")

    if scale_params is None:
        scale_params = {}
    cam_scale = scale_params.get("cam_scale", 1.0)
    char_scale = scale_params.get("char_scale", 1.0)

    # スケーリング適用後のカメラY位置（デフォルト -11.0 * cam_scale）
    base_cam_y = -7.5 * cam_scale

    # Z座標もスケールで調整
    cam_z_start = max(0.5, 0.5 * min(cam_scale, 2.0))
    cam_z_end = max(7.0, 7.0 * char_scale)
    cam_z_middle = (cam_z_start + cam_z_end) / 2.0

    # 动物は重叠位置を维持（fr0-fr144で不动）
    _set_location_keyframe(car_a, CUT1_START, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_START, center_pos_b[0], center_pos_b[1], center_pos_b[2])
    _set_location_keyframe(car_a, CUT1_END, center_pos_a[0], center_pos_a[1], center_pos_a[2])
    _set_location_keyframe(car_b, CUT1_END, center_pos_b[0], center_pos_b[1], center_pos_b[2])

    # カメラ位置: X固定、Yをスケール適用、Z渐变（AUTO_CLAMPEDが自動イージング）
    # 3段階キーフレーム設定
    cam_start = (cam_fixed[0], base_cam_y, cam_z_start)
    cam_middle = (cam_fixed[0], base_cam_y, cam_z_middle)
    cam_end = (cam_fixed[0], base_cam_y, cam_z_end)

    middle_frame = int((CUT1_START + CUT1_END) / 2)     # fr72

    _set_camera_location_keyframe(camera, CUT1_START, cam_start)
    _set_camera_location_keyframe(camera, middle_frame, cam_middle)
    _set_camera_location_keyframe(camera, CUT1_END, cam_end)

    print(f"  [フレーム {CUT1_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT1_START}-{CUT1_END}] カメラ: ({cam_fixed[0]},{base_cam_y:.1f},{cam_z_start:.1f})->({cam_fixed[0]},{base_cam_y:.1f},{cam_z_middle:.1f})->({cam_fixed[0]},{base_cam_y:.1f},{cam_z_end:.1f}) (AUTO_CLAMPED自動イージング)")
    print(f"  [フレーム {CUT1_END}] carA={center_pos_a}, carB={center_pos_b} (重叠維持)")


def setup_cut2_separation(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed, cam_height, scale_params=None):
    """
    カット2 (fr144-288, 6秒): 动物が横へスライドして2体が並ぶ。

    动物はfr144で重叠（center位置）→ fr288で分離位置に渐变スライド。
    カメラ: X固定、Yをスケール適用、Zをスケール係数で調整。

    fr288終了時、カメラ位置は (X, scaled_Y, 1.0) でカット3（円軌道）へ接続。

    Parameters:
        camera: カメラオブジェクト
        car_a: 動物Aのオブジェクト
        car_b: 動物Bのオブジェクト
        center_pos_a: 動物Aの中心位置
        center_pos_b: 動物Bの中心位置
        separated_pos_a: 動物Aの分離位置
        separated_pos_b: 動物Bの分離位置
        cam_fixed: 固定カメラ位置 (X, Y_base, Z_ref) の参照値
        cam_height: カメラ高さ（スケール適用済み）
        scale_params: スケールパラメータ辞書 (オプション)
    """
    print("\n  === カット2: 动物横スライド分离 + カメラZ渐变 (AUTO_CLAMPED) ===")

    if scale_params is None:
        scale_params = {}
    cam_scale = scale_params.get("cam_scale", 1.0)

    # スケーリング適用後のカメラY位置
    base_cam_y = -7.5 * cam_scale

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

    # カメラ: X固定、Yをスケール適用、Z渐变（AUTO_CLAMPEDが自動イージング）
    cam_start = (cam_fixed[0], base_cam_y, 7.0 * min(cam_scale, 2.0))
    cam_end = (cam_fixed[0], base_cam_y, cam_height)

    _set_camera_location_keyframe(camera, CUT2_START, cam_start)
    _set_camera_location_keyframe(camera, CUT2_END, cam_end)

    # fr288終了時、X=1のままで円軌道へ接続（X=0に戻さない）
    final_cam_cut2 = (cam_fixed[0], base_cam_y, cam_height)
    _set_camera_location_keyframe(camera, CUT2_END, final_cam_cut2)

    print(f"  [フレーム {CUT2_START}] carA={center_pos_a}, carB={center_pos_b} (重叠)")
    print(f"  [フレーム {CUT2_END}] carA={separated_pos_a}, carB={separated_pos_b} (スライド分离完了) | カメラZ: {cam_start[2]:.1f}->{cam_height:.1f}, X={cam_fixed[0]}维持, Y={base_cam_y:.1f}固定")


def setup_cut3_orbit(camera, car_a, car_b, separated_pos_a, separated_pos_b, cam_height, scale_params=None):
    """
    カット3 (fr288-936, 27秒): 円軌道カメラで1.1周。

    両方の動物を視界に入れながら、中心(0,0)を中心として回転。
    动物は分离位置を维持。

    軌道パラメータ:
      - 半径: スケール係数に応じて動的に決定（デフォルト 11m）
      - fr288: カット2終了位置から开始
      - 開始角度: カット2終了位置に合わせて计算
      - 半径補間: 平滑に移行
      - カメラの向き: ターゲットEmptyが高位（max高さ*0.75）を向く。

    Parameters:
        camera: カメラオブジェクト
        car_a: 動物Aのオブジェクト
        car_b: 動物Bのオブジェクト
        separated_pos_a: 動物Aの分離位置
        separated_pos_b: 動物Bの分離位置
        cam_height: カメラ高さ（スケール適用済み）
        scale_params: スケールパラメータ辞書 (オプション)
            - cam_scale: カメラ距離用スケール係数
    """
    print("\n  === カット3: 円軌道1.1周（27秒、両方視界に）===")

    if scale_params is None:
        scale_params = {}
    cam_scale = scale_params.get("cam_scale", 1.0)
    char_scale = scale_params.get("char_scale", 1.0)

    ORBIT_CENTER = (0.0, 0.0)
    ORBIT_RADIUS = 7.5 * cam_scale  # スケール係数で動的に半径調整
    print(f"  円軌道半径: {ORBIT_RADIUS:.1f}m（スケール調整）")

    # カット2終了時のカメラY位置をスケール適用
    base_cam_y = -7.5 * cam_scale

    # 開始角度を再计算 - カット2終了位置 (X=1, Y=scaled_base) から円軌道へ接続
    orbit_start_angle = math.atan2(base_cam_y, 1.0)
    initial_radius = math.sqrt(1.0**2 + base_cam_y**2)

    # fr288: カット2終了位置から直接接続（X=1维持）
    _set_camera_location_keyframe(camera, CUT3_START, (1.0, base_cam_y, cam_height))

    # 軌道移行フェーズ: fr288→fr304 で半径を initial_radius → ORBIT_RADIUS へ渐变
    transition_frames = [288, 296, 304]
    for sf in transition_frames:
        if sf == 288:
            continue  # fr288 はすでに設定済み
        t = (sf - 288) / (304 - 288)  # 0 → 1
        radius = initial_radius + (ORBIT_RADIUS - initial_radius) * t
        cam_x = ORBIT_CENTER[0] + radius * math.cos(orbit_start_angle)
        cam_y = ORBIT_CENTER[1] + radius * math.sin(orbit_start_angle)
        _set_camera_location_keyframe(camera, sf, (cam_x, cam_y, cam_height))

    # 通常の軌道キーフレーム（8フレーム間隔、fr304から继续）
    orbit_keyframe_interval = 8
    orbit_keyframes = list(range(312, CUT3_END + 1, orbit_keyframe_interval))
    if orbit_keyframes[-1] != CUT3_END:
        orbit_keyframes.append(CUT3_END)

    num_orbit_segments = len(orbit_keyframes) - 1 if len(orbit_keyframes) > 1 else 1

    for i, frame in enumerate(orbit_keyframes):
        progress = i / num_orbit_segments if num_orbit_segments > 0 else 0
        angle = orbit_start_angle + 2.2 * math.pi * progress  # 1.1周 = 2.2 * pi

        cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(angle)
        cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(angle)
        cam_pos = (cam_x, cam_y, cam_height)

        _set_camera_location_keyframe(camera, frame, cam_pos)

        if i % 20 == 0 or i == num_orbit_segments:
            print(f"  [フレーム {frame}] カメラ={cam_pos} (角度={math.degrees(angle):.1f}°)")

    # 动物は分离位置を维持
    _set_location_keyframe(car_a, CUT3_START, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT3_START, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])
    _set_location_keyframe(car_a, CUT3_END, separated_pos_a[0], separated_pos_a[1], separated_pos_a[2])
    _set_location_keyframe(car_b, CUT3_END, separated_pos_b[0], separated_pos_b[1], separated_pos_b[2])

    # 円軌道の最終位置を计算
    final_orbit_angle = orbit_start_angle + 2.2 * math.pi  # 1.1周
    final_cam_x = ORBIT_CENTER[0] + ORBIT_RADIUS * math.cos(final_orbit_angle)
    final_cam_y = ORBIT_CENTER[1] + ORBIT_RADIUS * math.sin(final_orbit_angle)
    final_cam_cut3 = (final_cam_x, final_cam_y, cam_height)

    print(f"  [フレーム {CUT3_END}] 円軌道1.1周完了（半径{ORBIT_RADIUS:.1f}m）")
    print(f"  軌道始点: (1, {base_cam_y:.1f}, {cam_height:.1f}), 開始角度={math.degrees(orbit_start_angle):.1f}°")

    return {'final_cam_cut3': final_cam_cut3}
