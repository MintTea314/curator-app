import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
import qrcode

def create_restaurant_card(data):
    """
    맛집 정보를 받아 카드 이미지를 생성하고 경로를 반환
    """
    # 1. 배경 이미지 생성
    width, height = 800, 1000
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # 2. 폰트 설정 (서버에 설치된 나눔고딕 경로 지정)
    # Ubuntu 리눅스 표준 폰트 경로
    font_path_bold = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    
    # 윈도우나 다른 환경일 경우를 대비한 예비책
    if not os.path.exists(font_path_bold):
        # 만약 경로에 없으면 그냥 시스템 기본 폰트 시도 (깨질 수 있음)
        font_path_bold = "arial.ttf" 
        font_path_reg = "arial.ttf"

    try:
        title_font = ImageFont.truetype(font_path_bold, 50)  # 제목 (볼드)
        text_font = ImageFont.truetype(font_path_reg, 30)    # 본문 (일반)
        small_font = ImageFont.truetype(font_path_reg, 20)   # 소제목
    except:
        # 폰트 로드 실패 시 기본 폰트 (한글 깨짐)
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # 3. 텍스트 그리기 위치 설정
    current_y = 50 

    # 식당 이름
    name = data.get('식당이름', '알 수 없는 식당')
    
    # 제목 줄바꿈 처리
    wrapped_title = textwrap.wrap(name, width=18) 
    for line in wrapped_title:
        draw.text((50, current_y), line, font=title_font, fill="black")
        current_y += 60
    
    current_y += 20 # 여백

    # 평점
    rating = data.get('평점', 0.0)
    draw.text((50, current_y), f"⭐ 구글 평점: {rating}점", font=text_font, fill="#f39c12")
    current_y += 50

    # 특징 (소제목)
    draw.text((50, current_y), "💡 특징:", font=title_font, fill="#2980b9") # 제목 폰트로 강조
    current_y += 55 # 간격 조금 더 벌림
    
    desc = data.get('특징', '특징 정보 없음')
    desc_lines = textwrap.wrap(desc, width=32) # 한글 기준 너비 조절
    
    for line in desc_lines:
        draw.text((50, current_y), line, font=text_font, fill="#333333")
        current_y += 38

    current_y += 30 

    # 후기 요약 (소제목)
    draw.text((50, current_y), "🗣️ 후기 요약:", font=title_font, fill="#27ae60")
    current_y += 55
    
    review = data.get('리뷰요약', '리뷰 정보 없음')
    review_lines = textwrap.wrap(review, width=32)
    
    for line in review_lines:
        draw.text((50, current_y), line, font=text_font, fill="#333333")
        current_y += 38

    # 4. QR 코드 생성 (우측 하단)
    try:
        map_link = data.get('지도링크', 'https://google.com')
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(map_link)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((180, 180)) # 크기 살짝 조정
        
        # 카드 우측 하단에 붙이기
        img.paste(qr_img, (width - 230, height - 230))
    except Exception as e:
        print(f"QR 생성 실패: {e}")
    
    # 5. 파일 저장
    filename = "restaurant_card.png"
    img.save(filename)
    return filename
