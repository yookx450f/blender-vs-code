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
    delete_comparison,
    set_comparison_pair_to_config,
    get_combined_status,
    is_invalid_pair,
    bulk_update_all_stats,
)
from youtube_stats_fetcher import (
    get_youtube_api_key,
    fetch_stats_for_comparisons,
)

# DB初期化
init_comparisons_table()

st.set_page_config(page_title="📊 比較マトリクス", page_icon="📊", layout="wide")

# ボタンカラーを青系に設定（Streamlitの内部スタイルを上書き）
st.markdown("""
<style>
/* Streamlit v1.28+ 対応 */
[data-testid="stFormSubmitButton"],
.stButton > button,
button[kind="primary"] {
    background-color: #1E88E5 !important;
    color: white !important;
    border: 1px solid #1E88E5 !important;
}
[data-testid="stFormSubmitButton"]:hover,
.stButton > button:hover,
button[kind="primary"]:hover {
    background-color: #1565C0 !important;
    border-color: #1565C0 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 動画比較マトリクス")
st.caption("セルをクリックして制作状況を確認・編集できます")

# ============================================================
# セッション状態初期化
# ============================================================
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
if "config_success_msg" not in st.session_state:
    st.session_state.config_success_msg = None
if "config_error_msg" not in st.session_state:
    st.session_state.config_error_msg = None
if "youtube_update_result" not in st.session_state:
    st.session_state.youtube_update_result = None


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
col_search, col_status = st.columns([3, 2])

# URLパラメータからフィルタ状態を復元（絞り込み条件を保持）
default_search = st.query_params.get("search", "")
default_status = st.query_params.get("status", "全件表示")
default_type_a = st.query_params.get("type_a", "全タイプ")
default_type_b = st.query_params.get("type_b", "全タイプ")

with col_search:
    search_query = st.text_input("🔍 車名で絞り込み", value=default_search, key="matrix_search")

with col_status:
    status_options = ["全件表示", "未着手のみ", "登録済・未着手のみ", "制作中のみ", "ショート完了のみ", "長尺制作中のみ", "両方完了のみ"]
    default_status_idx = status_options.index(default_status) if default_status in status_options else 0
    status_filter = st.selectbox(
        "制作状況でフィルタ",
        status_options,
        index=default_status_idx
    )

# 車種タイプフィルタ（登録件数の多い順に並べる）
type_counts = cars_df["car_type"].value_counts()
all_types = list(type_counts.index.tolist())
col_type_a, col_type_b = st.columns([1, 1])
with col_type_a:
    type_options_a = ["全タイプ"] + all_types
    default_type_a_idx = type_options_a.index(default_type_a) if default_type_a in type_options_a else 0
    type_filter_a = st.selectbox("🚗 車A - タイプ", type_options_a, index=default_type_a_idx)
with col_type_b:
    type_options_b = ["全タイプ"] + all_types
    default_type_b_idx = type_options_b.index(default_type_b) if default_type_b in type_options_b else 0
    type_filter_b = st.selectbox("🚙 車B - タイプ", type_options_b, index=default_type_b_idx)

# フィルタ状態をURLパラメータに保存
st.query_params["search"] = search_query
st.query_params["status"] = status_filter
st.query_params["type_a"] = type_filter_a
st.query_params["type_b"] = type_filter_b

# 車リストのフィルタリング（車A用と車B用に分離）
filtered_cars_a = car_list.copy()
if search_query:
    filtered_cars_a = [c for c in filtered_cars_a if search_query.lower() in c["name"].lower()]
if type_filter_a != "全タイプ":
    # cars_dfからcar_typeを取得してフィルタ
    matching_ids_a = set(row["id"] for _, row in cars_df.iterrows() if row.get("car_type") == type_filter_a)
    filtered_cars_a = [c for c in filtered_cars_a if c["id"] in matching_ids_a]

filtered_cars_b = car_list.copy()
if search_query:
    filtered_cars_b = [c for c in filtered_cars_b if search_query.lower() in c["name"].lower()]
if type_filter_b != "全タイプ":
    matching_ids_b = set(row["id"] for _, row in cars_df.iterrows() if row.get("car_type") == type_filter_b)
    filtered_cars_b = [c for c in filtered_cars_b if c["id"] in matching_ids_b]

if not filtered_cars_a or not filtered_cars_b:
    st.info("条件に一致する車種が見つかりませんでした。")
    st.stop()

# ============================================================
# マトリクス表示 (HTMLテーブル)
# ============================================================
st.subheader("📋 比較マトリクス")

# 無効ペアのセットを事前に計算（同じ車種 + 逆順ペア）
invalid_pairs = set()
for car in filtered_cars_a:
    invalid_pairs.add((car["id"], car["id"]))
for car in filtered_cars_b:
    invalid_pairs.add((car["id"], car["id"]))

# DBに登録済みのペアIDセット
registered_pairs = set()
if not comparisons_df.empty:
    for _, row in comparisons_df.iterrows():
        registered_pairs.add((row["car_a_id"], row["car_b_id"]))

# 無効ペアに逆順も追加
for car_a in filtered_cars_a:
    for car_b in filtered_cars_b:
        if (car_b["id"], car_a["id"]) in registered_pairs and car_a["id"] != car_b["id"]:
            invalid_pairs.add((car_a["id"], car_b["id"]))

# フィルタ条件に合致する行・列のID集合を事前に計算
def compute_active_ids_for_filter(filtered_cars_a, filtered_cars_b, status_filter, invalid_pairs):
    """フィルタ条件に合致する車A/車BのID集合を返す。全件表示の場合はNoneを返す。"""
    if status_filter == "全件表示":
        return None, None
    
    active_a_ids = set()
    active_b_ids = set()
    
    for car_a in filtered_cars_a:
        for car_b in filtered_cars_b:
            pair_key = (car_a["id"], car_b["id"])
            if pair_key in invalid_pairs:
                continue
            
            comp = get_comparison_by_ids(car_a["id"], car_b["id"])
            has_registration = comp is not None
            if comp:
                short_status = comp["short_status"]
                long_status = comp["long_status"]
            else:
                short_status = 0
                long_status = 0
            
            label, _ = get_combined_status(short_status, long_status)
            
            # フィルタ条件に合致するか判定
            matches = False
            if status_filter == "未着手のみ" and label == "未着手":
                matches = True
            elif status_filter == "登録済・未着手のみ" and has_registration and label == "未着手":
                matches = True
            elif status_filter == "制作中のみ" and label == "制作中":
                matches = True
            elif status_filter == "ショート完了のみ" and label == "ショート完了":
                matches = True
            elif status_filter == "長尺制作中のみ" and label == "長尺制作中":
                matches = True
            elif status_filter == "両方完了のみ" and label == "両方完了":
                matches = True
            
            if matches:
                active_a_ids.add(car_a["id"])
                active_b_ids.add(car_b["id"])
    
    return active_a_ids, active_b_ids


# HTMLテーブルを生成（ダークテーマ対応）
def generate_matrix_html(filtered_cars_a, filtered_cars_b, status_filter, invalid_pairs, search_query, type_filter_a, type_filter_b, active_car_a_ids=None, active_car_b_ids=None):
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
        "未着手": "#3d3d3d",         # 濃いグレー（登録なし）
        "登録済・未着手": "#1a237e", # 紺色（DBに登録済みだが未着手）
        "制作中": "#1565c0",         # 濃い青
        "ショート完了": "#f9a825",   # ダークイエロー
        "長尺制作中": "#e65100",     # ダークオレンジ
        "両方完了": "#2e7d32",       # ダークグリーン
    }
    
    html = f'''<div style="overflow: auto; max-height: 75vh;"><table style="border-collapse: separate; border-spacing: 0; width: 100%; font-family: 'Meiryo UI', sans-serif; table-layout: fixed;">'''
    
    # ヘッダー行 - 車B（列）をヘッダーに表示（フィルタ中は有効な列のみ）
    # position: sticky でスクロール時にも常に表示されるようにする
    html += f'<tr><th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; width: 140px; text-align: left; color: {text_header}; position: sticky; top: 0; left: 0; z-index: 20; min-width: 140px;"></th>'
    for car_b in filtered_cars_b:
        if active_car_b_ids is not None and car_b["id"] not in active_car_b_ids:
            continue
        full_name = car_b["name"]
        html += f'<th style="padding: 10px; border: 1px solid {border_color}; background: {bg_header}; width: 100px; text-align: center; color: {text_header}; font-size: 13px; word-wrap: break-word; white-space: pre-line; position: sticky; top: 0; z-index: 10;">{full_name}</th>'
    html += '</tr>'
    
    # データ行 - 車A（行）を左側に表示
    for car_a in filtered_cars_a:
        # フィルタ中は有効な行のみ表示
        if active_car_a_ids is not None and car_a["id"] not in active_car_a_ids:
            continue
        
        full_name_a = car_a["name"]
        html += f'<tr><td style="padding: 4px 6px; border: 1px solid {border_color}; background: {bg_row_header}; font-weight: bold; color: {text_color}; font-size: 12px; word-wrap: break-word; white-space: pre-line; position: sticky; left: 0; z-index: 5;">{full_name_a}</td>'
        
        for car_b in filtered_cars_b:
            # フィルタ中は有効な列のみ表示
            if active_car_b_ids is not None and car_b["id"] not in active_car_b_ids:
                continue
            pair_key = (car_a["id"], car_b["id"])
            
            # 無効ペアのチェック（フィルタ中は空白に）
            if pair_key in invalid_pairs:
                if status_filter == "全件表示":
                    reason = "同じ車種" if car_a["id"] == car_b["id"] else "重複ペア"
                    html += f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: {invalid_bg}; color: {invalid_text}; text-align: center; cursor: not-allowed; font-size: 11px;">⫘ {reason}</td>'
                else:
                    html += f'<td style="padding: 4px 6px; border: 1px solid {border_color}; background: transparent;"></td>'
                continue
            
            # ステータスを取得
            comp = get_comparison_by_ids(car_a["id"], car_b["id"])
            has_registration = comp is not None
            if comp:
                short_status = comp["short_status"]
                long_status = comp["long_status"]
                short_views = comp.get("short_views", 0)
                long_views = comp.get("long_views", 0)
            else:
                short_status = 0
                long_status = 0
                short_views = 0
                long_views = 0
            
            label, _ = get_combined_status(short_status, long_status)
            
            # DBに登録済みで未着手の場合は紺色で区別
            if has_registration and label == "未着手":
                cell_bg = status_colors_dark.get("登録済・未着手", "#1a237e")
                text_fg = "#9fa8da"
            else:
                cell_bg = status_colors_dark.get(label, "#3d3d3d")
                text_fg = "#999999" if label == "未着手" else "#ffffff"
            
            # ステータスフィルタの適用（get_combined_statusのラベルで判定）
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
            
            # クリック可能なセル - 上段: 長尺視聴回数 / 下段: ショート視聴回数（2段表示）
            # ツールチップで高評価・コメント数を表示
            cell_id = f"cell_{car_a['id']}_{car_b['id']}"
            link_url = f"?car_a={car_a['id']}&car_b={car_b['id']}&search={search_query}&status={status_filter}&type_a={type_filter_a}&type_b={type_filter_b}#edit-panel"
            long_views_display = f"{long_views:,}" if long_views > 0 else "-"
            short_views_display = f"{short_views:,}" if short_views > 0 else "-"
            
            # ツールチップ用データ（高評価・コメント数）
            short_likes_val = comp.get("short_likes", 0) or 0 if comp else 0
            short_comments_val = comp.get("short_comments", 0) or 0 if comp else 0
            long_likes_val = comp.get("long_likes", 0) or 0 if comp else 0
            long_comments_val = comp.get("long_comments", 0) or 0 if comp else 0
            
            tooltip_title = ""
            if has_registration:
                tooltip_title = f"🎬 長尺: 👁{long_views:,} 👍{long_likes_val:,} 💬{long_comments_val:,}<br>📱 ショート: 👁{short_views:,} 👍{short_likes_val:,} 💬{short_comments_val:,}"
            
            html += f'''<td style="padding: 4px 6px; border: 1px solid {border_color}; background: {cell_bg}; color: {text_fg}; text-align: center; cursor: pointer; font-size: 12px; font-weight: bold;"
                    title="{tooltip_title}"
                    onmouseover="this.style.border='2px solid #ffffff'"
                    onmouseout="this.style.border='1px solid {border_color}'">
                <a href="{link_url}" style="text-decoration: none; color: inherit;">
                    <div style="font-size: 12px; line-height: 1.2; font-weight: bold;">{long_views_display}</div>
                    <div style="font-size: 12px; line-height: 1.2; font-weight: bold;">{short_views_display}</div>
                </a>
            </td>'''
        
        html += '</tr>'
    
    html += '</table></div>'
    return html


# 有効な行・列のID集合を計算
active_a_ids, active_b_ids = compute_active_ids_for_filter(filtered_cars_a, filtered_cars_b, status_filter, invalid_pairs)

matrix_html = generate_matrix_html(filtered_cars_a, filtered_cars_b, status_filter, invalid_pairs, search_query, type_filter_a, type_filter_b, active_a_ids, active_b_ids)
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

# ============================================================
# YouTube API キー設定セクション（サイドバー上部）
# ============================================================
st.sidebar.header("🔑 YouTube API 設定")

api_key = get_youtube_api_key()
if api_key:
    masked_key = api_key[:5] + "..." + api_key[-4:]
    st.sidebar.success(f"APIキー設定済み: {masked_key}")
else:
    new_key = st.sidebar.text_input(
        "YouTube Data API v3 キー",
        type="password",
        help="Google Cloud Console で取得したAPIキーを入力してください。"
    )
    if new_key:
        # .env ファイルに保存
        import os
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
        env_path = os.path.normpath(env_path)
        try:
            # 既存の.envを読み込み、APIキーを更新または追加
            existing_lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()
            
            # YOUTUBE_API_KEY行がある場合は置き換え
            found = False
            new_lines = []
            for line in existing_lines:
                if line.startswith("YOUTUBE_API_KEY="):
                    new_lines.append(f"YOUTUBE_API_KEY={new_key}\n")
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(f"\n# YouTube Data API v3 キー\nYOUTUBE_API_KEY={new_key}\n")
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            st.sidebar.success("✓ APIキーを保存しました")
        except Exception as e:
            st.sidebar.error(f"✗ 保存失敗: {e}")

st.sidebar.markdown("---")

# ============================================================
# YouTube 統計一括更新ボタン
# ============================================================
st.sidebar.header("📊 YouTube 統計更新")
st.sidebar.caption("登録済みの動画URLから統計データを自動取得します")

if st.button("🔄 全ペアの統計を一括更新", type="primary", use_container_width=True, key="youtube_bulk_update"):
    if not api_key:
        st.sidebar.error("✗ YouTube APIキーが設定されていません。")
    else:
        try:
            # DBから全比較ペアを取得（動画URLがあるもののみ）
            from comparison_manager import get_all_comparisons
            all_comps_df = get_all_comparisons()
            
            # 動画URLが登録されているペアのみをフィルタ
            valid_comps = []
            for _, row in all_comps_df.iterrows():
                has_url = (row.get("short_video_url", "") or "").strip() or \
                          (row.get("long_video_url", "") or "").strip()
                if has_url:
                    valid_comps.append(dict(row))
            
            if not valid_comps:
                st.sidebar.warning("動画URLが登録されたペアがありません。")
            else:
                # 処理中のログをsession_stateに保存（再描画中表示維持用）
                st.session_state.youtube_update_result = {
                    "success": 0,
                    "failed": 0,
                    "errors": [],
                    "log": ["⏳ YouTubeから統計データを取得中..."],
                }
                
                # YouTube API で統計を取得
                result = fetch_stats_for_comparisons(valid_comps)
                
                # DBに保存
                save_result = bulk_update_all_stats(valid_comps, result["stats"])
                
                st.session_state.youtube_update_result = {
                    "success": save_result["success"],
                    "failed": save_result["failed"],
                    "errors": result.get("errors", []) + save_result.get("errors", []),
                    "log": result.get("log", []),
                }
                
                import time
                time.sleep(1)
                st.rerun()
        
        except RuntimeError as e:
            err_msg = str(e)
            if "quota" in err_msg.lower():
                st.sidebar.error("✗ APIクォータを超過しました。明日再試行してください。")
            else:
                st.session_state.youtube_update_result = {
                    "success": 0,
                    "failed": 0,
                    "errors": [err_msg],
                    "log": [f"❌ 更新失敗: {err_msg}"],
                }
                import time
                time.sleep(2)
                st.rerun()
        except Exception as e:
            st.session_state.youtube_update_result = {
                "success": 0,
                "failed": 0,
                "errors": [str(e)],
                "log": [f"❌ 予期しないエラー: {e}"],
            }
            import time
            time.sleep(2)
            st.rerun()

# 更新結果表示（ログ付き）
if st.session_state.youtube_update_result:
    res = st.session_state.youtube_update_result
    
    # 成功/失敗サマリー
    succ = res.get("success", 0)
    fail = res.get("failed", 0)
    if succ > 0 or fail > 0:
        st.sidebar.success(f"✓ 更新完了: {succ}件成功, {fail}件失敗")
    
    # エラー詳細表示（エクスパンダー）
    err_list = res.get("errors", [])
    if err_list:
        with st.sidebar.expander(f"⚠️ エラー {len(err_list)}件発生 (クリックで展開)", expanded=True):
            for err_msg in err_list:
                # タプル形式 (comp_id, message) の場合も対応
                if isinstance(err_msg, tuple):
                    comp_id, message = err_msg
                    st.error(f"comp_id={comp_id}: {message}")
                else:
                    st.error(str(err_msg))
    
    # ログ表示（エクスパンダー）
    log_entries = res.get("log", [])
    if log_entries:
        with st.sidebar.expander(f"📋 処理ログ ({len(log_entries)}行)", expanded=True):
            for entry in log_entries:
                st.text(entry)
    
    st.session_state.youtube_update_result = None

st.sidebar.markdown("---")

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
initial_idx_b = 1 if len(filtered_cars_b) > 1 else 0

if car_a_param:
    for idx, car in enumerate(filtered_cars_a):
        if str(car["id"]) == str(car_a_param):
            initial_idx_a = idx
            break

if car_b_param:
    for idx, car in enumerate(filtered_cars_b):
        if str(car["id"]) == str(car_b_param):
            initial_idx_b = idx
            break

selected_car_a = st.sidebar.selectbox(
    "車Aを選択",
    options=filtered_cars_a,
    format_func=lambda x: x["name"],
    index=initial_idx_a,
    key="edit_car_a"
)
selected_car_b = st.sidebar.selectbox(
    "車Bを選択",
    options=filtered_cars_b,
    format_func=lambda x: x["name"],
    index=initial_idx_b,
    key="edit_car_b"
)

car_a_id = selected_car_a["id"]
car_b_id = selected_car_b["id"]

# 無効ペアのチェック
if car_a_id == car_b_id:
    st.sidebar.error("同じ車種を選択できません。")
else:
    # DBから既存レコードを取得（自動作成はしない）
    comp = get_comparison_by_ids(car_a_id, car_b_id)
    comp_id = comp["id"] if comp else None
    
    st.sidebar.markdown(f"### {selected_car_a['name']} vs {selected_car_b['name']}")
    
    if comp_id:
        # レコードが存在する場合 → 編集フォーム表示
        st.sidebar.caption("制作状況・視聴回数を編集できます")
        
        with st.form("comparison_edit_form", clear_on_submit=False):
            # --- ショート動画 ---
            short_status = st.radio(
                "📱 ショート動画ステータス",
                options=[0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["short_status"] if comp else 0,
                horizontal=True
            )
            
            # ショート動画URL入力
            short_url = st.text_input(
                "ショート動画URL",
                value=comp.get("short_video_url", "") or "",
                help="YouTube動画のURLを入力（統計自動取得用）"
            )
            
            # ショート動画統計データ
            st.caption("📊 ショート動画統計")
            col_sv, col_sl, col_sc = st.columns(3)
            with col_sv:
                short_views = st.number_input(
                    "視聴",
                    min_value=0,
                    value=comp.get("short_views", 0) or 0,
                    step=1,
                    key="short_views_input"
                )
            with col_sl:
                short_likes = st.number_input(
                    "高評価",
                    min_value=0,
                    value=comp.get("short_likes", 0) or 0,
                    step=1,
                    key="short_likes_input"
                )
            with col_sc:
                short_comments = st.number_input(
                    "コメント",
                    min_value=0,
                    value=comp.get("short_comments", 0) or 0,
                    step=1,
                    key="short_comments_input"
                )
            
            # --- 長尺動画 ---
            long_status = st.radio(
                "🎬 長尺動画ステータス",
                options=[0, 1, 2],
                format_func=lambda x: ["未着手", "制作中", "公開済み"][x],
                index=comp["long_status"] if comp else 0,
                horizontal=True
            )
            
            # 長尺動画URL入力
            long_url = st.text_input(
                "長尺動画URL",
                value=comp.get("long_video_url", "") or "",
                help="YouTube動画のURLを入力（統計自動取得用）"
            )
            
            # 長尺動画統計データ
            st.caption("📊 長尺動画統計")
            col_lv, col_ll, col_lc = st.columns(3)
            with col_lv:
                long_views = st.number_input(
                    "視聴",
                    min_value=0,
                    value=comp.get("long_views", 0) or 0,
                    step=1,
                    key="long_views_input"
                )
            with col_ll:
                long_likes = st.number_input(
                    "高評価",
                    min_value=0,
                    value=comp.get("long_likes", 0) or 0,
                    step=1,
                    key="long_likes_input"
                )
            with col_lc:
                long_comments = st.number_input(
                    "コメント",
                    min_value=0,
                    value=comp.get("long_comments", 0) or 0,
                    step=1,
                    key="long_comments_input"
                )
            
            # 最終更新日時表示
            stats_updated = comp.get("stats_updated_at")
            if stats_updated:
                st.caption(f"🕐 統計最終更新: {stats_updated}")
            
            notes = st.text_area("メモ", value=comp["notes"] if comp else "", height=80)
            
            submitted = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
        
        if submitted:
            # URLも同時に更新
            from comparison_manager import update_comparison_url
            if short_url:
                update_comparison_url(comp_id, "short", short_url)
            if long_url:
                update_comparison_url(comp_id, "long", long_url)
            
            success = update_comparison_full(
                comp_id, short_status, long_status,
                short_views, long_views, notes,
                short_likes, short_comments, long_likes, long_comments
            )
            if success:
                st.sidebar.success("✓ 更新しました")
                st.rerun()
            else:
                st.sidebar.error("✗ 更新に失敗しました")
        
        # 削除セクション
        st.sidebar.markdown("---")
        st.sidebar.subheader("🗑️ レコード削除")
        st.sidebar.caption("この比較ペアをデータベースから削除します")
        
        # 削除ボタンは幅を狭くして誤クリックを防ぐ
        st.sidebar.markdown("""
        <style>
        .delete-btn-container {
            display: inline-block;
            max-width: 180px;
        }
        .delete-btn-container button {
            background-color: #c62828 !important;
            border-color: #c62828 !important;
        }
        .delete-btn-container button:hover {
            background-color: #b71c1c !important;
            border-color: #b71c1c !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        delete_cols = st.sidebar.columns([1, 2])
        with delete_cols[0]:
            if st.button("🗑️ このペアを削除", type="primary", key="delete_comparison_btn"):
                success = delete_comparison(comp_id)
                if success:
                    st.sidebar.success("✓ 削除しました")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.sidebar.error("✗ 削除に失敗しました")
    else:
        # レコードが存在しない場合 → 未登録メッセージ + 新規追加ボタン
        # 逆順ペアがある場合は警告も表示
        reverse_comp = get_comparison_by_ids(car_b_id, car_a_id)
        if reverse_comp:
            st.sidebar.warning(f"このペアは既に\n(車B vs 車A) として登録されています。")
        
        st.sidebar.info("このペアはまだ登録されていません。")
        
        if st.button("➕ 新規追加", type="primary", use_container_width=True, key="add_comparison_btn"):
            new_id = create_comparison_if_not_exists(car_a_id, car_b_id)
            if new_id:
                st.sidebar.success("✓ 登録しました")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.sidebar.error("✗ 登録に失敗しました")
    
    # 🎬 cars_configに設定ボタン（常に表示）
    st.sidebar.markdown("---")
    with st.form("set_config_form", clear_on_submit=False):
        set_config_btn = st.form_submit_button("🎬 cars_configに設定", type="primary", use_container_width=True)
    
    if set_config_btn:
        success, msg = set_comparison_pair_to_config(car_a_id, car_b_id)
        if success:
            st.session_state.config_success_msg = f"✓ {msg}"
            st.rerun()
        else:
            st.session_state.config_error_msg = f"✗ {msg}"

# 設定結果メッセージ表示
if st.session_state.config_success_msg:
    st.sidebar.success(st.session_state.config_success_msg)
    st.sidebar.info("cars_config.json が更新されました。")
    st.session_state.config_success_msg = None
if st.session_state.config_error_msg:
    st.sidebar.error(st.session_state.config_error_msg)
    st.session_state.config_error_msg = None

# ============================================================
# 選択車種の諸元比較表示
# ============================================================
car_a_row = cars_df[cars_df["id"] == car_a_id].iloc[0] if not cars_df.empty else None
car_b_row = cars_df[cars_df["id"] == car_b_id].iloc[0] if not cars_df.empty else None

if car_a_row is not None and car_b_row is not None:
    st.markdown("---")
    st.subheader("📐 選択車種の諸元比較")
    
    # HTMLテーブルで車A一行・車B一行（項目を列に転置）
    # mirror_offset_mm の値を取得（存在しない場合は空文字）
    mirror_a = car_a_row.get('mirror_offset_mm', '') or ''
    mirror_b = car_b_row.get('mirror_offset_mm', '') or ''
    mirror_a_display = f"{int(mirror_a):,}" if mirror_a else "-"
    mirror_b_display = f"{int(mirror_b):,}" if mirror_b else "-"

    specs_html = f'''
    <table style="width:100%; border-collapse:collapse; font-family:'Meiryo UI',sans-serif; font-size:13px;">
        <thead>
            <tr style="border-bottom: 2px solid #555;">
                <th style="padding:8px; text-align:left; color:#aaa; width:90px;"></th>
                <th style="padding:8px; text-align:center; color:#aaa;">GLBファイル</th>
                <th style="padding:8px; text-align:center; color:#aaa;">全長 (mm)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">全幅 (mm)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">全高 (mm)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">地上高 (mm)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">回転半径 (m)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">加速 (秒)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">Z回転 (度)</th>
                <th style="padding:8px; text-align:center; color:#aaa;">タイプ</th>
                <th style="padding:8px; text-align:center; color:#aaa;">ミラー突出量 (mm)</th>
            </tr>
        </thead>
        <tbody>
            <tr style="background:#1a2a3e; border-left: 3px solid #64b5f6;">
                <td style="padding:8px; font-weight:bold; color:#64b5f6;">🚗 {car_a_row['name']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row['glb_filename']}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_a_row['length']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_a_row['width']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_a_row['height']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row['ground_clearance']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row['turning_radius']/1000:.1f}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row['acceleration_0_to_100']:.1f}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row['rotation_direction']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_a_row.get('car_type', '')}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{mirror_a_display}</td>
            </tr>
            <tr style="background:#3e2a1a; border-left: 3px solid #ffb74d;">
                <td style="padding:8px; font-weight:bold; color:#ffb74d;">🚙 {car_b_row['name']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row['glb_filename']}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_b_row['length']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_b_row['width']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{car_b_row['height']:,}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row['ground_clearance']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row['turning_radius']/1000:.1f}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row['acceleration_0_to_100']:.1f}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row['rotation_direction']}</td>
                <td style="padding:6px 8px; text-align:center; color:#ccc;">{car_b_row.get('car_type', '')}</td>
                <td style="padding:6px 8px; text-align:center; color:#fff; font-weight:bold;">{mirror_b_display}</td>
            </tr>
        </tbody>
    </table>
    '''
    st.markdown(specs_html, unsafe_allow_html=True)

# ============================================================
# 統計情報
# ============================================================
st.markdown("---")
st.subheader("📊 統計情報")

total_valid = len(filtered_cars_a) * len(filtered_cars_b)
comps_in_view = 0
short_done = 0
both_done = 0

if not comparisons_df.empty:
    filtered_ids_a = set(c["id"] for c in filtered_cars_a)
    filtered_ids_b = set(c["id"] for c in filtered_cars_b)
    view_comps = comparisons_df[
        comparisons_df["car_a_id"].isin(filtered_ids_a) &
        comparisons_df["car_b_id"].isin(filtered_ids_b)
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
