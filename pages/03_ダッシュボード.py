"""
ダッシュボード ページ

動画比較ペアの統計情報を可視化する。
"""

import streamlit as st
import pandas as pd
from comparison_manager import (
    init_comparisons_table,
    get_dashboard_stats,
    get_long_video_candidates,
    get_car_comparison_counts,
    get_all_comparisons
)

# DB初期化
init_comparisons_table()

st.set_page_config(page_title="📈 ダッシュボード", page_icon="📈", layout="wide")

st.title("📈 制作状況ダッシュボード")

# ============================================================
# 概要統計カード
# ============================================================
stats = get_dashboard_stats()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("全比較ペア", stats["total_pairs"], delta=f"登録済み")
with col2:
    st.metric("未着手", stats["not_started"], delta="制作待ち")
with col3:
    st.metric("ショート完了", stats["short_published"], delta="公開済み")
with col4:
    st.metric("長尺制作中", stats["long_in_progress"], delta="進行中")
with col5:
    st.metric("両方完了", stats["both_done"], delta="完了!")

st.markdown("---")

# ============================================================
# 進捗円グラフ
# ============================================================
st.subheader("📊 制作状況内訳")

if stats["total_pairs"] > 0:
    status_data = pd.DataFrame({
        "ステータス": ["未着手", "ショート完了", "長尺制作中", "両方完了"],
        "件数": [stats["not_started"], stats["short_only"], stats["long_in_progress"], stats["both_done"]],
        "色": ["#e0e0e0", "#ffeb3b", "#ff9800", "#4caf50"]
    })
    
    col_chart, col_table = st.columns(2)
    
    with col_chart:
        # 円グラフ表示 (plotlyを使用)
        try:
            import plotly.express as px
            fig = px.pie(
                status_data, 
                values="件数", 
                names="ステータス",
                color="ステータス",
                color_discrete_map=dict(zip(status_data["ステータス"], status_data["色"])),
                hole=0.4,
                title="制作状況内訳"
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # plotlyがない場合はバーチャートで代替
            st.bar_chart(status_data.set_index("ステータス"))
            st.info("plotlyをインストールすると円グラフが表示されます: `pip install plotly`")
    
    with col_table:
        st.dataframe(status_data, use_container_width=True, hide_index=True)

else:
    st.info("比較ペアデータがありません。マトリクスページからペアを追加してください。")

st.markdown("---")

# ============================================================
# 長尺制作候補ランキング
# ============================================================
st.subheader("🏆 長尺制作候補 (ショート視聴回数順)")
st.caption("ショート動画が公開済みで、長尺が未着手のペアを視聴回数順に表示")

candidates = get_long_video_candidates(limit=20)

if not candidates.empty:
    # ランキング表示
    medals = ["🏆", "🥈", "🥉"]
    
    display_data = []
    for idx, row in candidates.iterrows():
        rank = idx + 1
        medal = medals[rank - 1] if rank <= 3 else f"{rank}位"
        display_data.append({
            "順位": f"{medal}",
            "車A": row["car_a_name"],
            "車B": row["car_b_name"],
            "視聴回数": row["short_views"]
        })
    
    display_df = pd.DataFrame(display_data)
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # 上位ペアのクイックアクション
    st.markdown("---")
    st.subheader("⚡ クイックアクション")
    
    top_candidates = candidates.head(5)
    for idx, row in top_candidates.iterrows():
        with st.expander(f"{row['car_a_name']} vs {row['car_b_name']} ({row['short_views']}回視聴)"):
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button(
                    "🎬 cars_configに設定",
                    key=f"config_{row['id']}",
                    use_container_width=True
                ):
                    from comparison_manager import set_comparison_pair_to_config
                    success, msg = set_comparison_pair_to_config(row["car_a_id"], row["car_b_id"])
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
            with col_act2:
                if st.button(
                    "📊 長尺制作中にステータス変更",
                    key=f"status_{row['id']}",
                    use_container_width=True
                ):
                    from comparison_manager import update_comparison_status
                    success = update_comparison_status(row["id"], long_status=1)
                    if success:
                        st.success("長尺制作中に更新しました")
                        st.rerun()
                    else:
                        st.error("更新に失敗しました")

else:
    st.info("候補がありません。ショート動画を公開するとここに表示されます。")

st.markdown("---")

# ============================================================
# 車別比較カウント
# ============================================================
st.subheader("🚗 車別比較回数")
st.caption("各車が何回の比較ペアに含まれているか")

car_counts = get_car_comparison_counts()

if not car_counts.empty:
    # バーチャート表示
    try:
        import plotly.express as px
        fig = px.bar(
            car_counts.head(15),
            x="car_name",
            y="comparison_count",
            title="車別比較回数 (Top 15)",
            labels={"car_name": "車名", "comparison_count": "比較回数"},
            color="comparison_count",
            color_continuous_scale="Blues"
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.bar_chart(car_counts.set_index("car_name"))
        st.info("plotlyをインストールすると詳細チャートが表示されます")
    
    # テーブル表示
    st.dataframe(
        car_counts[["car_name", "comparison_count"]], 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("比較ペアデータがありません。")

st.markdown("---")

# ============================================================
# 全比較ペア一覧
# ============================================================
st.subheader("📋 全比較ペア一覧")

all_comps = get_all_comparisons()

if not all_comps.empty:
    # ステータスラベルに変換
    def status_label(row):
        from comparison_manager import get_combined_status
        label, _ = get_combined_status(row["short_status"], row["long_status"])
        return label
    
    display_df = all_comps.copy()
    display_df["ステータス"] = display_df.apply(status_label, axis=1)
    
    # 表示用カラムを選択
    show_cols = ["car_a_name", "car_b_name", "ステータス", "short_views", "short_video_url"]
    col_names = {"car_a_name": "車A", "car_b_name": "車B", "ステータス": "状況", 
                 "short_views": "視聴回数", "short_video_url": "ショートURL"}
    
    st.dataframe(
        display_df[show_cols].rename(columns=col_names),
        use_container_width=True,
        height=400
    )
else:
    st.info("比較ペアデータがありません。")

# ============================================================
# フッター
# ============================================================
st.markdown("---")
st.caption(f"📊 最終更新: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} | 全車種: {len(pd.read_csv('cars.csv')) - 1}台")
