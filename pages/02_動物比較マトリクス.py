"""
動物比較マトリクス ページ

動物同士の比較動画制作状況を行列形式で表示・管理する。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from comparison_manager import (
    init_animals_table,
    init_animal_comparisons_table,
    get_animal_matrix_data,
    get_animal_comparison_by_ids,
    create_animal_comparison_if_not_exists,
    update_animal_comparison_full,
    delete_animal_comparison,
    set_animal_comparison_pair_to_config,
    is_invalid_animal_pair,
)

# DB初期化
init_animals_table()
init_animal_comparisons_table()

st.set_page_config(page_title="🐾 動物比較マトリクス", page_icon="🐾", layout="wide")

# ボタンカラーを緑系に設定
st.markdown("""
<style>
[data-testid="stFormSubmitButton"],
.stButton > button,
button[kind="primary"] {
    background-color: #43A047 !important;
    color: white !important;
    border: 1px solid #43A047 !important;
}
[data-testid="stFormSubmitButton"]:hover,
.stButton > button:hover,
button[kind="primary"]:hover {
    background-color: #2E7D32 !important;
    border-color: #2E7D32 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🐾 動物比較マトリクス")
st.caption("セルをクリックして制作状況を確認・編集できます")

# セッション状態初期化
if "animal_selected_cell" not in st.session_state:
    st.session_state.animal_selected_cell = None
if "animal_config_success_msg" not in st.session_state:
    st.session_state.animal_config_success_msg = None
if "animal_config_error_msg" not in st.session_state:
    st.session_state.animal_config_error_msg = None

# データ取得
animals_df, comparisons_df = get_animal_matrix_data()

if animals_df.empty:
    st.warning("動物データがありません。まず「🐾 動物一覧」から動物を登録してください。")
    st.stop()

animal_list = animals_df[["id", "name"]].to_dict("records")

# フィルタセクション
col_search, col_status = st.columns([3, 2])

default_search = st.query_params.get("search", "")
default_status = st.query_params.get("status", "全件表示")
default_type_a = st.query_params.get("type_a", "全タイプ")
default_type_b = st.query_params.get("type_b", "全タイプ")

with col_search:
    search_query = st.text_input("🔍 動物名で絞り込み", value=default_search, key="animal_matrix_search")

with col_status:
    status_options = ["全件表示", "未着手のみ", "登録済・未着手のみ", "制作中のみ", "ショート完了のみ", "長尺制作中のみ", "両方完了のみ"]
    default_status_idx = status_options.index(default_status) if default_status in status_options else 0
    status_filter = st.selectbox(
        "制作状況でフィルタ",
        status_options,
        index=default_status_idx
    )

# 動物タイプフィルタ
if "animal_type" in animals_df.columns:
    type_counts = animals_df["animal_type"].value_counts()
    all_types = list(type_counts.index.tolist())
    col_type_a, col_type_b = st.columns([1, 1])
    with col_type_a:
        type_options_a = ["全タイプ"] + all_types
        default_type_a_idx = type_options_a.index(default_type_a) if default_type_a in type_options_a else 0
        type_filter_a = st.selectbox("🐾 動物A - タイプ", type_options_a, index=default_type_a_idx)
    with col_type_b:
        type_options_b = ["全タイプ"] + all_types
        default_type_b_idx = type_options_b.index(default_type_b) if default_type_b in type_options_b else 0
        type_filter_b = st.selectbox("🐾 動物B - タイプ", type_options_b, index=default_type_b_idx)
else:
    type_filter_a = "全タイプ"
    type_filter_b = "全タイプ"

# フィルタ状態をURLパラメータに保存
st.query_params["search"] = search_query
st.query_params["status"] = status_filter
st.query_params["type_a"] = type_filter_a
st.query_params["type_b"] = type_filter_b

# 動物リストのフィルタリング
filtered_animals_a = animal_list.copy()
if search_query:
    filtered_animals_a = [a for a in filtered_animals_a if search_query.lower() in a["name"].lower()]
if type_filter_a != "全タイプ" and "animal_type" in animals_df.columns:
    matching_ids_a = set(row["id"] for _, row in animals_df.iterrows() if row.get("animal_type") == type_filter_a)
    filtered_animals_a = [a for a in filtered_animals_a if a["id"] in matching_ids_a]

filtered_animals_b = animal_list.copy()
if search_query:
    filtered_animals_b = [a for a in filtered_animals_b if search_query.lower() in a["name"].lower()]
if type_filter_b != "全タイプ" and "animal_type" in animals_df.columns:
    matching_ids_b = set(row["id"] for _, row in animals_df.iterrows() if row.get("animal_type") == type_filter_b)
    filtered_animals_b = [a for a in filtered_animals_b if a["id"] in matching_ids_b]

if not filtered_animals_a or not filtered_animals_b:
    st.info("条件に一致する動物が見つかりませんでした。")
    st.stop()

# 無効ペアのセットを事前に計算
invalid_pairs = set()
for animal_a in filtered_animals_a:
    for animal_b in filtered_animals_b:
        if animal_a["id"] == animal_b["id"]:
            invalid_pairs.add((animal_a["id"], animal_b["id"]))

# DBに登録済みのペアIDセット
registered_pairs = set()
if not comparisons_df.empty:
    for _, row in comparisons_df.iterrows():
        registered_pairs.add((row["animal_a_id"], row["animal_b_id"]))

# 無効ペアに逆順も追加
for animal_a in filtered_animals_a:
    for animal_b in filtered_animals_b:
        if (animal_b["id"], animal_a["id"]) in registered_pairs and animal_a["id"] != animal_b["id"]:
            invalid_pairs.add((animal_a["id"], animal_b["id"]))

# ステータスラベル取得関数（車用のget_combined_statusと同じロジック）
def get_animal_combined_status(short_status, long_status):
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

def generate_animal_matrix_html(filtered_animals_a, filtered_animals_b):
    bg_header = "#2d2d2d"
    bg_row_header = "#333333"
    border_color = "#555555"
    text_color = "#e0e0e0"
    text_header = "#ffffff"
    
    status_colors_dark = {
        "未着手": "#3d3d3d",
        "登録済・未着手": "#1a237e",
        "制作中": "#1565c0",
        "ショート完了": "#f9a825",
        "長尺制作中": "#e65100",
        "両方完了": "#2e7d32",
    }
    
    html = f'''<div style="overflow: auto; max-height: 75vh;"><table style="border-collapse: separate; border-spacing: 0; width: 100%; font-family: 'Meiryo UI', sans-serif;">'''
    
    # ヘッダー行
    html += f'<tr><th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; min-width: 120px; color: {text_header}; position: sticky; top: 0; z-index: 20;"></th>'
    for animal_b in filtered_animals_b:
        html += f'<th style="padding: 8px; border: 1px solid {border_color}; background: {bg_header}; text-align: center; color: {text_header}; font-size: 12px; position: sticky; top: 0; z-index: 10;">{animal_b["name"]}</th>'
    html += '</tr>'
    
    # データ行
    for animal_a in filtered_animals_a:
        html += f'<tr><td style="padding: 4px 6px; border: 1px solid {border_color}; background: {bg_row_header}; font-weight: bold; color: {text_color}; font-size: 12px; position: sticky; left: 0; z-index: 5;">{animal_a["name"]}</td>'
        
        for animal_b in filtered_animals_b:
            pair_key = (animal_a["id"], animal_b["id"])
            
            if pair_key in invalid_pairs:
                if status_filter == "全件表示":
                    reason = "同じ動物" if animal_a["id"] == animal_b["id"] else "重複ペア"
                    html += f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: #4a4a4a; color: #888888; text-align: center; font-size: 11px;">⫘ {reason}</td>'
                else:
                    html += f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: transparent;"></td>'
                continue
            
            comp = get_animal_comparison_by_ids(animal_a["id"], animal_b["id"])
            has_registration = comp is not None
            
            if comp:
                short_status = comp["short_status"]
                long_status = comp["long_status"]
            else:
                short_status = 0
                long_status = 0
            
            label, _ = get_animal_combined_status(short_status, long_status)
            
            if has_registration and label == "未着手":
                cell_bg = status_colors_dark.get("登録済・未着手", "#1a237e")
                text_fg = "#9fa8da"
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
                html += f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: transparent;"></td>'
                continue
            
            link_url = f"?animal_a={animal_a['id']}&animal_b={animal_b['id']}#edit-panel"
            html += f'''<td style="padding: 4px 6px; border: 1px solid {border_color}; background: {cell_bg}; color: {text_fg}; text-align: center; cursor: pointer; font-size: 12px;">
                <a href="{link_url}" style="text-decoration: none; color: inherit;">{label}</a>
            </td>'''
        
        html += '</tr>'
    
    html += '</table></div>'
    return html

matrix_html = generate_animal_matrix_html(filtered_animals_a, filtered_animals_b)
st.markdown(matrix_html, unsafe_allow_html=True)

# ラジェンド
st.markdown("---")
legend_items = [
    ("⬜", "未着手（登録なし）", "#3d3d3d"),
    ("🔲", "登録済・未着手", "#1a237e"),
    ("🔵", "制作中", "#1565c0"),
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
st.sidebar.header("✏️ 動物比較ペア編集")

car_a_param = st.query_params.get("animal_a", "")
car_b_param = st.query_params.get("animal_b", "")

initial_idx_a = 0
initial_idx_b = 1 if len(filtered_animals_b) > 1 else 0

if car_a_param:
    for idx, animal in enumerate(filtered_animals_a):
        if str(animal["id"]) == str(car_a_param):
            initial_idx_a = idx
            break

if car_b_param:
    for idx, animal in enumerate(filtered_animals_b):
        if str(animal["id"]) == str(car_b_param):
            initial_idx_b = idx
            break

selected_animal_a = st.sidebar.selectbox(
    "動物Aを選択",
    options=filtered_animals_a,
    format_func=lambda x: x["name"],
    index=initial_idx_a,
    key="edit_animal_a"
)
selected_animal_b = st.sidebar.selectbox(
    "動物Bを選択",
    options=filtered_animals_b,
    format_func=lambda x: x["name"],
    index=initial_idx_b,
    key="edit_animal_b"
)

animal_a_id = selected_animal_a["id"]
animal_b_id = selected_animal_b["id"]

if animal_a_id == animal_b_id:
    st.sidebar.error("同じ動物を選択できません。")
else:
    comp = get_animal_comparison_by_ids(animal_a_id, animal_b_id)
    comp_id = comp["id"] if comp else None
    
    st.sidebar.markdown(f"### {selected_animal_a['name']} vs {selected_animal_b['name']}")
    
    if comp_id:
        st.sidebar.caption("制作状況・視聴回数を編集できます")
        
        with st.form("animal_comparison_edit_form", clear_on_submit=False):
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
                key="animal_short_views_input"
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
            
            submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
        
        if submitted:
            from comparison_manager import update_animal_comparison_url
            if short_url:
                update_animal_comparison_url(comp_id, "short", short_url)
            if long_url:
                update_animal_comparison_url(comp_id, "long", long_url)
            
            success = update_animal_comparison_full(
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
        
        if st.button("🗑️ このペアを削除", type="primary", key="delete_animal_comparison_btn"):
            success = delete_animal_comparison(comp_id)
            if success:
                st.sidebar.success("✓ 削除しました")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("✗ 削除に失敗しました")
    else:
        reverse_comp = get_animal_comparison_by_ids(animal_b_id, animal_a_id)
        if reverse_comp:
            st.sidebar.warning(f"このペアは既に\n(動物B vs 動物A) として登録されています。")
        
        st.sidebar.info("このペアはまだ登録されていません。")
        
        if st.button("➕ 新規追加", type="primary", use_container_width=True, key="add_animal_comparison_btn"):
            new_id = create_animal_comparison_if_not_exists(animal_a_id, animal_b_id)
            if new_id:
                st.sidebar.success("✓ 登録しました")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("✗ 登録に失敗しました")
    
    st.sidebar.markdown("---")
    with st.form("set_animal_config_form", clear_on_submit=False):
        set_config_btn = st.form_submit_button("🎬 animals_configに設定", type="primary", use_container_width=True)
    
    if set_config_btn:
        success, msg = set_animal_comparison_pair_to_config(animal_a_id, animal_b_id)
        if success:
            st.session_state.animal_config_success_msg = f"✓ {msg}"
            st.rerun()
        else:
            st.session_state.animal_config_error_msg = f"✗ {msg}"

if st.session_state.animal_config_success_msg:
    st.sidebar.success(st.session_state.animal_config_success_msg)
    st.session_state.animal_config_success_msg = None
if st.session_state.animal_config_error_msg:
    st.sidebar.error(st.session_state.animal_config_error_msg)
    st.session_state.animal_config_error_msg = None

# 統計情報
st.markdown("---")
st.subheader("📊 統計情報")

total_valid = len(filtered_animals_a) * len(filtered_animals_b)
short_done = 0
both_done = 0

if not comparisons_df.empty:
    filtered_ids_a = set(a["id"] for a in filtered_animals_a)
    filtered_ids_b = set(a["id"] for a in filtered_animals_b)
    view_comps = comparisons_df[
        comparisons_df["animal_a_id"].isin(filtered_ids_a) &
        comparisons_df["animal_b_id"].isin(filtered_ids_b)
    ]
    short_done = len(view_comps[view_comps["short_status"] == 2])
    both_done = len(view_comps[(view_comps["short_status"] == 2) & (view_comps["long_status"] == 2)])

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("有効ペア数", total_valid)
with col_s2:
    st.metric("登録済みペア", len(comparisons_df) if not comparisons_df.empty else 0)
with col_s3:
    st.metric("ショート完了", short_done)
with col_s4:
    st.metric("両方完了", both_done)
