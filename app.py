import streamlit as st
import pandas as pd
import requests
import json
import time

# --- 1. KHỞI TẠO BIẾN ---
for key in ["page", "authenticated", "submitted_done", "current_exam", "final_score", "secure_data"]:
    if key not in st.session_state:
        if key == "page": st.session_state[key] = "Home"
        elif key == "final_score": st.session_state[key] = 0.0
        elif key in ["authenticated", "submitted_done"]: st.session_state[key] = False
        else: st.session_state[key] = None

st.set_page_config(page_title="Hệ Thống Toán 2026", layout="wide")

# --- THÔNG SỐ GID ---
GID_MAP = {"topics": "0", "security": "1125343128", "config": "1961957372", "questions": "1136737670"}

# --- 2. HÀM TẢI DỮ LIỆU THÔNG MINH ---
@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        # Chuẩn hóa tên cột để tránh lỗi viết hoa/thường
        df.columns = [str(c).strip().lower() for c in df.columns]
        # Xóa dòng trống và lọc bỏ giá trị "0" rác
        df = df.dropna(how='all')
        return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except:
        return None

def get_csv_url(sheet_url, gid):
    try:
        file_id = sheet_url.split('/')[-2]
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"
    except: return ""

# --- 3. CSS GIAO DIỆN (DARK MODE & ẢNH GỌN) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px !important;
        padding: 20px !important; margin-bottom: 15px !important;
    }
    .stImage > img {
        display: block; margin-left: auto; margin-right: auto;
        max-width: 450px !important; width: 100% !important; border-radius: 10px;
    }
    div.stButton > button { background-color: #238636 !important; color: white !important; width: 100% !important; border: none !important;}
    .main-title { text-align: center; color: #58A6FF; font-size: 2.2em; font-weight: 800; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

try:
    SHEET_BASE_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Thầy chưa dán link Sheets vào mục Secrets của Streamlit Cloud!")
    st.stop()

# --- 4. TRANG CHỦ (HOME) ---
if st.session_state.page == "Home":
    st.markdown('<p class="main-title">LUYỆN THI TOÁN 2026</p>', unsafe_allow_html=True)
    df_topics = load_data(get_csv_url(SHEET_BASE_URL, GID_MAP["topics"]))
    
    if df_topics is not None:
        # TỰ ĐỘNG NHẬN DIỆN CỘT: Nếu không có 'id', dùng 'topic_id'
        id_col = 'topic_id' if 'topic_id' in df_topics.columns else df_topics.columns[0]
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        configs = [("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]
        
        for i, (prefix, icon) in enumerate(configs):
            with tabs[i]:
                # Lọc bài tập theo tiền tố (TN_, DS_, SN_)
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(prefix)]
                if filtered.empty: st.info("Chưa có bài tập.")
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.markdown(f'<div style="line-height:35px">**{icon} {row["title"]}**</div>', unsafe_allow_html=True)
                        if c2.button("Luyện tập", key=f"btn_{row[id_col]}"):
                            st.session_state.update({
                                "current_id": str(row[id_col]).lower(), 
                                "current_title": row['title'],
                                "page": "Security", "authenticated": False, "submitted_done": False
                            })
                            st.rerun()
    else:
        st.warning("⚠️ Không kết nối được dữ liệu. Kiểm tra quyền 'Anyone with the link' trên Sheets!")

# --- 5. BẢO MẬT (SECURITY) ---
elif st.session_state.page == "Security":
    st.subheader(f"🔐 Xác thực: {st.session_state.current_title}")
    df_sec = load_data(get_csv_url(SHEET_BASE_URL, GID_MAP["security"]))
    
    # Nếu không có tab bảo mật hoặc không có dữ liệu cho bài này, cho qua luôn
    if df_sec is not None and 'topic_id' in df_sec.columns:
        pool = df_sec[df_sec['topic_id'].str.lower() == st.session_state.current_id]
        if pool.empty: 
            st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()
        
        if st.session_state.secure_data is None: st.session_state.secure_data = pool.sample(n=1).iloc[0]
        
        with st.container(border=True):
            if st.session_state.secure_data.get('youtube_url'): st.video(st.session_state.secure_data['youtube_url'])
            u_ans = st.text_input(f"❓ {st.session_state.secure_data.get('secure_q', 'Mã bảo mật là gì?')}")
            if st.button("Xác thực & Vào bài"):
                if u_ans.strip().lower() == str(st.session_state.secure_data.get('secure_a','')).strip().lower():
                    st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()
                else: st.error("Sai rồi thầy ơi! Xem kỹ video nhé.")
    else:
        st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()

# --- 6. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        df_q = load_data(get_csv_url(SHEET_BASE_URL, GID_MAP["questions"]))
        df_c = load_data(get_csv_url(SHEET_BASE_URL, GID_MAP["config"]))
        
        # Tìm câu hỏi và cấu hình dựa trên topic_id
        q_p = df_q[df_q['topic_id'].str.lower() == st.session_state.current_id]
        cf = df_c[df_c['topic_id'].str.lower() == st.session_state.current_id]
        
        if q_p.empty or cf.empty:
            st.error("Không tìm thấy câu hỏi cho bài này trong Sheets!"); st.stop()
            
        selected = []
        for _, r in cf.iterrows():
            lv = q_p[q_p['level'] == str(r['level']).strip()]
            if not lv.empty:
                selected.append(lv.sample(n=min(len(lv), int(r['num_questions']))))
        st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"### 📝 {st.session_state.current_title}")
    if st.button("⬅️ Thoát"): 
        st.session_state.update({"page": "Home", "current_exam": None, "secure_data": None})
        st.rerun()

    with st.form("f_quiz"):
        un = st.text_input("👤 Họ tên:")
        uc = st.text_input("🏫 Lớp:")
        for i, row in st.session_state.current_exam.iterrows():
            with st.container(border=True):
                st.write(f"**Câu {i+1}:** {row['q']}")
                if str(row.get('image','')).startswith("http"): st.image(row['image'])
                
                tp = str(row['type']).lower()
                if tp == "choice":
                    opts = [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)]
                    st.radio("Chọn:", opts, key=f"r_{i}", index=None)
                elif tp == "tf":
                    for ch in ['a','b','c','d']:
                        if row.get(f'opt_{ch}'):
                            c1, c2 = st.columns([4,1])
                            c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch,["Đ","S"],key=f"tf_{i}_{ch}",horizontal=True,label_visibility="collapsed",index=None)
                elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
        
        if st.form_submit_button("NỘP BÀI"):
            if un and uc:
                st.balloons(); st.success("Đã ghi nhận bài làm!"); st.session_state.submitted_done = True
            else: st.error("Điền tên và lớp nhé!")
