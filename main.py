import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="동별 편의점 & 카페 + 세계 유명 관광지 지도",
    page_icon="🗺️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# [하버사인 공식] 두 위도/경도 지점 사이의 대권 거리(km)를 계산하는 함수
# -----------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # 지구 반지름 (km)
    
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


# -----------------------------------------------------------------------------
# [세계 주요 관광지 데이터] 기본 제공 레이어
# -----------------------------------------------------------------------------
@st.cache_data
def load_world_landmarks():
    landmarks = [
        {"상호명": "파리 에펠탑 (Eiffel Tower)", "위도": 48.8584, "경도": 2.2945, "상권업종소분류명": "세계 관광지", "동명": "파리"},
        {"상호명": "루브르 박물관 (Louvre)", "위도": 48.8606, "경도": 2.3376, "상권업종소분류명": "세계 관광지", "동명": "파리"},
        {"상호명": "뉴욕 타임스퀘어 (Times Square)", "위도": 40.7580, "경도": -73.9855, "상권업종소분류명": "세계 관광지", "동명": "뉴욕"},
        {"상호명": "로마 콜로세움 (Colosseum)", "위도": 41.8902, "경도": 12.4922, "상권업종소분류명": "세계 관광지", "동명": "로마"},
        {"상호명": "도쿄 타워 (Tokyo Tower)", "위도": 35.6586, "경도": 139.7454, "상권업종소분류명": "세계 관광지", "동명": "도쿄"},
        {"상호명": "아그라 타지마할 (Taj Mahal)", "위도": 27.1751, "경도": 78.0421, "상권업종소분류명": "세계 관광지", "동명": "아그라"},
        {"상호명": "시드니 오페라 하우스 (Opera House)", "위도": -33.8568, "경도": 151.2153, "상권업종소분류명": "세계 관광지", "동명": "시드니"},
        {"상호명": "런던 타워브리지 (Tower Bridge)", "위도": 51.5055, "경도": -0.0754, "상권업종소분류명": "세계 관광지", "동명": "런던"},
        {"상호명": "서울 N서울타워 (N Seoul Tower)", "위도": 37.5512, "경도": 126.9882, "상권업종소분류명": "세계 관광지", "동명": "서울"},
        {"상호명": "바르셀로나 사그라다 파밀리아", "위도": 41.4036, "경도": 2.1744, "상권업종소분류명": "세계 관광지", "동명": "바르셀로나"}
    ]
    return pd.DataFrame(landmarks)


# -----------------------------------------------------------------------------
# [데이터 로드 및 전처리] CSV 파일 로드 및 동 컬럼 자동 추출
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("store.csv")
    except FileNotFoundError:
        try:
            df = pd.read_csv("store_filtered.csv")
        except FileNotFoundError:
            # CSV 파일이 없을 때는 세계 관광지 데이터만 기본으로 반환
            return load_world_landmarks()

    required_cols = ["상호명", "위도", "경도", "상권업종소분류명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필수 열이 없습니다: {missing_cols}")
        return load_world_landmarks()

    # 동 구분 컬럼 자동 탐색
    dong_col = None
    if "행정동명" in df.columns:
        dong_col = "행정동명"
    elif "법정동명" in df.columns:
        dong_col = "법정동명"
    
    # 위도/경도 데이터 정제
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df = df.dropna(subset=["위도", "경도"]).copy()

    # 편의점, 카페 업종만 추출
    df = df[df["상권업종소분류명"].isin(["편의점", "카페"])].copy()

    # 동 컬럼명을 '동명'으로 통일
    if dong_col:
        df["동명"] = df[dong_col].fillna("미분류")
    else:
        df["동명"] = "전체"

    # 세계 관광지 데이터 통합
    landmarks_df = load_world_landmarks()
    combined_df = pd.concat([df, landmarks_df], ignore_index=True)

    return combined_df

df = load_data()

if df is None or df.empty:
    st.warning("표시할 매장 및 관광지 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 세계 관광지 포함 여부 & 동 선택 & 키워드/반경 검색
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 매장 및 관광지 검색")

# 1) 세계 관광지 표시 여부 체크박스
show_landmarks = st.sidebar.checkbox("⭐ 세계 유명 관광지 표시", value=True)

# 2) 동 선택
all_dongs = ["전체"] + sorted(df["동명"].dropna().unique().tolist())
selected_dong = st.sidebar.selectbox("🏘️ 동/도시 선택", all_dongs)

filtered_df = df.copy()

# 세계 관광지 필터링 조건 적용
if not show_landmarks:
    filtered_df = filtered_df[filtered_df["상권업종소분류명"] != "세계 관광지"]

# 동 선택 필터링
if selected_dong != "전체":
    filtered_df = filtered_df[filtered_df["동명"] == selected_dong].copy()

# 3) 상호명 키워드 검색
search_keyword = st.sidebar.text_input("🔎 상호명/관광지 검색 (예: 에펠탑, 스타벅스)", "")
if search_keyword.strip():
    filtered_df = filtered_df[filtered_df["상호명"].str.contains(search_keyword, case=False, na=False)].copy()

# 4) 반경 검색 기능
st.sidebar.markdown("---")
st.sidebar.header("🎯 반경 검색 옵션")
use_radius_search = st.sidebar.checkbox("반경 검색 사용하기")

selected_store_name = None
radius_km = 1.0

if use_radius_search:
    if filtered_df.empty:
        st.sidebar.warning("조건에 맞는 장소가 없어 반경 검색을 진행할 수 없습니다.")
    else:
        store_options = filtered_df["상호명"].tolist()
        selected_store_idx = st.sidebar.selectbox(
            "기준 장소/매장 선택", 
            range(len(store_options)), 
            format_func=lambda x: f"{store_options[x]} ({filtered_df.iloc[x]['상권업종소분류명']})"
        )
        
        radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=20.0, value=2.0, step=0.5)

        target_store = filtered_df.iloc[selected_store_idx]
        target_lat = target_store["위도"]
        target_lon = target_store["경도"]
        selected_store_name = target_store["상호명"]

        # 거리 계산
        filtered_df["거리(km)"] = haversine_distance(
            target_lat, target_lon, filtered_df["위도"], filtered_df["경도"]
        ).round(2)
        filtered_df = filtered_df[filtered_df["거리(km)"] <= radius_km].copy()


# -----------------------------------------------------------------------------
# [메인 화면] 지표(st.metric) 및 타이틀
# -----------------------------------------------------------------------------
st.title("🗺️ 편의점 & 카페 + 세계 유명 관광지 지도")

title_text = ""
if use_radius_search and selected_store_name:
    title_text = f"📌 기준 장소: **[{selected_store_name}]** 반경 **{radius_km} km** 이내"
elif selected_dong != "전체":
    title_text = f"🏘️ **{selected_dong}** 매장 및 관광지 현황"
else:
    title_text = "🌏 **전체** 매장 및 관광지 현황"

if search_keyword.strip():
    title_text += f" (검색어: '{search_keyword}')"

st.subheader(title_text)

# 지표 카드 계산
conv_count = len(filtered_df[filtered_df["상권업종소분류명"] == "편의점"])
cafe_count = len(filtered_df[filtered_df["상권업종소분류명"] == "카페"])
landmark_count = len(filtered_df[filtered_df["상권업종소분류명"] == "세계 관광지"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("🏪 편의점 수", f"{conv_count:,} 개")
col2.metric("☕ 카페 수", f"{cafe_count:,} 개")
col3.metric("⭐ 관광지 수", f"{landmark_count:,} 개")
col4.metric("🏢 전체 장소 수", f"{len(filtered_df):,} 개")

st.markdown("---")


# -----------------------------------------------------------------------------
# [메인 화면] 1. Plotly 지도 시각화
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.info("조건에 맞는 장소가 없습니다. 사이드바의 검색어 또는 옵션을 변경해 보세요.")
else:
    # 업종 및 관광지별 색상 매핑
    color_map = {
        "편의점": "#1f77b4",     # 파란색
        "카페": "#ff7f0e",        # 주황색
        "세계 관광지": "#ffd700"  # 황금색
    }

    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        zoom_level = 13 if radius_km <= 2.0 else (10 if radius_km <= 10.0 else 6)
    elif selected_dong != "전체":
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 12
    else:
        # 전체 보기 시 지도 중심
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 2 if landmark_count > 0 and len(filtered_df) < 50 else 10

    hover_cols = {"상권업종소분류명": True, "동명": True, "위도": False, "경도": False}
    if "거리(km)" in filtered_df.columns:
        hover_cols["거리(km)"] = True

    map_kwargs = {
        "data_frame": filtered_df,
        "lat": "위도",
        "lon": "경도",
        "color": "상권업종소분류명",
        "color_discrete_map": color_map,
        "hover_name": "상호명",
        "hover_data": hover_cols,
        "zoom": zoom_level,
        "center": {"lat": center_lat, "lon": center_lon},
        "height": 650
    }

    if hasattr(px, "scatter_map"):
        fig_map = px.scatter_map(**map_kwargs, map_style="open-street-map")
    else:
        fig_map = px.scatter_mapbox(**map_kwargs, mapbox_style="open-street-map")

    fig_map.update_traces(marker=dict(size=12))
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="구분"
    )

    st.plotly_chart(fig_map, use_container_width=True)


    # -------------------------------------------------------------------------
    # [메인 화면] 2. 동/지역별 분포 차트
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 지역별 업종 및 관광지 수 비교")

    chart_data = filtered_df.groupby(["동명", "상권업종소분류명"]).size().reset_index(name="개수")

    if not chart_data.empty:
        fig_bar = px.bar(
            chart_data,
            x="동명",
            y="개수",
            color="상권업종소분류명",
            barmode="group",
            color_discrete_map=color_map,
            text_auto=True,
            title="지역/동별 상세 분포"
        )
        fig_bar.update_layout(
            xaxis_title="지역 / 동 이름",
            yaxis_title="개수",
            legend_title_text="구분",
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)


    # -------------------------------------------------------------------------
    # [메인 화면] 3. 데이터 목록 및 CSV 다운로드
    # -------------------------------------------------------------------------
    st.markdown("---")
    col_table_header, col_download = st.columns([3, 1])

    with col_table_header:
        st.subheader("📋 장소 목록 데이터")

    @st.cache_data
    def convert_df_to_csv(data_frame):
        return data_frame.to_csv(index=False, encoding="utf-8-sig")

    csv_data = convert_df_to_csv(filtered_df)

    with col_download:
        st.download_button(
            label="📥 검색 결과 CSV 다운로드",
            data=csv_data,
            file_name="places_and_stores.csv",
            mime="text/csv"
        )

    display_cols = [col for col in ["상호명", "상권업종소분류명", "동명", "위도", "경도", "거리(km)"] if col in filtered_df.columns]
    st.dataframe(filtered_df[display_cols], use_container_width=True, height=300)
