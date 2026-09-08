import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="동별 편의점 & 카페 지도 시각화",
    page_icon="📍",
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
# [데이터 로드 및 전처리] CSV 파일 로드 및 동 컬럼 자동 추출
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

    # 필수 컬럼 검증
    required_cols = ["상호명", "위도", "경도", "상권업종소분류명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필수 열이 없습니다: {missing_cols}")
        return None

    # '동' 구분 컬럼 자동 탐색 ('행정동명' 우선, 없으면 '법정동명')
    dong_col = None
    if "행정동명" in df.columns:
        dong_col = "행정동명"
    elif "법정동명" in df.columns:
        dong_col = "법정동명"
    
    # 1) 위도/경도 결측치 및 숫자가 아닌 데이터 제거
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df = df.dropna(subset=["위도", "경도"]).copy()

    # 2) 편의점, 카페 업종만 추출
    df = df[df["상권업종소분류명"].isin(["편의점", "카페"])].copy()

    # 3) 동 컬럼명을 '동명'으로 통일
    if dong_col:
        df["동명"] = df[dong_col].fillna("미분류")
    else:
        df["동명"] = "전체"

    return df

# 데이터 로드
df = load_data()

if df is None or df.empty:
    st.warning("표시할 매장 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 동별 필터링
# -----------------------------------------------------------------------------
st.sidebar.header("🏘️ 동 선택")

# 전체 동 목록 추출 및 선택 옵션 생성
all_dongs = ["전체"] + sorted(df["동명"].unique().tolist())
selected_dong = st.sidebar.selectbox("검색할 동을 선택하세요", all_dongs)

# 동 단위 데이터 필터링
if selected_dong != "전체":
    filtered_df = df[df["동명"] == selected_dong].copy()
else:
    filtered_df = df.copy()


# -----------------------------------------------------------------------------
# [사이드바 설정] 반경 검색 옵션
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🎯 반경 검색 옵션")
use_radius_search = st.sidebar.checkbox("반경 검색 사용하기")

selected_store_name = None
radius_km = 1.0

if use_radius_search:
    if filtered_df.empty:
        st.sidebar.warning("선택한 동에 매장이 없어 반경 검색을 할 수 없습니다.")
    else:
        # 드롭다운에서 매장 선택
        store_options = filtered_df["상호명"].tolist()
        selected_store_idx = st.sidebar.selectbox(
            "기준 매장 선택", 
            range(len(store_options)), 
            format_func=lambda x: f"{store_options[x]} ({filtered_df.iloc[x]['상권업종소분류명']})"
        )
        
        radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

        # 기준 매장 좌표 추출
        target_store = filtered_df.iloc[selected_store_idx]
        target_lat = target_store["위도"]
        target_lon = target_store["경도"]
        selected_store_name = target_store["상호명"]

        # 하버사인 공식으로 거리를 계산 후 조건에 맞는 매장만 추출
        filtered_df["거리"] = haversine_distance(
            target_lat, target_lon, filtered_df["위도"], filtered_df["경도"]
        )
        filtered_df = filtered_df[filtered_df["거리"] <= radius_km].copy()


# -----------------------------------------------------------------------------
# [메인 화면] 지표(st.metric) 및 상단 서두
# -----------------------------------------------------------------------------
st.title("📍 동별 편의점 & 카페 지도 시각화")

if use_radius_search and selected_store_name:
    st.subheader(f"📌 기준 매장: **[{selected_store_name}]** 반경 **{radius_km} km** 이내")
elif selected_dong != "전체":
    st.subheader(f"🏘️ **{selected_dong}** 매장 현황")
else:
    st.subheader("🏘️ **전체 동** 매장 현황")

# 매장 수 지표 계산
conv_count = len(filtered_df[filtered_df["상권업종소분류명"] == "편의점"])
cafe_count = len(filtered_df[filtered_df["상권업종소분류명"] == "카페"])
total_count = len(filtered_df)

col1, col2, col3 = st.columns(3)
col1.metric("🏪 편의점 수", f"{conv_count:,} 개")
col2.metric("☕ 카페 수", f"{cafe_count:,} 개")
col3.metric("🏢 전체 매장 수", f"{total_count:,} 개")

st.markdown("---")


# -----------------------------------------------------------------------------
# [지도 시각화] Plotly 렌더링
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.info("조건에 맞는 매장이 없습니다. 다른 동을 선택하거나 검색 반경을 넓혀주세요.")
else:
    color_map = {
        "편의점": "#1f77b4",  # 파란색
        "카페": "#ff7f0e"     # 주황색
    }

    # 지도 줌 레벨 및 중심 위치 설정
    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        zoom_level = 14 if radius_km <= 1.0 else (13 if radius_km <= 3.0 else 11)
    elif selected_dong != "전체":
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 14  # 특정 동 선택 시 적절한 확대 수준
    else:
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 11

    map_kwargs = {
        "data_frame": filtered_df,
        "lat": "위도",
        "lon": "경도",
        "color": "상권업종소분류명",
        "color_discrete_map": color_map,
        "hover_name": "상호명",
        "hover_data": {"상권업종소분류명": True, "동명": True, "위도": False, "경도": False},
        "zoom": zoom_level,
        "center": {"lat": center_lat, "lon": center_lon},
        "height": 650
    }

    # Plotly 버전 호환 처리 (scatter_map vs scatter_mapbox)
    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(**map_kwargs, map_style="open-street-map")
    else:
        fig = px.scatter_mapbox(**map_kwargs, mapbox_style="open-street-map")

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="업종 구분"
    )

    st.plotly_chart(fig, use_container_width=True)
