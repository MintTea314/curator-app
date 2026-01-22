import streamlit as st
import os
import re
import pandas as pd
import io
import services.scraper_service as scraper
import services.ai_service as ai
import services.map_service as map_api
import services.image_service as image_gen 

st.set_page_config(page_title="AI 큐레이터 Pro", page_icon="🎥", layout="centered")

st.title("🎥 보고 듣는 AI 맛집 큐레이터")
st.caption("유튜브 쇼츠, 인스타 릴스/게시물 링크를 넣으면 AI가 맛집을 찾아줍니다!")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

def clean_text_for_card(text):
    if not text: return ""
    cleaned = re.sub(r'[^가-힣a-zA-Z0-9\s\(\)\-\&]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

with st.form("input_form"):
    url = st.text_input("링크 입력 (Youtube, Instagram, Naver)", placeholder="https://...")
    submitted = st.form_submit_button("분석 시작 🚀", type="primary")

if submitted and url:
    # 링크 타입 판단
    is_youtube = "youtube.com" in url or "youtu.be" in url
    is_instagram = "instagram.com" in url
    
    with st.status("🕵️ AI가 분석을 시작합니다...", expanded=True) as status:
        
        ai_result = {"summary": "분석 실패", "places": []}
        
        # [A] 유튜브 처리 (영상)
        if is_youtube:
            st.write("📥 유튜브 영상 다운로드 중...")
            video_path, error = scraper.get_video_file(url)
            if error:
                st.error(error)
                st.stop()
            
            st.write("🧠 Gemini가 유튜브 영상을 분석 중...")
            ai_result = ai.analyze_video(video_path)
            if os.path.exists(video_path): os.remove(video_path)

        # [B] 인스타그램 처리 (릴스 or 게시물)
        elif is_instagram:
            st.write("📸 인스타그램 콘텐츠 가져오는 중 (Apify)...")
            # scraper가 'video'인지 'image'인지 알려줌
            content_type, content_path, error = scraper.get_instagram_content(url)
            
            if error:
                st.error(error)
                st.stop()
            
            if content_type == 'video':
                st.write("🎥 릴스(영상) 분석 중...")
                ai_result = ai.analyze_video(content_path)
                if os.path.exists(content_path): os.remove(content_path)
                
            elif content_type == 'image':
                st.write(f"🖼️ 사진 게시물({len(content_path)}장) 분석 중...")
                ai_result = ai.analyze_images(content_path)
                # 사용한 이미지 파일 삭제
                for p in content_path:
                    if os.path.exists(p): os.remove(p)

        # [C] 텍스트 (블로그 등)
        else:
            st.write("📄 텍스트 정보 수집 중...")
            raw_text = scraper.get_naver_blog_content(url) if "naver" in url else "텍스트 추출 불가"
            st.write("🧠 텍스트 읽는 중...")
            ai_result = ai.analyze_text(raw_text)

        # [공통] 지도 검색 및 결과 정리
        places_data = []
        if ai_result.get("places"):
            st.write("🗺️ 구글 지도에서 위치 확인 중...")
            
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

# --- 결과 화면 ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    
    st.divider()
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
        
        if p_map and p_map.get('name'):
            original_name = p_map['name']
        elif p_ai.get('display_name'):
            original_name = p_ai['display_name']
        else:
            original_name = p_ai.get('search_query', '알 수 없는 식당')

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

    # 엑셀 다운로드 (최하단)
    if res["places_data"]:
        st.subheader("📊 데이터 모아보기")
        excel_data = []
        for item in res["places_data"]:
            p_ai = item['ai_info']
            p_map = item['map_info']
            excel_data.append({
                "식당이름": p_map['name'] if p_map else p_ai.get('search_query'),
                "평점": p_map['rating'] if p_map else 0.0,
                "특징": p_ai.get('description', ''),
                "리뷰요약": item.get('review_summary', ''),
                "주소": p_map['address'] if p_map else "",
                "구글맵링크": map_api.get_map_link(p_map['place_id']) if p_map else ""
            })
            
        df = pd.DataFrame(excel_data)
        st.dataframe(df, use_container_width=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='맛집리스트')
            
        st.download_button(
            label="📥 엑셀 파일로 다운로드",
            data=buffer.getvalue(),
            file_name="AI_맛집리스트.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
