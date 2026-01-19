import streamlit as st
import pandas as pd
import os
import datetime
import services.scraper_service as scraper
import services.ai_service as ai
import services.map_service as map_api
import services.notion_service as notion
import services.image_service as image_gen

st.set_page_config(page_title="AI 큐레이터", page_icon="✈️", layout="centered")

st.markdown("""
<style>
    .main-header {text-align: center; margin-bottom: 1rem;}
    .stTextInput input {text-align: center;}
    .place-title {font-size: 1.2rem; font-weight: bold; color: #1f77b4;}
    .stImageCaption {font-size: 0.8rem; color: #666; text-align: center;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>✈️ 여행/맛집 AI 큐레이터</h1>", unsafe_allow_html=True)
st.write("유튜브/인스타 링크를 넣고 **엔터(Enter)**를 누르세요! 오타가 있는 자막도 AI가 찰떡같이 알아듣고 찾아줍니다.")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

with st.form(key='analysis_form'):
    url = st.text_input(label="링크 입력", placeholder="https://youtube.com/shorts/...", label_visibility="collapsed")
    # [수정 1] use_container_width=True -> width="stretch" (최신 문법 적용)
    submit_button = st.form_submit_button(label="분석 시작 🚀", type="primary", width="stretch")

if submit_button and url:
    with st.status("🕵️ 맛집을 찾고 있습니다...", expanded=True) as status:
        
        # 1. 텍스트 데이터 수집
        st.write("📥 영상의 자막/설명글을 읽어오는 중...")
        if "youtu" in url:
            content, error = scraper.get_youtube_data(url)
        else:
            content, error = scraper.get_instagram_data(url)
        
        if error:
            status.update(label="❌ 수집 실패", state="error")
            st.error(error)
            st.stop()
        
        # 2. AI 분석
        st.write("🧠 AI가 자막을 분석하고 맛집 이름을 추리하는 중...")
        ai_result = ai.summarize_text(content)
        
        # 3. 지도 정보 & 리뷰 요약 찾기
        places_data = []
        if ai_result.get("places"):
            st.write("📸 구글 지도 검색 & 실제 리뷰 분석 중...")
            for place in ai_result["places"]:
                # (1) 지도 기본 정보 검색
                map_info = map_api.search_place(place["search_query"])
                
                review_summary = ""
                if map_info:
                    # (2) 리뷰 가져오기 & AI 요약
                    reviews = map_api.get_place_reviews(map_info['place_id'])
                    if reviews:
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

if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    places_data = result["places_data"]
    
    st.divider()
    st.subheader("📝 3줄 요약")
    st.info(result["summary"])
    
    st.subheader("📍 발견된 장소 리스트")
    if not places_data:
        st.warning("발견된 장소가 없습니다.")
    
    save_data = []
    
    for item in places_data:
        p_ai = item['ai_info']
        p_map = item['map_info']
        review_summ = item.get('review_summary', '')
        
        name = p_map['name'] if p_map else p_ai['search_query']
        address = p_map['address'] if p_map else "주소 미상"
        rating = p_map['rating'] if p_map else 0.0
        place_link = map_api.get_map_link(p_map['place_id']) if p_map else ""
        photo = p_map.get('photo_url') if p_map else None

        current_place_data = {
            "식당이름": name,
            "평점": rating,
            "특징": p_ai['description'],
            "리뷰요약": review_summ,
            "주소": address,
            "지도링크": place_link,
            "원본영상": result["url"],
            "사진URL": photo 
        }
        save_data.append(current_place_data)

        # UI 출력
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"<div class='place-title'>{name}</div>", unsafe_allow_html=True)
                st.caption(f"💡 {p_ai['description']}")
                if review_summ:
                    st.info(f"🗣️ **실제 후기 요약:**\n{review_summ}")
                    
                if p_map:
                    st.markdown(f"⭐ **{p_map['rating']}** ({p_map['user_ratings_total']:,})")
            with col2:
                if p_map:
                    st.link_button("지도 보기 🗺️", place_link)
                else:
                    st.button("정보 없음", disabled=True, key=name)
            
        # 카드 이미지
        if place_link:
            with st.spinner(f"'{name}' 카드 이미지 생성 중..."):
                card_image = image_gen.create_restaurant_card(current_place_data)
                # [수정 2] 에러를 유발하는 use_container_width 삭제 (기본값으로 충분함)
                st.image(card_image, caption="☝️ 꾹 눌러서 이미지 저장/공유하세요! (QR코드 포함)")
        
        st.markdown("---")

    # 하단 공유 섹션
    st.divider()
    st.subheader("📤 결과 공유 및 저장")
    
    tab1, tab2, tab3 = st.tabs(["💬 텍스트 복사", "📊 엑셀(표) 복사/다운", "🔒 관리자"])
    
    with tab1:
        share_text = f"[✈️ AI가 요약한 맛집 리스트]\n원본영상: {result['url']}\n\n"
        for item in save_data:
            share_text += f"📍 {item['식당이름']}"
            if item['평점'] > 0: share_text += f" (⭐{item['평점']})"
            share_text += f"\n💡 {item['특징']}\n"
            if item['리뷰요약']: share_text += f"🗣️ 후기: {item['리뷰요약'].replace(chr(10), ' ')}\n"
            if item['지도링크']: share_text += f"🔗 지도: {item['지도링크']}\n"
            share_text += "------------------\n"
        st.code(share_text, language="text")

    with tab2:
        st.write("마우스로 드래그해서 복사(Ctrl+C) 후 엑셀에 붙여넣기(Ctrl+V) 할 수 있습니다.")
        df = pd.DataFrame(save_data)
        df_clean = df.drop(columns=['사진URL'], errors='ignore')
        # [수정 3] use_container_width 제거
        st.dataframe(df_clean, hide_index=True)
        st.write("") 
        csv_data = df_clean.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        # [수정 4] use_container_width 제거 (필요시 help 사용 등)
        st.download_button("엑셀 파일로 다운로드 (.csv) 📥", csv_data, f"맛집리스트.csv", "text/csv")

    with tab3:
        admin_password = st.text_input("관리자 키를 입력하세요", type="password")
        if admin_password == "1234": 
            # [수정 5] use_container_width=True -> width="stretch"
            if st.button("내 노션에 저장하기 🚀", type="primary", width="stretch"):
                with st.spinner("노션으로 전송 중..."):
                    success, msg = notion.save_to_notion(save_data)
                    if success: st.success(msg)
                    else: st.error(msg)
