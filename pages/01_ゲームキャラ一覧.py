"""
ゲームキャラクターデータベース管理ページ (Streamlit)

ゲームキャラクターの新規追加・編集・削除・検索を行う。
使い方:
    streamlit run web_manage_cars.py
    → ブラウザで http://localhost:8501/ゲームキャラ一覧 にアクセス
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
from comparison_manager import (
    init_games_table,
    get_all_games,
    search_games,
    get_game_by_id,
    add_game,
    update_game,
    delete_game,
    export_games_to_csv,
)

# ゲームキャラクタータイプ別のオプション
GAME_TYPE_OPTIONS = ["RPG", "アクション", "アドベンチャー", "シューター", "格闘", "オープンワールド", "インディー", "その他"]

# クレイモデルの色オプション（DBと連動）
from comparison_manager import CLAY_COLOR_OPTIONS, CLAY_COLOR_MAP


def main():
    st.set_page_config(
        page_title="🎮 ゲームキャラ一覧",
        page_icon="🎮",
        layout="wide"
    )

    # プライマリーカラーを紫系に設定（CSSで上書き）
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #AB47BC !important;
        color: white !important;
    }
    .stButton > button:hover {
        background-color: #8E24AA !important;
    }
    </style>
    """, unsafe_allow_html=True)

    init_games_table()

    st.title("🎮 ゲームキャラ一覧")
    st.caption("ゲームキャラクターの新規追加・編集・削除が行えます。比較マトリクス画面で制作状況も管理できます。")
    st.markdown("---")

    # セッション状態初期化
    if "game_edit_mode" not in st.session_state:
        st.session_state.game_edit_mode = False
    if "game_edit_id" not in st.session_state:
        st.session_state.game_edit_id = None

    # ============================================================
    # 検索セクション
    # ============================================================
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 キャラクター名で検索", key="game_search_box")
    with col_count:
        pass

    if search_query:
        df = search_games(search_query)
        if df.empty:
            st.warning(f"「{search_query}」に一致するキャラクターが見つかりませんでした。")
        else:
            st.success(f"{len(df)} 件のキャラクターが見つかりました")
    else:
        df = get_all_games()
        if df.empty:
            st.info("データベースにキャラクターデータがありません。新規追加してください。")
        else:
            st.success(f"全 {len(df)} 件のキャラクターを登録中")

    # ============================================================
    # キャラクター一覧テーブル
    # ============================================================
    st.subheader("📋 キャラクター一覧")
    if not df.empty:
        # DBスキーマ変更に対応：存在する列だけを選択
        expected_cols = ["id", "name", "glb_filename", "game_name", "height", "length", "rotation_direction", "color_name"]
        available_cols = [c for c in expected_cols if c in df.columns]
        display_df = df[available_cols].copy()
        col_names_map = {
            "id": "ID", "name": "キャラ名", "glb_filename": "GLBファイル",
            "game_name": "ゲーム名", "height": "全高(mm)", "length": "全長(mm)",
            "rotation_direction": "Z軸回転(度)",
            "color_name": "クレイモデルの色"
        }
        display_df = display_df.rename(columns={k: col_names_map[k] for k in available_cols})
        # テーブルを描画
        st.dataframe(display_df, width='stretch', hide_index=True)
    else:
        st.info("データベースにキャラクターデータがありません。")

    st.markdown("---")

    # ============================================================
    # 操作セクション (2カラム)
    # ============================================================
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("➕ 新規追加 / ✏️ 編集")

        with st.form("game_form", clear_on_submit=False):
            if st.session_state.game_edit_mode and st.session_state.game_edit_id:
                st.caption(f"✏️ 編集モード (ID: {st.session_state.game_edit_id})")
                edit_game_data = get_game_by_id(st.session_state.game_edit_id)

                inp_name = st.text_input("キャラ名", value=edit_game_data["name"] if edit_game_data else "")
                inp_glb = st.text_input("GLBファイル名", value=edit_game_data.get("glb_filename", "") if edit_game_data else "")
                inp_gamename = st.text_input("ゲーム名", value=edit_game_data.get("game_name", "") if edit_game_data else "")
                col_dims_a, col_dims_b = st.columns(2)
                with col_dims_a:
                    inp_height = st.number_input("全高 (mm)", value=float(edit_game_data.get("height", 0)) if edit_game_data else 0.0, step=1.0)
                    inp_length = st.number_input("全長 (mm)", value=float(edit_game_data.get("length", 0)) if edit_game_data else 0.0, step=1.0)
                with col_dims_b:
                    inp_rot = st.number_input("Z軸回転角度 (度)", value=float(edit_game_data.get("rotation_direction", 0)) if edit_game_data else 0.0, step=1.0)
                    inp_color = st.selectbox(
                        "クレイモデルの色",
                        CLAY_COLOR_OPTIONS,
                        index=(CLAY_COLOR_OPTIONS.index(edit_game_data.get("color_name", "グレー"))
                               if edit_game_data.get("color_name") and edit_game_data["color_name"] in CLAY_COLOR_OPTIONS else 0)
                    )
            else:
                st.caption("➕ 新規追加モード")

                inp_name = st.text_input("キャラ名", placeholder="例: クロノトリガー")
                inp_glb = st.text_input("GLBファイル名", placeholder="例: chrono.glb")
                inp_gamename = st.text_input("ゲーム名", placeholder="例: クロノトリガー")
                col_dims_a, col_dims_b = st.columns(2)
                with col_dims_a:
                    inp_height = st.number_input("全高 (mm)", min_value=1.0, max_value=10000.0, step=1.0, key="new_game_height")
                    inp_length = st.number_input("全長 (mm)", min_value=0.0, max_value=10000.0, step=1.0, key="new_game_length")
                with col_dims_b:
                    inp_rot = st.number_input("Z軸回転角度 (度)", min_value=0.0, max_value=360.0, step=1.0, key="new_game_rot")
                    inp_color = st.selectbox(
                        "クレイモデルの色",
                        CLAY_COLOR_OPTIONS,
                        index=0,  # デフォルト: グレー
                        key="new_game_color"
                    )

            col_submit, col_cancel = st.columns([1, 1])
            with col_submit:
                submitted = st.form_submit_button(
                    "💾 更新" if st.session_state.game_edit_mode else "✅ 追加",
                    type="primary",
                    width='stretch'
                )
            with col_cancel:
                if st.session_state.game_edit_mode:
                    if st.form_submit_button("❌ キャンセル", width='stretch'):
                        st.session_state.game_edit_mode = False
                        st.session_state.game_edit_id = None
                        st.rerun()

            if submitted:
                if not inp_name:
                    st.error("キャラ名は必須です。")
                else:
                    if st.session_state.game_edit_mode and st.session_state.game_edit_id:
                        success, msg = update_game(
                            st.session_state.game_edit_id, inp_name, inp_glb,
                            inp_gamename, int(inp_height), int(inp_length), int(inp_rot), inp_color
                        )
                        if success:
                            st.success(f"✓ キャラクター ID {st.session_state.game_edit_id} を更新しました")
                            st.session_state.game_edit_mode = False
                            st.session_state.game_edit_id = None
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {msg}")
                    else:
                        success, result = add_game(
                            inp_name, inp_glb,
                            inp_gamename, int(inp_height), int(inp_length), int(inp_rot), inp_color
                        )
                        if success:
                            st.success(f"✓ キャラクターを追加しました (ID: {result})")
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {result}")

    with col_right:
        st.subheader("🔍 詳細表示 / 🗑️ 削除")

        selected_id = st.number_input(
            "操作対象のIDを入力",
            min_value=1,
            step=1,
            key="selected_game_id"
        )

        game_detail = get_game_by_id(selected_id)

        if game_detail:
            st.markdown(f"### {game_detail['name']}")
            detail_df = pd.DataFrame([{
                "ID": game_detail["id"],
                "キャラ名": game_detail["name"],
                "GLBファイル": game_detail.get("glb_filename", ""),
                "ゲーム名": game_detail.get("game_name", ""),
                "全高(mm)": game_detail.get("height", 0),
                "全長(mm)": game_detail.get("length", 0),
                "Z軸回転(度)": game_detail.get("rotation_direction", 0),
                "クレイモデルの色": game_detail.get("color_name", "グレー"),
            }])
            st.dataframe(detail_df.set_index("ID"), width='stretch')

            col_edit, col_delete = st.columns(2)
            with col_edit:
                if st.button("✏️ 編集モードに切り替え", type="secondary", width='stretch'):
                    st.session_state.game_edit_mode = True
                    st.session_state.game_edit_id = selected_id
                    st.rerun()
            with col_delete:
                if st.button("🗑️ このキャラクターを削除", type="secondary", width='stretch'):
                    st.session_state.confirm_game_delete = selected_id

        else:
            st.info(f"ID {selected_id} のキャラクターが見つかりません。")

        # 削除確認
        if "confirm_game_delete" in st.session_state and st.session_state.confirm_game_delete:
            with st.expander("⚠️ 削除確認", expanded=True):
                confirm_game = get_game_by_id(st.session_state.confirm_game_delete)
                if confirm_game:
                    st.warning(f"「{confirm_game['name']}」(ID: {st.session_state.confirm_game_delete}) を削除しますか？")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("はい、削除する", type="primary", width='stretch'):
                            success, result = delete_game(st.session_state.confirm_game_delete)
                            if success:
                                st.success(f"✓ 「{result}」を削除しました")
                                del st.session_state.confirm_game_delete
                                st.rerun()
                            else:
                                st.error(result)
                    with col_n:
                        if st.button("キャンセル", width='stretch'):
                            del st.session_state.confirm_game_delete
                            st.rerun()

        st.markdown("---")
        st.subheader("📥 CSVエクスポート")
        if st.download_button(
            label="💾 CSVとしてダウンロード",
            data=export_games_to_csv(),
            file_name=f"games_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width='stretch'
        ):
            st.success("CSVエクスポート準備完了")

    # ============================================================
    # フッター
    # ============================================================
    st.markdown("---")
    total_games = len(get_all_games())
    st.caption(f"📊 登録キャラクター数: {total_games} 種類")


if __name__ == "__main__":
    main()
