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

st.set_page_config(page_title="대한민국 행정구역 업체관리 (GIS v2)", layout="wide", initial_sidebar_state="collapsed")

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
# 2. GIS 데이터 로드 및 정제 (안정성 강화)
# ─────────────────────────────────────────────
@st.cache_data
def load_shp_data():
    if not os.path.exists(SHP_PATH):
        st.error(f"⚠️ SHP 파일을 찾을 수 없습니다: {SHP_PATH}\n같은 폴더에 .dbf, .shx, .prj 파일이 모두 있어야 합니다.")
        st.stop()
    
    # 인코딩 유연한 처리
    try:
        gdf = gpd.read_file(SHP_PATH, encoding="cp949")
    except Exception:
        gdf = gpd.read_file(SHP_PATH, encoding="euc-kr")
        
    # 명세 분석 결과 'NAME' 컬럼이 존재하므로 강제 매핑 및 공백 제거
    if "NAME" in gdf.columns:
        gdf["NAME"] = gdf["NAME"].astype(str).str.strip()
    else:
        # 혹시 모를 예외 대비 첫 문자열 컬럼 백업
        for col in gdf.columns:
            if gdf[col].dtype == 'object' and not col.lower().startswith('ufid'):
                gdf["NAME"] = gdf[col].astype(str).str.strip()
                break

    # 지도가 유실되거나 결측치 데이터 선제 제외
    gdf = gdf.dropna(subset=["NAME", "geometry"])
    gdf = gdf[gdf["NAME"] != "None"]
    
    # 좌표계 정의 변환 (국가 통합 원점 TM 좌표 -> 표준 위경도 EPSG:4326)
    if gdf.crs is None:
        gdf.crs = "EPSG:5179"
    gdf = gdf.to_crs(epsg=4326)
    
    # 폴리곤 연산 오류 방지를 위한 버퍼 처리
    gdf["geometry"] = gdf["geometry"].buffer(0)
    
    # Folium 클릭 매핑 정확도를 극대화하기 위해 유니크 스트링 ID를 인덱스로 강제 지정
    gdf["id"] = gdf["NAME"]
    gdf = gdf.set_index("id", drop=False)
    
    return gdf

gdf_regions = load_shp_data()
all_region_names = sorted(gdf_regions["NAME"].unique().tolist())

if not all_region_names:
    st.error("SHP 파일 내에서 유효한 행정구역 이름을 추출하지 못했습니다.")
    st.stop()

# ─────────────────────────────────────────────
# 3. 데이터 저장 및 상태 관리
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

# 세션 상태 초기화 및 유효성 보호
if "selected_region" not in st.session_state or st.session_state.selected_region not in all_region_names:
    st.session_state.selected_region = all_region_names[0]

def get_csv() -> bytes:
    rows = []
    for r, comps in st.session_state.region_data.items():
        for c in comps:
            if c.get("name", "").strip():
                rows.append({"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")})
    if not rows:
        return "지역,업체명,위치,전화번호\n".encode("utf-8-sig")
    return pd.DataFrame(rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

# 통계량 파싱
total_regions = len([r for r, c in st.session_state.region_data.items() if c])
all_companies_list = [
    {"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")}
    for r, comps in st.session_state.region_data.items()
    for c in comps if c.get("name","").strip()
]
total_companies = len(all_companies_list)

# ─────────────────────────────────────────────
# 4. 레이아웃 스케치
# ─────────────────────────────────────────────
st.title("🗺️ 대한민국 행정구역 업체관리 (공식 수치지도 버전)")

st.markdown(f"""
<div class="stat-row">
  <div class="stat-card"><div class="stat-num">{total_regions}</div><div class="stat-label">등록 지역</div></div>
  <div class="stat-card"><div class="stat-num">{total_companies}</div><div class="stat-label">전체 업체 수</div></div>
  <div class="stat-card"><div class="stat-num">{len(all_region_names)}</div><div class="stat-label">인식된 총 구역 수</div></div>
</div>
""", unsafe_allow_html=True)

tab_map, tab_list = st.tabs(["📍 지도에서 관리하기", f"📋 등록된 전체 업체 목록 ({total_companies}개)"])

with tab_map:
    col_map, col_panel = st.columns([3, 2], gap="large")

    with col_map:
        st.markdown("#### 📍 행정구역을 마우스로 클릭하세요 (확대/축소 지원)")
        
        # 지도의 첫 포커스 중심 위치 산출 (전체 구역의 중앙값)
        bounds = gdf_regions.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles="OpenStreetMap")
        
        selected_target = st.session_state.selected_region
        
        # 지도 테두리 및 내부 색상 로직 정의
        def style_function(feature):
            f_name = feature['properties'].get('NAME', '')
            is_selected = (f_name == selected_target)
            return {
                'fillColor': '#ffb6c1' if is_selected else '#4361ee',
                'color': '#dc325a' if is_selected else '#4361ee',
                'weight': 3 if is_selected else 1.2,
                'fillOpacity': 0.6 if is_selected else 0.15
            }

        def highlight_function(feature):
            return {
                'fillColor': '#ffb6c1',
                'weight': 2.5,
                'fillOpacity': 0.75
            }

        # 정제된 GeoJSON을 지도에 바인딩
        geojson_layer = folium.GeoJson(
            gdf_regions.__geo_interface__,
            style_function=style_function,
            highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(fields=["NAME"], aliases=["지역명:"], localize=True)
        )
        geojson_layer.add_to(m)
        
        # Folium 맵 출력 및 세션 컨트롤
        map_output = st_folium(m, width="100%", height=620, key="gis_map_final")
        
        # [핵심 피드백 반영] 클릭 시 안전성 강화를 위해 'last_object_clicked_popup' 대체 검증
        if map_output and map_output.get("last_active_drawing"):
            props = map_output["last_active_drawing"].get("properties", {})
            clicked_name = props.get("NAME")
            if clicked_name and clicked_name in all_region_names and clicked_name != st.session_state.selected_region:
                st.session_state.selected_region = clicked_name
                st.rerun()

        st.markdown("##### 🔍 동기화 선택 박스 (검색 가능)")
        sel_idx = all_region_names.index(st.session_state.selected_region) if st.session_state.selected_region in all_region_names else 0
        chosen = st.selectbox("행정구역 리스트", all_region_names, index=sel_idx, label_visibility="collapsed")
        if chosen != st.session_state.selected_region:
            st.session_state.selected_region = chosen
            st.rerun()

    with col_
