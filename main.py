import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="편의점 & 카페 지도 시각화",
    page_icon="📍",
    layout="wide"
)

# -----------------------------------------------------------------------------
# [하버사인 공식] 두 위도/경도 지점 사이의 대권 거리(km)를 계산하는 함수
# -----------------------------------------------------------------------------
def haversine_distance(lat1, lon1, lat2, lon2):
    # 지구 반지름 (단위: km)
    R = 6371.0
    
    # 라디안 단위로 변환
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # 위도 및 경도 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # 하버사인 공식 계산
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


# -----------------------------------------------------------------------------
# [데이터 로드 및 전처리] CSV 파일을 읽고 필요한 필터링을 수행하는 캐시 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 파일명 시도 (store.csv -> 없으면 store_filtered.csv)
    try:
        df = pd.read_csv("store.csv")
    except FileNotFoundError:
        try:
            df = pd.read_csv("store_filtered.csv")
        except FileNotFoundError:
            st.error("데이터 파일('store.csv' 또는 'store_filtered.csv')을 찾을 수 없습니다.")
            return None

    # 필요한 컬럼 체크
    required_cols = ["상호명", "위도", "경도", "상권업종소분류명", "시도명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필요한 열이 없습니다: {missing_cols}")
        return None

    # 1) 위도, 경도 숫자형 변환 및 결측치 제거
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df = df.dropna(subset=["위도", "경도"]).copy()

    # 2) 편의점, 카페 업종만 필터링
    df = df[df["상권업종소분류명"].isin(["편의점", "카페"])].copy()

    return df

# 데이터 불러오기
df = load_data()

# 데이터가 정상 로드되지 않은 경우 중단
if df is None or df.empty:
    st.warning("표시할 매장 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 지역 선택 및 반경 검색 옵션
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 검색 옵션")

# 1) 시/도 선택
sido_list = sorted(df["시도명"].dropna().unique().tolist())
selected_sido = st.sidebar.selectbox("지역(시/도) 선택", sido_list)

# 선택된 시/도로 기본 데이터 1차 필터링
filtered_df = df[df["시도명"] == selected_sido].copy()

# 2) 반경 검색 기능 설정
st.sidebar.markdown("---")
use_radius_search = st.sidebar.checkbox("반경 검색 사용하기")

selected_store_name = None
radius_km = 1.0

if use_radius_search:
    if filtered_df.empty:
        st.sidebar.warning("선택한 지역에 매장이 없어 반경 검색을 할 수 없습니다.")
    else:
        # 기준 매장 선택 드롭다운 (매장 중복 이름을 고려해 인덱스 기반 처리)
        store_options = filtered_df["상호명"].tolist()
        selected_store_idx = st.sidebar.selectbox(
            "기준 매장 선택", 
            range(len(store_options)), 
            format_func=lambda x: f"{store_options[x]} ({filtered_df.iloc[x]['상권업종소분류명']})"
        )
        
        # 반경(km) 지정 슬라이더
        radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

        # 기준 매장의 위도/경도
        target_store = filtered_df.iloc[selected_store_idx]
        target_lat = target_store["위도"]
        target_lon = target_store["경도"]
        selected_store_name = target_store["상호명"]

        # 하버사인 거리 계산 후 반경 이내 매장만 필터링
        filtered_df["거리"] = haversine_distance(
            target_lat, target_lon, filtered_df["위도"], filtered_df["경도"]
        )
        filtered_df = filtered_df[filtered_df["거리"] <= radius_km].copy()


# -----------------------------------------------------------------------------
# [메인 화면] 타이틀 및 지표 카드(st.metric)
# -----------------------------------------------------------------------------
st.title("📍 편의점 & 카페 지도 시각화")

# 반경 검색 설정 시 안내 부제목 표시
if use_radius_search and selected_store_name:
    st.subheader(f"📌 기준 매장: **[{selected_store_name}]** 반경 **{radius_km} km** 이내")
else:
    st.subheader(f"🌆 **{selected_sido}** 매장 현황")

# 지표(Metric) 계산
conv_count = len(filtered_df[filtered_df["상권업종소분류명"] == "편의점"])
cafe_count = len(filtered_df[filtered_df["상권업종소분류명"] == "카페"])
total_count = len(filtered_df)

# 지표 카드 3개 나란히 배치
col1, col2, col3 = st.columns(3)
col1.metric("🏪 편의점 수", f"{conv_count:,} 개")
col2.metric("☕ 카페 수", f"{cafe_count:,} 개")
col3.metric("🏢 전체 매장 수", f"{total_count:,} 개")

st.markdown("---")


# -----------------------------------------------------------------------------
# [지도 시각화] Plotly를 이용한 지도 렌더링
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.info("조건에 맞는 매장이 하나도 없습니다. 다른 지역이나 더 넓은 반경을 선택해 주세요.")
else:
    # 매장 종류별 색상 매핑 (편의점: 파란색, 카페: 주황색)
    color_map = {
        "편의점": "#1f77b4",  # Blue
        "카페": "#ff7f0e"     # Orange
    }

    # 반경 검색 사용 시 중심점 및 줌 레벨 조정
    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        # 반경에 따라 적절한 줌 레벨 계산 (반경이 작을수록 더 확대)
        zoom_level = 14 if radius_km <= 1.0 else (12 if radius_km <= 3.0 else 10)
    else:
        # 기본 지역 지도 중심점 (데이터의 평균 위경도)
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 10

    # Plotly 최신/구버전 호환 처리 (scatter_map vs scatter_mapbox)
    map_kwargs = {
        "data_frame": filtered_df,
        "lat": "위도",
        "lon": "경도",
        "color": "상권업종소분류명",
        "color_discrete_map": color_map,
        "hover_name": "상호명",
        "hover_data": {"상권업종소분류명": True, "위도": False, "경도": False},
        "zoom": zoom_level,
        "center": {"lat": center_lat, "lon": center_lon},
        "height": 650
    }

    if hasattr(px, "scatter_map"):
        # Plotly v5.24.0 이상
        fig = px.scatter_map(
            **map_kwargs,
            map_style="open-street-map"
        )
    else:
        # Plotly 구버전
        fig = px.scatter_mapbox(
            **map_kwargs,
            mapbox_style="open-street-map"
        )

    # 마진 최소화 레이아웃 설정
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="업종 구분"
    )

    # 지도 출력
    st.plotly_chart(fig, use_container_width=True)
