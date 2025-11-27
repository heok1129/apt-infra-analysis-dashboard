import streamlit as st
import pandas as pd
import numpy as np
import folium
import streamlit.components.v1 as components

# ====================================================================
# --- 1. 헬퍼 함수 정의 ---
# ====================================================================

@st.cache_data(show_spinner="인프라 데이터 통합 로드 중...")
def load_all_infrastructure_data():
    all_data = []
    debug_info = [] # 디버깅 정보를 저장할 리스트
    
    # 인코딩 에러 방지를 위한 헬퍼 함수
    def read_csv_safe(file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='cp949')
    
    # 1. 학교 데이터
    try:
        df_school = read_csv_safe("school.csv")
        df_school = df_school.rename(columns={'school_name': 'infra_name'})
        all_data.append(df_school[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 학교: {len(df_school)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 학교 파일 없음 (school.csv)")
    except Exception as e:
        debug_info.append(f"❌ 학교 파일 오류: {e}")
        
    # 2. 문화시설 데이터
    try:
        df_art = read_csv_safe("art.csv")
        df_art['type'] = '문화시설'
        df_art = df_art.rename(columns={'문화시설명': 'infra_name'})
        all_data.append(df_art[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 문화시설: {len(df_art)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 문화시설 파일 없음 (art.csv)")
    except Exception as e:
        debug_info.append(f"❌ 문화시설 파일 오류: {e}")

    # 3. 병원 데이터
    try:
        df_hospital = read_csv_safe("hospital.csv")
        def classify_hospital(row):
            if '응급의료기관코드명' in row:
                val = str(row['응급의료기관코드명'])
                if '이외' in val: return '일반병원'
                elif '응급' in val: return '대형병원'
            if '응급실운영여부(1/2)' in row:
                if row['응급실운영여부(1/2)'] == 1: return '대형병원'
            return '일반병원' 

        df_hospital['type'] = df_hospital.apply(classify_hospital, axis=1)
        if '기관명' in df_hospital.columns:
            df_hospital = df_hospital.rename(columns={'기관명': 'infra_name'})
            all_data.append(df_hospital[['type', 'infra_name', 'lat', 'lng']])
            debug_info.append(f"✅ 병원: {len(df_hospital)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 병원 파일 없음 (hospital.csv)")
    except Exception as e:
        debug_info.append(f"❌ 병원 파일 오류: {e}")

    # 4. 공원 데이터
    try:
        df_park = read_csv_safe("park.csv")
        df_park['type'] = '공원'
        df_park = df_park.rename(columns={'공원명': 'infra_name'})
        all_data.append(df_park[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 공원: {len(df_park)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 공원 파일 없음 (park.csv)")
    except Exception as e:
        debug_info.append(f"❌ 공원 파일 오류: {e}")

    # 5. 버스정류장 데이터
    try:
        df_bus = read_csv_safe("bus_stop.csv")
        df_bus['type'] = '버스정류장'
        df_bus = df_bus.rename(columns={'name': 'infra_name'})
        all_data.append(df_bus[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 버스정류장: {len(df_bus)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 버스정류장 파일 없음 (bus_stop.csv)")
    except Exception as e:
        debug_info.append(f"❌ 버스정류장 파일 오류: {e}")

    # 6. 지하철역 데이터
    try:
        df_subway = read_csv_safe("subway.csv")
        df_subway['type'] = '지하철역'
        
        # 컬럼명 처리 (name 우선)
        if 'name' in df_subway.columns:
            df_subway = df_subway.rename(columns={'name': 'infra_name'})
        elif '역사명' in df_subway.columns:
            df_subway = df_subway.rename(columns={'역사명': 'infra_name'})
            
        all_data.append(df_subway[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 지하철역: {len(df_subway)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 지하철역 파일 없음 (subway.csv)")
    except Exception as e:
        debug_info.append(f"❌ 지하철역 파일 오류: {e}")

    # 7. 대형마트/백화점 데이터
    try:
        df_market = read_csv_safe("big_market.csv")
        if '업태구분명' in df_market.columns:
            df_market['type'] = df_market['업태구분명']
        else:
            df_market['type'] = '대형마트'
            
        df_market = df_market.rename(columns={'사업장명': 'infra_name'})
        all_data.append(df_market[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 대형마트/백화점: {len(df_market)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 대형마트 파일 없음 (big_market.csv)")
    except Exception as e:
        debug_info.append(f"❌ 대형마트 파일 오류: {e}")

    # 8. 체육시설 데이터
    try:
        df_gym = read_csv_safe("gym.csv")
        # 컬럼명 변경: name -> infra_name, 위도 -> lat, 경도 -> lng
        df_gym = df_gym.rename(columns={'name': 'infra_name', '위도': 'lat', '경도': 'lng'})
        df_gym['type'] = df_gym['type'].fillna('기타')
        
        all_data.append(df_gym[['type', 'infra_name', 'lat', 'lng']])
        debug_info.append(f"✅ 체육시설: {len(df_gym)}개 로드")
    except FileNotFoundError:
        debug_info.append("❌ 체육시설 파일 없음 (gym.csv)")
    except Exception as e:
        debug_info.append(f"❌ 체육시설 파일 오류: {e}")

    if not all_data:
        return pd.DataFrame(), debug_info
        
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
    target_infra_types = list(selected_filters.keys())

    for index, apt in df_apt.iterrows():
        apt_lat = apt['lat']
        apt_lng = apt['lng']
        
        meets_all_criteria = True
        individual_counts = {f'{t}_카운트': 0 for t in target_infra_types}

        for infra_type, radius_m in selected_filters.items():
            infra_of_type = df_infra[df_infra['type'] == infra_type].copy()
            if infra_of_type.empty:
                meets_all_criteria = False; break

            distances = haversine(apt_lat, apt_lng, infra_of_type['lat'].values, infra_of_type['lng'].values)
            if np.min(distances) > radius_m:
                meets_all_criteria = False; break

            count_type = np.sum(distances <= radius_m)
            individual_counts[infra_type + '_카운트'] = int(count_type)

        if meets_all_criteria:
            apt_data = apt.to_dict()
            apt_data.update(individual_counts)
            
            if '자치구명' not in apt_data:
                apt_data['자치구명'] = ''
                
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

def create_folium_map(df_map, df_infra, selected_filters):
    center_lat = df_map['latitude'].mean()
    center_lng = df_map['longitude'].mean()

    vworld_tiles = 'https://xdworld.vworld.kr/2d/Base/service/{z}/{x}/{y}.png'
    vworld_attr = 'Vworld'

    m = folium.Map(
        location=[center_lat, center_lng], 
        zoom_start=12,
        tiles=vworld_tiles, 
        attr=vworld_attr
    )
    
    # 색상 및 아이콘 설정
    colors = {
        '초등학교': 'blue', '중학교': 'green', '고등학교': 'orange',
        '문화시설': 'purple', '공원': 'darkgreen',
        '대형병원': 'red', '일반병원': 'lightred',
        '버스정류장': 'cadetblue', '지하철역': 'darkblue',
        '대형마트': 'pink', '백화점': 'beige',
        
        # 체육시설
        '수영장': 'lightblue', '생활체육관': 'lightgreen', 
        '축구장': 'lightgreen', '야구장': 'orange', 
        '농구장': 'orange', '테니스장': 'lightgreen', 
        '배드민턴장': 'cadetblue', '골프연습장': 'green', 
        '기타': 'gray'
    }
    
    def get_color(itype):
        return colors.get(itype, 'gray')

    icons = {
        '초등학교': 'graduation-cap', '중학교': 'university', '고등학교': 'landmark',
        '문화시설': 'palette', '공원': 'tree',
        '대형병원': 'ambulance', '일반병원': 'plus-square',
        '버스정류장': 'bus', '지하철역': 'subway',
        '대형마트': 'shopping-cart', '백화점': 'gift',
        
        # 체육시설 아이콘
        '수영장': 'person-swimming', '생활체육관': 'dumbbell', 
        '축구장': 'futbol', '야구장': 'baseball-bat-ball', 
        '농구장': 'basketball', '테니스장': 'table-tennis-paddle-ball',
        '배드민턴장': 'feather', '골프연습장': 'golf-ball-tee',
        '기타': 'star'
    }
    
    def get_icon(itype):
        return icons.get(itype, 'star')
    
    relevant_infra_list = []
    for infra_type, radius_m in selected_filters.items():
        infra_of_type = df_infra[df_infra['type'] == infra_type].copy()
        for idx_s, item in infra_of_type.iterrows():
            distances = haversine(item['lat'], item['lng'], df_map['latitude'].values, df_map['longitude'].values)
            if np.min(distances) <= radius_m:
                if not any(s.get('infra_name') == item['infra_name'] for s in relevant_infra_list):
                    infra_data = item.to_dict()
                    relevant_infra_list.append(infra_data)

    df_relevant_infra = pd.DataFrame(relevant_infra_list)
    
    # Infra Markers
    if not df_relevant_infra.empty:
        infra_group = folium.FeatureGroup(name="발견된 인프라 마커", show=True).add_to(m)
        for idx, item in df_relevant_infra.iterrows():
            infra_type = item['type']
            color = get_color(infra_type)
            icon_name = get_icon(infra_type)
            
            folium.Marker(
                location=[item['lat'], item['lng']],
                popup=f"{item['infra_name']}",
                icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
            ).add_to(infra_group)

    # Apt Markers
    apt_group = folium.FeatureGroup(name="필터링된 아파트", show=True).add_to(m)
    for idx, apt in df_map.iterrows():
        folium.Marker(
            location=[apt['latitude'], apt['longitude']],
            popup=f"{apt['자치구명']} {apt['건물명']}",
            icon=folium.Icon(color='darkpurple', icon='home', prefix='fa')
        ).add_to(apt_group)
        
    folium.LayerControl(collapsed=True).add_to(m)

    tip_html = """
    <div style="
        width: 100%;
        background-color: #ffffff;
        padding: 10px;
        border-top: 1px solid #e0e0e0;
        font-size: 12px;
        color: #000000;
        font-weight: 700;
        font-family: sans-serif;
        text-align: left;
    ">
        💡 <b>Tip:</b> 지도 우측 상단의 레이어 아이콘을 클릭하여 인프라 유형별 표시를 끄거나 켤 수 있습니다.
    </div>
    """
    m.get_root().html.add_child(folium.Element(tip_html))

    return components.html(m.get_root().render(), height=740, scrolling=True)

def create_detailed_map(apt_data, df_details):
    center_lat = apt_data['latitude']
    center_lng = apt_data['longitude']

    vworld_tiles = 'https://xdworld.vworld.kr/2d/Base/service/{z}/{x}/{y}.png'
    vworld_attr = 'Vworld'
    
    m = folium.Map(
        location=[center_lat, center_lng], 
        zoom_start=14, 
        tiles=vworld_tiles, 
        attr=vworld_attr
    )
    
    # 상세 지도용 색상 (Line용)
    line_colors = {
        '초등학교': 'blue', '중학교': 'green', '고등학교': 'orange',
        '문화시설': 'purple', '공원': 'darkgreen',
        '대형병원': 'red', '일반병원': '#FF7F7F',
        '버스정류장': 'cadetblue', '지하철역': 'darkblue',
        '대형마트': '#FF1493', '백화점': '#DAA520',
        '수영장': '#4682B4', '생활체육관': '#2E8B57', '축구장': '#006400',
        '야구장': '#FF8C00', '농구장': '#FF4500', '테니스장': '#32CD32', 
        '배드민턴장': '#5F9EA0', '골프연습장': '#008000', '기타': '#808080'
    }
    
    # 마커용 색상 (Folium Icon용)
    marker_colors = {
        '초등학교': 'blue', '중학교': 'green', '고등학교': 'orange',
        '문화시설': 'purple', '공원': 'darkgreen',
        '대형병원': 'red', '일반병원': 'lightred',
        '버스정류장': 'cadetblue', '지하철역': 'darkblue',
        '대형마트': 'pink', '백화점': 'beige',
        '수영장': 'lightblue', '생활체육관': 'lightgreen', '축구장': 'green',
        '야구장': 'orange', '농구장': 'orange', '테니스장': 'lightgreen', 
        '배드민턴장': 'cadetblue', '골프연습장': 'green', '기타': 'gray'
    }

    icons = {
        '초등학교': 'graduation-cap', '중학교': 'university', '고등학교': 'landmark',
        '문화시설': 'palette', '공원': 'tree',
        '대형병원': 'ambulance', '일반병원': 'plus-square',
        '버스정류장': 'bus', '지하철역': 'subway',
        '대형마트': 'shopping-cart', '백화점': 'gift',
        '수영장': 'person-swimming', '생활체육관': 'dumbbell', 
        '축구장': 'futbol', '야구장': 'baseball-bat-ball', 
        '농구장': 'basketball', '테니스장': 'table-tennis-paddle-ball',
        '배드민턴장': 'feather', '골프연습장': 'golf-ball-tee',
        '기타': 'star'
    }

    # Center Apt (아파트 위치)
    folium.Marker(
        location=[center_lat, center_lng],
        popup=f"선택: {apt_data['자치구명']} {apt_data['건물명']}",
        icon=folium.Icon(color='black', icon='building', prefix='fa')
    ).add_to(m)
    
    # Infra Items (주변 인프라)
    for idx, item in df_details.iterrows():
        infra_type = item['인프라_유형']
        m_color = marker_colors.get(infra_type, 'gray')
        l_color = line_colors.get(infra_type, 'gray')
        icon_name = icons.get(infra_type, 'star')
        
        # [삭제됨] 원(Circle) 그리기 부분 제거
        # folium.Circle(...).add_to(m) 코드를 삭제했습니다.
        
        # 마커(아이콘) 표시
        folium.Marker(
            location=[item['lat'], item['lng']],
            popup=f"{item['시설명']} ({item['거리(m)']}m)",
            icon=folium.Icon(color=m_color, icon=icon_name, prefix='fa')
        ).add_to(m)
        
        # 선(PolyLine) 그리기 - 아파트와 시설 연결
        folium.PolyLine(
            locations=[(center_lat, center_lng), (item['lat'], item['lng'])],
            color=l_color, weight=2, opacity=0.7
        ).add_to(m)

    info_html = f"""
    <div style="
        width: 100%;
        background-color: #ffffff;
        padding: 10px;
        border-top: 1px solid #e0e0e0;
        font-size: 12px;
        color: #000000;
        font-weight: 700;
        font-family: sans-serif;
        text-align: left;
    ">
        📌 <b>안내:</b> 선택된 아파트(<b>{apt_data['자치구명']} {apt_data['건물명']}</b>)를 기준으로 반경 내 주요 시설 위치와 직선 거리를 보여줍니다.
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    return components.html(m.get_root().render(), height=740, scrolling=True)

# ====================================================================
# --- 7. Streamlit 애플리케이션 메인 함수 ---
# ====================================================================

def main():
    st.set_page_config(layout="wide")
    
    st.markdown("""
    <style>
    .metric-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 8px;
        background-color: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid #e0e0e0;
        min-width: 100px;
    }
    .metric-box {
        text-align: center;
        width: 100%;
    }
    .metric-label {
        font-size: 1.0rem;
        font-weight: 700;
        color: #31333F;
        margin-bottom: 2px;
        white-space: nowrap;
    }
    .metric-value {
        font-size: 0.9rem;
        color: #555;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🏡 인프라 접근성 분석 대시보드")
    st.markdown("---")

    df_infra, debug_info = load_all_infrastructure_data()
    
    # [사이드바]
    
    # 1. 아파트 업로드
    st.sidebar.markdown("### 🏢 아파트 데이터 업로드")
    with st.sidebar.container(border=True):
        uploaded_file = st.file_uploader("", type="csv", label_visibility="hidden")
    
    df_apt = None
    if uploaded_file is not None:
        try:
            df_apt_temp = pd.read_csv(uploaded_file)
            required_cols = ['자치구명', '건물명', 'lat', 'lng']
            if not all(col in df_apt_temp.columns for col in required_cols):
                st.sidebar.error(f"❌ 아파트 파일에 필수 컬럼({', '.join(required_cols)}) 중 하나 이상이 누락되었습니다.")
            else:
                st.sidebar.success(f"✅ **{uploaded_file.name}** 데이터 로드 완료.")
                df_apt = df_apt_temp.copy()
        except Exception as e:
            st.sidebar.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")
            df_apt = None
    else:
        st.sidebar.info("업로드할 CSV 파일을 선택하거나 드래그 앤 드롭하세요.")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    # 2. 인프라 필터
    st.sidebar.markdown("### 🎛️ 인프라 필터 설정")
    selected_filters = {}
    max_radius = 5000

    with st.sidebar.container(border=True):
        # 4-1. 학교
        st.markdown("#### 🏫 학교 시설")
        if st.checkbox("초등학교", value=False): selected_filters['초등학교'] = st.slider("초등학교 반경 (m):", 100, max_radius, 500, 50, key="s_elem")
        if st.checkbox("중학교", value=False): selected_filters['중학교'] = st.slider("중학교 반경 (m):", 100, max_radius, 1000, 50, key="s_mid")
        if st.checkbox("고등학교", value=False): selected_filters['고등학교'] = st.slider("고등학교 반경 (m):", 100, max_radius, 1500, 50, key="s_high")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4-2. 문화/여가
        st.markdown("#### 🎨 문화/여가 시설")
        if st.checkbox("공원", value=False): selected_filters['공원'] = st.slider("공원 반경 (m):", 100, max_radius, 1000, 50, key="s_park")
        if st.checkbox("문화시설", value=False): selected_filters['문화시설'] = st.slider("문화시설 반경 (m):", 100, max_radius, 2000, 50, key="s_art")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4-3. 병원
        st.markdown("#### 🏥 병원 시설")
        if st.checkbox("대형병원", value=False): selected_filters['대형병원'] = st.slider("대형병원 반경 (m):", 100, max_radius, 1500, 50, key="s_er")
        if st.checkbox("일반병원", value=False): selected_filters['일반병원'] = st.slider("일반병원 반경 (m):", 100, max_radius, 1000, 50, key="s_gen")
        st.markdown("<br>", unsafe_allow_html=True)

        # 4-4. 교통
        st.markdown("#### 🚗 교통 시설")
        if st.checkbox("버스정류장", value=False): selected_filters['버스정류장'] = st.slider("버스정류장 반경 (m):", 100, max_radius, 500, 50, key="s_bus")
        if st.checkbox("지하철역", value=False): selected_filters['지하철역'] = st.slider("지하철역 반경 (m):", 100, max_radius, 1000, 50, key="s_sub")
        st.markdown("<br>", unsafe_allow_html=True)

        # 4-5. 생활 편의
        st.markdown("#### 🛒 생활 편의 시설")
        if st.checkbox("대형마트", value=False): selected_filters['대형마트'] = st.slider("대형마트 반경 (m):", 100, max_radius, 2000, 50, key="s_mart")
        if st.checkbox("백화점", value=False): selected_filters['백화점'] = st.slider("백화점 반경 (m):", 100, max_radius, 3000, 50, key="s_dept")
        st.markdown("<br>", unsafe_allow_html=True)

        # 4-6. 체육 시설
        st.markdown("#### 🏃 체육 시설")
        if st.checkbox("수영장", value=False): selected_filters['수영장'] = st.slider("수영장 반경 (m):", 100, max_radius, 1500, 50, key="s_swim")
        if st.checkbox("생활체육관", value=False): selected_filters['생활체육관'] = st.slider("생활체육관 반경 (m):", 100, max_radius, 1500, 50, key="s_gym")
        if st.checkbox("축구장", value=False): selected_filters['축구장'] = st.slider("축구장 반경 (m):", 100, max_radius, 2000, 50, key="s_soc")
        if st.checkbox("야구장", value=False): selected_filters['야구장'] = st.slider("야구장 반경 (m):", 100, max_radius, 2000, 50, key="s_base")
        if st.checkbox("농구장", value=False): selected_filters['농구장'] = st.slider("농구장 반경 (m):", 100, max_radius, 1000, 50, key="s_bask")
        if st.checkbox("테니스장", value=False): selected_filters['테니스장'] = st.slider("테니스장 반경 (m):", 100, max_radius, 1500, 50, key="s_ten")
        if st.checkbox("배드민턴장", value=False): selected_filters['배드민턴장'] = st.slider("배드민턴장 반경 (m):", 100, max_radius, 1500, 50, key="s_bad")
        if st.checkbox("골프연습장", value=False): selected_filters['골프연습장'] = st.slider("골프연습장 반경 (m):", 100, max_radius, 1500, 50, key="s_golf")
        if st.checkbox("기타 (체육시설)", value=False): selected_filters['기타'] = st.slider("기타 체육시설 반경 (m):", 100, max_radius, 1500, 50, key="s_etc")

    # [디버깅] 패널
    with st.sidebar.expander("🔧 데이터 로드 현황", expanded=False):
        for msg in debug_info:
            st.text(msg)

    if df_apt is None:
        st.info("👋 **환영합니다!** 분석을 시작하려면 **왼쪽 사이드바**에서 아파트 데이터 파일(CSV)을 업로드해주세요.")
        return
        
    if not selected_filters:
        st.warning("👈 **안내:** 왼쪽 사이드바에서 분석할 **인프라 종류를 하나 이상 체크**해 주세요.")
        return

    with st.container(border=True):
        st.markdown("### 🔍 필터링 기준")
        
        icon_map_filter = {
            '초등학교':'🎒', '중학교':'📚', '고등학교':'🏛️', 
            '문화시설':'🎨', '공원':'🌳', '대형병원':'🚑', '일반병원':'🏥',
            '버스정류장':'🚌', '지하철역':'🚇', '대형마트':'🛒', '백화점':'🛍️',
            '수영장':'🏊', '생활체육관':'🏋️', '축구장':'⚽', '야구장':'⚾',
            '농구장':'🏀', '테니스장':'🎾', '배드민턴장':'🏸', '골프연습장':'⛳',
            '기타':'⭐'
        }

        tags_html = """
<div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 8px; align-items: center; width: 100%; margin-bottom: 24px;">
"""
        
        for key, radius in selected_filters.items():
            icon = icon_map_filter.get(key, '📍')
            tags_html += f"""
<div style="display: inline-flex; align-items: center; background-color: #f0f2f6; border: 1px solid #d1d5db; border-radius: 20px; padding: 6px 12px; color: #31333F; font-size: 14px; font-weight: 500; white-space: nowrap; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
    <span style="margin-right: 6px; font-size: 16px;">{icon}</span>
    {key} 
    <span style="color: #666; font-size: 12px; margin-left: 6px; font-weight: 400;">{radius}m</span>
</div>
"""
        tags_html += "</div>"
        
        st.markdown(tags_html, unsafe_allow_html=True)
    
    df_filtered = filter_apartments(df_apt, df_infra, selected_filters)
    
    if df_filtered.empty:
        st.warning("선택된 조건(거리/인프라 종류)에 해당하는 아파트가 없습니다. 설정을 변경해 보세요.")
        return
    
    df_map = df_filtered.rename(columns={'lat': 'latitude', 'lng': 'longitude'})
    
    # 드롭다운용 이름 생성
    df_filtered['display_name'] = "[" + df_filtered['자치구명'] + "] " + df_filtered['건물명']
    apartment_names = ['--- 전체 요약 보기 ---'] + df_filtered['display_name'].tolist()
    
    head_col1, head_col2 = st.columns(2)
    with head_col1:
        header_left_placeholder = st.empty()
    with head_col2:
        header_right_placeholder = st.empty()
    
    body_col1, body_col2 = st.columns(2)
    
    with body_col2:
        with st.container(border=True):
            st.markdown("##### 📍 매물 선택")
            selected_name_display = st.selectbox(
                "매물 선택",
                apartment_names,
                key='drill_down_select',
                label_visibility='collapsed'
            )
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
            display_cols = ['자치구명', '건물명'] + [f'{k}_카운트' for k in selected_filters.keys()]
            rename_map = {f'{k}_카운트': k for k in selected_filters.keys()}
            
            st.dataframe(
                df_map[display_cols].rename(columns=rename_map),
                use_container_width=True, 
                hide_index=True
            )

    else:
        # [B] 상세 분석 모드
        selected_apt_row = df_filtered[df_filtered['display_name'] == selected_name_display].iloc[0]
        
        apt_data_for_detail = {
            'latitude': selected_apt_row['lat'], 
            'longitude': selected_apt_row['lng'], 
            '건물명': selected_apt_row['건물명'],
            '자치구명': selected_apt_row['자치구명']
        }
        df_details = get_apartment_infrastructure_details(apt_data_for_detail, df_infra, selected_filters)
        
        detail_cols = ['인프라_유형', '시설명', '거리(m)']

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
                infra_counts = df_details['인프라_유형'].value_counts()
                
                filter_keys = list(selected_filters.keys())
                
                for i in range(0, len(filter_keys), 3):
                    cols = st.columns(3)
                    chunk = filter_keys[i:i+3]
                    for j, key in enumerate(chunk):
                        with cols[j]:
                            count = infra_counts.get(key, 0)
                            icon_map = {
                                '초등학교':'🎒', '중학교':'📚', '고등학교':'🏛️', 
                                '문화시설':'🎨', '공원':'🌳', '대형병원':'🚑', '일반병원':'🏥',
                                '버스정류장':'🚌', '지하철역':'🚇', '대형마트':'🛒', '백화점':'🛍️',
                                '수영장':'🏊', '생활체육관':'🏋️', '축구장':'⚽', '야구장':'⚾',
                                '농구장':'🏀', '테니스장':'🎾', '배드민턴장':'🏸', '골프연습장':'⛳',
                                '기타':'⭐'
                            }
                            label = f"{icon_map.get(key, '')} {key}"
                            st.markdown(f"""<div class="metric-container"><div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value">{count}개</div></div></div>""", unsafe_allow_html=True)
        
        with table_container:
            st.markdown("##### 📋 인프라 상세 목록")
            if not df_details.empty:
                st.dataframe(
                    df_details[detail_cols],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("선택된 반경 내에 해당 인프라가 없습니다.")

if __name__ == "__main__":
    main()
