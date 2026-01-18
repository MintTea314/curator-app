import streamlit as st
import pandas as pd
import os
import datetime
import services.scraper_service as scraper
import services.ai_service as ai
import services.map_service as map_api
import services.notion_service as notion
# [추가] 이미지 생성 서비스 임포트
import services.image_service as image_gen 

st.set_page_config(page_title="AI 큐레이터", page_icon="✈️", layout="centered")

st.markdown("""
<style>
    .main-header {text-align: center; margin-bottom: 1rem;}
    .stTextInput input {text-align: center;}
    .place-title {font-size: 1.2rem; font-weight: bold; color: #1f77b4;}
    /* 이미지 카드 캡션 스타일 */
    .stImageCaption {font-size: 0.8rem; color: #666; text-align: center;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>✈️ 여행/맛집 AI 큐레이터</h1>", unsafe_allow_html=True)
st.write("유튜브/인스타 링크를 넣고 **엔터(Enter)**를 누르세요! 사진과 지도 정보까지 찾아드립니다.")

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

with st.form(key='analysis_form'):
    url = st.text_input(label="링크 입력", placeholder="https://youtube.com/shorts/...", label_visibility="collapsed")
    submit_button = st.form_submit_button(label="분석 시작 🚀", type="primary", use_container_width=True)

if submit_button and url:
    with st.status("🕵️ 맛집을 찾고 있습니다...", expanded=True) as status:
        st.write("📥 영상/댓글 데이터 수집 중...")
        content, error = scraper.get_youtube_data(url) if "youtu" in url else scraper.get_instagram_data(url)
        
        if error:
            status.update(label="❌ 수집 실패", state="error")
            st.error(error)
            st.session_state.analysis_result = None
        else:
            st.write("🧠 AI가 장소 이름을 추출하는 중...")
            ai_result = ai.summarize_text(content)
            
            places_data = []
            if ai_result.get("places"):
                st.write("📸 구글 지도에서 사진과 평점을 조회하는 중...")
                for place in ai_result["places"]:
                    map_info = map_api.search_place(place["search_query"])
                    places_data.append({
                        "ai_info": place,
                        "map_info": map_info
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
        
        name = p_map['name'] if p_map else p_ai['search_query']
        address = p_map['address'] if p_map else "주소 미상"
        rating = p_map['rating'] if p_map else 0.0
        place_link = map_api.get_map_link(p_map['place_id']) if p_map else ""
        photo = p_map.get('photo_url') if p_map else None

        current_place_data = {
            "식당이름": name,
            "평점": rating,
            "특징": p_ai['description'],
            "주소": address,
            "지도링크": place_link,
            "원본영상": result["url"],
            "사진URL": photo 
        }
        save_data.append(current_place_data)

        # --- 기존 UI ---
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"<div class='place-title'>{name}</div>", unsafe_allow_html=True)
                st.caption(f"💡 {p_ai['description']}")
                if p_map:
                    st.markdown(f"⭐ **{p_map['rating']}** ({p_map['user_ratings_total']:,})")
            with col2:
                if p_map:
                    st.link_button("지도 보기 🗺️", place_link)
                else:
                    st.button("정보 없음", disabled=True, key=name)
            
        # --- [신규 기능 2] 이미지 카드 생성 및 출력 ---
        # 지도 링크가 있는 경우에만 카드를 만듭니다.
        if place_link:
            with st.spinner(f"'{name}' 카드 이미지 생성 중..."):
                card_image = image_gen.create_restaurant_card(current_place_data)
                # 이미지를 화면에 표시합니다. (사용자는 이걸 꾹 눌러 저장할 수 있습니다)
                st.image(card_image, caption="☝️ 꾹 눌러서 이미지 저장/공유하세요! (QR코드 포함)", use_container_width=True)
        
        st.markdown("---")


    # --- [수정된 공유 및 저장 섹션] ---
    st.divider()
    st.subheader("📤 결과 공유 및 저장")
    
    tab1, tab2, tab3 = st.tabs(["💬 텍스트 복사", "📊 엑셀(표) 복사/다운", "🔒 관리자"])
    
    with tab1:
        # (기존 카톡 복사 기능)
        share_text = f"[✈️ AI가 요약한 맛집 리스트]\n원본영상: {result['url']}\n\n"
        for item in save_data:
            share_text += f"📍 {item['식당이름']}"
            if item['평점'] > 0: share_text += f" (⭐{item['평점']})"
            share_text += f"\n💡 {item['특징']}\n"
            if item['지도링크']: share_text += f"🔗 지도: {item['지도링크']}\n"
            share_text += "------------------\n"
        st.code(share_text, language="text")

    with tab2:
        # [신규 기능 1] 인라인 엑셀 표 (드래그 복사 가능)
        st.write("마우스로 드래그해서 복사(Ctrl+C) 후 엑셀에 붙여넣기(Ctrl+V) 할 수 있습니다.")
        
        df = pd.DataFrame(save_data)
        df_clean = df.drop(columns=['사진URL'], errors='ignore')
        
        # interactive한 표를 그려줍니다.
        st.dataframe(df_clean, hide_index=True, use_container_width=True)
        
        st.write("") # 여백
        
        # 기존 엑셀 다운로드 버튼
        csv_data = df_clean.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="엑셀 파일로 다운로드 (.csv) 📥",
            data=csv_data,
            file_name=f"맛집리스트_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with tab3:
        # (기존 관리자 노션 저장 기능)
        admin_password = st.text_input("관리자 키를 입력하세요", type="password")
        if admin_password == "1234": 
            if st.button("내 노션에 저장하기 🚀", type="primary", use_container_width=True):
                with st.spinner("노션으로 전송 중..."):
                    success, msg = notion.save_to_notion(save_data)
                    if success: st.success(msg)
                    else: st.error(msg)
