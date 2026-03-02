import streamlit as st
import pandas as pd
import time

# --- 1. KHỞI TẠO ---
for key in ["page", "current_id", "current_exam"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else None

st.set_page_config(page_title="Toán Thầy ... 2026", layout="wide")

# --- 2. HÀM TẢI DỮ LIỆU ---
@st.cache_data(ttl=1) # Giảm cache xuống để cập nhật nhanh
def load_data(url):
    try:
        # Ép đọc dữ liệu thô từ CSV
        df = pd.read_csv(url, dtype=str)
        # Chuẩn hóa tên cột: xóa khoảng trắng, viết thường
        df.columns = [str(c).strip().lower() for c in df.columns]
        # Lọc rác (0, nan)
        df = df.dropna(how='all')
        return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except Exception as e:
        return None

def get_csv_url(sheet_url, gid):
    try:
        # Tách lấy phần gốc của link Sheets để tạo link tải CSV
        base_url = sheet_url.split('/edit')[0]
        return f"{base_url}/export?format=csv&gid={gid}"
    except: return ""

# --- 3. CSS GIAO DIỆN ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stVerticalBlockBorderWrapper"] { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 10px !important; }
    .stImage > img { display: block; margin: auto; max-width: 450px !important; width: 100% !important; border-radius: 8px; }
    .main-title { text-align: center; color: #58A6FF; font-size: 2.2em; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# Lấy link từ Secrets
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Lỗi: Thầy chưa dán link vào mục Secrets của Streamlit Cloud!"); st.stop()

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<p class="main-title">LUYỆN THI TOÁN 2026</p>', unsafe_allow_html=True)
    
    # GID=0 cho tab danh sách bài tập
    df_topics = load_data(get_csv_url(SHEET_URL, "0"))
    
    if df_topics is not None:
        # TÌM CỘT ID THÔNG MINH: Thầy đặt tên là 'id' hay 'topic_id' đều được
        cols = df_topics.columns.tolist()
        id_col = 'topic_id' if 'topic_id' in cols else ('id' if 'id' in cols else cols[0])
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        for i, (pref, ico) in enumerate([("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(pref)]
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.write(f"**{ico} {row.get('title', 'Không tiêu đề')}**")
                        if c2.button("Làm bài", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row['title'], "page": "Quiz"})
                            st.rerun()
    else:
        st.error(f"❌ KHÔNG TÌM THẤY DỮ LIỆU (Lỗi 404).")
        st.info("💡 Cách sửa: Thầy mở Sheets -> Nhấn Chia sẻ -> Chọn 'Bất kỳ ai có đường liên kết'.")

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
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

    st.write(f"### {st.session_state.current_title}")
    if st.button("⬅️ Quay lại"): st.session_state.update({"page": "Home", "current_exam": None}); st.rerun()

    if st.session_state.current_exam is not None:
        with st.form("f_quiz"):
            un, uc = st.text_input("👤 Họ tên:"), st.text_input("🏫 Lớp:")
            for i, row in st.session_state.current_exam.iterrows():
                with st.container(border=True):
                    st.write(f"**Câu {i+1}:** {row['q']}")
                    img = str(row.get('image','')).strip()
                    if img.startswith("http"): st.image(img)
                    
                    tp = str(row['type']).lower()
                    if tp == "choice":
                        opts = [row[o] for o in ['opt_a','opt_b','opt_c','opt_d'] if row.get(o)]
                        st.radio("Chọn:", opts, key=f"r_{i}", index=None)
                    elif tp == "tf":
                        for ch in ['a','b','c','d']:
                            if row.get(f'opt_{ch}'):
                                c1, c2 = st.columns([4,1])
                                c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch, ["Đ","S"], key=f"tf_{i}_{ch}", horizontal=True, label_visibility="collapsed", index=None)
                    elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
            
            if st.form_submit_button("NỘP BÀI"):
                if un and uc: st.balloons(); st.success("Nộp bài thành công!")
                else: st.error("Vui lòng điền đủ Tên và Lớp!")
    else:
        st.warning("Đang tải câu hỏi hoặc không tìm thấy nội dung...")
