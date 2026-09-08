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
# [데이터 로드 및 전처리] CSV 파일 자동 로드 및 필터링
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

    # 필수 컬럼 체크 (동 이름의 경우 행정동명/법정동명 중 하나 사용)
    required_cols = ["상호명", "위도", "경도", "상권업종소분류명", "시도명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필수 열이 없습니다: {missing_cols}")
        return None

    # '동'을 구분할 컬럼 확인 (행정동명 우선, 없으면 법정동명 사용)
    dong_col = None
    if "행정동명" in df.columns:
        dong_col = "행정동명"
    elif "법정동명" in df.columns:
        dong_col = "법정동명"
    
    # 1) 위도, 경도 숫자형 변환 및 결측치 제거
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df = df.dropna(subset=["위도", "경도"]).copy()

    # 2) 편의점, 카페 업종만 필터링
    df = df[df["상권업종소분류명"].isin(["편의점", "카페"])].copy()

    # 동 컬럼명을 '동명'으로 통일하여 정리
    if dong_col:
        df["동명"] = df[dong_col]
    else:
        df["동명"] = "전체"

    return df

# 데이터 불러오기
df = load_data()

if df is None or df.empty:
    st.warning("표시할 매장 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 시/도 -> 시군구 -> 동 단계별 필터링
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 지역 선택")

# 1) 시/도 선택
sido_list = sorted(df["시도명"].dropna().unique().tolist())
selected_sido = st.sidebar.selectbox("시/도 선택", sido_list)

filtered_df = df[df["시도명"] == selected_sido].copy()

# 2) 시군구 선택 (데이터에 시군구명이 있는 경우)
selected_sigungu = "전체"
if "시군구명" in filtered_df.columns:
    sigungu_list = ["전체"] + sorted(filtered_df["시군구명"].dropna().unique().tolist())
    selected_sigungu = st.sidebar.selectbox("시/군/구 선택", sigungu_list)
    if selected_sigungu != "전체":
        filtered_df = filtered_df[filtered_df["시군구명"] == selected_sigungu].copy()

# 3) 동 선택 (행정동 또는 법정동)
selected_dong = "전체"
if "동명" in filtered_df.columns and filtered_df["동명"].nunique() > 1:
    dong_list = ["전체"] + sorted(filtered_df["동명"].dropna().unique().tolist())
    selected_dong = st.sidebar.selectbox("읍/면/동 선택", dong_list)
    if selected_dong != "전체":
        filtered_df = filtered_df[filtered_df["동명"] == selected_dong].copy()


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
        st.sidebar.warning("선택한 지역 조건에 매장이 없어 반경 검색을 할 수 없습니다.")
    else:
        store_options = filtered_df["상호명"].tolist()
        selected_store_idx = st.sidebar.selectbox(
            "기준 매장 선택", 
            range(len(store_options)), 
            format_func=lambda x: f"{store_options[x]} ({filtered_df.iloc[x]['상권업종소분류명']})"
        )
        
        radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

        target_store = filtered_df.iloc[selected_store_idx]
        target_lat = target_store["위도"]
        target_lon = target_store["경도"]
        selected_store_name = target_store["상호명"]

        # 하버사인 거리 계산 후 필터링
        filtered_df["거리"] = haversine_distance(
            target_lat, target_lon, filtered_df["위도"], filtered_df["경도"]
        )
        filtered_df = filtered_df[filtered_df["거리"] <= radius_km].copy()


# -----------------------------------------------------------------------------
# [메인 화면] 타이틀 및 지표 카드(st.metric)
# -----------------------------------------------------------------------------
st.title("📍 편의점 & 카페 지도 시각화")

# 지역 표시 문자열 생성
location_label = f"{selected_sido}"
if selected_sigungu != "전체":
    location_label += f" {selected_sigungu}"
if selected_dong != "전체":
    location_label += f" {selected_dong}"

if use_radius_search and selected_store_name:
    st.subheader(f"📌 기준 매장: **[{selected_store_name}]** 반경 **{radius_km} km** 이내")
else:
    st.subheader(f"🌆 **{location_label}** 매장 현황")

# 지표 계산
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
    st.info("조건에 맞는 매장이 없습니다. 사이드바에서 선택 범위를 조정해 주세요.")
else:
    color_map = {
        "편의점": "#1f77b4",  # Blue
        "카페": "#ff7f0e"     # Orange
    }

    # 줌 레벨 조정 (동 단위로 선택했거나 반경 검색 시 더 크게 확대)
    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        zoom_level = 14 if radius_km <= 1.0 else (13 if radius_km <= 3.0 else 11)
    elif selected_dong != "전체":
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 13  # 동 단위 선택 시 지도 확대
    else:
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 10 if selected_sigungu == "전체" else 12

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

    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(**map_kwargs, map_style="open-street-map")
    else:
        fig = px.scatter_mapbox(**map_kwargs, mapbox_style="open-street-map")

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="업종 구분"
    )

    st.plotly_chart(fig, use_container_width=True)
