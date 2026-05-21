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
SHP_PATH  = "N3A_G0100000.shp"  # 업로드하신 SHP 파일 경로 (세트 파일들이 같은 폴더에 있어야 함)
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
# 2. GIS 데이터 로드 및 좌표계 변환 (WGS84)
# ─────────────────────────────────────────────
@st.cache_data
def load_shp_data():
    if not os.path.exists(SHP_PATH):
        st.error(f"SHP 파일을 찾을 수 없습니다. 경로를 확인해주세요: {SHP_PATH}\n(.dbf, .shx, .prj 파일도 같은 폴더에 있어야 합니다.)")
        st.stop()
    
    # SHP 읽기
    gdf = gpd.read_file(SHP_PATH, encoding="euc-kr") # 또는 cp949
    
    # 지도(Folium)에 띄우기 위해 표준 위경도 좌표계(EPSG:4326)로 변환
    if gdf.crs is None:
        # 업로드한 prj 파일 기반으로 설정하되, 없을 경우 한국 표준 통합좌표계 설정
        gdf.crs = "EPSG:5179"
    gdf = gdf.to_crs(epsg=4326)
    
    # 공백 제거 및 이름 매핑 정제 (NAME 컬럼 활용)
    if "NAME" in gdf.columns:
        gdf["NAME"] = gdf["NAME"].str.strip()
    return gdf

gdf_regions = load_shp_data()
all_region_names = sorted(gdf_regions["NAME"].dropna().unique().tolist())

# ─────────────────────────────────────────────
# 3. 데이터 입출력 및 상태 초기화
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
if "selected_region" not in st.session_state:
    st.session_state.selected_region = "종로구"  # 기본값 변경

def get_csv() -> bytes:
    rows = []
    for r, comps in st.session_state.region_data.items():
        for c in comps:
            if c.get("name", "").strip():
                rows.append({"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")})
    if not rows:
        return "지역,업체명,위치,전화번호\n".encode("utf-8-sig")
    return pd.DataFrame(rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

# 실시간 통계 집계
total_regions = len([r for r, c in st.session_state.region_data.items() if c])
all_companies_list = [
    {"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")}
    for r, comps in st.session_state.region_data.items()
    for c in comps if c.get("name","").strip()
]
total_companies = len(all_companies_list)

# ─────────────────────────────────────────────
# 4. UI 레이아웃
# ─────────────────────────────────────────────
st.title("🗺️ 대한민국 행정구역 업체관리 (GIS 자동인식 버전)")

st.markdown(f"""
<div class="stat-row">
  <div class="stat-card"><div class="stat-num">{total_regions}</div><div class="stat-label">등록 지역</div></div>
  <div class="stat-card"><div class="stat-num">{total_companies}</div><div class="stat-label">전체 업체 수</div></div>
  <div class="stat-card"><div class="stat-num">{len(all_region_names)}</div><div class="stat-label">인식된 총 행정구역 수</div></div>
</div>
""", unsafe_allow_html=True)

tab_map, tab_list = st.tabs(["📍 지도에서 관리하기", f"📋 등록된 전체 업체 목록 ({total_companies}개)"])

# ── 탭 1: 지도 관리 ──
with tab_map:
    col_map, col_panel = st.columns([3, 2], gap="large")

    with col_map:
        st.markdown("#### 📍 지도 구역을 클릭하여 선택하세요")
        
        # 대한민국 중심점 설정
        m = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles="OpenStreetMap")
        
        # 행정구역 테두리선(GeoJSON)을 지도에 주입
        selected_target = st.session_state.selected_region
        
        def style_function(feature):
            is_selected = feature['properties']['NAME'] == selected_target
            return {
                'fillColor': '#ffb6c1' if is_selected else '#4361ee',
                'color': '#dc325a' if is_selected else '#ffffff',
                'weight': 3 if is_selected else 1.2,
                'fillOpacity': 0.6 if is_selected else 0.2
            }

        def highlight_function(feature):
            return {
                'fillColor': '#ffb6c1',
                'weight': 3,
                'fillOpacity': 0.8
            }

        # 지도 레이어 추가
        geojson_data = folium.GeoJson(
            gdf_regions,
            name="행정경계",
            style_function=style_function,
            highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(fields=["NAME"], aliases=["지역명:"], localize=True)
        )
        geojson_data.add_to(m)
        
        # 스트림릿에 Folium 지도 렌더링 및 클릭 감지
        map_output = st_folium(m, width="100%", height=600, key="gis_map")
        
        # 지도를 클릭했을 때 이벤트 처리
        if map_output and map_output.get("last_active_drawing"):
            clicked_props = map_output["last_active_drawing"]["properties"]
            clicked_name = clicked_props.get("NAME")
            if clicked_name and clicked_name != st.session_state.selected_region:
                st.session_state.selected_region = clicked_name
                st.rerun()

        st.markdown("##### 또는 목록에서 선택")
        sel_idx = all_region_names.index(st.session_state.selected_region) if st.session_state.selected_region in all_region_names else 0
        chosen = st.selectbox("행정구역 검색/선택", all_region_names, index=sel_idx)
        if chosen != st.session_state.selected_region:
            st.session_state.selected_region = chosen
            st.rerun()

    with col_panel:
        region = st.session_state.selected_region
        st.markdown(f'<div class="region-badge">📌 {region}</div>', unsafe_allow_html=True)
        st.markdown("#### 업체 목록")

        if region not in st.session_state.region_data:
            st.session_state.region_data[region] = []

        companies = st.session_state.region_data[region]

        if not companies:
            st.info("등록된 업체가 없습니다. 아래 버튼으로 추가하세요.")

        to_delete = None
        for idx, company in enumerate(companies):
            with st.container():
                name = st.text_input("업체명 *", value=company.get("name", ""), key=f"name_{region}_{idx}", placeholder="예) 홍길동 전자")
                address = st.text_input("위치", value=company.get("address", ""), key=f"addr_{region}_{idx}", placeholder="예) 해당 시군구 주소")
                phone = st.text_input("전화번호", value=company.get("phone", ""), key=f"phon_{region}_{idx}", placeholder="예) 010-1234-5678")
                st.session_state.region_data[region][idx] = {"name": name, "address": address, "phone": phone}
                if st.button("🗑️ 삭제", key=f"del_{region}_{idx}", use_container_width=True):
                    to_delete = idx
                st.markdown("---")

        if to_delete is not None:
            st.session_state.region_data[region].pop(to_delete)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.region_data, f, ensure_ascii=False, indent=4)
            st.rerun()

        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("➕ 업체 추가", use_container_width=True):
                st.session_state.region_data[region].append({"name": "", "address": "", "phone": ""})
                st.rerun()
        with btn2:
            valid = [c for c in companies if c.get("name", "").strip()]
            dropped = len(companies) - len(valid)
            if st.button("💾 저장", type="primary", use_container_width=True):
                st.session_state.region_data[region] = valid
                try:
                    with open(DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(st.session_state.region_data, f, ensure_ascii=False, indent=4)
                    if dropped:
                        st.warning(f"업체명 없는 항목 {dropped}개 제외")
                    else:
                        st.success(f"✅ {region} 저장 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 오류: {e}")

# ── 탭 2: 등록된 전체 업체 목록 ──
with tab_list:
    st.markdown("#### 📋 대한민국 전체 등록 업체")
    if all_companies_list:
        df = pd.DataFrame(all_companies_list)
        unique_regions = ["전체"] + sorted(list(df["지역"].unique()))
        filter_region = st.selectbox("🔍 검색할 지역 필터", unique_regions)
        
        if filter_region != "전체":
            df = df[df["지역"] == filter_region]
            
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 전체 목록 CSV 다운로드", data=get_csv(), file_name="전체_업체목록.csv", mime="text/csv")
    else:
        st.info("등록된 업체가 없습니다. '지도에서 관리하기' 탭에서 업체를 먼저 추가해 주세요.")
