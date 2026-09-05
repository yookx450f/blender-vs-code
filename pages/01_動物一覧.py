"""
動物データベース管理ページ (Streamlit)

动物の新規追加・編集・削除・検索を行う。
使い方:
    streamlit run web_manage_cars.py
    → ブラウザで http://localhost:8501/動物一覧 にアクセス
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
from comparison_manager import (
    init_animals_table,
    get_all_animals,
    search_animals,
    get_animal_by_id,
    add_animal,
    update_animal,
    delete_animal,
    export_animals_to_csv,
)

# 動物タイプ別のオプション
ANIMAL_TYPE_OPTIONS = ["哺乳類", "鳥類", "爬虫類", "両生類", "魚類", "昆虫", "海洋生物", "その他"]

# クレイモデルの色オプション（DBと連動）
from comparison_manager import CLAY_COLOR_OPTIONS, CLAY_COLOR_MAP


def main():
    st.set_page_config(
        page_title="🐾 動物一覧",
        page_icon="🐾",
        layout="wide"
    )

    # プライマリーカラーを緑系に設定（CSSで上書き）
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #43A047 !important;
        color: white !important;
    }
    .stButton > button:hover {
        background-color: #2E7D32 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    init_animals_table()

    st.title("🐾 動物一覧")
    st.caption("动物の新規追加・編集・削除が行えます。比較マトリクス画面で制作状況も管理できます。")
    st.markdown("---")

    # セッション状態初期化
    if "animal_edit_mode" not in st.session_state:
        st.session_state.animal_edit_mode = False
    if "animal_edit_id" not in st.session_state:
        st.session_state.animal_edit_id = None

    # ============================================================
    # 検索セクション
    # ============================================================
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 動物名で検索", key="animal_search_box")
    with col_count:
        pass

    if search_query:
        df = search_animals(search_query)
        if df.empty:
            st.warning(f"「{search_query}」に一致する动物が見つかりませんでした。")
        else:
            st.success(f"{len(df)} 件の动物が見つかりました")
    else:
        df = get_all_animals()
        if df.empty:
            st.info("データベースに动物データがありません。新規追加してください。")
        else:
            st.success(f"全 {len(df)} 件の动物を登録中")

    # ============================================================
    # 動物一覧テーブル
    # ============================================================
    st.subheader("📋 動物一覧")
    if not df.empty:
        # DBスキーマ変更に対応：存在する列だけを選択
        expected_cols = ["id", "name", "glb_filename", "animal_type", "height", "weight", "rotation_direction", "color_name"]
        available_cols = [c for c in expected_cols if c in df.columns]
        display_df = df[available_cols].copy()
        col_names_map = {
            "id": "ID", "name": "動物名", "glb_filename": "GLBファイル",
            "animal_type": "動物タイプ", "height": "全高(mm)",
            "weight": "体重(kg)", "rotation_direction": "Z軸回転(度)",
            "color_name": "クレイモデルの色"
        }
        display_df = display_df.rename(columns={k: col_names_map[k] for k in available_cols})
        # テーブルを描画
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("データベースに动物データがありません。")

    st.markdown("---")

    # ============================================================
    # 操作セクション (2カラム)
    # ============================================================
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("➕ 新規追加 / ✏️ 編集")

        with st.form("animal_form", clear_on_submit=False):
            if st.session_state.animal_edit_mode and st.session_state.animal_edit_id:
                st.caption(f"✏️ 編集モード (ID: {st.session_state.animal_edit_id})")
                edit_animal_data = get_animal_by_id(st.session_state.animal_edit_id)

                inp_name = st.text_input("動物名", value=edit_animal_data["name"] if edit_animal_data else "")
                inp_glb = st.text_input("GLBファイル名", value=edit_animal_data.get("glb_filename", "") if edit_animal_data else "")
                inp_type = st.selectbox(
                    "動物タイプ",
                    ANIMAL_TYPE_OPTIONS,
                    index=(ANIMAL_TYPE_OPTIONS.index(edit_animal_data["animal_type"]) 
                           if edit_animal_data.get("animal_type") and edit_animal_data["animal_type"] in ANIMAL_TYPE_OPTIONS else len(ANIMAL_TYPE_OPTIONS) - 1)
                )
                col_dims_a, col_dims_b = st.columns(2)
                with col_dims_a:
                    inp_height = st.number_input("全高 (mm)", value=float(edit_animal_data.get("height", 0)) if edit_animal_data else 0.0, step=1.0)
                    inp_weight = st.number_input("体重 (kg)", value=float(edit_animal_data.get("weight", 0)) if edit_animal_data else 0.0, step=1.0)
                with col_dims_b:
                    inp_rot = st.number_input("Z軸回転角度 (度)", value=float(edit_animal_data.get("rotation_direction", 0)) if edit_animal_data else 0.0, step=1.0)
                    inp_color = st.selectbox(
                        "クレイモデルの色",
                        CLAY_COLOR_OPTIONS,
                        index=(CLAY_COLOR_OPTIONS.index(edit_animal_data.get("color_name", "グレー"))
                               if edit_animal_data.get("color_name") and edit_animal_data["color_name"] in CLAY_COLOR_OPTIONS else 0)
                    )
            else:
                st.caption("➕ 新規追加モード")

                inp_name = st.text_input("動物名", placeholder="例: ライオン")
                inp_glb = st.text_input("GLBファイル名", placeholder="例: lion.glb")
                inp_type = st.selectbox(
                    "動物タイプ",
                    ANIMAL_TYPE_OPTIONS,
                    key="new_animal_type"
                )
                col_dims_a, col_dims_b = st.columns(2)
                with col_dims_a:
                    inp_height = st.number_input("全高 (mm)", min_value=1.0, max_value=10000.0, step=1.0, key="new_animal_height")
                    inp_weight = st.number_input("体重 (kg)", min_value=0.1, max_value=100000.0, step=0.1, key="new_animal_weight")
                with col_dims_b:
                    inp_rot = st.number_input("Z軸回転角度 (度)", min_value=0.0, max_value=360.0, step=1.0, key="new_animal_rot")
                    inp_color = st.selectbox(
                        "クレイモデルの色",
                        CLAY_COLOR_OPTIONS,
                        index=0,  # デフォルト: グレー
                        key="new_animal_color"
                    )

            col_submit, col_cancel = st.columns([1, 1])
            with col_submit:
                submitted = st.form_submit_button(
                    "💾 更新" if st.session_state.animal_edit_mode else "✅ 追加",
                    type="primary",
                    use_container_width=True
                )
            with col_cancel:
                if st.session_state.animal_edit_mode:
                    if st.form_submit_button("❌ キャンセル", use_container_width=True):
                        st.session_state.animal_edit_mode = False
                        st.session_state.animal_edit_id = None
                        st.rerun()

            if submitted:
                if not inp_name:
                    st.error("動物名は必須です。")
                else:
                    if st.session_state.animal_edit_mode and st.session_state.animal_edit_id:
                        success, msg = update_animal(
                            st.session_state.animal_edit_id, inp_name, inp_glb,
                            inp_type, int(inp_height), float(inp_weight), int(inp_rot), inp_color
                        )
                        if success:
                            st.success(f"✓ 动物 ID {st.session_state.animal_edit_id} を更新しました")
                            st.session_state.animal_edit_mode = False
                            st.session_state.animal_edit_id = None
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {msg}")
                    else:
                        success, result = add_animal(
                            inp_name, inp_glb,
                            inp_type, int(inp_height), float(inp_weight), int(inp_rot), inp_color
                        )
                        if success:
                            st.success(f"✓ 动物を追加しました (ID: {result})")
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {result}")

    with col_right:
        st.subheader("🔍 詳細表示 / 🗑️ 削除")

        selected_id = st.number_input(
            "操作対象のIDを入力",
            min_value=1,
            step=1,
            key="selected_animal_id"
        )

        animal_detail = get_animal_by_id(selected_id)

        if animal_detail:
            st.markdown(f"### {animal_detail['name']}")
            detail_df = pd.DataFrame([{
                "ID": animal_detail["id"],
                "動物名": animal_detail["name"],
                "GLBファイル": animal_detail.get("glb_filename", ""),
                "動物タイプ": animal_detail.get("animal_type", ""),
                "全高(mm)": animal_detail.get("height", 0),
                "体重(kg)": animal_detail.get("weight", 0),
                "Z軸回転(度)": animal_detail.get("rotation_direction", 0),
                "クレイモデルの色": animal_detail.get("color_name", "グレー"),
            }])
            st.dataframe(detail_df.set_index("ID"), use_container_width=True)

            col_edit, col_delete = st.columns(2)
            with col_edit:
                if st.button("✏️ 編集モードに切り替え", type="secondary", use_container_width=True):
                    st.session_state.animal_edit_mode = True
                    st.session_state.animal_edit_id = selected_id
                    st.rerun()
            with col_delete:
                if st.button("🗑️ この动物を削除", type="secondary", use_container_width=True):
                    st.session_state.confirm_animal_delete = selected_id

        else:
            st.info(f"ID {selected_id} の动物が見つかりません。")

        # 削除確認
        if "confirm_animal_delete" in st.session_state and st.session_state.confirm_animal_delete:
            with st.expander("⚠️ 削除確認", expanded=True):
                confirm_animal = get_animal_by_id(st.session_state.confirm_animal_delete)
                if confirm_animal:
                    st.warning(f"「{confirm_animal['name']}」(ID: {st.session_state.confirm_animal_delete}) を削除しますか？")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("はい、削除する", type="primary", use_container_width=True):
                            success, result = delete_animal(st.session_state.confirm_animal_delete)
                            if success:
                                st.success(f"✓ 「{result}」を削除しました")
                                del st.session_state.confirm_animal_delete
                                st.rerun()
                            else:
                                st.error(result)
                    with col_n:
                        if st.button("キャンセル", use_container_width=True):
                            del st.session_state.confirm_animal_delete
                            st.rerun()

        st.markdown("---")
        st.subheader("📥 CSVエクスポート")
        if st.download_button(
            label="💾 CSVとしてダウンロード",
            data=export_animals_to_csv(),
            file_name=f"animals_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        ):
            st.success("CSVエクスポート準備完了")

    # ============================================================
    # フッター
    # ============================================================
    st.markdown("---")
    total_animals = len(get_all_animals())
    st.caption(f"📊 登録动物数: {total_animals} 種類")


if __name__ == "__main__":
    main()
