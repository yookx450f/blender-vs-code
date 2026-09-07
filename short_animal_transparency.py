"""
動物ショート動画 - CarB / Human 半透明化モジュール

动物B・Humanの透明度を制御するドライバー式を設定する。
瞬時切り替え式（グラデーション遷移禁止）を使用。

【2026-09-07 変更】カット1 (fr0-72) を削除し、フレーム番号を72分ずらした。

使い方:
    from short_animal_transparency import setup_carb_transparency, setup_human_transparency
    setup_carb_transparency(car_b)
    setup_human_transparency(human_figure)
"""

import bpy
from animation_common import _collect_all_mesh_objects_recursive


def setup_carb_transparency(car_b):
    """
    CarB の半透明化アニメーションを設定（瞬時切り替え式）。

    Alpha のタイミング（瞬時切り替え式 - グラデーション遷移禁止）:
      【変更】カット1削除でフレーム番号を72分ずらした
      fr0-144 (カット1):     半透明 (alpha=0.35、動画開始時から)
      fr144-288 (カット2):   半透明 (alpha=0.35维持)
      fr288-960 (カット3-4): 不透明 (alpha=1.0、瞬時切り替え)

    Parameters:
        car_b: 动物Bのルートオブジェクト
    """
    if not car_b:
        return

    print("\n  === CarB 半透明化設定（瞬時切り替え式）===")

    all_meshes = _collect_all_mesh_objects_recursive(car_b)
    if not all_meshes:
        if car_b.type == 'MESH' and len(car_b.data.materials) > 0:
            all_meshes = [car_b]

    # Alpha のタイミング（瞬時切り替え式）
    # fr0から半透明、fr288で完全分離時に不透明に戻す
    alpha_expr = (
        "0.35 if frame < 288 else"
        " 1.0"
    )

    count = _apply_alpha_driver(all_meshes, alpha_expr)
    print(f"  Alpha(CarB): ドライバー式 [瞬時切り替え] を {count} マテリアルに設定")
    print(f"  タイミング: fr0-288:0.35 → fr288:1.0")


def setup_human_transparency(human_figure):
    """
    HumanFigure の半透明化アニメーションを設定（瞬時切り替え式）。

    Alpha のタイミング（CarB と同期）:
      【変更】カット1削除でフレーム番号を72分ずらした
      fr0-144 (カット1):     半透明 (alpha=0.35、動画開始時から)
      fr144-288 (カット2):   半透明 (alpha=0.35维持)
      fr288-960 (カット3-4): 不透明 (alpha=1.0、瞬時切り替え)

    Parameters:
        human_figure: HumanFigure のルートオブジェクト
    """
    if not human_figure:
        return

    print("\n  === HumanFigure 半透明化設定（瞬時切り替え式）===")

    all_meshes = _collect_all_mesh_objects_recursive(human_figure)
    if not all_meshes:
        if human_figure.type == 'MESH' and human_figure.data and len(human_figure.data.materials) > 0:
            all_meshes = [human_figure]

    # Alpha のタイミング（CarB と同期する瞬時切り替え式）
    alpha_expr = (
        "0.35 if frame < 288 else"
        " 1.0"
    )

    count = _apply_alpha_driver(all_meshes, alpha_expr)
    print(f"  Alpha(Human): ドライバー式 [瞬時切り替え] を {count} マテリアルに設定")
    print(f"  タイミング: fr0-288:0.35 → fr288:1.0")


def _apply_alpha_driver(mesh_objects, alpha_expr):
    """
    指定されたメッシュオブジェクト一覧にAlphaドライバーを適用する共通処理。

    Parameters:
        mesh_objects: メッシュオブジェクトのリスト
        alpha_expr: ドライバー式の文字列

    Returns:
        適用したマテリアルの数
    """
    count = 0
    for mesh_obj in mesh_objects:
        if not hasattr(mesh_obj, 'data') or mesh_obj.data is None:
            continue
        for material in mesh_obj.data.materials:
            if material is None or not material.use_nodes:
                continue
            try:
                material.blend_method = 'BLEND'
            except AttributeError:
                pass
            nodes = material.node_tree.nodes
            principled_node = None
            for node in nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                    break
            if principled_node is None or 'Alpha' not in principled_node.inputs:
                continue
            alpha_input = principled_node.inputs['Alpha']
            alpha_input.driver_remove("default_value")
            driver = alpha_input.driver_add("default_value").driver
            driver.type = 'SCRIPTED'
            driver.expression = alpha_expr
            count += 1
    return count
