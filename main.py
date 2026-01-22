import streamlit as st
import os
import re
import pandas as pd  # [추가] 엑셀 데이터 처리용
import io            # [추가] 엑셀 파일 메모리 저장용
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

# 텍스트 청소 함수 (카드용)
def clean_text_for_card(text):
    if not text: return ""
    cleaned = re.sub(r'[^가-힣a-zA-Z0-9\s\(\)\-\&]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# 입력 폼
with st.form("input_form"):
    url = st.text_input("링크 입력 (유튜브, 인스타, 블로그)", placeholder="https://...")
    submitted = st.form_submit_button("분석 시작 🚀", type="primary")

if submitted and url:
    is_video = "youtube.com" in url or "youtu.be" in url or "instagram.com" in url
    
    with st.status("🕵️ AI가 분석을 시작합니다...", expanded=True) as status:
        
        # [A] 영상 처리
        if is_video:
            st.write("📥 영상 다운로드 중... (서버 성능 풀가동!)")
            video_path, error = scraper.get_video_file(url)
            
            if error:
                status.update(label="❌ 다운로드 실패", state="error")
                st.error(error)
                st.stop()
            
            st.write("🧠 Gemini 2.5 Pro가 영상을 시청 중입니다... (시각+청각 분석)")
            ai_result = ai.analyze_video(video_path)
            
            if os.path.exists(video_path):
                os.remove(video_path)

        # [B] 텍스트 처리
        else:
            st.write("📄 텍스트 정보를 수집 중입니다...")
            raw_text = scraper.get_naver_blog_content(url) if "naver" in url else "텍스트 추출 불가"
            st.write("🧠 Gemini 2.5 Pro가 텍스트를 읽는 중입니다...")
            ai_result = ai.analyze_text(raw_text)

        # [공통] 지도 검색
        places_data = []
        if ai_result.get("places"):
            st.write("🗺️ 구글 지도에서 정확한 위치 찾는 중...")
            
            for place in ai_result["places"]:
                query = place.get("search_query", "맛집")
                map_info = map_api.search_place(query)
                review_summary = ""
                
                if map_info:
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

# --- 결과 출력 ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    
    st.divider()
    
    # [부활] 엑셀 다운로드 버튼 영역
    if res["places_data"]:
        excel_data = []
        for item in res["places_data"]:
            p_ai = item['ai_info']
            p_map = item['map_info']
            
            # 엑셀에 저장할 데이터 정리
            name = p_map['name'] if p_map else p_ai.get('search_query')
            addr = p_map['address'] if p_map else "주소 정보 없음"
            rating = p_map['rating'] if p_map else 0.0
            link = map_api.get_map_link(p_map['place_id']) if p_map else ""
            
            excel_data.append({
                "식당이름": name,
                "평점": rating,
                "특징": p_ai.get('description', ''),
                "리뷰요약": item.get('review_summary', ''),
                "주소": addr,
                "구글맵링크": link
            })
            
        # 데이터프레임 생성
        df = pd.DataFrame(excel_data)
        
        # 엑셀 파일로 변환 (메모리 상에서)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='맛집리스트')
            
        # 다운로드 버튼 표시
        st.download_button(
            label="📥 엑셀 파일로 다운로드",
            data=buffer.getvalue(),
            file_name="AI_맛집리스트.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.subheader("📝 3줄 요약")
    if res.get("summary"):
        st.info(res["summary"])
    
    st.subheader("📍 발견된 맛집 리스트")
    
    if not res["places_data"]:
        st.write("발견된 식당이 없습니다.")
    
    for item in res["places_data"]:
        p_ai = item['ai_info']
        p_map = item['map_info']
        review_summ = item.get('review_summary', '')
        
        # 이름 우선순위 (구글맵 > AI)
        if p_map and p_map.get('name'):
            original_name = p_map['name']
        elif p_ai.get('display_name'):
            original_name = p_ai['display_name']
        else:
            original_name = p_ai.get('search_query', '알 수 없는 식당')

        # 카드용 이름 청소
        card_name_clean = clean_text_for_card(original_name)
        if not card_name_clean.strip():
            card_name_clean = clean_text_for_card(p_ai.get('display_name', 'Global Restaurant'))

        desc = p_ai.get('description', '')
        
        card_data = {
            "식당이름": card_name_clean,
            "평점": p_map['rating'] if p_map else 0.0,
            "특징": desc,
            "리뷰요약": review_summ,
            "지도링크": map_api.get_map_link(p_map['place_id']) if p_map else "",
            "사진URL": p_map.get('photo_url') if p_map else None
        }

        with st.container():
            c1, c2 = st.columns([3, 2])
            
            with c1:
                st.markdown(f"### {original_name}")  
                st.write(f"💡 {desc}")
                if review_summ:
                    st.success(f"🗣️ **후기 요약:** {review_summ}")
                
                if p_map:
                    map_link = map_api.get_map_link(p_map['place_id'])
                    st.link_button("🗺️ 구글 지도 보기", map_link)
                    
            with c2:
                try:
                    img_path = image_gen.create_restaurant_card(card_data)
                    st.image(img_path, caption="📸 저장해서 공유하세요!", use_container_width=True)
                except Exception as e:
                    st.error(f"카드 생성 실패: {e}")
        
        st.markdown("---")
