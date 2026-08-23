"""
車種データベース Web管理画面 (Streamlit)

使い方:
    python web_manage_cars.py
    → ブラウザで http://localhost:8501 にアクセス
"""

import sqlite3
import pandas as pd
import streamlit as st
import os
from datetime import datetime

# ============================================================
# データベース設定
# ============================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars.db")


def get_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 同時アクセス対応
    return conn


def init_db():
    """データベース初期化 (テーブル作成)"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            glb_filename TEXT NOT NULL UNIQUE,
            length INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            ground_clearance INTEGER DEFAULT 0,
            turning_radius INTEGER DEFAULT 0,
            acceleration_0_to_100 REAL DEFAULT 0.0,
            rotation_direction INTEGER DEFAULT 0,
            car_type TEXT DEFAULT '',
            mirror_offset_mm INTEGER DEFAULT 100
        )
    """)
    # mirror_offset_mm 列が存在しない場合は追加（マイグレーション対応）
    try:
        conn.execute("ALTER TABLE cars ADD COLUMN mirror_offset_mm INTEGER DEFAULT 100")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列が既に存在する場合は無視
    conn.close()


# 車種タイプ別のミラー突出量（片側 mm）
MIRROR_OFFSET_BY_TYPE = {
    "軽自動車": 70,
    "スポーツカー": 90,
    "セダン": 95,
    "ハッチバック": 95,
    "SUV": 100,
    "ミニバン": 100,
    "ピックアップ": 110,
    "バス/トラック": 80,
}

CAR_TYPE_OPTIONS = ["SUV", "セダン", "ハッチバック", "スポーツカー", "ミニバン", "ピックアップ", "軽自動車", "バス/トラック"]


def get_all_cars():
    """全車種データをDataFrameとして取得"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM cars ORDER BY id", conn)
    conn.close()
    return df


def search_cars(query):
    """車名で部分一致検索"""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM cars WHERE name LIKE ? ORDER BY id",
        (f"%{query}%",),
        conn
    )
    conn.close()
    return df


def get_car_by_id(car_id):
    """IDで車種データを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars WHERE id = ?", (car_id,))
    row = cursor.fetchone()
    conn.close()
    # sqlite3.Row を辞書に変換して返す
    if row:
        return dict(row)
    return None


def add_car(name, glb_filename, length, width, height, ground_clearance, turning_radius, acceleration, rotation, car_type):
    """新規車種追加"""
    mirror_offset = MIRROR_OFFSET_BY_TYPE.get(car_type, 100)
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO cars (name, glb_filename, length, width, height,
                             ground_clearance, turning_radius,
                             acceleration_0_to_100, rotation_direction, car_type, mirror_offset_mm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, glb_filename, length, width, height,
              ground_clearance, turning_radius, acceleration, rotation, car_type, mirror_offset))
        conn.commit()
        new_id = conn.cursor().lastrowid
        conn.close()
        return True, new_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "GLBファイル名が既に登録されています"
    except Exception as e:
        conn.close()
        return False, str(e)


def update_car(car_id, name, glb_filename, length, width, height, ground_clearance, turning_radius, acceleration, rotation, car_type):
    """車種情報更新"""
    mirror_offset = MIRROR_OFFSET_BY_TYPE.get(car_type, 100)
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE cars SET
                name = ?, glb_filename = ?, length = ?, width = ?, height = ?,
                ground_clearance = ?, turning_radius = ?,
                acceleration_0_to_100 = ?, rotation_direction = ?, car_type = ?,
                mirror_offset_mm = ?
            WHERE id = ?
        """, (name, glb_filename, length, width, height,
              ground_clearance, turning_radius, acceleration, rotation, car_type,
              mirror_offset, car_id))
        conn.commit()
        conn.close()
        return True, "更新しました"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "GLBファイル名が既に登録されています"
    except Exception as e:
        conn.close()
        return False, str(e)


def delete_car(car_id):
    """車種削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cars WHERE id = ?", (car_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "指定されたIDの車種が見つかりません"
    car_name = row["name"]
    cursor.execute("DELETE FROM cars WHERE id = ?", (car_id,))
    conn.commit()
    conn.close()
    return True, car_name


def export_to_csv():
    """CSVデータを生成"""
    df = get_all_cars()
    return df.to_csv(index=False, encoding="utf-8-sig")


# ============================================================
# Streamlit アプリ
# ============================================================
def main():
    st.set_page_config(
        page_title="🚗 車種データベース管理",
        page_icon="🚗",
        layout="wide"
    )

    # プライマリーカラーを青系に設定（CSSで上書き）
    st.markdown("""
    <style>
    .stButton > button {
        background-color: #1E88E5 !important;
        color: white !important;
    }
    .stButton > button:hover {
        background-color: #1565C0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    init_db()

    st.title("🚗 車種データベース管理")
    st.markdown("---")

    # セッション状態初期化
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None

    # ============================================================
    # 検索セクション
    # ============================================================
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 車名で検索", key="search_box")
    with col_count:
        pass

    if search_query:
        df = search_cars(search_query)
        if df.empty:
            st.warning(f"「{search_query}」に一致する車種が見つかりませんでした。")
        else:
            st.success(f"{len(df)} 件の車種が見つかりました")
    else:
        df = get_all_cars()

    # ============================================================
    # 車種一覧テーブル
    # ============================================================
    st.subheader("📋 車種一覧")
    if not df.empty:
        display_df = df.copy()
        display_df.columns = ["ID", "車名", "GLBファイル", "全長(mm)", "全幅(mm)", "全高(mm)",
                              "最低地上高(mm)", "最小回転半径(mm)", "0-100km/h加速(秒)", "Z軸回転(度)",
                              "車種タイプ", "ミラー突出量(mm)"]
        st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("データベースに車種データがありません。")

    st.markdown("---")

    # ============================================================
    # 操作セクション (2カラム)
    # ============================================================
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("➕ 新規追加 / ✏️ 編集")

        with st.form("car_form", clear_on_submit=False):
            if st.session_state.edit_mode and st.session_state.edit_id:
                st.caption(f"✏️ 編集モード (ID: {st.session_state.edit_id})")
                edit_car = get_car_by_id(st.session_state.edit_id)

                inp_name = st.text_input("車名", value=edit_car["name"] if edit_car else "")
                inp_glb = st.text_input("GLBファイル名", value=edit_car["glb_filename"] if edit_car else "")
                inp_type = st.selectbox(
                    "車種タイプ",
                    CAR_TYPE_OPTIONS,
                    index=CAR_TYPE_OPTIONS.index(edit_car["car_type"]) if edit_car.get("car_type") and edit_car["car_type"] in CAR_TYPE_OPTIONS else 0
                )
                # ミラー突出量を表示（タイプ選択で自動設定）
                auto_offset = MIRROR_OFFSET_BY_TYPE.get(inp_type, 100)
                current_offset = edit_car.get("mirror_offset_mm", 100) if edit_car else 100
                inp_mirror_offset = st.number_input(
                    "ミラー突出量 (mm/片側)",
                    min_value=50, max_value=150, step=5,
                    value=current_offset,
                    help=f"車種タイプ「{inp_type}」の推奨値: {auto_offset}mm。3Dスケール計算時に 全幅 + (この値 × 2) を使用します。"
                )
                col_dims_a, col_dims_b, col_dims_c = st.columns(3)
                with col_dims_a:
                    inp_length = st.number_input("全長 (mm)", value=edit_car["length"] if edit_car else 0, step=1)
                    inp_width = st.number_input("全幅 (mm)", value=edit_car["width"] if edit_car else 0, step=1)
                with col_dims_b:
                    inp_height = st.number_input("全高 (mm)", value=edit_car["height"] if edit_car else 0, step=1)
                    inp_gc = st.number_input("最低地上高 (mm)", value=edit_car["ground_clearance"] if edit_car else 0, step=1)
                with col_dims_c:
                    inp_tr = st.number_input("最小回転半径 (mm)", value=edit_car["turning_radius"] if edit_car else 0, step=1)
                    inp_acc = st.number_input("0-100km/h加速 (秒)", value=edit_car["acceleration_0_to_100"] if edit_car else 0.0, step=0.1)
                col_dims_d = st.columns(1)[0]
                with col_dims_d:
                    inp_rot = st.number_input("Z軸回転角度 (度)", value=edit_car["rotation_direction"] if edit_car else 0, step=1)
            else:
                st.caption("➕ 新規追加モード")

                inp_name = st.text_input("車名", placeholder="例: 新型シビック")
                inp_glb = st.text_input("GLBファイル名", placeholder="例: civic2027.glb")
                inp_type = st.selectbox(
                    "車種タイプ",
                    CAR_TYPE_OPTIONS,
                    key="new_car_type"
                )
                # ミラー突出量を表示（タイプ選択で自動設定）
                auto_offset = MIRROR_OFFSET_BY_TYPE.get(inp_type, 100)
                inp_mirror_offset = st.number_input(
                    "ミラー突出量 (mm/片側)",
                    min_value=50, max_value=150, step=5,
                    value=auto_offset,
                    key="new_mirror_offset",
                    help=f"車種タイプ「{inp_type}」の推奨値: {auto_offset}mm。3Dスケール計算時に 全幅 + (この値 × 2) を使用します。"
                )
                col_dims_a, col_dims_b, col_dims_c = st.columns(3)
                with col_dims_a:
                    inp_length = st.number_input("全長 (mm)", min_value=100, max_value=10000, step=1, key="new_length")
                    inp_width = st.number_input("全幅 (mm)", min_value=100, max_value=5000, step=1, key="new_width")
                with col_dims_b:
                    inp_height = st.number_input("全高 (mm)", min_value=100, max_value=5000, step=1, key="new_height")
                    inp_gc = st.number_input("最低地上高 (mm)", min_value=0, max_value=1000, step=1, key="new_gc")
                with col_dims_c:
                    inp_tr = st.number_input("最小回転半径 (mm)", min_value=0, max_value=10000, step=1, key="new_tr")
                    inp_acc = st.number_input("0-100km/h加速 (秒)", min_value=0.0, max_value=30.0, step=0.1, key="new_acc")
                col_dims_d = st.columns(1)[0]
                with col_dims_d:
                    inp_rot = st.number_input("Z軸回転角度 (度)", min_value=0, max_value=360, step=1, key="new_rot")

            col_submit, col_cancel = st.columns([1, 1])
            with col_submit:
                submitted = st.form_submit_button(
                    "💾 更新" if st.session_state.edit_mode else "✅ 追加",
                    type="primary",
                    use_container_width=True
                )
            with col_cancel:
                if st.session_state.edit_mode:
                    if st.form_submit_button("❌ キャンセル", use_container_width=True):
                        st.session_state.edit_mode = False
                        st.session_state.edit_id = None
                        st.rerun()

            if submitted:
                if not inp_name or not inp_glb:
                    st.error("車名とGLBファイル名は必須です。")
                else:
                    if st.session_state.edit_mode and st.session_state.edit_id:
                        success, msg = update_car(
                            st.session_state.edit_id, inp_name, inp_glb,
                            int(inp_length), int(inp_width), int(inp_height),
                            int(inp_gc), int(inp_tr), float(inp_acc), int(inp_rot),
                            inp_type
                        )
                        if success:
                            st.success(f"✓ 車種 ID {st.session_state.edit_id} を更新しました")
                            st.session_state.edit_mode = False
                            st.session_state.edit_id = None
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {msg}")
                    else:
                        success, result = add_car(
                            inp_name, inp_glb,
                            int(inp_length), int(inp_width), int(inp_height),
                            int(inp_gc), int(inp_tr), float(inp_acc), int(inp_rot),
                            inp_type
                        )
                        if success:
                            st.success(f"✓ 車種を追加しました (ID: {result})")
                            st.rerun()
                        else:
                            st.error(f"✗ エラー: {result}")

    with col_right:
        st.subheader("🔍 詳細表示 / 🗑️ 削除")

        selected_id = st.number_input(
            "操作対象のIDを入力",
            min_value=1,
            step=1,
            key="selected_id"
        )

        car_detail = get_car_by_id(selected_id)

        if car_detail:
            st.markdown(f"### {car_detail['name']}")
            mirror_offset = car_detail.get("mirror_offset_mm", 100)
            effective_width = car_detail["width"] + (mirror_offset * 2)
            detail_df = pd.DataFrame([{
                "ID": car_detail["id"],
                "車名": car_detail["name"],
                "GLBファイル": car_detail["glb_filename"],
                "全長(mm)": car_detail["length"],
                "全幅(mm)": car_detail["width"],
                "全幅(ミラー包含)(mm)": effective_width,
                "全高(mm)": car_detail["height"],
                "最低地上高(mm)": car_detail["ground_clearance"],
                "最小回転半径(mm)": car_detail["turning_radius"],
                "0-100km/h加速(秒)": car_detail["acceleration_0_to_100"],
                "Z軸回転(度)": car_detail["rotation_direction"],
                "車種タイプ": car_detail.get("car_type", ""),
                "ミラー突出量(mm/片側)": mirror_offset
            }])
            st.dataframe(detail_df.set_index("ID"), use_container_width=True)

            col_edit, col_delete = st.columns(2)
            with col_edit:
                if st.button("✏️ 編集モードに切り替え", type="secondary", use_container_width=True):
                    st.session_state.edit_mode = True
                    st.session_state.edit_id = selected_id
                    st.rerun()
            with col_delete:
                if st.button("🗑️ この車種を削除", type="secondary", use_container_width=True):
                    st.session_state.confirm_delete = selected_id

        else:
            st.info(f"ID {selected_id} の車種が見つかりません。")

        # 削除確認
        if "confirm_delete" in st.session_state and st.session_state.confirm_delete:
            with st.expander("⚠️ 削除確認", expanded=True):
                confirm_car = get_car_by_id(st.session_state.confirm_delete)
                if confirm_car:
                    st.warning(f"「{confirm_car['name']}」(ID: {st.session_state.confirm_delete}) を削除しますか？")
                    col_y, col_n = st.columns(2)
                    with col_y:
                        if st.button("はい、削除する", type="primary", use_container_width=True):
                            success, result = delete_car(st.session_state.confirm_delete)
                            if success:
                                st.success(f"✓ 「{result}」を削除しました")
                                del st.session_state.confirm_delete
                                st.rerun()
                            else:
                                st.error(result)
                    with col_n:
                        if st.button("キャンセル", use_container_width=True):
                            del st.session_state.confirm_delete
                            st.rerun()

        st.markdown("---")
        st.subheader("📥 CSVエクスポート")
        if st.download_button(
            label="💾 CSVとしてダウンロード",
            data=export_to_csv(),
            file_name=f"cars_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        ):
            st.success("CSVエクスポート準備完了")

    # ============================================================
    # フッター
    # ============================================================
    st.markdown("---")
    total_cars = len(get_all_cars())
    st.caption(f"📊 登録車種数: {total_cars} 台 | データベース: {DB_PATH}")


if __name__ == "__main__":
    main()
