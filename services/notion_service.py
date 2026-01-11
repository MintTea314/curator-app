import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def save_to_notion(data_list):
    token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not token or not database_id:
        return False, "❌ .env 파일에 노션 키나 데이터베이스 ID가 없습니다."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    success_count = 0
    errors = []

    for item in data_list:
        # 노션에 보낼 데이터 포맷 (이 부분이 까다롭습니다)
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "식당이름": {
                    "title": [{"text": {"content": item['식당이름']}}]
                },
                "특징": {
                    "rich_text": [{"text": {"content": item['특징']}}]
                },
                "주소": {
                    "rich_text": [{"text": {"content": item['주소']}}]
                },
                "평점": {
                    "number": float(item['평점']) if item['평점'] else 0
                },
                "지도링크": {
                    "url": item['지도링크'] if item['지도링크'] else None
                },
                "원본영상": {
                    "url": item['원본영상'] if item['원본영상'] else None
                }
            },
            # 페이지 본문(내용)에 사진을 넣어줍니다!
            "children": []
        }

        # 사진이 있다면 본문에 이미지 블록 추가
        if item.get('사진URL'):
             payload["children"].append({
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {"url": item['사진URL']}
                }
            })

        try:
            response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            if response.status_code == 200:
                success_count += 1
            else:
                err_msg = response.json().get('message', '알 수 없는 오류')
                errors.append(f"{item['식당이름']}: {err_msg}")
        except Exception as e:
            errors.append(str(e))

    if success_count == len(data_list):
        return True, f"✅ 총 {success_count}개 맛집을 노션에 저장했습니다!"
    elif success_count > 0:
        return True, f"⚠️ {success_count}개는 저장했지만, {len(errors)}개는 실패했습니다.\n({errors[0]})"
    else:
        return False, f"❌ 저장 실패: {errors[0] if errors else '알 수 없는 오류'}"