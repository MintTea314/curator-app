import os
import textwrap  # [추가] 긴 글자 줄바꿈용
from PIL import Image, ImageDraw, ImageFont
import qrcode

def create_restaurant_card(data):
    """
    맛집 정보를 받아 카드 이미지를 생성하고 경로를 반환
    data: {식당이름, 평점, 특징, 리뷰요약, 지도링크, 사진URL(옵션)}
    """
    # 1. 배경 이미지 생성 (흰색 배경)
    width, height = 800, 1000  # 카드 크기 넉넉하게
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # 2. 폰트 설정 (서버에 폰트 파일이 있어야 함)
    # 폰트 파일 경로가 맞는지 꼭 확인하세요!
    font_path = "NotoSansKR-Bold.ttf" 
    
    try:
        title_font = ImageFont.truetype(font_path, 50)  # 제목
        text_font = ImageFont.truetype(font_path, 30)   # 본문
        small_font = ImageFont.truetype(font_path, 20)  # 소제목
    except:
        # 폰트 없으면 기본 폰트 (한글 깨질 수 있음)
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # 3. 메인 이미지 (식당 사진) 처리
    try:
        # 사진 URL이 있으면 다운로드해서 붙여넣기 기능은 나중에 추가 가능
        # 지금은 그냥 회색 박스로 대체하거나, 선생님이 구현하신 로직 유지
        # (여기서는 심플하게 상단 여백으로 처리)
        pass 
    except:
        pass

    # 4. 텍스트 그리기 위치 설정
    current_y = 50 

    # [수정] 식당 이름 (display_name 사용 권장, 없으면 식당이름)
    # AI 서비스에서 'display_name'을 안 보내줄 경우를 대비해 처리
    name = data.get('식당이름', '알 수 없는 식당')
    
    # 제목이 너무 길면 자르기
    wrapped_title = textwrap.wrap(name, width=20) 
    for line in wrapped_title:
        draw.text((50, current_y), line, font=title_font, fill="black")
        current_y += 60  # 줄간격
    
    current_y += 20 # 여백

    # 평점
    rating = data.get('평점', 0.0)
    draw.text((50, current_y), f"⭐ 구글 평점: {rating}점", font=text_font, fill="#f39c12") # 오렌지색
    current_y += 50

    # 특징 (줄바꿈 처리)
    draw.text((50, current_y), "💡 특징:", font=text_font, fill="#2980b9") # 파란색
    current_y += 40
    
    desc = data.get('특징', '특징 정보 없음')
    # textwrap.wrap(text, width=글자수) -> 한 줄에 35자 정도가 적당
    desc_lines = textwrap.wrap(desc, width=35)
    
    for line in desc_lines:
        draw.text((50, current_y), line, font=text_font, fill="black")
        current_y += 35 # 본문 줄간격

    current_y += 30 # 단락 간격

    # [수정] 후기 요약 (줄바꿈 처리)
    draw.text((50, current_y), "🗣️ 후기 요약:", font=text_font, fill="#27ae60") # 초록색
    current_y += 40
    
    review = data.get('리뷰요약', '리뷰 정보 없음')
    review_lines = textwrap.wrap(review, width=35)
    
    for line in review_lines:
        draw.text((50, current_y), line, font=text_font, fill="black")
        current_y += 35

    # 5. QR 코드 생성 및 부착 (우측 하단)
    map_link = data.get('지도링크', 'https://google.com')
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(map_link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # QR코드 크기 조절
    qr_img = qr_img.resize((200, 200))
    
    # 우측 하단에 붙이기
    img.paste(qr_img, (width - 250, height - 250))
    
    # 6. 파일 저장
    filename = "restaurant_card.png"
    img.save(filename)
    return filename
