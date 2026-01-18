import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import sys

# 폰트 파일 경로 지정
# (반드시 프로젝트 폴더 안에 'fonts' 폴더를 만들고 그 안에 폰트 파일을 넣어야 합니다!)
FONT_PATH = os.path.join("fonts", "NanumGothic.ttf")

def load_font(size):
    """폰트를 불러오는 헬퍼 함수"""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        # 폰트 파일이 없으면 시스템 기본 폰트 사용 (한글 깨질 수 있음)
        print(f"\n⚠️ [경고] 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        print("👉 'fonts' 폴더에 'NanumGothic.ttf' 파일이 있는지 확인해주세요.")
        print("👉 폰트가 없으면 이미지의 한글이 '☒'처럼 나옵니다.\n")
        # 기본 폰트는 크기 조절이 안 돼서 너무 작게 나옵니다.
        return ImageFont.load_default()

def generate_qr_code(link):
    """링크를 받아서 QR코드 이미지 생성"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    # QR코드 크기를 조금 더 키워서 찍기 편하게 함
    return img.resize((180, 180))

def create_restaurant_card(restaurant_data):
    """맛집 데이터를 받아 카드 뉴스 형태의 이미지를 생성합니다."""
    
    # 1. 캔버스 준비
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # 폰트 준비 (파일이 없으면 여기서 경고 메시지 출력됨)
    font_title = load_font(40)
    font_text = load_font(24)
    font_small = load_font(18)

    # 2. 상단 이미지 영역 채우기
    photo_url = restaurant_data.get('사진URL')
    if photo_url:
        try:
            response = requests.get(photo_url, timeout=5)
            photo = Image.open(io.BytesIO(response.content)).convert("RGB")
            
            target_height = 400
            aspect_ratio = photo.width / photo.height
            new_width = int(target_height * aspect_ratio)
            photo = photo.resize((new_width, target_height))
            
            left = (canvas_width - new_width) // 2
            card.paste(photo, (left, 0))
        except Exception as e:
            print(f"이미지 다운로드 실패: {e}")
            draw.rectangle([(0,0), (canvas_width, 400)], fill=(200, 200, 200))
            draw.text((200, 180), "사진을 불러올 수 없음", font=font_text, fill=(100,100,100))
    else:
        draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
        draw.text((250, 180), "사진 없음", font=font_text, fill=(100,100,100))

    # 3. 하단 정보 영역 그리기
    text_start_y = 430
    margin = 30
    
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    address = restaurant_data.get('주소', '')

    # 검은색 폰트
    fill_color = (0, 0, 0)
    # 폰트 로딩 실패 시 load_default()는 색상 적용이 안 될 수 있어서 대비
    if font_title.getname()[0] == "Default": fill_color = None

    # 3-1. 식당 이름
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_color)
    
    # 3-2. 평점 (주황색)
    rating_fill = (255, 165, 0)
    if font_text.getname()[0] == "Default": rating_fill = None
    if rating > 0:
        draw.text((margin, text_start_y + 50), f"⭐ 구글 평점: {rating}점", font=font_text, fill=rating_fill)

    # 3-3. 특징 (줄바꿈 처리)
    desc_fill = (50, 50, 50)
    if font_text.getname()[0] == "Default": desc_fill = None
    if description:
        import textwrap
        wrapped_desc = textwrap.fill(description, width=25)
        draw.text((margin, text_start_y + 100), f"💡 특징:\n{wrapped_desc}", font=font_text, fill=desc_fill)

    # 4. QR코드 배치 (우측 하단)
    map_link = restaurant_data.get('지도링크')
    qr_height = 0
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_height = qr_img.height
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))
        # [수정] "Scan for Map" 문구 삭제함

    # 5. 주소 (좌측 하단, QR코드 옆 공간 활용)
    addr_fill = (100, 100, 100)
    if font_small.getname()[0] == "Default": addr_fill = None
    if address:
        # 주소 들어갈 공간 계산
        available_width = canvas_width - (margin * 3) - qr_height
        # 너무 길면 자르기
        short_address = address
        if len(address) > 25:
             short_address = address[:25] + "..."

        draw.text((margin, canvas_height - 50), f"📍 {short_address}", font=font_small, fill=addr_fill)

    return card
