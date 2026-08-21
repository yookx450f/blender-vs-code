"""
比較マトリクス ページ

車同士の比較動画制作状況を行列形式で表示・管理する。
"""

import streamlit as st
import pandas as pd
from comparison_manager import (
    init_comparisons_table,
    get_matrix_data,
    get_comparison_by_ids,
    create_comparison_if_not_exists,
    update_comparison_full,
    set_comparison_pair_to_config,
    get_combined_status,
    is_invalid_pair
)

# DB初期化
init_comparisons_table()

st.set_page_config(page_title="📊 比較マトリクス", page_icon="📊", layout="wide")

st.title("📊 動画比較マトリクス")
st.caption("セルをクリックして制作状況を確認・編集できます")

# ============================================================
# セッション状態初期化
# ============================================================
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None


# ============================================================
# データ取得
# ============================================================
cars_df, comparisons_df = get_matrix_data()

if cars_df.empty:
    st.warning("車種データがありません。まず「📋 車種一覧」から車種を登録してください。")
    st.stop()

# 車種リストを整理
car_list = cars_df[["id", "name"]].to_dict("records")

# ============================================================
# フィルタセクション
# ============================================================
col_search, col_status, col_brand = st.columns([3, 2, 2])

with col_search:
    search_query = st.text_input("🔍 車名で絞り込み", key="matrix_search")

with col_status:
    status_filter = st.selectbox(
        "制作状況でフィルタ",
        ["全件表示", "未着手のみ", "ショート完了のみ", "両方完了のみ"]
    )

with col_brand:
    # ブランドフィルタ（車名の先頭文字で簡易分類）
    all_brands = sorted(set(row["name"].split()[0] for _, row in cars_df.iterrows()))
    brand_filter = st.selectbox("ブランドでフィルタ", ["全車種"] + all_brands)

# 車リストのフィルタリング
filtered_cars = car_list.copy()

if search_query:
    filtered_cars = [c for c in filtered_cars if search_query.lower() in c["name"].lower()]

if brand_filter != "全車種":
    filtered_cars = [c for c in filtered_cars if c["name"].startswith(brand_filter)]

if not filtered_cars:
    st.info("条件に一致する車種が見つかりませんでした。")
    st.stop()

# ============================================================
# マトリクス表示 (HTMLテーブル)
# ============================================================
st.subheader("📋 比較マトリクス")

# 無効ペアのセットを事前に計算（同じ車種 + 逆順ペア）
invalid_pairs = set()
for car in filtered_cars:
    invalid_pairs.add((car["id"], car["id"]))

# DBに登録済みのペアIDセット
registered_pairs = set()
if not comparisons_df.empty:
    for _, row in comparisons_df.iterrows():
        registered_pairs.add((row["car_a_id"], row["car_b_id"]))

# 無効ペアに逆順も追加
for car_a in filtered_cars:
    for car_b in filtered_cars:
        if (car_b["id"], car_a["id"]) in registered_pairs and car_a["id"] != car_b["id"]:
            invalid_pairs.add((car_a["id"], car_b["id"]))

# HTMLテーブルを生成（ダークテーマ対応）
def generate_matrix_html(filtered_cars, status_filter):
    # ダークテーマ用カラーパレット
    bg_header = "#2d2d2d"
    bg_row_header = "#333333"
    border_color = "#555555"
    text_color = "#e0e0e0"
    text_header = "#ffffff"
    invalid_bg = "#4a4a4a"
    invalid_text = "#888888"
    
    # ステータスカラー（ダークテーマ向けに調整）
    status_colors_dark = {
        "未着手": "#3d3d3d",      # 濃いグレー
        "制作中": "#1565c0",      # 濃い青
        "ショート完了": "#f9a825", # ダークイエロー
        "長尺制作中": "#e65100",   # ダークオレンジ
        "両方完了": "#2e7d32",     # ダークグリーン
    }
    
    html = f'''<table style="border-collapse: collapse; width: 100%; font-family: 'Meiryo UI', sans-serif;">'''
    
    # ヘッダー行 - 車種名を全表示（改行許可）
    html += f'<tr><th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; min-width: 140px; text-align: left; color: {text_header};"></th>'
    for car_b in filtered_cars:
        full_name = car_b["name"]
        html += f'<th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; min-width: 120px; text-align: center; color: {text_header}; font-size: 13px; word-wrap: break-word; white-space: pre-line;">{full_name}</th>'
    html += '</tr>'
    
    # データ行 - 車種名を全表示（改行許可）
    for car_a in filtered_cars:
        full_name_a = car_a["name"]
        html += f'<tr><td style="padding: 10px; border: 1px solid {border_color}; background: {bg_row_header}; font-weight: bold; color: {text_color}; font-size: 13px; word-wrap: break-word; white-space: pre-line;">{full_name_a}</td>'
        
        for car_b in filtered_cars:
            pair_key = (car_a["id"], car_b["id"])
            
            # 無効ペアのチェック
            if pair_key in invalid_pairs:
                reason = "同じ車種" if car_a["id"] == car_b["id"] else "重複ペア"
                html += f'<td style="padding: 10px; border: 1px solid {border_color}; background: {invalid_bg}; color: {invalid_text}; text-align: center; cursor: not-allowed; font-size: 11px;">⫘ {reason}</td>'
                continue
            
            # ステータスを取得
            comp = get_comparison_by_ids(car_a["id"], car_b["id"])
            if comp:
                short_status = comp["short_status"]
                long_status = comp["long_status"]
            else:
                short_status = 0
                long_status = 0
            
            label, _ = get_combined_status(short_status, long_status)
            cell_bg = status_colors_dark.get(label, "#3d3d3d")
            
            # テキストカラーを背景色に応じて調整
            if label == "未着手":
                text_fg = "#999999"
            else:
                text_fg = "#ffffff"
            
            # ステータスフィルタの適用
            show_cell = True
            if status_filter == "未着手のみ" and short_status != 0:
                show_cell = False
            elif status_filter == "ショート完了のみ" and not (short_status == 2 and long_status == 0):
                show_cell = False
            elif status_filter == "両方完了のみ" and not (short_status == 2 and long_status == 2):
                show_cell = False
            
            if not show_cell:
                html += f'<td style="padding: 10px; border: 1px solid {border_color}; background: #2a2a2a; text-align: center; opacity: 0.3;">-</td>'
                continue
            
            # クリック可能なセル - <a>タグでURLパラメータを伝達（Streamlitではonclickがブロックされるため）
            cell_id = f"cell_{car_a['id']}_{car_b['id']}"
            link_url = f"?car_a={car_a['id']}&car_b={car_b['id']}#edit-panel"
            html += f'''<td style="padding: 10px; border: 1px solid {border_color}; background: {cell_bg}; color: {text_fg}; text-align: center; cursor: pointer; font-size: 12px; font-weight: bold;"
                    onmouseover="this.style.border='2px solid #ffffff'"
                    onmouseout="this.style.border='1px solid {border_color}'">
                <a href="{link_url}" style="text-decoration: none; color: inherit;">{label}</a>
            </td>'''
        
        html += '</tr>'
    
    html += '</table>'
    return html


matrix_html = generate_matrix_html(filtered_cars, status_filter)
st.markdown(matrix_html, unsafe_allow_html=True)

# スクロール用JavaScriptを注入
st.markdown('''
<script>
// URLに#edit-panelがある場合、自動スクロール
window.addEventListener('load', function() {
    if (window.location.hash === '#edit-panel') {
        setTimeout(function() {
            const panel = document.getElementById('edit-panel');
            if (panel) {
                panel.scrollIntoView({behavior: 'smooth'});
            }
        }, 500);
    }
});
</script>
''', unsafe_allow_html=True)

# ============================================================
# ラジェンド（ダークテーマ対応）
# ============================================================
st.markdown("---")
legend_items = [
    ("⬜", "未着手", "#3d3d3d"),
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

# ============================================================
# セル編集パネル（サイドバー）
# ============================================================
st.sidebar.header("✏️ 比較ペア編集")
st.sidebar.caption("マトリクスセルをクリックで自動選択")

# URLパラメータから選択状態を読み取る
car_a_param = st.query_params.get("car_a", "")
car_b_param = st.query_params.get("car_b", "")

# 初期インデックスを決定
initial_idx_a = 0
initial_idx_b = 1 if len(filtered_cars) > 1 else 0

if car_a_param:
    for idx, car in enumerate(filtered_cars):
        if str(car["id"]) == str(car_a_param):
            initial_idx_a = idx
            break

if car_b_param:
    for idx, car in enumerate(filtered_cars):
        if str(car["id"]) == str(car_b_param):
            initial_idx_b = idx
            break

selected_car_a = st.sidebar.selectbox(
    "車Aを選択",
    options=filtered_cars,
    format_func=lambda x: x["name"],
    index=initial_idx_a,
    key="edit_car_a"
)
selected_car_b = st.sidebar.selectbox(
    "車Bを選択",
    options=filtered_cars,
    format_func=lambda x: x["name"],
    index=initial_idx_b,
    key="edit_car_b"
)

car_a_id = selected_car_a["id"]
car_b_id = selected_car_b["id"]

# 無効ペアのチェック
if car_a_id == car_b_id:
    st.sidebar.error("同じ車種を選択できません。")
elif is_invalid_pair(car_a_id, car_b_id):
    st.sidebar.warning(f"このペアは既に\n(車B vs 車A) として登録されています。")
else:
    # ペアが存在しない場合は自動作成
    comp_id = create_comparison_if_not_exists(car_a_id, car_b_id)
    
    if comp_id:
        comp = get_comparison_by_ids(car_a_id, car_b_id)
        
        st.sidebar.markdown(f"### {selected_car_a['name']} vs {selected_car_b['name']}")
        
        # ステータス編集フォーム
        with st.form("comparison_edit_form", clear_on_submit=False):
            short_status = st.selectbox(
                "ショート動画ステータス",
                [0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["short_status"] if comp else 0
            )
            short_url = st.text_input(
                "ショート動画URL",
                value=comp["short_video_url"] if comp else ""
            )
            short_views = st.number_input(
                "視聴回数",
                min_value=0,
                value=comp["short_views"] if comp else 0,
                step=1
            )
            
            long_status = st.selectbox(
                "長尺動画ステータス",
                [0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["long_status"] if comp else 0
            )
            long_url = st.text_input(
                "長尺動画URL",
                value=comp["long_video_url"] if comp else ""
            )
            notes = st.text_area("メモ", value=comp["notes"] if comp else "", height=80)
            
            submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
            set_config = st.form_submit_button("🎬 cars_configに設定", use_container_width=True)
        
        if submitted:
            success = update_comparison_full(
                comp_id, short_status, long_status,
                short_url, long_url, short_views, notes
            )
            if success:
                st.sidebar.success("✓ 更新しました")
                st.rerun()
            else:
                st.sidebar.error("✗ 更新に失敗しました")
        
        if set_config:
            success, msg = set_comparison_pair_to_config(car_a_id, car_b_id)
            if success:
                st.sidebar.success(f"✓ {msg}")
                st.sidebar.info("cars_config.json が更新されました。")
            else:
                st.sidebar.error(f"✗ {msg}")
    else:
        st.sidebar.error("ペアの作成に失敗しました。")

# ============================================================
# 統計情報
# ============================================================
st.markdown("---")
st.subheader("📊 統計情報")

total_valid = len(filtered_cars) * (len(filtered_cars) - 1)
comps_in_view = 0
short_done = 0
both_done = 0

if not comparisons_df.empty:
    filtered_ids = set(c["id"] for c in filtered_cars)
    view_comps = comparisons_df[
        comparisons_df["car_a_id"].isin(filtered_ids) & 
        comparisons_df["car_b_id"].isin(filtered_ids)
    ]
    total_valid_comps = len(view_comps)
    short_done = len(view_comps[view_comps["short_status"] == 2])
    both_done = len(view_comps[(view_comps["short_status"] == 2) & (view_comps["long_status"] == 2)])

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("有効ペア数", total_valid)
with col_s2:
    st.metric("登録済みペア", comps_in_view if 'comps_in_view' in dir() else 0)
with col_s3:
    st.metric("ショート完了", short_done)
with col_s4:
    st.metric("両方完了", both_done)
