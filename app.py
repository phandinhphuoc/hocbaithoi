import streamlit as st
import pandas as pd
import re

# --- 1. KHỞI TẠO ---
for key in ["page", "current_id", "current_exam"]:
    if key not in st.session_state:
        st.session_state[key] = "Home" if key == "page" else None

st.set_page_config(page_title="Toán Thầy 2026", layout="wide")

# --- 2. HÀM TẢI DỮ LIỆU "SIÊU SẠCH" ---
def get_csv_url(sheet_url, gid):
    try:
        # Tự động trích xuất ID file từ bất kỳ định dạng link nào thầy dán vào
        file_id = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url).group(1)
        # Ép link về dạng xuất bản CSV trực tiếp
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"
    except:
        return ""

@st.cache_data(ttl=2) # Cache ngắn để thầy sửa Sheets là hiện ngay
def load_data(url):
    if not url: return None
    try:
        # Thêm tham số storage_options để tránh lỗi kết nối trên Cloud
        df = pd.read_csv(url, dtype=str, on_bad_lines='skip')
        df.columns = [str(c).strip().lower() for c in df.columns]
        df = df.dropna(how='all')
        return df.map(lambda x: "" if pd.isna(x) or str(x).strip() in ["0", "0.0", "nan", "None"] else str(x).strip())
    except Exception as e:
        # Nếu lỗi, in lỗi ra để thầy biết đường sửa
        st.error(f"Lỗi kết nối: {e}")
        return None

# --- 3. GIAO DIỆN ---
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    [data-testid="stVerticalBlockBorderWrapper"] { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 10px !important; margin-bottom: 10px; }
    .stImage > img { display: block; margin: auto; max-width: 400px !important; width: 100% !important; border-radius: 8px; }
    div.stButton > button { background-color: #238636 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

try:
    SHEET_BASE = st.secrets["connections"]["gsheets"]["spreadsheet"]
except:
    st.error("❌ Thầy chưa dán link vào Secrets của Streamlit Cloud!"); st.stop()

# --- 4. TRANG CHỦ ---
if st.session_state.page == "Home":
    st.markdown('<h1 style="text-align:center;color:#58A6FF;">LUYỆN THI TOÁN 2026</h1>', unsafe_allow_html=True)
    
    # GID=0 (Tab Danh mục bài tập)
    df_topics = load_data(get_csv_url(SHEET_BASE, "0"))
    
    if df_topics is not None:
        # Tìm cột định danh (ưu tiên topic_id hoặc id)
        cols = df_topics.columns.tolist()
        id_col = next((c for c in ['topic_id', 'id'] if c in cols), cols[0])
        
        tabs = st.tabs(["📑 TRẮC NGHIỆM", "⚖️ ĐÚNG / SAI", "✍️ TRẢ LỜI NGẮN"])
        for i, (pref, ico) in enumerate([("TN_", "📘"), ("DS_", "⚖️"), ("SN_", "✍️")]):
            with tabs[i]:
                filtered = df_topics[df_topics[id_col].str.upper().str.startswith(pref)]
                if filtered.empty: st.info("Đang chờ thầy thêm bài mới...")
                for _, row in filtered.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1.2])
                        c1.write(f"**{ico} {row.get('title', 'Bài tập')}**")
                        if c2.button("Làm bài", key=f"btn_{row[id_col]}"):
                            st.session_state.update({"current_id": row[id_col].lower(), "current_title": row['title'], "page": "Quiz"})
                            st.rerun()
    else:
        st.warning("⚠️ Đang thử kết nối lại với Google Sheets...")
        if st.button("Tải lại trang"): st.rerun()

# --- 5. TRANG LÀM BÀI ---
elif st.session_state.page == "Quiz":
    if st.session_state.current_exam is None:
        # GID câu hỏi: 1136737670, GID cấu hình: 1961957372
        df_q = load_data(get_csv_url(SHEET_BASE, "1136737670"))
        df_c = load_data(get_csv_url(SHEET_BASE, "1961957372"))
        
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
            un, uc = st.text_input("Họ tên:"), st.text_input("Lớp:")
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
                                c1, c2 = st.columns([4,1]); c1.write(f"{ch}. {row[f'opt_{ch}']}"); c2.radio(ch, ["Đ","S"], key=f"tf_{i}_{ch}", horizontal=True, label_visibility="collapsed", index=None)
                    elif tp == "short": st.text_input("Đáp án:", key=f"s_{i}")
            if st.form_submit_button("NỘP BÀI"):
                if un and uc: st.balloons(); st.success("Xong rồi!")
                else: st.error("Điền tên lớp đã nhé!")
