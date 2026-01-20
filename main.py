import streamlit as st
import os
import services.scraper_service as scraper
import services.ai_service as ai
import services.map_service as map_api
import services.image_service as image_gen # (기존에 만든 이미지 서비스 유지)

st.set_page_config(page_title="AI 큐레이터 Pro", page_icon="🎥", layout="centered")

st.title("🎥 보고 듣는 AI 맛집 큐레이터")
st.caption("유튜브/인스타 영상 링크를 넣으면, AI가 **간판을 읽고 소리를 들어서** 맛집을 찾아줍니다!")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

with st.form("input_form"):
    url = st.text_input("링크 입력 (유튜브, 인스타, 블로그)", placeholder="https://...")
    submitted = st.form_submit_button("분석 시작 🚀", type="primary")

if submitted and url:
    # 1. 영상인지 텍스트인지 판단
    is_video = "youtube.com" in url or "youtu.be" in url or "instagram.com" in url
    
    with st.status("🕵️ AI가 분석을 시작합니다...", expanded=True) as status:
        
        # [A] 영상 처리 모드
        if is_video:
            st.write("📥 영상 다운로드 중... (서버 성능 풀가동!)")
            video_path, error = scraper.get_video_file(url)
            
            if error:
                status.update(label="❌ 다운로드 실패", state="error")
                st.error(error)
                st.stop()
            
            st.write("🧠 Gemini 2.0이 영상을 시청 중입니다... (시각+청각 분석)")
            ai_result = ai.analyze_video(video_path)
            
            # 용량 관리를 위해 파일 삭제
            if os.path.exists(video_path):
                os.remove(video_path)

        # [B] 텍스트(블로그) 처리 모드
        else:
            st.write("📄 텍스트 정보를 수집 중입니다...")
            # (기존 블로그 로직 간소화 호출)
            # 네이버 블로그라면 scraper.get_naver_blog_content(url) 등을 호출
            # 여기서는 편의상 심플하게 처리한다고 가정
            raw_text = scraper.get_naver_blog_content(url) if "naver" in url else "텍스트 추출 불가"
            ai_result = ai.analyze_text(raw_text)

        # [공통] 지도 정보 검색
        places_data = []
        if ai_result.get("places"):
            st.write("🗺️ 구글 지도에서 정확한 위치 찾는 중...")
            for place in ai_result["places"]:
                # AI가 찾은 이름으로 검색
                map_info = map_api.search_place(place["search_query"])
                review_summary = ""
                
                if map_info:
                    # 리뷰 가져와서 요약
                    reviews = map_api.get_place_reviews(map_info['place_id'])
                    review_summary = ai.summarize_reviews(reviews)
                
                places_data.append({
                    "ai_info": place,
                    "map_info": map_info,
                    "review_summary": review_summary
                })
        
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
    st.info(res["summary"])
    
    st.subheader("📍 발견된 맛집 리스트")
    
    for item in res["places_data"]:
        p_ai = item['ai_info']
        p_map = item['map_info']
        review_summ = item.get('review_summary', '')
        
        name = p_map['name'] if p_map else p_ai['search_query']
        desc = p_ai['description']
        
        # 카드 데이터 구성
        card_data = {
            "식당이름": name,
            "평점": p_map['rating'] if p_map else 0.0,
            "특징": desc,
            "리뷰요약": review_summ,
            "지도링크": map_api.get_map_link(p_map['place_id']) if p_map else "",
            "사진URL": p_map.get('photo_url') if p_map else None
        }

        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### {name}")
                st.write(f"💡 {desc}")
                if review_summ:
                    st.caption(f"🗣️ **후기 요약:** {review_summ}")
            with c2:
                # 카드 이미지 생성 (우리가 힘들게 만든 Noto Sans 버전!)
                img = image_gen.create_restaurant_card(card_data)
                st.image(img, caption="저장용 카드")
        
        st.markdown("---")
