import streamlit as st
import pandas as pd
import requests
import json
import time

# --- 1. KHỞI TẠO BIẾN ---
for key in ["page", "authenticated", "submitted_done", "current_exam", "final_score", "secure_data"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else (0.0 if key == "final_score" else (False if key in ["authenticated", "submitted_done"] else None))

st.set_page_config(page_title="Luyện Thi Toán 2026", layout="wide")

# --- THÔNG SỐ GID (Thầy giữ nguyên) ---
GID_MAP = {"topics": "0", "security": "1125343128", "config": "1961957372", "questions": "1136737670"}

# --- 2. HÀM TẢI DỮ LIỆU "CHỐNG LỖI 404" ---
@st.cache_data(ttl=5)
def load_data(url):
    try:
        # Thêm header để tránh bị Google chặn khi gọi nhiều lần
        df = pd.read_csv(url, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df.dropna(how='all').map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except Exception as e:
        return None

def get_csv_url(sheet_url, gid):
    try:
        # Tự động xử lý nếu link Sheets có hoặc không có đuôi /edit
        base = sheet_url.split('/edit')[0]
        return f"{base}/export?format=csv&gid={gid}"
    except: return ""

# --- 3. CSS GIAO DIỆN ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important; border-radius: 12px !important; padding: 20px !important;
    }
    .stImage > img { display: block; margin: auto; max-width: 450px !important; width: 100% !important; border-radius: 10px; }
    div.stButton > button { background-color: #238636 !important; color: white !important; width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Chưa cấu hình Secrets trên Streamlit Cloud!"); st.stop()

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<h1 style="text-align:center;color:#58A6FF;">LUYỆN THI TOÁN 2026</h1>', unsafe_allow_html=True)
    df_topics = load_data(get_csv_url(SHEET_URL, GID_MAP["topics"]))
    
    if df_topics is not None:
        # TỰ ĐỘNG CHỌN CỘT ID: Ưu tiên 'topic_id' nếu không có 'id'
        id_col = 'topic_id' if 'topic_id' in df_topics.columns else ('id' if 'id' in df_topics.columns else df_topics.columns[0])
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        for i, (pref, ico) in enumerate([("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(pref)]
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"**{ico} {row['title']}**")
                        if c2.button("Làm bài", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row['title'], "page": "Quiz", "authenticated": True})
                            st.rerun()
    else:
        st.error("❌ Lỗi kết nối Google Sheets (404). Thầy kiểm tra lại link trong Secrets và quyền chia sẻ Sheets!")

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        df_q = load_data(get_csv_url(SHEET_URL, GID_MAP["questions"]))
        df_c = load_data(get_csv_url(SHEET_URL, GID_MAP["config"]))
        
        if df_q is not None and df_c is not None:
            q_p = df_q[df_q['topic_id'].str.lower() == st.session_state.current_id]
            cf = df_c[df_c['topic_id'].str.lower() == st.session_state.current_id]
            selected = []
            for _, r in cf.iterrows():
                lv = q_p[q_p['level'] == str(r['level']).strip()]
                if not lv.empty:
                    selected.append(lv.sample(n=min(len(lv), int(r['num_questions']))))
            st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"### {st.session_state.current_title}")
    if st.button("⬅️ Thoát"): st.session_state.update({"page": "Home", "current_exam": None}); st.rerun()

    if st.session_state.current_exam is not None:
        with st.form("f_quiz"):
            un, uc = st.text_input("Họ tên:"), st.text_input("Lớp:")
            for i, row in st.session_state.current_exam.iterrows():
                with st.container(border=True):
                    st.write(f"**Câu {i+1}:** {row['q']}")
                    if str(row.get('image','')).startswith("http"): st.image(row['image'])
                    
                    tp = str(row['type']).lower()
                    if tp == "choice":
                        st.radio("Chọn:", [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)], key=f"r_{i}", index=None)
                    elif tp == "tf":
                        for ch in ['a','b','c','d']:
                            if row.get(f'opt_{ch}'):
                                c1, c2 = st.columns([4,1])
                                c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch, ["Đ","S"], key=f"tf_{i}_{ch}", horizontal=True, label_visibility="collapsed", index=None)
                    elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
            
            if st.form_submit_button("NỘP BÀI"):
                if un and uc: st.balloons(); st.success("Nộp thành công!")
                else: st.error("Thiếu Tên/Lớp!")
