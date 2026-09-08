import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="동별 편의점 & 카페 + 국가별 세계 유명 관광지 지도",
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
# [국가별 유명 관광지 데이터] 국가별 5개 이상 (총 40여 개 랜드마크)
# -----------------------------------------------------------------------------
@st.cache_data
def load_world_landmarks():
    landmarks = [
        # 🇫🇷 프랑스 (5개)
        {"상호명": "파리 에펠탑 (Eiffel Tower)", "위도": 48.8584, "경도": 2.2945, "상권업종소분류명": "세계 관광지", "국가": "프랑스", "동명": "파리"},
        {"상호명": "루브르 박물관 (Louvre Museum)", "위도": 48.8606, "경도": 2.3376, "상권업종소분류명": "세계 관광지", "국가": "프랑스", "동명": "파리"},
        {"상호명": "파리 개선문 (Arc de Triomphe)", "위도": 48.8738, "경도": 2.2950, "상권업종소분류명": "세계 관광지", "국가": "프랑스", "동명": "파리"},
        {"상호명": "베르사유 궁전 (Palace of Versailles)", "위도": 48.8049, "경도": 2.1204, "상권업종소분류명": "세계 관광지", "국가": "프랑스", "동명": "베르사유"},
        {"상호명": "몽생미셸 (Mont Saint-Michel)", "위도": 48.6361, "경도": -1.5115, "상권업종소분류명": "세계 관광지", "국가": "프랑스", "동명": "노르망디"},

        # 🇺🇸 미국 (5개)
        {"상호명": "뉴욕 자유의 여신상 (Statue of Liberty)", "위도": 40.6892, "경도": -74.0445, "상권업종소분류명": "세계 관광지", "국가": "미국", "동명": "뉴욕"},
        {"상호명": "뉴욕 타임스퀘어 (Times Square)", "위도": 40.7580, "경도": -73.9855, "상권업종소분류명": "세계 관광지", "국가": "미국", "동명": "뉴욕"},
        {"상호명": "샌프란시스코 금문교 (Golden Gate Bridge)", "위도": 37.8199, "경도": -122.4783, "상권업종소분류명": "세계 관광지", "국가": "미국", "동명": "샌프란시스코"},
        {"상호명": "그랜드 캐니언 (Grand Canyon)", "위도": 36.1069, "경도": -112.1129, "상권업종소분류명": "세계 관광지", "국가": "미국", "동명": "애리조나"},
        {"상호명": "워싱턴 백악관 (The White House)", "위도": 38.8977, "경도": -77.0365, "상권업종소분류명": "세계 관광지", "국가": "미국", "동명": "워싱턴 D.C."},

        # 🇯🇵 일본 (5개)
        {"상호명": "도쿄 타워 (Tokyo Tower)", "위도": 35.6586, "경도": 139.7454, "상권업종소분류명": "세계 관광지", "국가": "일본", "동명": "도쿄"},
        {"상호명": "후지산 (Mount Fuji)", "위도": 35.3606, "경도": 138.7274, "상권업종소분류명": "세계 관광지", "국가": "일본", "동명": "시즈오카"},
        {"상호명": "교토 청수사 (Kiyomizu-dera)", "위도": 34.9949, "경도": 135.7850, "상권업종소분류명": "세계 관광지", "국가": "일본", "동명": "교토"},
        {"상호명": "오사카성 (Osaka Castle)", "위도": 34.6873, "경도": 135.5262, "상권업종소분류명": "세계 관광지", "국가": "일본", "동명": "오사카"},
        {"상호명": "도쿄 스카이트리 (Tokyo Skytree)", "위도": 35.7101, "경도": 139.8107, "상권업종소분류명": "세계 관광지", "국가": "일본", "동명": "도쿄"},

        # 🇮🇹 이탈리아 (5개)
        {"상호명": "로마 콜로세움 (Colosseum)", "위도": 41.8902, "경도": 12.4922, "상권업종소분류명": "세계 관광지", "국가": "이탈리아", "동명": "로마"},
        {"상호명": "피사의 사탑 (Leaning Tower of Pisa)", "위도": 43.7230, "경도": 10.3966, "상권업종소분류명": "세계 관광지", "국가": "이탈리아", "동명": "피사"},
        {"상호명": "베네치아 리알토 다리 (Rialto Bridge)", "위도": 45.4380, "경도": 12.3359, "상권업종소분류명": "세계 관광지", "국가": "이탈리아", "동명": "베네치아"},
        {"상호명": "바티칸 성 베드로 대성당", "위도": 41.9022, "경도": 12.4539, "상권업종소분류명": "세계 관광지", "국가": "이탈리아", "동명": "바티칸"},
        {"상호명": "피렌체 두오모 성당 (Florence Cathedral)", "위도": 43.7731, "경도": 11.2560, "상권업종소분류명": "세계 관광지", "국가": "이탈리아", "동명": "피렌체"},

        # 🇬🇧 영국 (5개)
        {"상호명": "런던 빅벤 & 의회의사당 (Big Ben)", "위도": 51.5007, "경도": -0.1246, "상권업종소분류명": "세계 관광지", "국가": "영국", "동명": "런던"},
        {"상호명": "런던 타워브리지 (Tower Bridge)", "위도": 51.5055, "경도": -0.0754, "상권업종소분류명": "세계 관광지", "국가": "영국", "동명": "런던"},
        {"상호명": "런던 아이 (London Eye)", "위도": 51.5033, "경도": -0.1195, "상권업종소분류명": "세계 관광지", "국가": "영국", "동명": "런던"},
        {"상호명": "대영박물관 (British Museum)", "위도": 51.5194, "경도": -0.1270, "상권업종소분류명": "세계 관광지", "국가": "영국", "동명": "런던"},
        {"상호명": "스톤헨지 (Stonehenge)", "위도": 51.1789, "경도": -1.8262, "상권업종소분류명": "세계 관광지", "국가": "영국", "동명": "솔즈베리"},

        # 🇨🇳 중국 (5개)
        {"상호명": "베이징 만리장성 (Great Wall of China)", "위도": 40.4319, "경도": 116.5704, "상권업종소분류명": "세계 관광지", "국가": "중국", "동명": "베이징"},
        {"상호명": "베이징 자금성 (Forbidden City)", "위도": 39.9163, "경도": 116.3972, "상권업종소분류명": "세계 관광지", "국가": "중국", "동명": "베이징"},
        {"상호명": "시안 병마용 (Terracotta Army)", "위도": 34.3841, "경도": 109.2785, "상권업종소분류명": "세계 관광지", "국가": "중국", "동명": "시안"},
        {"상호명": "상하이 동방명주 (Oriental Pearl Tower)", "위도": 31.2397, "경도": 121.4998, "상권업종소분류명": "세계 관광지", "국가": "중국", "동명": "상하이"},
        {"상호명": "구이린 리강 (Li River)", "위도": 25.2736, "경도": 110.2902, "상권업종소분류명": "세계 관광지", "국가": "중국", "동명": "구이린"},

        # 🇪🇸 스페인 (5개)
        {"상호명": "바르셀로나 사그라다 파밀리아", "위도": 41.4036, "경도": 2.1744, "상권업종소분류명": "세계 관광지", "국가": "스페인", "동명": "바르셀로나"},
        {"상호명": "바르셀로나 구엘 공원 (Park Güell)", "위도": 41.4145, "경도": 2.1527, "상권업종소분류명": "세계 관광지", "국가": "스페인", "동명": "바르셀로나"},
        {"상호명": "그라나다 알람브라 궁전 (Alhambra)", "위도": 37.1773, "경도": -3.5881, "상권업종소분류명": "세계 관광지", "국가": "스페인", "동명": "그라나다"},
        {"상호명": "마드리드 왕궁 (Royal Palace of Madrid)", "위도": 40.4180, "경도": -3.7143, "상권업종소분류명": "세계 관광지", "국가": "스페인", "동명": "마드리드"},
        {"상호명": "세비야 대성당 (Seville Cathedral)", "위도": 37.3858, "경도": -5.9931, "상권업종소분류명": "세계 관광지", "국가": "스페인", "동명": "세비야"},

        # 🇰🇷 대한민국 (5개)
        {"상호명": "서울 경복궁 (Gyeongbokgung)", "위도": 37.5796, "경도": 126.9770, "상권업종소분류명": "세계 관광지", "국가": "대한민국", "동명": "세종로"},
        {"상호명": "서울 N서울타워 (N Seoul Tower)", "위도": 37.5512, "경도": 126.9882, "상권업종소분류명": "세계 관광지", "국가": "대한민국", "동명": "용산동"},
        {"상호명": "경주 불국사 (Bulguksa)", "위도": 35.7900, "경도": 129.3323, "상권업종소분류명": "세계 관광지", "국가": "대한민국", "동명": "진현동"},
        {"상호명": "제주 성산일출봉 (Seongsan Ilchulbong)", "위도": 33.4581, "경도": 126.9425, "상권업종소분류명": "세계 관광지", "국가": "대한민국", "동명": "성산읍"},
        {"상호명": "부산 해운대 해수욕장 (Haeundae Beach)", "위도": 35.1587, "경도": 129.1604, "상권업종소분류명": "세계 관광지", "국가": "대한민국", "동명": "우동"}
    ]
    return pd.DataFrame(landmarks)


# -----------------------------------------------------------------------------
# [데이터 로드 및 전처리] CSV 데이터와 관광지 데이터 통합
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    landmarks_df = load_world_landmarks()

    try:
        df = pd.read_csv("store.csv")
    except FileNotFoundError:
        try:
            df = pd.read_csv("store_filtered.csv")
        except FileNotFoundError:
            # CSV 파일이 없을 때 관광지 데이터만 반환
            return landmarks_df

    required_cols = ["상호명", "위도", "경도", "상권업종소분류명"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"데이터에 필수 열이 없습니다: {missing_cols}")
        return landmarks_df

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
    
    df["국가"] = "대한민국"

    # 상권 데이터 + 관광지 데이터 병합
    combined_df = pd.concat([df, landmarks_df], ignore_index=True)
    return combined_df

df = load_data()

if df is None or df.empty:
    st.warning("표시할 매장 및 관광지 데이터가 없습니다.")
    st.stop()


# -----------------------------------------------------------------------------
# [사이드바 설정] 국가 선택 & 세계 관광지 표시 여부 & 동 선택
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 검색 및 필터 옵션")

# 1) 국가 선택 필터
country_list = ["전체"] + sorted(df["국가"].dropna().unique().tolist())
selected_country = st.sidebar.selectbox("🌏 국가 선택", country_list)

filtered_df = df.copy()

if selected_country != "전체":
    filtered_df = filtered_df[filtered_df["국가"] == selected_country].copy()

# 2) 세계 관광지 표시 여부 체크박스
show_landmarks = st.sidebar.checkbox("⭐ 세계 유명 관광지 표시", value=True)
if not show_landmarks:
    filtered_df = filtered_df[filtered_df["상권업종소분류명"] != "세계 관광지"]

# 3) 동/도시 선택
all_dongs = ["전체"] + sorted(filtered_df["동명"].dropna().unique().tolist())
selected_dong = st.sidebar.selectbox("🏘️ 동/도시 선택", all_dongs)

if selected_dong != "전체":
    filtered_df = filtered_df[filtered_df["동명"] == selected_dong].copy()

# 4) 상호명/관광지 키워드 검색
search_keyword = st.sidebar.text_input("🔎 상호명/관광지 키워드 검색", "")
if search_keyword.strip():
    filtered_df = filtered_df[filtered_df["상호명"].str.contains(search_keyword, case=False, na=False)].copy()

# 5) 반경 검색 기능
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
            format_func=lambda x: f"[{filtered_df.iloc[x]['국가']}] {store_options[x]} ({filtered_df.iloc[x]['상권업종소분류명']})"
        )
        
        radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=50.0, value=5.0, step=0.5)

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
st.title("🗺️ 국가별 유명 관광지 & 상권 지도")

title_text = ""
if use_radius_search and selected_store_name:
    title_text = f"📌 기준 장소: **[{selected_store_name}]** 반경 **{radius_km} km** 이내"
else:
    country_label = f"[{selected_country}]" if selected_country != "전체" else "[전 세계]"
    dong_label = f" {selected_dong}" if selected_dong != "전체" else ""
    title_text = f"🌏 **{country_label}{dong_label}** 장소 및 상권 현황"

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
    st.info("조건에 맞는 장소가 없습니다. 사이드바의 국가 선택 또는 검색어를 변경해 보세요.")
else:
    color_map = {
        "편의점": "#1f77b4",     # 파란색
        "카페": "#ff7f0e",        # 주황색
        "세계 관광지": "#ffd700"  # 황금색
    }

    if use_radius_search and selected_store_name:
        center_lat = target_lat
        center_lon = target_lon
        zoom_level = 13 if radius_km <= 2.0 else (10 if radius_km <= 10.0 else 6)
    elif selected_country != "전체" or selected_dong != "전체":
        center_lat = filtered_df["위도"].mean()
        center_lon = filtered_df["경도"].mean()
        zoom_level = 11 if selected_dong != "전체" else 5
    else:
        center_lat = 20.0
        center_lon = 10.0
        zoom_level = 1

    hover_cols = {"상권업종소분류명": True, "국가": True, "동명": True, "위도": False, "경도": False}
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

    fig_map.update_traces(marker=dict(size=11))
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text="구분"
    )

    st.plotly_chart(fig_map, use_container_width=True)


    # -------------------------------------------------------------------------
    # [메인 화면] 2. 국가 / 지역별 분포 차트
    # -------------------------------------------------------------------------
    st.markdown("---")
    group_col = "국가" if selected_country == "전체" else "동명"
    st.subheader(f"📊 {group_col}별 업종 및 관광지 수 비교")

    chart_data = filtered_df.groupby([group_col, "상권업종소분류명"]).size().reset_index(name="개수")

    if not chart_data.empty:
        fig_bar = px.bar(
            chart_data,
            x=group_col,
            y="개수",
            color="상권업종소분류명",
            barmode="group",
            color_discrete_map=color_map,
            text_auto=True,
            title=f"{group_col} 기준 분포 현황"
        )
        fig_bar.update_layout(
            xaxis_title=f"{group_col} 이름",
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
        st.subheader("📋 전체 장소/매장 목록 데이터")

    @st.cache_data
    def convert_df_to_csv(data_frame):
        return data_frame.to_csv(index=False, encoding="utf-8-sig")

    csv_data = convert_df_to_csv(filtered_df)

    with col_download:
        st.download_button(
            label="📥 검색 결과 CSV 다운로드",
            data=csv_data,
            file_name="landmarks_and_stores.csv",
            mime="text/csv"
        )

    display_cols = [col for col in ["상호명", "상권업종소분류명", "국가", "동명", "위도", "경도", "거리(km)"] if col in filtered_df.columns]
    st.dataframe(filtered_df[display_cols], use_container_width=True, height=300)
