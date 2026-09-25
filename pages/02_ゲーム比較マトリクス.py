"""
ゲームキャラクター比較マトリクス ページ

ゲームキャラクター同士の比較動画制作状況を行列形式で表示・管理する。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from comparison_manager import (
    init_games_table,
    init_game_comparisons_table,
    get_game_matrix_data,
    get_game_comparison_by_ids,
    create_game_comparison_if_not_exists,
    update_game_comparison_full,
    delete_game_comparison,
    set_game_comparison_pair_to_config,
)

# DB初期化
init_games_table()
init_game_comparisons_table()

st.set_page_config(page_title="🎮 ゲーム比較マトリクス", page_icon="🎮", layout="wide")

# ボタンカラーを紫系に設定
st.markdown("""
<style>
[data-testid="stFormSubmitButton"],
.stButton > button,
button[kind="primary"] {
    background-color: #AB47BC !important;
    color: white !important;
    border: 1px solid #AB47BC !important;
}
[data-testid="stFormSubmitButton"]:hover,
.stButton > button:hover,
button[kind="primary"]:hover {
    background-color: #8E24AA !important;
    border-color: #8E24AA !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🎮 ゲーム比較マトリクス")
st.caption("セルをクリックして制作状況を確認・編集できます")

# セッション状態初期化
if "game_selected_cell" not in st.session_state:
    st.session_state.game_selected_cell = None
if "game_config_success_msg" not in st.session_state:
    st.session_state.game_config_success_msg = None
if "game_config_error_msg" not in st.session_state:
    st.session_state.game_config_error_msg = None

# データ取得
games_df, status_map = get_game_matrix_data()

if games_df.empty:
    st.warning("ゲームキャラクターデータがありません。まず「🎮 ゲームキャラ一覧」からキャラクターを登録してください。")
    st.stop()

game_list = games_df[["id", "name"]].to_dict("records")

# フィルタセクション
col_search, col_status = st.columns([3, 2])

default_search = st.query_params.get("search", "")
default_status = st.query_params.get("status", "全件表示")

with col_search:
    search_query = st.text_input("🔍 キャラクター名で絞り込み", value=default_search, key="game_matrix_search")

with col_status:
    status_options = ["全件表示", "未着手のみ", "登録済・未着手のみ", "制作中のみ", "ショート完了のみ", "長尺制作中のみ", "両方完了のみ"]
    default_status_idx = status_options.index(default_status) if default_status in status_options else 0
    status_filter = st.selectbox(
        "制作状況でフィルタ",
        status_options,
        index=default_status_idx
    )

# フィルタ状態をURLパラメータに保存
st.query_params["search"] = search_query
st.query_params["status"] = status_filter

# ゲームリストのフィルタリング
filtered_games_a = game_list.copy()
if search_query:
    filtered_games_a = [g for g in filtered_games_a if search_query.lower() in g["name"].lower()]

filtered_games_b = game_list.copy()
if search_query:
    filtered_games_b = [g for g in filtered_games_b if search_query.lower() in g["name"].lower()]

if not filtered_games_a or not filtered_games_b:
    st.info("条件に一致するキャラクターが見つかりませんでした。")
    st.stop()

# 無効ペアのセットを事前に計算
invalid_pairs = set()
for game_a in filtered_games_a:
    for game_b in filtered_games_b:
        if game_a["id"] == game_b["id"]:
            invalid_pairs.add((game_a["id"], game_b["id"]))

# DBに登録済みのペアIDセット
registered_pairs = set()
if status_map:
    registered_pairs = set(status_map.keys())

# 無効ペアに逆順も追加
for game_a in filtered_games_a:
    for game_b in filtered_games_b:
        if (game_b["id"], game_a["id"]) in registered_pairs and game_a["id"] != game_b["id"]:
            invalid_pairs.add((game_a["id"], game_b["id"]))

# ステータスラベル取得関数
def get_game_combined_status(short_status, long_status):
    if short_status == 2 and long_status == 2:
        return "両方完了", "#2e7d32"
    elif short_status == 2 and long_status == 1:
        return "長尺制作中", "#ff9800"
    elif short_status == 2 and long_status == 0:
        return "ショート完了", "#ffeb3b"
    elif short_status >= 1 or long_status >= 1:
        return "制作中", "#64b5f6"
    else:
        return "未着手", "#e0e0e0"

# マトリクス表示
st.subheader("📋 比較マトリクス")

def generate_game_matrix_html(filtered_games_a, filtered_games_b, game_compare_lookup=None):
    bg_header = "#2d2d2d"
    bg_row_header = "#333333"
    border_color = "#555555"
    text_color = "#e0e0e0"
    text_header = "#ffffff"
    
    status_colors_dark = {
        "未着手": "#3d3d3d",
        "登録済・未着手": "#4a148c",
        "制作中": "#7b1fa2",
        "ショート完了": "#f9a825",
        "長尺制作中": "#e65100",
        "両方完了": "#2e7d32",
    }
    
    parts = []
    parts.append('<div style="overflow: auto; max-height: 75vh;"><table style="border-collapse: separate; border-spacing: 0; width: 100%; font-family: \'Meiryo UI\', sans-serif;">')
    
    # ヘッダー行
    parts.append(f'<tr><th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; min-width: 120px; color: {text_header}; position: sticky; top: 0; z-index: 20;"></th>')
    for game_b in filtered_games_b:
        parts.append(f'<th style="padding: 8px; border: 1px solid {border_color}; background: {bg_header}; text-align: center; color: {text_header}; font-size: 12px; position: sticky; top: 0; z-index: 10;">{game_b["name"]}</th>')
    parts.append('</tr>')
    
    # データ行
    for game_a in filtered_games_a:
        parts.append(f'<tr><td style="padding: 4px 6px; border: 1px solid {border_color}; background: {bg_row_header}; font-weight: bold; color: {text_color}; font-size: 12px; position: sticky; left: 0; z-index: 5;">{game_a["name"]}</td>')
        
        for game_b in filtered_games_b:
            pair_key = (game_a["id"], game_b["id"])
            
            if pair_key in invalid_pairs:
                if status_filter == "全件表示":
                    reason = "同じキャラクター" if game_a["id"] == game_b["id"] else "重複ペア"
                    parts.append(f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: #4a4a4a; color: #888888; text-align: center; font-size: 11px;">⫘ {reason}</td>')
                else:
                    parts.append(f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: transparent;"></td>')
                continue
            
            # 辞書参照でステータスを取得（DBクエリなし）
            comp = game_compare_lookup.get(pair_key) if game_compare_lookup else None
            has_registration = comp is not None
            
            if comp:
                short_status = comp["short_status"]
                long_status = comp["long_status"]
            else:
                short_status = 0
                long_status = 0
            
            label, _ = get_game_combined_status(short_status, long_status)
            
            if has_registration and label == "未着手":
                cell_bg = status_colors_dark.get("登録済・未着手", "#4a148c")
                text_fg = "#ce93d8"
            else:
                cell_bg = status_colors_dark.get(label, "#3d3d3d")
                text_fg = "#999999" if label == "未着手" else "#ffffff"
            
            # ステータスフィルタ
            show_cell = True
            if status_filter == "未着手のみ" and label != "未着手":
                show_cell = False
            elif status_filter == "登録済・未着手のみ" and not (has_registration and label == "未着手"):
                show_cell = False
            elif status_filter == "制作中のみ" and label != "制作中":
                show_cell = False
            elif status_filter == "ショート完了のみ" and label != "ショート完了":
                show_cell = False
            elif status_filter == "長尺制作中のみ" and label != "長尺制作中":
                show_cell = False
            elif status_filter == "両方完了のみ" and label != "両方完了":
                show_cell = False
            
            if not show_cell:
                parts.append(f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: transparent;"></td>')
                continue
            
            link_url = f"?game_a={game_a['id']}&game_b={game_b['id']}#edit-panel"
            parts.append(f'''<td style="padding: 4px 6px; border: 1px solid {border_color}; background: {cell_bg}; color: {text_fg}; text-align: center; cursor: pointer; font-size: 12px;">
                <a href="{link_url}" style="text-decoration: none; color: inherit;">{label}</a>
            </td>''')
        
        parts.append('</tr>')
    
    parts.append('</table></div>')
    return "".join(parts)

# status_map を辞書参照用に整形（O(N²) DBクエリをO(1)辞書参照に最適化）
game_compare_lookup = {}
if status_map:
    for pair_key, comp_data in status_map.items():
        game_compare_lookup[pair_key] = comp_data

matrix_html = generate_game_matrix_html(filtered_games_a, filtered_games_b, game_compare_lookup)
st.markdown(matrix_html, unsafe_allow_html=True)

# ラジェンド
st.markdown("---")
legend_items = [
    ("⬜", "未着手（登録なし）", "#3d3d3d"),
    ("🔲", "登録済・未着手", "#4a148c"),
    ("🟣", "制作中", "#7b1fa2"),
    ("🟡", "ショート完了", "#f9a825"),
    ("🟠", "長尺制作中", "#e65100"),
    ("🟢", "両方完了", "#2e7d32"),
    ("⫘", "無効ペア", "#4a4a4a")
]

legend_html = '<div style="display: flex; gap: 16px; flex-wrap: wrap; padding: 8px;">'
for icon, label, color in legend_items:
    legend_html += f'<span style="display: inline-flex; align-items: center; gap: 4px;"><span style="display: inline-block; width: 16px; height: 16px; background: {color}; border: 1px solid #666;"></span> <span style="color: #e0e0e0;">{label}</span></span>'
legend_html += '</div>'
st.markdown(legend_html, unsafe_allow_html=True)

# セル編集パネル（サイドバー）
st.sidebar.header("✏️ ゲーム比較ペア編集")

game_a_param = st.query_params.get("game_a", "")
game_b_param = st.query_params.get("game_b", "")

initial_idx_a = 0
initial_idx_b = 1 if len(filtered_games_b) > 1 else 0

if game_a_param:
    for idx, game in enumerate(filtered_games_a):
        if str(game["id"]) == str(game_a_param):
            initial_idx_a = idx
            break

if game_b_param:
    for idx, game in enumerate(filtered_games_b):
        if str(game["id"]) == str(game_b_param):
            initial_idx_b = idx
            break

selected_game_a = st.sidebar.selectbox(
    "キャラクターAを選択",
    options=filtered_games_a,
    format_func=lambda x: x["name"],
    index=initial_idx_a,
    key="edit_game_a"
)
selected_game_b = st.sidebar.selectbox(
    "キャラクターBを選択",
    options=filtered_games_b,
    format_func=lambda x: x["name"],
    index=initial_idx_b,
    key="edit_game_b"
)

game_a_id = selected_game_a["id"]
game_b_id = selected_game_b["id"]

if game_a_id == game_b_id:
    st.sidebar.error("同じキャラクターを選択できません。")
else:
    comp = get_game_comparison_by_ids(game_a_id, game_b_id)
    comp_id = comp["id"] if comp else None
    
    st.sidebar.markdown(f"### {selected_game_a['name']} vs {selected_game_b['name']}")
    
    if comp_id:
        st.sidebar.caption("制作状況・視聴回数を編集できます")
        
        with st.form("game_comparison_edit_form", clear_on_submit=False):
            short_status = st.radio(
                "📱 ショート動画ステータス",
                options=[0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["short_status"] if comp else 0,
                horizontal=True
            )
            
            short_url = st.text_input(
                "ショート動画URL",
                value=comp.get("short_video_url", "") or "",
                help="YouTube動画のURLを入力"
            )
            
            short_views = st.number_input(
                "視聴回数",
                min_value=0,
                value=comp.get("short_views", 0) or 0,
                step=1,
                key="game_short_views_input"
            )
            
            long_status = st.radio(
                "🎬 長尺動画ステータス",
                options=[0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["long_status"] if comp else 0,
                horizontal=True
            )
            
            long_url = st.text_input(
                "長尺動画URL",
                value=comp.get("long_video_url", "") or "",
                help="YouTube動画のURLを入力"
            )
            
            notes = st.text_area("メモ", value=comp["notes"] if comp else "", height=80)
            
            submitted = st.form_submit_button("💾 保存", type="primary", width='stretch')
        
        if submitted:
            from comparison_manager import update_game_comparison_url
            if short_url:
                update_game_comparison_url(comp_id, "short", short_url)
            if long_url:
                update_game_comparison_url(comp_id, "long", long_url)
            
            success = update_game_comparison_full(
                comp_id, short_status, long_status,
                short_views, 0, notes
            )
            if success:
                st.sidebar.success("✓ 更新しました")
                st.rerun()
            else:
                st.sidebar.error("✗ 更新に失敗しました")
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🗑️ レコード削除")
        
        if st.button("🗑️ このペアを削除", type="primary", key="delete_game_comparison_btn"):
            success = delete_game_comparison(comp_id)
            if success:
                st.sidebar.success("✓ 削除しました")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("✗ 削除に失敗しました")
    else:
        reverse_comp = get_game_comparison_by_ids(game_b_id, game_a_id)
        if reverse_comp:
            st.sidebar.warning(f"このペアは既に\n(キャラクターB vs キャラクターA) として登録されています。")
        
        st.sidebar.info("このペアはまだ登録されていません。")
        
        if st.button("➕ 新規追加", type="primary", width='stretch', key="add_game_comparison_btn"):
            new_id = create_game_comparison_if_not_exists(game_a_id, game_b_id)
            if new_id:
                st.sidebar.success("✓ 登録しました")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("✗ 登録に失敗しました")
    
    st.sidebar.markdown("---")
    with st.form("set_game_config_form", clear_on_submit=False):
        set_config_btn = st.form_submit_button("🎬 games_configに設定", type="primary", width='stretch')
    
    if set_config_btn:
        success, msg = set_game_comparison_pair_to_config(game_a_id, game_b_id)
        if success:
            st.session_state.game_config_success_msg = f"✓ {msg}"
            st.rerun()
        else:
            st.session_state.game_config_error_msg = f"✗ {msg}"

if st.session_state.game_config_success_msg:
    st.sidebar.success(st.session_state.game_config_success_msg)
    st.session_state.game_config_success_msg = None
if st.session_state.game_config_error_msg:
    st.sidebar.error(st.session_state.game_config_error_msg)
    st.session_state.game_config_error_msg = None

# 統計情報
st.markdown("---")
st.subheader("📊 統計情報")

total_valid = len(filtered_games_a) * len(filtered_games_b) - len([g for g in filtered_games_a if g["id"] in [gb["id"] for gb in filtered_games_b]])
short_done = 0
both_done = 0

if status_map:
    short_done = sum(1 for k, v in status_map.items() if v.get("short_status", 0) == 2)
    both_done = sum(1 for k, v in status_map.items() if v.get("short_status", 0) == 2 and v.get("long_status", 0) == 2)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("有効ペア数", total_valid)
with col_s2:
    st.metric("登録済みペア", len(status_map))
with col_s3:
    st.metric("ショート完了", short_done)
with col_s4:
    st.metric("両方完了", both_done)
