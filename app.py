import streamlit as st
import pandas as pd
import re
import time

# --- 1. CẤU HÌNH HỆ THỐNG ---
for key in ["page", "current_id", "current_exam"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else None

st.set_page_config(page_title="Toán Thầy 2026", layout="wide")

# --- 2. HÀM TẢI DỮ LIỆU CHỐNG LỖI 404 ---
def get_csv_url(sheet_url, gid):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if match:
            # Ép link về định dạng export CSV kèm mã GID chuẩn
            return f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv&gid={gid}"
        return ""
    except: return ""

@st.cache_data(ttl=5)
def load_data(url):
    if not url: return None
    for _ in range(3): # Thử lại 3 lần nếu Google chặn
        try:
            df = pd.read_csv(url, dtype=str)
            df.columns = [str(c).strip().lower() for c in df.columns]
            df = df.dropna(how='all')
            return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
        except:
            time.sleep(1)
    return None

# --- 3. GIAO DIỆN ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stVerticalBlockBorderWrapper"] { 
        background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 12px !important; 
    }
    .stImage > img { display: block; margin: auto; max-width: 400px !important; width: 100% !important; border-radius: 10px; }
    div.stButton > button { background-color: #238636 !important; color: white !important; font-weight: bold; width: 100%; }
    </style>
""", unsafe_allow_html=True)

try:
    SHEET_BASE = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Thầy chưa dán link vào Secrets!"); st.stop()

# --- 4. TRANG CHỦ (GID TOPICS = 1125343128) ---
if st.session_state.page == "Home":
    st.markdown('<h1 style="text-align:center; color:#58A6FF;">LUYỆN THI TOÁN 2026</h1>', unsafe_allow_html=True)
    
    # SỬA GID Ở ĐÂY CHO KHỚP VỚI TAB TOPICS CỦA THẦY
    df_topics = load_data(get_csv_url(SHEET_BASE, "1125343128"))
    
    if df_topics is not None:
        # Tự tìm cột ID trong tab Topics
        id_col = next((c for c in df_topics.columns if 'id' in c), df_topics.columns[0])
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        prefs = [("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]
        
        for i, (p, ico) in enumerate(prefs):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(p)]
                if filtered.empty: st.info("Đang cập nhật...")
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.write(f"**{ico} {row.get('title', 'Bài tập')}**")
                        if c2.button("Làm bài", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row['title'], "page": "Quiz"})
                            st.rerun()
    else:
        st.error(f"❌ Không tìm thấy dữ liệu tại GID 1125343128. Thầy kiểm tra lại link Secrets!")

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        # GID QUESTIONS = 1136737670 | GID CONFIG = 1961957372
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
                    selected.append(lv.sample(n=min(len(lv), int(r['num_questions']))))
            if selected: st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"### {st.session_state.current_title}")
    if st.button("⬅️ Quay lại"): st.session_state.update({"page": "Home", "current_exam": None}); st.rerun()

    if st.session_state.current_exam is not None:
        with st.form("quiz"):
            st.text_input("Họ tên:"), st.text_input("Lớp:")
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
                                c1, c2 = st.columns([4,1]); c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch,["Đ","S"],key=f"tf_{i}_{ch}",horizontal=True,label_visibility="collapsed",index=None)
                    elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
            st.form_submit_button("NỘP BÀI")
