import streamlit as st
import pandas as pd
import re

# --- 1. KHỞI TẠO ---
st.set_page_config(page_title="Toán Thầy 2026", layout="wide")
for key in ["page", "current_id", "current_exam"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else None

# --- 2. HÀM TẢI DỮ LIỆU "BẤT BẠI" ---
def get_csv_url(sheet_url, gid):
    # Trích xuất ID file: 1dQa0evyJJ1JU28ftCwRtCehAPYljdcGECqnlUTuiMrY
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    file_id = match.group(1) if match else "1dQa0evyJJ1JU28ftCwRtCehAPYljdcGECqnlUTuiMrY"
    return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df.fillna("")
    except Exception as e:
        return None

# --- 3. LẤY LINK ---
try:
    SHEET_BASE = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    SHEET_BASE = "https://docs.google.com/spreadsheets/d/1dQa0evyJJ1JU28ftCwRtCehAPYljdcGECqnlUTuiMrY/edit"

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<h1 style="text-align:center; color:#58A6FF;">LUYỆN THI TOÁN 2026</h1>', unsafe_allow_html=True)
    
    # Thử tải tab danh mục (Thầy hãy thử GID 0 nếu 1125343128 lỗi)
    df_topics = load_data(get_csv_url(SHEET_BASE, "1125343128"))
    if df_topics is None: df_topics = load_data(get_csv_url(SHEET_BASE, "0"))
    
    if df_topics is not None:
        id_col = next((c for c in df_topics.columns if 'id' in c), df_topics.columns[0])
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        for i, pref in enumerate(["TN_", "DS_", "SN_"]):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(pref)]
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.write(f"**{row.get('title', 'Bài tập')}**")
                        if c2.button("Vào làm", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row.get('title',''), "page": "Quiz"})
                            st.rerun()
    else:
        st.error("⚠️ Không thể tải dữ liệu. Thầy hãy kiểm tra nút 'Chia sẻ' trên Sheets đã chọn 'Bất kỳ ai có liên kết' chưa?")

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        df_q = load_data(get_csv_url(SHEET_BASE, "1136737670"))
        df_c = load_data(get_csv_url(SHEET_BASE, "1961957372"))
        
        if df_q is not None and df_c is not None:
            q_id_col = next((c for c in df_q.columns if 'id' in c), 'topic_id')
            q_p = df_q[df_q[q_id_col].str.lower() == st.session_state.current_id]
            cf = df_c[df_c[next((c for c in df_c.columns if 'id' in c), 'topic_id')].str.lower() == st.session_state.current_id]
            
            selected = []
            for _, r in cf.iterrows():
                lv = q_p[q_p['level'] == str(r['level']).strip()]
                if not lv.empty:
                    selected.append(lv.sample(n=min(len(lv), int(r.get('num_questions', 0)))))
            if selected: st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"### 📝 {st.session_state.current_title}")
    if st.button("⬅️ Quay lại"): st.session_state.update({"page": "Home", "current_exam": None}); st.rerun()

    if st.session_state.current_exam is not None:
        with st.form("quiz"):
            for i, row in st.session_state.current_exam.iterrows():
                st.write(f"**Câu {i+1}:** {row['q']}")
                if row.get('image'): st.image(row['image'])
                tp = str(row['type']).lower()
                if tp == "choice":
                    st.radio("Chọn:", [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)], key=f"r_{i}", index=None)
                elif tp == "tf":
                    for ch in ['a','b','c','d']:
                        if row.get(f'opt_{ch}'):
                            c1, c2 = st.columns([4,1]); c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch,["Đ","S"],key=f"tf_{i}_{ch}",horizontal=True,label_visibility="collapsed",index=None)
                elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
            st.form_submit_button("NỘP BÀI")
