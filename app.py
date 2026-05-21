import os
import json
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# ─────────────────────────────────────────────
# 1. 경로 및 페이지 설정
# ─────────────────────────────────────────────
SHP_PATH  = "N3A_G0100000.shp"  # 업로드하신 세트 파일명
DATA_FILE = "companies.json"

st.set_page_config(page_title="대한민국 행정구역 업체관리 (GIS)", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .main { background-color: #f5f6fa; }
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 1.6rem !important; font-weight: 700; color: #1a1a2e; }
    .region-badge {
        display: inline-block; background: #4361ee; color: #fff;
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. GIS 데이터 자동 파싱 및 유효성 검사
# ─────────────────────────────────────────────
@st.cache_data
def load_shp_data():
    if not os.path.exists(SHP_PATH):
        st.error(f"⚠️ SHP 파일을 찾을 수 없습니다! 현재 경로에 '{SHP_PATH}' 파일과 확장자 자매 파일들(.dbf, .shx, .prj)이 한 폴더에 있는지 확인해주세요.")
        st.stop()
    
    # 한국 지리 데이터 인코딩 대응 (cp949 / euc-kr 순차 시도)
    try:
        gdf = gpd.read_file(SHP_PATH, encoding="cp949")
    except Exception:
        gdf = gpd.read_file(SHP_PATH, encoding="euc-kr")
        
    # [핵심] 캡처하신 에러 원인 해결: 실제 이름이 들어있는 컬럼 자동 매핑
    name_col = None
    possible_cols = ["NAME", "name", "SIG_KOR_NM", "EMD_KOR_NM", "CTP_KOR_NM", "행정구역명", "시군구명"]
    
    # 딕셔너리 내부 컬럼 중 매칭되는 것 찾기
    for col in possible_cols:
        if col in gdf.columns:
            name_col = col
            break
            
    # 만약 위 목록에 없으면 문자열을 포함한 컬럼 중 가장 적합한 것 자동 선택
    if not name_col:
        for col in gdf.columns:
            if gdf[col].dtype == 'object' and not col.lower().startswith('ufid'):
                name_col = col
                break
                
    if not name_col:
        st.error("SHP 파일 내부에서 지역 이름 컬럼을 찾지 못했습니다. 데이터 구조를 확인해주세요.")
        st.stop()
        
    # 표준 컬럼명 'NAME'으로 통일 변환
    gdf["NAME"] = gdf[name_col].astype(str).str.strip()
    
    # 지도용 위경도 표준 좌표계(WGS84, EPSG:4326) 변환
    if gdf.crs is None:
        gdf.crs = "EPSG:5179" # 기본 국가 통합 좌표계 가정
    gdf = gdf.to_crs(epsg=4326)
    
    # 기하학적 에러(도형 꼬임 등)가 있을 경우를 대비한 자동 보정
    gdf["geometry"] = gdf["geometry"].buffer(0)
    
    return gdf

gdf_regions = load_shp_data()
all_region_names = sorted(gdf_regions["NAME"].dropna().unique().tolist())

# ─────────────────────────────────────────────
# 3. 데이터 입출력 함수 및 상태 초기화
# ─────────────────────────────────────────────
def load_json_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

if "region_data" not in st.session_state:
    st.session_state.region_data = load_json_data()

# 데이터 로드 후 기본 선택 값 안전하게 처리
if "selected_region" not in st.session_state or st.session_state.selected_region not in all_region_names:
    st.session_state.selected_region = all_region_names[0]
