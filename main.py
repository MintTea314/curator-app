# [main.py 중간 부분]

if submit_button and url:
    with st.status("🕵️ 맛집을 찾고 있습니다...", expanded=True) as status:
        
        # 1. 비디오 다운로드 시도
        st.write("📥 AI가 영상을 다운로드하고 있습니다... (약 10~20초 소요)")
        video_path, error = scraper.download_video(url)
        
        if video_path:
            # 2. 영상을 AI에게 보여주기
            st.write("👀 AI가 영상을 시청하고 화면 속 글자를 읽는 중...")
            ai_result = ai.analyze_video(video_path)
            
            # 다 쓴 파일 삭제 (서버 용량 확보)
            if os.path.exists(video_path):
                os.remove(video_path)
                
        else:
            # 다운로드 실패 시 기존 방식(텍스트 수집)으로 폴백(Fallback)
            st.warning("영상 다운로드 실패. 텍스트 데이터만 수집합니다.")
            content, error = scraper.get_youtube_data(url)
            if error:
                st.error(error)
                st.stop()
            ai_result = ai.summarize_text(content)

        # 3. 지도 정보 찾기 (공통 로직)
        places_data = []
        if ai_result.get("places"):
            st.write("📸 구글 지도에서 위치와 사진을 찾는 중...")
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
