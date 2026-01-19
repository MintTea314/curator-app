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
        
        if places_result['status'] == 'OK' and places_result['results']:
            place = places_result['results'][0]
            place_id = place['place_id']
            
            # 기본 정보 추출
            name = place.get('name')
            address = place.get('formatted_address')
            rating = place.get('rating', 0.0)
            user_ratings_total = place.get('user_ratings_total', 0)
            
            # 사진 가져오기 (최대 너비 400px)
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
        return None
    except Exception as e:
        print(f"구글맵 검색 에러: {e}")
        return None

def get_place_reviews(place_id):
    """
    [신규 기능] Place ID를 이용해 리뷰 5개를 가져옵니다.
    """
    gmaps = get_client()
    try:
        # 리뷰 데이터 요청 (언어는 한국어로 시도)
        details = gmaps.place(place_id=place_id, fields=['reviews'], language='ko')
        
        reviews_text = []
        if 'result' in details and 'reviews' in details['result']:
            for review in details['result']['reviews']:
                # 리뷰 텍스트만 추출
                reviews_text.append(review.get('text', ''))
        
        return reviews_text
    except Exception as e:
        print(f"리뷰 가져오기 에러: {e}")
        return []

def get_map_link(place_id):
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"
