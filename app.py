# app.py
# pip install streamlit pillow pandas streamlit-image-coordinates

import pathlib
import json
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import pandas as pd

# ─────────────────────────────────────────────
# 경로 설정 (Streamlit Cloud 호환)
# ─────────────────────────────────────────────
BASE_DIR  = pathlib.Path(__file__).parent
IMG_PATH  = BASE_DIR / "FullSizeRender.jpeg"
DATA_FILE = BASE_DIR / "companies.json"

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
# session_state 초기화
# ─────────────────────────────────────────────
if "region_data" not in st.session_state:
    st.session_state.region_data = {}

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
    # 특별시·광역시·특별자치시
    "서울":       (210, 190, 80, 60),
    "인천":       (150, 200, 65, 65),
    "대전":       (420, 530, 80, 65),
    "세종":       (405, 490, 58, 45),
    "대구":       (615, 648, 82, 65),
    "광주":       (272, 725, 75, 62),
    "울산":       (768, 685, 75, 62),
    "부산":       (722, 758, 90, 70),

    # 경기도
    "수원":       (208, 288, 52, 40),
    "성남":       (238, 258, 50, 38),
    "안양":       (202, 260, 42, 35),
    "부천":       (168, 225, 48, 38),
    "광명":       (183, 248, 40, 32),
    "평택":       (202, 332, 62, 48),
    "안성":       (262, 338, 55, 45),
    "화성":       (168, 298, 58, 52),
    "용인":       (248, 282, 58, 48),
    "이천":       (292, 278, 55, 45),
    "여주":       (332, 260, 55, 45),
    "광주(경기)": (262, 240, 50, 40),
    "하남":       (248, 228, 42, 30),
    "구리":       (240, 210, 38, 28),
    "남양주":     (270, 202, 62, 40),
    "의정부":     (232, 182, 45, 32),
    "양주":       (230, 162, 50, 38),
    "동두천":     (220, 144, 45, 32),
    "포천":       (264, 147, 62, 52),
    "가평":       (322, 168, 62, 52),
    "양평":       (300, 240, 52, 42),
    "고양":       (188, 182, 55, 38),
    "파주":       (154, 160, 58, 50),
    "김포":       (142, 197, 48, 40),
    "연천":       (202, 127, 55, 45),
    "안산":       (157, 262, 48, 42),
    "시흥":       (162, 240, 40, 35),
    "의왕":       (202, 270, 38, 30),
    "군포":       (197, 278, 38, 30),
    "과천":       (218, 262, 35, 28),
    "오산":       (204, 310, 42, 35),

    # 강원도
    "춘천":       (380, 157, 75, 65),
    "홍천":       (440, 184, 85, 70),
    "원주":       (370, 247, 65, 55),
    "횡성":       (422, 234, 58, 48),
    "평창":       (472, 220, 72, 58),
    "강릉":       (552, 187, 65, 52),
    "동해":       (572, 234, 52, 45),
    "삼척":       (580, 263, 58, 52),
    "태백":       (540, 250, 48, 45),
    "정선":       (502, 237, 55, 50),
    "영월":       (460, 260, 55, 50),
    "제천":       (424, 287, 58, 50),
    "충주":       (382, 287, 62, 50),
    "단양":       (447, 270, 50, 40),
    "화천":       (410, 130, 63, 48),
    "양구":       (450, 127, 55, 45),
    "인제":       (482, 140, 68, 62),
    "고성(강원)": (502, 112, 55, 45),
    "속초":       (527, 140, 45, 38),
    "양양":       (540, 167, 48, 40),
    "철원":       (347, 120, 68, 45),

    # 충청북도
    "청주":       (408, 428, 76, 64),
    "보은":       (440, 487, 62, 50),
    "옥천":       (422, 530, 55, 45),
    "영동":       (440, 560, 58, 48),
    "진천":       (376, 398, 55, 45),
    "음성":       (346, 368, 58, 48),
    "증평":       (378, 378, 42, 35),
    "괴산":       (408, 378, 58, 45),

    # 충청남도
    "천안":       (308, 358, 72, 58),
    "아산":       (275, 338, 62, 50),
    "당진":       (212, 338, 62, 50),
    "서산":       (165, 348, 62, 50),
    "태안":       (135, 345, 48, 58),
    "홍성":       (205, 395, 58, 48),
    "예산":       (245, 385, 55, 45),
    "공주":       (300, 425, 65, 52),
    "보령":       (178, 438, 62, 52),
    "청양":       (242, 428, 55, 45),
    "부여":       (258, 465, 62, 50),
    "서천":       (225, 495, 55, 48),
    "논산":       (288, 488, 62, 50),
    "금산":       (358, 525, 55, 48),
    "계룡":       (308, 502, 40, 32),

    # 전라북도
    "전주":       (305, 588, 72, 62),
    "익산":       (268, 562, 62, 52),
    "군산":       (228, 548, 58, 50),
    "김제":       (262, 605, 62, 52),
    "완주":       (328, 572, 55, 48),
    "부안":       (225, 628, 55, 52),
    "정읍":       (255, 648, 62, 52),
    "고창":       (228, 688, 58, 52),
    "남원":       (345, 638, 65, 58),
    "순창":       (308, 658, 55, 50),
    "임실":       (320, 620, 52, 45),
    "진안":       (358, 588, 55, 50),
    "무주":       (398, 548, 58, 50),
    "장수":       (368, 628, 55, 50),

    # 전라남도
    "목포":       (195, 805, 50, 42),
    "여수":       (378, 820, 62, 55),
    "순천":       (348, 790, 64, 55),
    "광양":       (380, 788, 50, 45),
    "나주":       (258, 768, 58, 50),
    "화순":       (298, 768, 55, 48),
    "담양":       (295, 728, 52, 45),
    "곡성":       (328, 748, 50, 45),
    "구례":       (358, 758, 50, 45),
    "장성":       (260, 718, 52, 45),
    "영광":       (218, 708, 55, 48),
    "함평":       (235, 738, 50, 45),
    "무안":       (212, 768, 48, 40),
    "신안":       (155, 780, 58, 62),
    "진도":       (165, 838, 55, 50),
    "해남":       (230, 838, 68, 58),
    "강진":       (270, 838, 55, 50),
    "장흥":       (300, 828, 55, 50),
    "보성":       (328, 798, 55, 50),
    "고흥":       (350, 830, 65, 58),
    "완도":       (280, 872, 65, 55),
    "영암":       (238, 802, 52, 45),

    # 경상북도
    "포항":       (682, 488, 75, 65),
    "경주":       (668, 552, 78, 68),
    "안동":       (615, 425, 84, 72),
    "구미":       (565, 508, 72, 58),
    "영주":       (568, 378, 64, 55),
    "영천":       (645, 588, 65, 55),
    "상주":       (538, 468, 65, 55),
    "문경":       (502, 418, 65, 55),
    "경산":       (640, 635, 62, 50),
    "군위":       (605, 535, 58, 50),
    "의성":       (588, 478, 62, 52),
    "청송":       (638, 458, 58, 50),
    "영양":       (658, 418, 55, 48),
    "영덕":       (682, 445, 52, 48),
    "청도":       (638, 670, 58, 50),
    "고령":       (588, 670, 55, 50),
    "성주":       (562, 588, 58, 50),
    "칠곡":       (572, 612, 50, 42),
    "예천":       (538, 418, 55, 48),
    "봉화":       (598, 378, 65, 50),
    "울진":       (662, 378, 58, 55),
    "김천":       (528, 538, 62, 52),

    # 경상남도
    "창원":       (640, 750, 78, 65),
    "진주":       (568, 768, 74, 63),
    "통영":       (618, 818, 62, 55),
    "사천":       (558, 802, 58, 50),
    "김해":       (685, 772, 64, 55),
    "밀양":       (658, 708, 65, 55),
    "거제":       (685, 830, 68, 62),
    "양산":       (715, 730, 58, 50),
    "의령":       (605, 738, 55, 48),
    "함안":       (625, 765, 55, 48),
    "창녕":       (618, 708, 55, 50),
    "고성(경남)": (590, 798, 55, 50),
    "남해":       (558, 838, 62, 55),
    "하동":       (488, 788, 58, 50),
    "산청":       (528, 748, 58, 50),
    "함양":       (495, 728, 55, 50),
    "거창":       (518, 698, 58, 50),
    "합천":       (558, 728, 62, 50),

    # 제주
    "제주":       (330, 945, 88, 68),
    "서귀포":     (330, 1000, 88, 58),
}

# ─────────────────────────────────────────────
# 이미지 로드 (캐싱)
# ─────────────────────────────────────────────
@st.cache_data
def load_image():
    return Image.open(IMG_PATH).convert("RGB")

# ─────────────────────────────────────────────
# 선택 지역 핑크 하이라이트
# ─────────────────────────────────────────────
def draw_overlay(img: Image.Image, selected: str) -> Image.Image:
    overlay = img.copy().convert("RGBA")
    draw = ImageDraw.Draw(overlay)
    if selected in REGIONS:
        x, y, w, h = REGIONS[selected]
        draw.rectangle(
            [x, y, x + w, y + h],
            fill=(255, 182, 193, 120),   # 연핑크 반투명
            outline=(220, 50, 90, 230),  # 진한 핑크 테두리
            width=3
        )
    return overlay.convert("RGB")

# ─────────────────────────────────────────────
# 클릭 좌표 → 지역명 (면적 작은 지역 우선)
# ─────────────────────────────────────────────
def detect_region(cx: int, cy: int) -> str | None:
    matched = []
    for region, (bx, by, bw, bh) in REGIONS.items():
        if bx <= cx <= bx + bw and by <= cy <= by + bh:
            matched.append((bw * bh, region))
    if matched:
        matched.sort()
        return matched[0][1]
    return None

# ─────────────────────────────────────────────
# 데이터 저장 (CSV 다운로드용 직렬화)
# ─────────────────────────────────────────────
def get_csv() -> bytes:
    rows = []
    for r, comps in st.session_state.region_data.items():
        for c in comps:
            if c.get("name", "").strip():
                rows.append({"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")})
    if not rows:
        return "지역,업체명,위치,전화번호\n".encode("utf-8-sig")
    return pd.DataFrame(rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

# ─────────────────────────────────────────────
# 제목 & 통계
# ─────────────────────────────────────────────
st.title("🗺️ 대한민국 행정구역 업체관리")

total_regions   = len([r for r, c in st.session_state.region_data.items() if c])
total_companies = sum(len(c) for c in st.session_state.region_data.values())

st.markdown(f"""
<div class="stat-row">
  <div class="stat-card"><div class="stat-num">{total_regions}</div><div class="stat-label">등록 지역</div></div>
  <div class="stat-card"><div class="stat-num">{total_companies}</div><div class="stat-label">전체 업체 수</div></div>
  <div class="stat-card"><div class="stat-num">{len(REGIONS)}</div><div class="stat-label">관리 가능 지역</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 레이아웃
# ─────────────────────────────────────────────
col_map, col_panel = st.columns([3, 2], gap="large")

# ── 지도 영역 ──
with col_map:
    st.markdown("#### 📍 지도에서 지역을 클릭하세요")

    debug_mode = st.checkbox("🔧 좌표 디버그 모드")

    orig_img     = load_image()
    display_img  = draw_overlay(orig_img, st.session_state.selected_region)
    coords       = streamlit_image_coordinates(display_img, key="korea_map", use_column_width=True)

    if coords and coords != st.session_state.last_click:
        st.session_state.last_click      = coords
        st.session_state.last_raw_coords = coords
        detected = detect_region(coords["x"], coords["y"])
        if detected:
            st.session_state.selected_region = detected
            st.rerun()

    if debug_mode and st.session_state.last_raw_coords:
        c   = st.session_state.last_raw_coords
        dbg = detect_region(c["x"], c["y"])
        st.markdown(f"""
        <div class="debug-box">
        🖱️ 클릭 좌표: x={c['x']}, y={c['y']}<br>
        🎯 감지된 지역: <b>{dbg if dbg else '없음 (좌표 범위 밖)'}</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### 또는 목록에서 선택")
    region_list = sorted(REGIONS.keys())
    sel_idx     = region_list.index(st.session_state.selected_region) if st.session_state.selected_region in region_list else 0
    chosen      = st.selectbox("행정구역", region_list, index=sel_idx, label_visibility="collapsed")
    if chosen != st.session_state.selected_region:
        st.session_state.selected_region = chosen
        st.rerun()

# ── 업체 관리 패널 ──
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
            name    = st.text_input("업체명 *", value=company.get("name", ""),    key=f"name_{region}_{idx}", placeholder="예) 홍길동 전자")
            address = st.text_input("위치",      value=company.get("address", ""), key=f"addr_{region}_{idx}", placeholder="예) 충북 괴산군 괴산읍")
            phone   = st.text_input("전화번호",  value=company.get("phone", ""),   key=f"phon_{region}_{idx}", placeholder="예) 043-123-4567")
            st.session_state.region_data[region][idx] = {"name": name, "address": address, "phone": phone}
            if st.button("🗑️ 삭제", key=f"del_{region}_{idx}", use_container_width=True):
                to_delete = idx
            st.markdown("---")

    if to_delete is not None:
        st.session_state.region_data[region].pop(to_delete)
        st.rerun()

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("➕ 업체 추가", use_container_width=True):
            st.session_state.region_data[region].append({"name": "", "address": "", "phone": ""})
            st.rerun()
    with btn2:
        valid   = [c for c in companies if c.get("name", "").strip()]
        dropped = len(companies) - len(valid)
        if st.button("💾 저장", type="primary", use_container_width=True):
            st.session_state.region_data[region] = valid
            if dropped:
                st.warning(f"업체명 없는 항목 {dropped}개 제외되었습니다.")
            else:
                st.success(f"✅ {region} 저장 완료!")

# ─────────────────────────────────────────────
# 전체 데이터 테이블 & CSV 다운로드
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 전체 등록 업체")

all_rows = [
    {"지역": r, "업체명": c["name"], "위치": c.get("address",""), "전화번호": c.get("phone","")}
    for r, comps in st.session_state.region_data.items()
    for c in comps if c.get("name","").strip()
]

if all_rows:
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)
else:
    st.info("아직 등록된 업체가 없습니다.")

st.download_button("📥 CSV 다운로드", data=get_csv(), file_name="업체목록.csv", mime="text/csv")