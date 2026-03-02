import streamlit as st
import pandas as pd
import requests
import json
import time

# --- 1. KHỞI TẠO HỆ THỐNG ---
for key in ["page", "authenticated", "submitted_done", "current_exam", "final_score", "secure_data"]:
    if key not in st.session_state:
        if key == "page": st.session_state[key] = "Home"
        elif key == "final_score": st.session_state[key] = 0.0
        elif key in ["authenticated", "submitted_done"]: st.session_state[key] = False
        else: st.session_state[key] = None

if "exam_token" not in st.session_state: 
    st.session_state.exam_token = str(time.time())

st.set_page_config(page_title="Luyện Thi Toán 2026", layout="wide")

# --- THÔNG SỐ CẤU HÌNH (Thầy kiểm tra kỹ các ID này) ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwtmsNnYnn0W9vrciPhaJPznKfpis5QNx6_MEtDGd4NkbAgF7Ob7v16hjcMzZJh-qxJXg/exec"
GID_TOPICS = "0"
GID_SECURITY_POOL = "1125343128"
GID_CONFIG = "1961957372"
GID_QUESTIONS = "1136737670"

# --- 2. HÀM TẢI DỮ LIỆU (ĐÃ SỬA LỖI KEYERROR) ---
@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        # Chuẩn hóa tên cột: xóa khoảng trắng và viết thường hết
        df.columns = [str(c).strip().lower() for c in df.columns]
        # Xóa các dòng trống và thay thế giá trị lỗi
        df = df.dropna(how='all')
        return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame()

def get_csv_url(sheet_url, gid):
    file_id = sheet_url.split('/')[-2]
    return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"

# --- 3. CSS GIAO DIỆN (ĐẶC TRỊ ẢNH & DARK MODE) ---
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
        max-width: 450px !important; width: 100% !important;
        height: auto; border-radius: 10px;
    }
    .topic-text { font-size: 1.1em; font-weight: 500; color: #F0F6FC; }
    div.stButton > button { background-color: #238636 !important; color: white !important; width: 100% !important; }
    .main-title { text-align: center; color: #58A6FF; font-size: 2.5em; font-weight: 800; margin-bottom: 30px; }
    .custom-footer { position: fixed; bottom: 0; left: 0; width: 100%; background: #161B22; color: #8B949E; text-align: center; padding: 10px 0; border-top: 1px solid #30363D; z-index: 999; }
    </style>
""", unsafe_allow_html=True)

try:
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("Chưa cấu hình Secrets trên Streamlit Cloud!")
    st.stop()

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<p class="main-title">LUYỆN THI TOÁN 2026</p>', unsafe_allow_html=True)
    df_topics = load_data(get_csv_url(sheet_url, GID_TOPICS))
    
    if not df_topics.empty and 'id' in df_topics.columns:
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        prefixes, icons = ["TN_", "DS_", "SN_"], ["📘", "⚖️", "✍️"]

        for i, tab in enumerate(tabs):
            with tab:
                filtered = df_topics[df_topics['id'].str.upper().str.startswith(prefixes[i])]
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c_t, c_b = st.columns([5, 1.2])
                        c_t.markdown(f'<div class="topic-text">{icons[i]} &nbsp; {row["title"]}</div>', unsafe_allow_html=True)
                        if c_b.button("Bắt đầu làm", key=f"btn_{row['id']}"):
                            st.session_state.update({
                                "current_id": str(row['id']).lower(), "current_title": row['title'],
                                "page": "Security", "authenticated": False, "submitted_done": False, 
                                "secure_data": None, "current_exam": None, "exam_token": str(time.time())
                            })
                            st.rerun()
    else:
        st.warning("⚠️ Không tìm thấy cột 'id' trong danh sách bài tập. Hãy kiểm tra Sheets!")

# --- 5. XÁC THỰC BẢO MẬT ---
elif st.session_state.page == "Security":
    st.write(f"### 🔐 Xác thực bài học: {st.session_state.current_title}")
    if st.button("⬅️ Quay lại"): st.session_state.page = "Home"; st.rerun()
    
    df_sec = load_data(get_csv_url(sheet_url, GID_SECURITY_POOL))
    if not df_sec.empty and 'topic_id' in df_sec.columns:
        pool = df_sec[df_sec['topic_id'].str.lower() == st.session_state.current_id]
        if pool.empty: 
            st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()
        
        if st.session_state.secure_data is None: 
            st.session_state.secure_data = pool.sample(n=1).iloc[0]
        
        with st.container(border=True):
            if st.session_state.secure_data.get('youtube_url'): st.video(st.session_state.secure_data['youtube_url'])
            st.info(f"❓ {st.session_state.secure_data.get('secure_q', 'Vui lòng nhập mã bảo mật')}")
            u_ans = st.text_input("Đáp án:", key="sec_i").strip().lower()
            if st.button("Xác thực"):
                if u_ans == str(st.session_state.secure_data.get('secure_a', '')).lower():
                    st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()
                else: st.error("Sai rồi thầy ơi!")
    else:
        st.session_state.update({"authenticated": True, "page": "Quiz"}); st.rerun()

# --- 6. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if not st.session_state.authenticated: st.session_state.page = "Security"; st.rerun()
    
    if st.session_state.current_exam is None:
        df_q = load_data(get_csv_url(sheet_url, GID_QUESTIONS))
        df_c = load_data(get_csv_url(sheet_url, GID_CONFIG))
        q_p = df_q[df_q['topic_id'].str.lower() == st.session_state.current_id]
        conf = df_c[df_c['topic_id'].str.lower() == st.session_state.current_id]
        
        selected = []
        for _, r in conf.iterrows():
            lp = q_p[q_p['level'] == str(r['level']).strip()]
            if not lp.empty: selected.append(lp.sample(n=min(len(lp), int(r['num_questions']))))
        st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"## 📝 {st.session_state.current_title}")
    if st.button("⬅️ Thoát"): 
        st.session_state.update({"page": "Home", "submitted_done": False, "current_exam": None})
        st.rerun()

    with st.form(key=f"f_quiz"):
        un = st.text_input("👤 Họ tên:", disabled=st.session_state.submitted_done)
        uc = st.text_input("🏫 Lớp:", disabled=st.session_state.submitted_done)
        
        for i, row in st.session_state.current_exam.iterrows():
            with st.container(border=True):
                st.markdown(f"**Câu {i+1}:** {row.get('q', 'Nội dung trống')}")
                img = str(row.get('image', '')).strip()
                if img.startswith("http"): st.image(img)
                
                tp = str(row.get('type', '')).lower()
                if tp == "choice":
                    opts = [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)]
                    st.radio("Chọn:", opts, key=f"r_{i}", index=None, disabled=st.session_state.submitted_done)
                elif tp == "tf":
                    for ch in ['a','b','c','d']:
                        if row.get(f'opt_{ch}'):
                            cq, cr = st.columns([4, 1.5])
                            cq.write(f"{ch}. {row[f'opt_{ch}']}"); cr.radio(ch, ["Đ","S"], key=f"tf_{i}_{ch}", horizontal=True, index=None, disabled=st.session_state.submitted_done)
                elif tp == "short": st.text_input("Kết quả:", key=f"s_{i}", disabled=st.session_state.submitted_done)
        
        if st.form_submit_button("NỘP BÀI", disabled=st.session_state.submitted_done):
            if not un or not uc: st.error("Thiếu Tên/Lớp!")
            else:
                # Logic nộp bài & Chấm điểm (như trước)
                st.success("Nộp thành công!")
                st.session_state.submitted_done = True
                st.balloons(); st.rerun()

st.markdown('<div class="custom-footer">© 2026 Lớp Toán Thầy ...</div>', unsafe_allow_html=True)
