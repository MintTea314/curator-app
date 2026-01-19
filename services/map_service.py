import googlemaps
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_client():
    try:
        api_key = st.secrets["GOOGLE_MAPS_API_KEY"]
    except:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    return googlemaps.Client(key=api_key)

def search_place(query):
    """장소 이름으로 검색해서 기본 정보를 가져옵니다."""
    gmaps = get_client()
    try:
        # 1. 텍스트 검색
        places_result = gmaps.places(query=query)
        
        # 검색 결과가 성공(OK)이고 데이터가 있을 때
        if places_result['status'] == 'OK' and places_result['results']:
            place = places_result['results'][0]
            place_id = place['place_id']
            
            # 기본 정보 추출
            name = place.get('name')
            address = place.get('formatted_address')
            rating = place.get('rating', 0.0)
            user_ratings_total = place.get('user_ratings_total', 0)
            
            # 사진 가져오기
            photo_url = None
            if 'photos' in place:
                photo_reference = place['photos'][0]['photo_reference']
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={gmaps.key}"
            
            return {
                "name": name,
                "address": address,
                "rating": rating,
                "user_ratings_total": user_ratings_total,
                "place_id": place_id,
                "photo_url": photo_url
            }
        
        # [진단 기능] OK가 아니라면 에러 메시지 출력
        elif places_result['status'] != 'OK':
            error_msg = places_result.get('error_message', '원인 불명')
            st.error(f"🚨 구글맵 검색 실패: {places_result['status']} - {error_msg}")
            
        return None

    except Exception as e:
        # API 키가 틀렸거나 연결 문제일 때
        st.error(f"🚨 구글맵 시스템 에러: {str(e)}")
        return None

def get_place_reviews(place_id):
    """리뷰 5개 가져오기"""
    gmaps = get_client()
    try:
        details = gmaps.place(place_id=place_id, fields=['reviews'], language='ko')
        reviews_text = []
        if 'result' in details and 'reviews' in details['result']:
            for review in details['result']['reviews']:
                reviews_text.append(review.get('text', ''))
        return reviews_text
    except Exception as e:
        # 리뷰 가져오기 실패는 치명적이지 않으니 로그만 출력
        print(f"리뷰 에러: {e}")
        return []

def get_map_link(place_id):
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"
