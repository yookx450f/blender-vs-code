"""
アニメーション設定モジュール - 動物ショート動画（縦長9:16）
フレーム 0-936（約39秒、24fps）を処理する。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。

【2026-09-08 変更】カメラのY位置を全カットで-11固定、カット3の軌道半径を11mに変更。

【2026-09-08 変更】カット4を削除し、カット3を27秒・1.1周に拡張。

【動的スケーリング】
    動物の寸法に基づいて、カメラ距離・軌道半径・レンズ・分離間隔を自動調整する。
    大きな動物ほど、カメラを遠ざけ・広角にし・間隔を広げる。

仕様書 (plans/shortAnimal仕様.md) に基づく3段階のカット構造:
  カット1 (fr0-144,   6秒):  重叠状態維持、動物Bが半透明(瞬時0.35)。カメラ位置Yをスケール適用 + Zをスケール調整。視点は動物Bの最高部からmax(A,B)*0.75へ移動
  カット2 (fr144-288, 6秒):  横向きスライドで2体が瞬時分離。不透明化完了（瞬時）。カメラ位置平滑下降、その後円軌道へ平滑接続
  カット3 (fr288-936, 27秒): 半径をスケール適用した円軌道で1.1周（両方の動物を視界に入れながら）

使い方:
    from animation_settings_shortAnimal import setup_shortAnimal_animations
    setup_shortAnimal_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions)

内部構造 (分割済み):
  short_animal_utils.py       — キーフレーム設定・オフセット計算などのツール関数
  short_animal_setup.py       — カメラターゲット/レンズ/動物位置の初期化
  short_animal_cuts.py        — カット1-3 の位置アニメーション
  short_animal_transparency.py — CarB の半透明化ドライバー設定
"""

import bpy
from animation_common import CutState
from short_animal_utils import _calculate_animal_scale_factor
from short_animal_setup import (
    setup_camera_target_and_lens,
    setup_animal_positions,
    setup_target_animation,
)
from short_animal_cuts import (
    setup_cut1_transparency_start,
    setup_cut2_separation,
    setup_cut3_orbit,
)
from short_animal_transparency import setup_carb_transparency


def setup_shortAnimal_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None, total_frames=936):
    """
    動物ショート動画のアニメーションを設定（フレーム 0-936、約39秒）

    【変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。
    【変更】カメラのY位置を全カットで-11固定、カット3の軌道半径を11mに変更。
    【変更】カット4を削除し、カット3を27秒・1.1周に拡張。

    【動的スケーリング】
        動物の寸法に基づいて、カメラ距離・軌道半径・レンズ・分離間隔を自動調整する。

    仕様書に基づく3段階のカット構造:
      カット1 (fr0-144,   6秒):  重叠状態維持、动物B半透明(瞬時0.35)。カメラYをスケール適用 + Zをスケール調整
      カット2 (fr144-288, 6秒):  横向きスライドで2体が瞬時分離。不透明化完了（瞬時）。カメラ位置平滑下降、その後円軌道へ平滑接続
      カット3 (fr288-936, 27秒): 半径をスケール適用した円軌道で1.1周（両方の動物を視界に入れながら）
    """
    print(f"\n=== 動物ショート動画 アニメーション設定を開始 (total_frames={total_frames}, 約{total_frames/24:.1f}秒) ===")

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # ============================================================
    # 動的スケーリング計算
    # ============================================================
    scale_factor = _calculate_animal_scale_factor(car_dimensions)

    # スケーリング適用後の基本値
    # 分離間隔: スケール係数の0.3乗で非常に緩やかに補正（中小型動物はほぼ変わらない）
    char_scale = scale_factor ** 0.3
    # カメラ距離: 1.3倍で中小型動物は寄ったまま、大型動物だけ適度に遠ざかる
    cam_scale = scale_factor * 1.3
    # カメラZの最小値をスケールで調整（デフォルト上限2.0倍）
    min_cam_z_cap = 2.0

    print(f"  動的スケーリング: scale_factor={scale_factor:.2f}, char_scale={char_scale:.2f}, cam_scale={cam_scale:.2f}")
    print(f"  分離間隔係数: {char_scale:.2f}")
    print(f"  カメラ距離係数: {cam_scale:.2f}")

    # スケールパラメータをまとめた辞書（カット関数へ渡す用）
    scale_params = {
        "scale_factor": scale_factor,
        "char_scale": char_scale,
        "cam_scale": cam_scale,
    }

    # ============================================================
    # ステップ1: 初期化（ターゲットEmpty、レンズ、動物位置計算）
    # ============================================================
    setup_result = setup_camera_target_and_lens(
        scene, camera, car_a, car_b, 
        grounded_z_positions.get(car_a.name, car_a.location.z),
        cam_scale=min(cam_scale, min_cam_z_cap)
    )
    target_empty = setup_result['target_empty']
    target_base = setup_result['target_base']
    target_height = setup_result['target_height']
    animal_a_max_z = setup_result['animal_a_max_z']
    animal_b_max_z = setup_result['animal_b_max_z']
    cam_height = setup_result['cam_height']

    pos_result = setup_animal_positions(car_a, car_b, grounded_z_positions, sep_scale=char_scale)
    center_pos_a = pos_result['center_pos_a']
    center_pos_b = pos_result['center_pos_b']
    separated_pos_a = pos_result['separated_pos_a']
    separated_pos_b = pos_result['separated_pos_b']

    # ============================================================
    # ステップ2: ターゲットEmptyのアニメーション設定
    # ============================================================
    setup_target_animation(target_empty, target_base, target_height, animal_a_max_z, animal_b_max_z)

    # カメラ位置定義（仕様に準拠）— スケール適用はカット関数内で处理
    cam_fixed_cut1 = (1.0, -11.0, 0.5)      # カット1: 正面、Y=-11m, Z=0.5m (参照値)
    cam_fixed_cut2 = (1.0, -11.0, 1.0)      # カット2: 分離、Y=-11m, Z=1m (参照値)

    # ============================================================
    # ステップ3: カット1-3 の位置アニメーションを順に設定
    # ============================================================
    print(f"\n  カット定義:")
    print(f"    カット1: fr0-144 ({0/24:.1f}-{144/24:.1f}秒)")
    print(f"    カット2: fr144-288 ({144/24:.1f}-{288/24:.1f}秒)")
    print(f"    カット3: fr288-936 ({288/24:.1f}-{936/24:.1f}秒) 半径{11.0 * cam_scale:.1f}m円軌道1.1周")

    # カット1: 半透明化 + 重叠状态维持 (カメラZをスケール適用)
    setup_cut1_transparency_start(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed_cut1, scale_params)

    # カット2: 分离状态维持（动物B不透明化）(カメラZ渐变、円軌道へ平滑接続)
    setup_cut2_separation(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed_cut2, cam_height, scale_params)

    # カット3: 円軌道1.1周 (半径をスケール適用、カメラZ=cam_height)
    orbit_result = setup_cut3_orbit(camera, car_a, car_b, separated_pos_a, separated_pos_b, cam_height, scale_params)
    final_cam_cut3 = orbit_result['final_cam_cut3']

    # ============================================================
    # ステップ4: CarB の半透明化ドライバー設定
    # ============================================================
    setup_carb_transparency(car_b)

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print(f"\n=== 動物ショート動画 アニメーション完了 (total_frames={total_frames}) ===")

    # 最終状態を取得して返す
    bpy.context.scene.frame_set(936)
    camera.location = final_cam_cut3
    final_rot = camera.rotation_euler.copy()

    return CutState(
        car_a_loc=center_pos_a,
        car_b_loc=center_pos_b,
        camera_loc=final_cam_cut3,
        camera_rot=(final_rot.x, final_rot.y, final_rot.z),
    )
