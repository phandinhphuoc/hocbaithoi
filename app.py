import streamlit as st
import pandas as pd
import re

# --- 1. KHỞI TẠO BIẾN HỆ THỐNG ---
for key in ["page", "current_id", "current_exam", "submitted_done"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else (False if key == "submitted_done" else None)

st.set_page_config(page_title="Toán Thầy 2026", layout="wide")

# --- 2. HÀM LẤY DỮ LIỆU (SỬA LỖI 404) ---
def get_csv_url(sheet_url, gid):
    try:
        # Tách lấy ID file từ link thầy gửi
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if match:
            file_id = match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"
        return ""
    except: return ""

@st.cache_data(ttl=5)
def load_data(url):
    if not url: return None
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = [str(c).strip().lower() for c in df.columns]
        # Loại bỏ các dòng hoàn toàn trống
        df = df.dropna(how='all')
        # Chuyển các giá trị "0", "nan" thành chuỗi rỗng để không hiện lỗi ảnh
        return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except: return None

# --- 3. CSS GIAO DIỆN (ĐẶC TRỊ ẢNH QUÁ LỚN) ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    
    /* Khung câu hỏi bo góc chuyên nghiệp */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
    }

    /* KHỐI LỆNH FIX ẢNH QUÁ TO */
    .stImage > img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        max-width: 400px !important; /* Ảnh rộng tối đa 400px trên máy tính */
        width: 100% !important;      /* Tự co lại trên điện thoại */
        height: auto;
        border-radius: 8px;
        border: 1px solid #30363D;
    }

    div.stButton > button { background-color: #238636 !important; color: white !important; width: 100% !important; }
    .main-title { text-align: center; color: #58A6FF; font-size: 2.2em; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# Lấy Link từ Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Thầy chưa dán link Sheets vào mục Secrets!"); st.stop()

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<p class="main-title">LUYỆN THI TOÁN 2026</p>', unsafe_allow_html=True)
    
    # Tải danh sách bài tập (GID=0)
    df_topics = load_data(get_csv_url(SHEET_URL, "0"))
    
    if df_topics is not None:
        # Dùng cột topic_id làm định danh
        id_col = 'topic_id' if 'topic_id' in df_topics.columns else df_topics.columns[0]
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        for i, (pref, ico) in enumerate([("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(pref)]
                if filtered.empty: st.info("Đang cập nhật nội dung...")
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.write(f"**{ico} {row.get('title', 'Bài tập')}**")
                        if c2.button("Luyện tập", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row['title'], "page": "Quiz", "submitted_done": False})
                            st.rerun()
    else:
        st.error("❌ Không thể tải dữ liệu từ Sheets. Thầy kiểm tra lại quyền Chia sẻ (Bất kỳ ai có link) nhé!")

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        # GID câu hỏi: 1136737670, GID cấu hình: 1961957372
        df_q = load_data(get_csv_url(SHEET_URL, "1136737670"))
        df_c = load_data(get_csv_url(SHEET_URL, "1961957372"))
        
        if df_q is not None and df_c is not None:
            q_p = df_q[df_q['topic_id'].str.lower() == st.session_state.current_id]
            cf = df_c[df_c['topic_id'].str.lower() == st.session_state.current_id]
            
            selected = []
            for _, r in cf.iterrows():
                lv = q_p[q_p['level'] == str(r['level']).strip()]
                if not lv.empty:
                    selected.append(lv.sample(n=min(len(lv), int(r['num_questions']))))
            if selected: st.session_state.current_exam = pd.concat(selected).reset_index(drop=True)

    st.write(f"### 📝 {st.session_state.current_title}")
    if st.button("⬅️ Quay lại"): 
        st.session_state.update({"page": "Home", "current_exam": None})
        st.rerun()

    if st.session_state.current_exam is not None:
        with st.form("f_quiz"):
            un, uc = st.text_input("Họ tên:"), st.text_input("Lớp:")
            for i, row in st.session_state.current_exam.iterrows():
                with st.container(border=True):
                    st.write(f"**Câu {i+1}:** {row['q']}")
                    
                    # HIỂN THỊ ẢNH (Đã được CSS thu nhỏ)
                    img = str(row.get('image','')).strip()
                    if img.startswith("http"): st.image(img)
                    
                    tp = str(row['type']).lower()
                    if tp == "choice":
                        opts = [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)]
                        st.radio("Chọn đáp án:", opts, key=f"r_{i}", index=None)
                    elif tp == "tf":
                        for ch in ['a','b','c','d']:
                            if row.get(f'opt_{ch}'):
                                c1, c2 = st.columns([4,1])
                                c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch, ["Đ","S"], key=f"tf_{i}_{ch}", horizontal=True, label_visibility="collapsed", index=None)
                    elif tp == "short": st.text_input("Đáp án ngắn:", key=f"s_{i}")
            
            if st.form_submit_button("🔔 NỘP BÀI"):
                if un and uc: 
                    st.balloons(); st.success("Nộp bài thành công!")
                    st.session_state.submitted_done = True
                else: st.error("Em quên nhập Tên hoặc Lớp rồi kìa!")
    else:
        st.warning("Đang tải dữ liệu câu hỏi...")

st.markdown('<div style="text-align:center; color:#8B949E; margin-top:50px;">© 2026 Lớp Toán Thầy ...</div>', unsafe_allow_html=True)
