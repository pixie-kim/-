import os
import pathlib
import json
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import pandas as pd

# ─────────────────────────────────────────────
# 경로 설정 (Streamlit Cloud 배포 환경 최적화)
# ─────────────────────────────────────────────
IMG_PATH  = "FullSizeRender.jpeg"
DATA_FILE = "companies.json"

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────
st.set_page_config(page_title="대한민국 행정구역 업체관리", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .main { background-color: #f5f6fa; }
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 1.6rem !important; font-weight: 700; color: #1a1a2e; }
    .region-badge {
        display: inline-block; background: #1a1a2e; color: #fff;
        border-radius: 6px; padding: 4px 14px; font-size: 1rem; font-weight: 700; margin-bottom: 12px;
    }
    .stButton > button { border-radius: 8px; font-family: 'Noto Sans KR', sans-serif; font-weight: 500; }
    .stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .stat-card {
        background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
        padding: 10px 18px; text-align: center; flex: 1; min-width: 80px;
    }
    .stat-num { font-size: 1.4rem; font-weight: 700; color: #4361ee; }
    .stat-label { font-size: 0.75rem; color: #888; }
    .debug-box {
        background: #fff3cd; border: 1px solid #ffc107;
        border-radius: 6px; padding: 8px 12px; font-size: 0.82rem; margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 데이터 로드 함수
# ─────────────────────────────────────────────
def load_json_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# session_state 초기화
if "region_data" not in st.session_state:
    st.session_state.region_data = load_json_data()

if "selected_region" not in st.session_state:
    st.session_state.selected_region = "서울"

if "last_click" not in st.session_state:
    st.session_state.last_click = None

if "last_raw_coords" not in st.session_state:
    st.session_state.last_raw_coords = None

# ─────────────────────────────────────────────
# 행정구역 좌표 (원본 이미지 1179×1450 기준, x, y, w, h)
# ─────────────────────────────────────────────
REGIONS = {
    "서울": (210, 190, 80, 60), "인천": (150, 200, 65, 65), "대전": (420, 530, 80, 65),
    "세종": (405, 490, 58, 45), "대구": (615, 648, 82, 65), "광주": (272, 725, 75, 62),
    "울산": (768, 685, 75, 62), "부산": (722, 758, 90, 70), "수원": (208, 288, 52, 40),
    "성남": (238, 258, 50, 38), "안양": (202, 260, 42, 35), "부천": (168, 225, 48, 38),
    "광명": (183, 248, 40, 32), "평택": (202, 332, 62, 48), "안성": (262, 338, 55, 45),
    "화성": (168, 298, 58, 52), "용인": (248, 282, 58, 48), "이천": (292, 278, 55, 45),
    "여주": (332, 260, 55, 45), "광주(경기)": (262, 240, 50, 40), "하남": (248, 228, 42, 30),
    "구리": (240, 210, 38, 28), "남양주": (270, 202, 62, 40), "의정부": (232, 182, 45, 32),
    "양주": (230, 162, 50, 38), "동두천": (220, 144, 45, 32), "포천": (264, 147, 62, 52),
    "가평": (322, 168, 62, 52), "양평": (300, 240, 52, 42), "고양": (188, 182, 55, 38),
    "파주": (154, 160, 58, 50), "김포": (142, 197, 48, 40), "연천": (202, 127, 55, 45),
    "안산": (157, 262, 48, 42), "시흥": (162, 240, 40, 35), "의왕": (202, 27
