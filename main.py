import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="동별 편의점 & 카페 지도 및 상권 분석",
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
    try:
        df = pd.read_csv("store.csv")
    except FileNotFoundError:
        try:
            df = pd.read_csv("store_filtered.csv")
        except FileNotFoundError:
            st.error("데이터 파일('store.csv' 또는 'store_filtered.csv')을 찾을 수 없습니다.")
            return None

    required_cols = ["상호명", "위도", "경도", "상권업종소분류명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필수 열이 없습니다: {missing_cols}")
        return None

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

    return df

df = load_data()

if df is None or df.empty:
    st.warning("표시할 매장 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 동 선택 & 키워드 검색 & 반경 검색
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 매장 검색 옵션")

# 1) 동 선택
all_dongs = ["전체"] + sorted(df["동명"].unique().tolist())
selected_dong = st.sidebar.selectbox("🏘️ 동 선택", all_dongs)

if selected_dong != "전체":
    filtered_df = df[df["동명"] == selected_dong].copy()
else:
    filtered_df = df.copy()

# 2) 상호명 키워드 검색 기능 (새 기능)
search_keyword = st.sidebar.text_input("🔎 상호명 키워드 검색 (예: 스타벅스, CU)", "")
if search_keyword.strip():
    filtered_df = filtered_df[filtered_df["상호명"].str.contains(search_keyword, case=False, na=False)].copy()

# 3) 반경 검색 기능
st.sidebar.markdown("---")
st.sidebar.header("🎯 반경 검색 옵션")
use_radius_search = st.sidebar.checkbox("반경 검색 사용하기")

selected_store_name = None
radius_km = 1.0

if use_radius_search:
    if filtered_df.empty:
        st.sidebar.warning("조건에 맞는 매장이 없어 반경 검색을 진행할 수 없습니다.")
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

        # 하버사인 거리 계산
        filtered_df["거리(km)"] = haversine_distance(
            target_lat, target_lon, filtered_df["위도"], filtered_df["경도"]
        ).round(2)
        filtered_df = filtered_df[filtered_df["거리(km)"] <= radius_km].copy()


# -----------------------------------------------------------------------------
# [메인 화면] 지표(st.metric) 및 타이틀
# -----------------------------------------------------------------------------
st.title("📍 동별 편의점 & 카페 지도 및 상권 분석")

# 서두 안내문 설정
title_text = ""
if use_radius_search and selected_store_name:
    title_text = f"📌 기준 매장: **[{selected_store_name}]** 반경 **{radius_km} km** 이내"
elif selected_dong != "전체":
    title_text = f"🏘️ **{selected_dong}** 매장 현황"
else:
    title_text = "🏘️ **전체 동** 매장 현황"

if search_keyword.strip():
    title_text += f" (검색어: '{search_keyword}')"

st.subheader(title_text)

# 지표 카드 계산
conv_count = len(filtered_df[filtered_df["상권업종소분류명"] == "편의점"])
cafe_count = len(filtered_df[filtered_df["상권업종소분류명"] == "카페"])
total_count = len(filtered_df)

col1, col2, col3 = st.columns(3)
col1.metric("🏪 편의점 수", f"{conv_count:,} 개")
col2.metric("☕ 카페 수", f"{cafe_count:,} 개")
col3.metric("🏢 전체 매장 수", f"{total_count:,} 개")

st.markdown("---")


# -----------------------------------------------------------------------------
# [메인 화면] 1. 지도 시각화
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.info("조건에 맞는 매장이 없습니다. 사이드바의 검색어나 동 선택을 변경해 보세요.")
else:
    color_map = {
        "편의점": "#1f77b4",  # 파란색
        "카페": "#ff7f0e"     # 주황색
    }

    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        zoom_level = 14 if radius_km <= 1.0 else (13 if radius_km <= 3.0 else 11)
    elif selected_dong != "전체":
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 14
    else:
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 11

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
        "height": 600
    }

    if hasattr(px, "scatter_map"):
        fig_map = px.scatter_map(**map_kwargs, map_style="open-street-map")
    else:
        fig_map = px.scatter_mapbox(**map_kwargs, mapbox_style="open-street-map")

    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="업종 구분"
    )

    st.plotly_chart(fig_map, use_container_width=True)


    # -------------------------------------------------------------------------
    # [메인 화면] 2. 동별 매장 비교 막대 차트 (새 기능)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 동별 편의점 vs 카페 매장 수 비교")

    # 동별, 업종별 매장 수 집계
    chart_data = filtered_df.groupby(["동명", "상권업종소분류명"]).size().reset_index(name="매장 수")

    if not chart_data.empty:
        fig_bar = px.bar(
            chart_data,
            x="동명",
            y="매장 수",
            color="상권업종소분류명",
            barmode="group",
            color_discrete_map=color_map,
            text_auto=True,
            title="지역 내 동별 매장 분포"
        )
        fig_bar.update_layout(
            xaxis_title="동 이름",
            yaxis_title="매장 개수",
            legend_title_text="업종 구분",
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)


    # -------------------------------------------------------------------------
    # [메인 화면] 3. 데이터 테이블 및 CSV 다운로드 (새 기능)
    # -------------------------------------------------------------------------
    st.markdown("---")
    col_table_header, col_download = st.columns([3, 1])

    with col_table_header:
        st.subheader("📋 매장 목록 데이터")

    # CSV 변환 함수
    @st.cache_data
    def convert_df_to_csv(data_frame):
        return data_frame.to_csv(index=False, encoding="utf-8-sig")

    csv_data = convert_df_to_csv(filtered_df)

    # 다운로드 버튼 표시
    with col_download:
        st.download_button(
            label="📥 검색 결과 CSV 다운로드",
            data=csv_data,
            file_name="filtered_stores.csv",
            mime="text/csv"
        )

    # 매장 데이터 표 표출 (원하는 컬럼 위주)
    display_cols = [col for col in ["상호명", "상권업종소분류명", "동명", "위도", "경도", "거리(km)"] if col in filtered_df.columns]
    st.dataframe(filtered_df[display_cols], use_container_width=True, height=300)
