import os
import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# ─────────────────────────────────────────────
# 1. 경로 및 파일 설정
# ─────────────────────────────────────────────
SHP_PATH  = "N3A_G0100000.shp"
DATA_FILE = "companies.json"

st.set_page_config(page_title="행정구역 업체관리 시스템", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .main { background-color: #f5f6fa; }
    h1 { font-size: 1.6rem !important; font-weight: 700; color: #1a1a2e; }
    .region-badge {
        display: inline-block; background: #4361ee; color: #fff;
        border-radius: 6px; padding: 6px 14px; font-size: 1rem; font-weight: 700; margin-bottom: 12px;
    }
    .stButton > button { border-radius: 8px; font-weight: 500; }
    .stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .stat-card {
        background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
        padding: 10px 18px; text-align: center; flex: 1; min-width: 100px;
    }
    .stat-num { font-size: 1.4rem; font-weight: 700; color: #4361ee; }
    .stat-label { font-size: 0.75rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. GIS 데이터 안전 로드 (KeyError 해결)
# ─────────────────────────────────────────────
@st.cache_data
def load_shp_data():
    if not os.path.exists(SHP_PATH):
        st.error(f"⚠️ SHP 파일을 찾을 수 없습니다: {SHP_PATH}")
        st.stop()
    
    # 인코딩 예외 처리
    try:
        gdf = gpd.read_file(SHP_PATH, encoding="cp949")
    except Exception:
        gdf = gpd.read_file(SHP_PATH, encoding="euc-kr")
        
    # [KeyError 해결] 파일 내부에 NAME 컬럼이 없거나 다를 경우를 대비한 100% 방어 로직
    target_col = None
    for col in gdf.columns:
        if str(col).upper() == "NAME":
            target_col = col
            break
            
    if target_col is None:
        # NAME이 없다면 텍스트(object) 형태를 가진 첫 번째 컬럼을 이름으로 강제 지정
        for col in gdf.columns:
            if gdf[col].dtype == 'object' and not str(col).upper().startswith('UFID'):
                target_col = col
                break

    if target_col is None:
        st.error("SHP 파일 내에서 지역 명칭 컬럼을 찾을 수 없습니다.")
        st.stop()
        
    # 새로운 표준 'NAME' 컬럼 생성 및 데이터 정제
    gdf["NAME"] = gdf[target_col].astype(str).str.strip()
    gdf = gdf.dropna(subset=["NAME", "geometry"])
    gdf
