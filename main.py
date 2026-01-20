import streamlit as st
import os
import services.scraper_service as scraper
import services.ai_service as ai
import services.map_service as map_api
import services.image_service as image_gen 

# 페이지 기본 설정
st.set_page_config(page_title="AI 큐레이터 Pro", page_icon="🎥", layout="centered")

st.title("🎥 보고 듣는 AI 맛집 큐레이터")
st.caption("유튜브/인스타 영상 링크를 넣으면, AI가 **간판을 읽고 소리를 들어서** 맛집을 찾아줍니다!")

# 세션 상태 초기화
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# 입력 폼
with st.form("input_form"):
    url = st.text_input("링크 입력 (유튜브, 인스타, 블로그)", placeholder="https://...")
    submitted = st.form_submit_button("분석 시작 🚀", type="primary")

if submitted and url:
    # 1. 영상인지 텍스트인지 판단
    is_video = "youtube.com" in url or "youtu.be" in url or "instagram.com" in url
    
    # 상태 메시지 표시
    with st.status("🕵️ AI가 분석을 시작합니다...", expanded=True) as status:
        
        # [A] 영상 처리 모드
        if is_video:
            st.write("📥 영상 다운로드 중... (서버 성능 풀가동!)")
            video_path, error = scraper.get_video_file(url)
            
            if error:
                status.update(label="❌ 다운로드 실패", state="error")
                st.error(error)
                st.stop()
            
            st.write("🧠 Gemini 2.5 Pro가 영상을 시청 중입니다... (시각+청각 분석)")
            ai_result = ai.analyze_video(video_path)
            
            # 용량 관리를 위해 분석 후 파일 삭제
            if os.path.exists(video_path):
                os.remove(video_path)

        # [B] 텍스트(블로그) 처리 모드
        else:
            st.write("📄 텍스트 정보를 수집 중입니다...")
            # 네이버 블로그 등 텍스트 추출
            raw_text = scraper.get_naver_blog_content(url) if "naver" in url else "텍스트 추출 불가"
            st.write("🧠 Gemini 2.5 Pro가 텍스트를 읽는 중입니다...")
            ai_result = ai.analyze_text(raw_text)

        # [공통] 지도 정보 검색 및 데이터 통합
        places_data = []
        if ai_result.get("places"):
            st.write("🗺️ 구글 지도에서 정확한 위치 찾는 중...")
            
            for place in ai_result["places"]:
                # AI가 찾은 검색어 (예: 런던베이글뮤지엄 도산)
                query = place.get("search_query", "맛집")
                
                # 구글 맵 검색
                map_info = map_api.search_place(query)
                review_summary = ""
                
                if map_info:
                    # 리뷰 가져와서 요약 (AI에게 "군더더기 없이 요약해"라고 시킨 함수 호출)
                    reviews = map_api.get_place_reviews(map_info['place_id'])
                    review_summary = ai.summarize_reviews(reviews)
                
                places_data.append({
                    "ai_info": place,
                    "map_info": map_info,
                    "review_summary": review_summary
                })
        
        # 결과 저장
        st.session_state.analysis_result = {
            "summary": ai_result.get("summary"),
            "places_data": places_data,
            "url": url
        }
        status.update(label="✅ 분석 완료!", state="complete")

# --- 결과 출력 화면 ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    
    st.divider()
    st.subheader("📝 3줄 요약")
    if res.get("summary"):
        st.info(res["summary"])
    else:
        st.warning("요약 내용을 가져오지 못했습니다.")
    
    st.subheader("📍 발견된 맛집 리스트")
    
    if not res["places_data"]:
        st.write("발견된 식당이 없습니다.")
    
    for item in res["places_data"]:
        p_ai = item['ai_info']
        p_map = item['map_info']
        review_summ = item.get('review_summary', '')
        
        # [핵심 로직] 카드에 넣을 이름 결정
        # 1순위: 구글맵 공식 상호명 (가장 정확함, 태국어 등 원본 유지)
        if p_map and p_map.get('name'):
            safe_name_for_card = p_map['name']
        # 2순위: 구글맵 정보가 없을 때만 AI가 만든 안전한 이름 사용
        elif p_ai.get('display_name'):
            safe_name_for_card = p_ai['display_name']
        # 3순위: 그마저도 없으면 검색어 사용
        else:
            safe_name_for_card = p_ai.get('search_query', '알 수 없는 식당')

        # 화면 UI 표시 이름도 카드 이름과 동일하게
        ui_name = safe_name_for_card
        
        desc = p_ai.get('description', '')
        
        # 카드 데이터 구성
        card_data = {
            "식당이름": safe_name_for_card, 
            "평점": p_map['rating'] if p_map else 0.0,
            "특징": desc,
            "리뷰요약": review_summ,
            "지도링크": map_api.get_map_link(p_map['place_id']) if p_map else "",
            # 사진 URL은 map_api에서 가져오거나 비워둠
            "사진URL": p_map.get('photo_url') if p_map else None
        }

        with st.container():
            c1, c2 = st.columns([3, 2]) # 카드 이미지가 좀 더 잘 보이게 비율 조정
            
            with c1:
                st.markdown(f"### {ui_name}")  
                st.write(f"💡 {desc}")
                if review_summ:
                    st.success(f"🗣️ **후기 요약:** {review_summ}")
                
                # 구글맵 링크 버튼
                if p_map:
                    map_link = map_api.get_map_link(p_map['place_id'])
                    st.link_button("🗺️ 구글 지도 보기", map_link)
                    
            with c2:
                # 카드 이미지 생성 (image_service.py 호출)
                try:
                    img_path = image_gen.create_restaurant_card(card_data)
                    st.image(img_path, caption="📸 저장해서 공유하세요!", use_container_width=True)
                except Exception as e:
                    st.error(f"카드 생성 실패: {e}")
        
        st.markdown("---")
