import os
import textwrap
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode
from qrcode.image.styledpil import StyledPilImage # 혹시 모를 고급 기능 대비

def create_restaurant_card(data):
    """
    맛집 정보를 받아 카드 이미지를 생성하고 경로를 반환
    """
    # 1. 캔버스 설정
    card_width, card_height = 800, 1100 
    img = Image.new('RGB', (card_width, card_height), color='white')
    draw = ImageDraw.Draw(img)

    # 2. 폰트 설정 (서버 나눔고딕 경로)
    font_path_bold = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    
    if not os.path.exists(font_path_bold): font_path_bold = "arial.ttf"
    if not os.path.exists(font_path_reg): font_path_reg = "arial.ttf"

    try:
        # [수정 1] 폰트 크기 2~4px 축소
        title_font = ImageFont.truetype(font_path_bold, 42) # 45 -> 42
        header_font = ImageFont.truetype(font_path_bold, 26) # 28 -> 26
        text_font = ImageFont.truetype(font_path_reg, 24)   # 26 -> 24
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # 3. 상단 이미지 처리
    current_y = 50 
    photo_url = data.get('사진URL')
    
    if photo_url:
        try:
            print(f"📸 이미지 다운로드: {photo_url[:30]}...")
            response = requests.get(photo_url, timeout=5)
            response.raise_for_status()
            
            food_img = Image.open(BytesIO(response.content)).convert("RGB")
            header_height = 400
            
            # 중앙 크롭
            food_img = ImageOps.fit(food_img, (card_width, header_height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            img.paste(food_img, (0, 0))
            current_y = header_height + 40 
            
        except Exception as e:
            print(f"❌ 이미지 실패: {e}")

    # 4. 텍스트 그리기
    
    # 식당 이름
    name = data.get('식당이름', '알 수 없는 식당')
    # 제목도 너무 길면 QR 침범할 수 있으니 적당히 줄바꿈
    wrapped_title = textwrap.wrap(name, width=20)
    for line in wrapped_title:
        draw.text((50, current_y), line, font=title_font, fill="#2c3e50") 
        current_y += 50 # 줄간격 축소 (55 -> 50)
    
    current_y += 15

    # 평점
    rating = data.get('평점', 0.0)
    draw.text((50, current_y), f"★ 구글 평점: {rating}점", font=text_font, fill="#d35400")
    current_y += 45

    # 특징
    draw.text((50, current_y), "▶ 특징:", font=header_font, fill="#2980b9")
    current_y += 35
    
    desc = data.get('특징', '특징 정보 없음')
    # 특징은 QR코드 위쪽에 있을 확률이 높지만, 안전하게 너비 제한
    desc_lines = textwrap.wrap(desc, width=36) # 38 -> 36
    for line in desc_lines:
        draw.text((50, current_y), line, font=text_font, fill="#34495e")
        current_y += 32 # 줄간격 축소 (35 -> 32)

    current_y += 25

    # 후기 요약
    draw.text((50, current_y), "▶ 후기 요약:", font=header_font, fill="#27ae60")
    current_y += 35
    
    review = data.get('리뷰요약', '리뷰 정보 없음')
    
    # [수정 2] QR코드 침범 방지를 위해 너비 대폭 축소 (핵심!)
    # QR코드가 우측 200px 정도 차지하므로, 글자는 왼쪽 600px 안에 갇혀야 함
    # 폰트크기 24px 기준, 한글 24자는 약 580px 차지.
    review_lines = textwrap.wrap(review, width=24) # 38 -> 24 (강제 줄바꿈)
    
    for line in review_lines:
        # 만약 글자가 너무 길어져서 카드 밑바닥을 뚫으려 하면 멈춤
        if current_y > card_height - 60: 
            break
        draw.text((50, current_y), line, font=text_font, fill="#34495e")
        current_y += 32

    # 5. QR 코드 생성 (우측 하단)
    try:
        map_link = data.get('지도링크')
        # 링크가 없거나 이상하면 구글 메인으로 (에러 방지)
        if not map_link or not map_link.startswith("http"):
            map_link = "https://www.google.com/maps"
            print("⚠️ 경고: 유효하지 않은 지도 링크입니다.")
        
        print(f"🔗 QR 생성 링크: {map_link}")

        # [수정 3] QR 인식률 개선
        qr = qrcode.QRCode(
            version=None,       # 자동 버전
            error_correction=qrcode.constants.ERROR_CORRECT_M, # 오류 복원 중간 단계 (손상 대비)
            box_size=10, 
            border=4            # 테두리(여백) 4칸 (표준) - 인식률 상승
        )
        qr.add_data(map_link)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((180, 180)) # 크기 확보
        
        # 우측 하단 배치 (여백 확보)
        # QR 위치: x=580 ~ 760, y=880 ~ 1060
        img.paste(qr_img, (card_width - 220, card_height - 220))
        
    except Exception as e:
        print(f"❌ QR 실패: {e}")
    
    # 6. 테두리
    draw.rectangle([(0,0), (card_width-1, card_height-1)], outline="#bdc3c7", width=5)

    filename = "restaurant_card.png"
    img.save(filename)
    return filename
