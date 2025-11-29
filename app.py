import streamlit as st
import pandas as pd
import numpy as np
import folium
import streamlit.components.v1 as components

# ====================================================================
# --- 1. 헬퍼 함수 정의 (데이터 로드 및 거리 계산) ---
# ====================================================================

@st.cache_data(show_spinner="인프라 데이터 통합 로드 중...")
def load_all_infrastructure_data():
    all_data = []
    debug_info = [] 
    
    def read_csv_safe(file_path):
        encodings = ['utf-8', 'cp949', 'euc-kr']
        for enc in encodings:
            try:
                return pd.read_csv(file_path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"❌ '{file_path}' 파일을 읽을 수 없습니다.")
    
    # 1. 학교
    try:
        df_school = read_csv_safe("school.csv")
        df_school = df_school.rename(columns={'school_name': 'infra_name'})
        all_data.append(df_school[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 학교: {len(df_school)}개 로드")
    except: debug_info.append("❌ 학교 파일 없음/오류")
        
    # 2. 문화시설
    try:
        df_art = read_csv_safe("art.csv")
        df_art['type'] = '문화시설'
        df_art = df_art.rename(columns={'문화시설명': 'infra_name'})
        all_data.append(df_art[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 문화시설: {len(df_art)}개 로드")
    except: debug_info.append("❌ 문화시설 파일 없음/오류")

    # 3. 병원 (대형/일반 분류 로직 포함)
    try:
        df_hospital = read_csv_safe("hospital.csv")
        def classify_hospital(row):
            val = str(row.get('응급의료기관코드명', ''))
            if '응급' in val and '이외' not in val: return '대형병원'
            if row.get('응급실운영여부(1/2)') == 1: return '대형병원'
            return '일반병원' 

        df_hospital['type'] = df_hospital.apply(classify_hospital, axis=1)
        if '기관명' in df_hospital.columns:
            df_hospital = df_hospital.rename(columns={'기관명': 'infra_name'})
            all_data.append(df_hospital[['type', 'infra_name', 'lat', 'lng']])
            debug_info.append(f"✅ 병원: {len(df_hospital)}개 로드")
    except: debug_info.append("❌ 병원 파일 없음/오류")

    # 4. 공원
    try:
        df_park = read_csv_safe("park.csv")
        df_park['type'] = '공원'
        df_park = df_park.rename(columns={'공원명': 'infra_name'})
        all_data.append(df_park[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 공원: {len(df_park)}개 로드")
    except: debug_info.append("❌ 공원 파일 없음/오류")

    # 5. 버스정류장
    try:
        df_bus = read_csv_safe("bus_stop.csv")
        df_bus['type'] = '버스정류장'
        df_bus = df_bus.rename(columns={'name': 'infra_name'})
        all_data.append(df_bus[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 버스정류장: {len(df_bus)}개 로드")
    except: debug_info.append("❌ 버스정류장 파일 없음/오류")

    # 6. 지하철역
    try:
        df_subway = read_csv_safe("subway.csv")
        df_subway['type'] = '지하철역'
        if 'name' in df_subway.columns: df_subway = df_subway.rename(columns={'name': 'infra_name'})
        elif '역사명' in df_subway.columns: df_subway = df_subway.rename(columns={'역사명': 'infra_name'})
        all_data.append(df_subway[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 지하철역: {len(df_subway)}개 로드")
    except: debug_info.append("❌ 지하철역 파일 없음/오류")

    # 7. 대형마트
    try:
        df_market = read_csv_safe("big_market.csv")
        df_market['type'] = df_market.get('업태구분명', '대형마트')
        df_market = df_market.rename(columns={'사업장명': 'infra_name'})
        all_data.append(df_market[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 대형마트: {len(df_market)}개 로드")
    except: debug_info.append("❌ 대형마트 파일 없음/오류")

    # 8. 체육시설
    try:
        df_gym = read_csv_safe("gym.csv")
        df_gym = df_gym.rename(columns={'name': 'infra_name', '위도': 'lat', '경도': 'lng'})
        df_gym['type'] = df_gym['type'].fillna('기타')
        all_data.append(df_gym[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 체육시설: {len(df_gym)}개 로드")
    except: debug_info.append("❌ 체육시설 파일 없음/오류")

    if not all_data: return pd.DataFrame(), debug_info
    return pd.concat(all_data, ignore_index=True), debug_info

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c * 1000.0

@st.cache_data(show_spinner="필터링 로직 실행 중...")
def filter_apartments(df_apt, df_infra, selected_filters):
    if df_apt is None or df_apt.empty or not selected_filters:
        return pd.DataFrame()

    filtered_apt_list = []
    
    # 인프라 데이터 미리 필터링 (속도 최적화)
    infra_dict = {}
    for infra_type in selected_filters.keys():
        infra_dict[infra_type] = df_infra[df_infra['type'] == infra_type].copy()

    for index, apt in df_apt.iterrows():
        apt_lat = apt['lat']
        apt_lng = apt['lng']
        
        meets_all_criteria = True
        individual_counts = {f'{t}_카운트': 0 for t in selected_filters.keys()}

        for infra_type, radius_m in selected_filters.items():
            infra_of_type = infra_dict[infra_type]
            if infra_of_type.empty:
                meets_all_criteria = False; break

            distances = haversine(apt_lat, apt_lng, infra_of_type['lat'].values, infra_of_type['lng'].values)
            
            # 하나라도 반경 내에 없으면 탈락 (AND 조건)
            if np.min(distances) > radius_m:
                meets_all_criteria = False; break

            count_type = np.sum(distances <= radius_m)
            individual_counts[infra_type + '_카운트'] = int(count_type)

        if meets_all_criteria:
            apt_data = apt.to_dict() # 여기서 원본 컬럼(주소 포함)이 다 들어감
            apt_data.update(individual_counts)
            if '자치구명' not in apt_data: apt_data['자치구명'] = ''
            filtered_apt_list.append(apt_data)

    df_filtered_apt = pd.DataFrame(filtered_apt_list)
    
    if df_filtered_apt.empty:
        return pd.DataFrame()

    count_cols = [col for col in df_filtered_apt.columns if col.endswith('_카운트')]
    df_filtered_apt['Total_Count'] = df_filtered_apt[count_cols].sum(axis=1)
        
    return df_filtered_apt.sort_values(by='Total_Count', ascending=False).drop(columns=['Total_Count']).copy()

def get_apartment_infrastructure_details(apt_data, df_infra, selected_filters):
    apt_lat = apt_data['latitude']
    apt_lng = apt_data['longitude']
    details_list = []
    
    for infra_type, radius_m in selected_filters.items():
        infra_of_type = df_infra[df_infra['type'] == infra_type]
        for idx, item in infra_of_type.iterrows():
            distance = haversine(apt_lat, apt_lng, item['lat'], item['lng'])
            if distance <= radius_m:
                details_list.append({
                    '인프라_유형': infra_type,
                    '시설명': item['infra_name'],
                    '거리(m)': int(round(distance)),
                    'lat': item['lat'],  
                    'lng': item['lng']    
                })
    return pd.DataFrame(details_list).sort_values(by='거리(m)')

# ====================================================================
# --- 2. 지도 생성 함수 ---
# ====================================================================

def create_folium_map(df_map, df_infra, selected_filters):
    center_lat = df_map['latitude'].mean()
    center_lng = df_map['longitude'].mean()

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12, tiles='https://xdworld.vworld.kr/2d/Base/service/{z}/{x}/{y}.png', attr='Vworld')
    
    colors = {'초등학교': 'blue', '중학교': 'green', '고등학교': 'orange', '문화시설': 'purple', '공원': 'darkgreen', '대형병원': 'red', '일반병원': 'lightred', '버스정류장': 'cadetblue', '지하철역': 'darkblue', '대형마트': 'pink', '백화점': 'beige', '수영장': 'lightblue', '생활체육관': 'lightgreen', '축구장': 'lightgreen', '야구장': 'orange', '농구장': 'orange', '테니스장': 'lightgreen', '배드민턴장': 'cadetblue', '골프연습장': 'green', '기타': 'gray'}
    icons = {'초등학교': 'graduation-cap', '중학교': 'university', '고등학교': 'landmark', '문화시설': 'palette', '공원': 'tree', '대형병원': 'ambulance', '일반병원': 'plus-square', '버스정류장': 'bus', '지하철역': 'subway', '대형마트': 'shopping-cart', '백화점': 'gift', '수영장': 'person-swimming', '생활체육관': 'dumbbell', '축구장': 'futbol', '야구장': 'baseball-bat-ball', '농구장': 'basketball', '테니스장': 'table-tennis-paddle-ball', '배드민턴장': 'feather', '골프연습장': 'golf-ball-tee', '기타': 'star'}
    
    relevant_infra_list = []
    # 인프라 마커 추가 로직
    for infra_type, radius_m in selected_filters.items():
        infra_of_type = df_infra[df_infra['type'] == infra_type].copy()
        # 벡터화 연산으로 거리 계산 최적화 가능하나 여기선 순회 유지
        for idx, item in infra_of_type.iterrows():
            distances = haversine(item['lat'], item['lng'], df_map['latitude'].values, df_map['longitude'].values)
            if np.min(distances) <= radius_m:
                 relevant_infra_list.append(item.to_dict())

    df_relevant_infra = pd.DataFrame(relevant_infra_list).drop_duplicates(subset=['infra_name', 'lat', 'lng'])

    if not df_relevant_infra.empty:
        infra_group = folium.FeatureGroup(name="발견된 인프라", show=True).add_to(m)
        for idx, item in df_relevant_infra.iterrows():
            folium.Marker(
                location=[item['lat'], item['lng']],
                popup=f"{item['infra_name']}",
                icon=folium.Icon(color=colors.get(item['type'], 'gray'), icon=icons.get(item['type'], 'star'), prefix='fa')
            ).add_to(infra_group)

    # 아파트 마커
    apt_group = folium.FeatureGroup(name="필터링된 아파트", show=True).add_to(m)
    for idx, apt in df_map.iterrows():
        folium.Marker(
            location=[apt['latitude'], apt['longitude']],
            popup=f"{apt['자치구명']} {apt['건물명']}",
            icon=folium.Icon(color='darkpurple', icon='home', prefix='fa')
        ).add_to(apt_group)
        
    folium.LayerControl(collapsed=True).add_to(m)
    return components.html(m.get_root().render(), height=740, scrolling=True)

def create_detailed_map(apt_data, df_details):
    center_lat = apt_data['latitude']
    center_lng = apt_data['longitude']
    m = folium.Map(location=[center_lat, center_lng], zoom_start=14, tiles='https://xdworld.vworld.kr/2d/Base/service/{z}/{x}/{y}.png', attr='Vworld')
    
    # 아파트 마커
    folium.Marker(
        location=[center_lat, center_lng],
        popup=f"선택: {apt_data['자치구명']} {apt_data['건물명']}",
        icon=folium.Icon(color='black', icon='building', prefix='fa')
    ).add_to(m)
    
    colors = {'초등학교': 'blue', '중학교': 'green', '고등학교': 'orange', '문화시설': 'purple', '공원': 'darkgreen', '대형병원': 'red', '일반병원': 'lightred', '버스정류장': 'cadetblue', '지하철역': 'darkblue', '대형마트': 'pink', '백화점': 'beige', '수영장': 'lightblue', '생활체육관': 'lightgreen', '축구장': 'lightgreen', '야구장': 'orange', '농구장': 'orange', '테니스장': 'lightgreen', '배드민턴장': 'cadetblue', '골프연습장': 'green', '기타': 'gray'}
    icons = {'초등학교': 'graduation-cap', '중학교': 'university', '고등학교': 'landmark', '문화시설': 'palette', '공원': 'tree', '대형병원': 'ambulance', '일반병원': 'plus-square', '버스정류장': 'bus', '지하철역': 'subway', '대형마트': 'shopping-cart', '백화점': 'gift', '수영장': 'person-swimming', '생활체육관': 'dumbbell', '축구장': 'futbol', '야구장': 'baseball-bat-ball', '농구장': 'basketball', '테니스장': 'table-tennis-paddle-ball', '배드민턴장': 'feather', '골프연습장': 'golf-ball-tee', '기타': 'star'}

    for idx, item in df_details.iterrows():
        itype = item['인프라_유형']
        folium.Marker(
            location=[item['lat'], item['lng']],
            popup=f"{item['시설명']} ({item['거리(m)']}m)",
            icon=folium.Icon(color=colors.get(itype,'gray'), icon=icons.get(itype,'star'), prefix='fa')
        ).add_to(m)
        folium.PolyLine(
            locations=[(center_lat, center_lng), (item['lat'], item['lng'])],
            color=colors.get(itype,'gray'), weight=2, opacity=0.7
        ).add_to(m)

    return components.html(m.get_root().render(), height=740, scrolling=True)

# ====================================================================
# --- 3. Streamlit 애플리케이션 메인 함수 ---
# ====================================================================

def main():
    st.set_page_config(layout="wide")
    
    # CSS 스타일링
    st.markdown("""
    <style>
    .metric-container { display: flex; justify-content: center; align-items: center; padding: 8px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e0e0e0; min-width: 100px; }
    .metric-box { text-align: center; width: 100%; }
    .metric-label { font-size: 1.0rem; font-weight: 700; color: #31333F; margin-bottom: 2px; white-space: nowrap; }
    .metric-value { font-size: 0.9rem; color: #555; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🏡 인프라 접근성 분석 대시보드")
    st.markdown("---")

    df_infra, debug_info = load_all_infrastructure_data()
    
    # [사이드바]
    st.sidebar.markdown("### 🏢 아파트 데이터 업로드")
    with st.sidebar.container(border=True):
        uploaded_file = st.file_uploader("", type="csv", label_visibility="hidden")
    
    df_apt = None
    if uploaded_file is not None:
        try:
            df_apt_temp = pd.read_csv(uploaded_file)
            # [수정] 조인 Key로 사용할 '주소' 컬럼 필수 확인
            required_cols = ['자치구명', '주소', '건물명', 'lat', 'lng']
            if not all(col in df_apt_temp.columns for col in required_cols):
                st.sidebar.error(f"❌ 필수 컬럼 누락! CSV 파일에 다음 컬럼이 모두 있어야 합니다:\n{', '.join(required_cols)}")
            else:
                st.sidebar.success(f"✅ **{uploaded_file.name}** 데이터 로드 완료.")
                df_apt = df_apt_temp.copy()
        except Exception as e:
            st.sidebar.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")
            df_apt = None
    else:
        st.sidebar.info("업로드할 CSV 파일을 선택하거나 드래그 앤 드롭하세요.")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    # [사이드바] 인프라 필터 설정
    st.sidebar.markdown("### 🎛️ 인프라 필터 설정")
    selected_filters = {}
    max_radius = 5000

    with st.sidebar.container(border=True):
        # 학교
        st.markdown("#### 🏫 학교 시설")
        if st.checkbox("초등학교", value=False): selected_filters['초등학교'] = st.slider("초등학교 (m)", 100, max_radius, 500, 50, key="s_elem")
        if st.checkbox("중학교", value=False): selected_filters['중학교'] = st.slider("중학교 (m)", 100, max_radius, 1000, 50, key="s_mid")
        if st.checkbox("고등학교", value=False): selected_filters['고등학교'] = st.slider("고등학교 (m)", 100, max_radius, 1500, 50, key="s_high")
        st.markdown("<br>", unsafe_allow_html=True)
        # 병원
        st.markdown("#### 🏥 병원 시설")
        if st.checkbox("대형병원", value=False): selected_filters['대형병원'] = st.slider("대형병원 (m)", 100, max_radius, 1500, 50, key="s_er")
        if st.checkbox("일반병원", value=False): selected_filters['일반병원'] = st.slider("일반병원 (m)", 100, max_radius, 1000, 50, key="s_gen")
        st.markdown("<br>", unsafe_allow_html=True)
        # 교통
        st.markdown("#### 🚗 교통 시설")
        if st.checkbox("버스정류장", value=False): selected_filters['버스정류장'] = st.slider("버스정류장 (m)", 100, max_radius, 500, 50, key="s_bus")
        if st.checkbox("지하철역", value=False): selected_filters['지하철역'] = st.slider("지하철역 (m)", 100, max_radius, 1000, 50, key="s_sub")
        st.markdown("<br>", unsafe_allow_html=True)
        # 편의
        st.markdown("#### 🛒 생활 편의")
        if st.checkbox("대형마트", value=False): selected_filters['대형마트'] = st.slider("대형마트 (m)", 100, max_radius, 2000, 50, key="s_mart")
        if st.checkbox("백화점", value=False): selected_filters['백화점'] = st.slider("백화점 (m)", 100, max_radius, 3000, 50, key="s_dept")
        st.markdown("<br>", unsafe_allow_html=True)
        # 문화
        st.markdown("#### 🎨 문화/여가")
        if st.checkbox("공원", value=False): selected_filters['공원'] = st.slider("공원 (m)", 100, max_radius, 1000, 50, key="s_park")
        if st.checkbox("문화시설", value=False): selected_filters['문화시설'] = st.slider("문화시설 (m)", 100, max_radius, 2000, 50, key="s_art")
        st.markdown("<br>", unsafe_allow_html=True)

    if df_apt is None:
        st.info("👋 **환영합니다!** 분석을 시작하려면 **왼쪽 사이드바**에서 아파트 데이터 파일(CSV)을 업로드해주세요.")
        return
        
    if not selected_filters:
        st.warning("👈 **안내:** 왼쪽 사이드바에서 분석할 **인프라 종류를 하나 이상 체크**해 주세요.")
        return

    # 태그 표시
    with st.container(border=True):
        st.markdown("### 🔍 필터링 기준")
        icon_map_filter = {'초등학교':'🎒', '중학교':'📚', '고등학교':'🏛️', '문화시설':'🎨', '공원':'🌳', '대형병원':'🚑', '일반병원':'🏥', '버스정류장':'🚌', '지하철역':'🚇', '대형마트':'🛒', '백화점':'🛍️'}
        tags_html = """<div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 8px; align-items: center; width: 100%; margin-bottom: 24px;">"""
        for key, radius in selected_filters.items():
            icon = icon_map_filter.get(key, '📍')
            tags_html += f"""<div style="display: inline-flex; align-items: center; background-color: #f0f2f6; border: 1px solid #d1d5db; border-radius: 20px; padding: 6px 12px; color: #31333F; font-size: 14px; font-weight: 500; white-space: nowrap; box-shadow: 0 1px 2px rgba(0,0,0,0.05);"><span style="margin-right: 6px; font-size: 16px;">{icon}</span>{key} <span style="color: #666; font-size: 12px; margin-left: 6px; font-weight: 400;">{radius}m</span></div>"""
        tags_html += "</div>"
        st.markdown(tags_html, unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # 필터링 실행
    # ---------------------------------------------------------
    df_filtered = filter_apartments(df_apt, df_infra, selected_filters)
    
    if df_filtered.empty:
        st.warning("선택된 조건(거리/인프라 종류)에 해당하는 아파트가 없습니다.")
        return
    
    # [수정] 지도 및 화면 표시용으로 이름 변경 (lat, lng -> latitude, longitude)
    df_map = df_filtered.rename(columns={'lat': 'latitude', 'lng': 'longitude'})
    df_map['display_name'] = "[" + df_map['자치구명'] + "] " + df_map['건물명']
    
    apartment_names = ['--- 전체 요약 보기 ---'] + df_map['display_name'].tolist()
    
    head_col1, head_col2 = st.columns(2)
    with head_col1: header_left_placeholder = st.empty()
    with head_col2: header_right_placeholder = st.empty()
    
    body_col1, body_col2 = st.columns(2)
    
    with body_col2:
        with st.container(border=True):
            st.markdown("##### 📍 매물 선택")
            selected_name_display = st.selectbox("매물 선택", apartment_names, key='drill_down_select', label_visibility='collapsed')
        summary_placeholder = st.empty()
        table_container = st.container(border=True)

    if selected_name_display == '--- 전체 요약 보기 ---':
        # [A] 전체 요약 모드
        with header_left_placeholder.container():
            with st.container(border=True):
                st.markdown(f"#### ✅ 최종 검색 결과: 총 **{len(df_filtered)}** 개의 매물")
        
        with header_right_placeholder.container():
            with st.container(border=True):
                st.markdown("#### 🏢 아파트 추천 목록")
        
        with body_col1:
            create_folium_map(df_map, df_infra, selected_filters)
            
        with table_container:
            st.markdown("##### 📋 아파트 상세 목록")
            
            # [수정] '주소' 컬럼을 display_cols에 포함시킴 (나중에 Export를 위해)
            display_cols = ['자치구명', '주소', '건물명'] + [f'{k}_카운트' for k in selected_filters.keys()]
            rename_map = {f'{k}_카운트': k for k in selected_filters.keys()}
            
            # [수정] column_config를 사용하여 '주소', 'lat', 'lng' 등을 화면에서만 숨김
            st.dataframe(
                df_map[display_cols].rename(columns=rename_map),
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "주소": None,  # <--- 화면에서 숨김 (데이터는 존재함)
                }
            )

            # [추가] 다운로드 버튼: 화면엔 안 보였던 '주소'가 포함된 CSV를 내려받음
            csv_data = df_map[display_cols].rename(columns=rename_map).to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 리스트 다운로드 (주소 포함)",
                data=csv_data,
                file_name='filtered_apartments_result.csv',
                mime='text/csv',
                help="다운로드된 파일에는 분석용 조인을 위한 '주소' 컬럼이 포함되어 있습니다."
            )

    else:
        # [B] 상세 분석 모드
        selected_apt_row = df_map[df_map['display_name'] == selected_name_display].iloc[0]
        
        apt_data_for_detail = {
            'latitude': selected_apt_row['latitude'], 
            'longitude': selected_apt_row['longitude'], 
            '건물명': selected_apt_row['건물명'],
            '자치구명': selected_apt_row['자치구명']
        }
        df_details = get_apartment_infrastructure_details(apt_data_for_detail, df_infra, selected_filters)
        
        selected_apt_total_count = df_details.shape[0]
        
        with header_left_placeholder.container():
            with st.container(border=True):
                st.markdown(f"#### ✅ **{selected_name_display}** 주변 인프라 : 총 **{selected_apt_total_count}**개")
        
        with header_right_placeholder.container():
            with st.container(border=True):
                st.markdown(f"#### 🏢 {selected_name_display} 주변 인프라 목록")
        
        with body_col1:
            create_detailed_map(apt_data_for_detail, df_details)
            
        with summary_placeholder.container():
            with st.container(border=True):
                st.markdown("##### 📊 인프라 요약")
                # (기존 요약 로직 유지)
                infra_counts = df_details['인프라_유형'].value_counts()
                filter_keys = list(selected_filters.keys())
                for i in range(0, len(filter_keys), 3):
                    cols = st.columns(3)
                    chunk = filter_keys[i:i+3]
                    for j, key in enumerate(chunk):
                        with cols[j]:
                            count = infra_counts.get(key, 0)
                            icon_map = {'초등학교':'🎒', '중학교':'📚', '고등학교':'🏛️', '문화시설':'🎨', '공원':'🌳', '대형병원':'🚑', '일반병원':'🏥', '버스정류장':'🚌', '지하철역':'🚇', '대형마트':'🛒', '백화점':'🛍️'}
                            label = f"{icon_map.get(key, '')} {key}"
                            st.markdown(f"""<div class="metric-container"><div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value">{count}개</div></div></div>""", unsafe_allow_html=True)
        
        with table_container:
            st.markdown("##### 📋 인프라 상세 목록")
            if not df_details.empty:
                st.dataframe(df_details[['인프라_유형', '시설명', '거리(m)']], use_container_width=True, hide_index=True)
            else:
                st.info("선택된 반경 내에 해당 인프라가 없습니다.")

if __name__ == "__main__":
    main()
