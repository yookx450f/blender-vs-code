"""
アニメーション設定モジュール - 動物ショート動画（縦長9:16）
フレーム 0-960（約40秒、24fps）を処理する。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。

仕様書 (plans/shortAnimal仕様.md) に基づく4段階のカット構造:
  カット1 (fr0-144,   6秒):  重叠状態維持、動物Bが半透明(瞬時0.35)。カメラ位置Y:-8→-9 + Z:0.5→7.0平滑移動（中間点Y:-8.5,Z:2.75経由）。視点は動物Bの最高部からmax(A,B)*0.75へ移動
  カット2 (fr144-288, 6秒):  横向きスライドで2体が瞬時分離。不透明化完了（瞬時）。カメラ位置(X:1m,Y:-9m,Z:7→1m)平滑下降、その後円軌道へ平滑接続
  カット3 (fr288-888, 25秒): 半径9m円軌道で1周（両方の動物を視界に入れながら）
  カット4 (fr888-960, 3秒):  カメラはゆっくり正面(X:2m,Y:-5m)に戻る、動物は動かさない

使い方:
    from animation_settings_shortAnimal import setup_shortAnimal_animations
    setup_shortAnimal_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions)

内部構造 (分割済み):
  short_animal_utils.py       — キーフレーム設定・オフセット計算などのツール関数
  short_animal_setup.py       — カメラターゲット/レンズ/動物位置の初期化
  short_animal_cuts.py        — カット1-4 の位置アニメーション
  short_animal_transparency.py — CarB の半透明化ドライバー設定
"""

import bpy
from animation_common import CutState
from short_animal_setup import (
    setup_camera_target_and_lens,
    setup_animal_positions,
    setup_target_animation,
)
from short_animal_cuts import (
    setup_cut1_transparency_start,
    setup_cut2_separation,
    setup_cut3_orbit,
    setup_cut4_return_front,
)
from short_animal_transparency import setup_carb_transparency


def setup_shortAnimal_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None, total_frames=960):
    """
    動物ショート動画のアニメーションを設定（フレーム 0-960、約40秒）

    【変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。
    仕様書に基づく4段階のカット構造:
      カット1 (fr0-144,   6秒):  重叠状態維持、动物B半透明(瞬時0.35)。カメラY:-8→-9 + Z:0.5→7平滑移動（中間点経由）
      カット2 (fr144-288, 6秒):  横向きスライドで2体が瞬時分離。不透明化完了（瞬時）。カメラ位置(X:1m,Y:-9m,Z:7→1m)平滑下降、その後円軌道へ平滑接続
      カット3 (fr288-888, 25秒): 半径9m円軌道で1周（両方の動物を視界に入れながら）
      カット4 (fr888-960, 3秒):  カメラはゆっくり正面(X:2m,Y:-5m)に戻る。动物は動かさない
    """
    print(f"\n=== 動物ショート動画 アニメーション設定を開始 (total_frames={total_frames}, 約{total_frames/24:.1f}秒) ===")

    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")

    if not car_a or not car_b:
        print("エラー: carA または carB が見つかりません")
        return None

    # ============================================================
    # ステップ1: 初期化（ターゲットEmpty、レンズ、動物位置計算）
    # ============================================================
    setup_result = setup_camera_target_and_lens(scene, camera, car_a, car_b, grounded_z_positions.get(car_a.name, car_a.location.z))
    target_empty = setup_result['target_empty']
    target_base = setup_result['target_base']
    target_height = setup_result['target_height']
    animal_a_max_z = setup_result['animal_a_max_z']
    animal_b_max_z = setup_result['animal_b_max_z']
    cam_height = setup_result['cam_height']

    pos_result = setup_animal_positions(car_a, car_b, grounded_z_positions)
    center_pos_a = pos_result['center_pos_a']
    center_pos_b = pos_result['center_pos_b']
    separated_pos_a = pos_result['separated_pos_a']
    separated_pos_b = pos_result['separated_pos_b']

    # ============================================================
    # ステップ2: ターゲットEmptyのアニメーション設定
    # ============================================================
    setup_target_animation(target_empty, target_base, target_height, animal_a_max_z, animal_b_max_z)

    # カメラ位置定義（仕様に準拠）
    # カット1: Y=-8, Z=0.5m; カット2: Y=-9, Z=1m; カット4: Y=-5に戻り
    cam_fixed_cut1 = (1.0, -8.0, 0.5)      # カット1: 正面、Y=-8m, Z=0.5m
    cam_fixed_cut2 = (1.0, -9.0, 1.0)      # カット2: 分離、Y=-9m, Z=1m
    cam_front = (2.0, -5.0, cam_height)    # カット4: 正面に戻り、Y=-5m

    # ============================================================
    # ステップ3: カット1-4 の位置アニメーションを順に設定
    # ============================================================
    print(f"\n  カット定義:")
    print(f"    カット1: fr0-144 ({0/24:.1f}-{144/24:.1f}秒)")
    print(f"    カット2: fr144-288 ({144/24:.1f}-{288/24:.1f}秒)")
    print(f"    カット3: fr288-888 ({288/24:.1f}-{888/24:.1f}秒) 半径9m円軌道")
    print(f"    カット4: fr888-960 ({888/24:.1f}-{960/24:.1f}秒)")

    # カット1: 半透明化 + 重叠状态维持 (カメラZ=0.5m开始)
    setup_cut1_transparency_start(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed_cut1)

    # カット2: 分离状态维持（动物B不透明化）(カメラZ:7→1m、円軌道へ平滑接続)
    setup_cut2_separation(camera, car_a, car_b, center_pos_a, center_pos_b, separated_pos_a, separated_pos_b, cam_fixed_cut2, cam_height)

    # カット3: 円軌道1周 (半径9m、カメラZ=cam_height)
    orbit_result = setup_cut3_orbit(camera, car_a, car_b, separated_pos_a, separated_pos_b, cam_height)
    final_cam_cut3 = orbit_result['final_cam_cut3']

    # カット4: カメラが正面に戻る
    setup_cut4_return_front(camera, car_a, car_b, separated_pos_a, separated_pos_b, final_cam_cut3, cam_front)

    # ============================================================
    # ステップ4: CarB の半透明化ドライバー設定
    # ============================================================
    setup_carb_transparency(car_b)

    # シーンをフレーム 0 に戻す
    bpy.context.scene.frame_set(0)

    print(f"\n=== 動物ショート動画 アニメーション完了 (total_frames={total_frames}) ===")

    # 最终状態を取得して返す
    bpy.context.scene.frame_set(960)
    camera.location = cam_front
    final_rot = camera.rotation_euler.copy()

    return CutState(
        car_a_loc=center_pos_a,
        car_b_loc=center_pos_b,
        camera_loc=cam_front,
        camera_rot=(final_rot.x, final_rot.y, final_rot.z),
    )
