import os
import json
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import pandas as pd

# ─────────────────────────────────────────────
# 1. 경로 및 페이지 설정 (배포 최적화)
# ─────────────────────────────────────────────
IMG_PATH  = "FullSizeRender.jpeg"
DATA_FILE = "companies.json"

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
# 2. 행정구역 좌표 데이터 (안전한 줄바꿈 분할)
# ─────────────────────────────────────────────
REGIONS = {
    # 특별시·광역시·특별자치시
    "서울": (210, 190, 80, 60), "인천": (150, 200, 65, 65), "대전": (420, 530, 80, 65),
    "세종": (405, 490, 58, 45), "대구": (615, 648, 82, 65), "광주": (272, 725, 75, 62),
    "울산": (768, 685, 75, 62), "부산": (722, 758, 90, 70),
    
    # 경기도 1
    "수원": (208, 288, 52, 40), "성남": (238, 258, 50, 38), "안양": (202, 260, 42, 35),
    "부천": (168,
