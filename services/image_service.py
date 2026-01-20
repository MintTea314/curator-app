import os
import textwrap
import requests  # [추가] 사진 다운로드용
from io import BytesIO # [추가] 이미지 데이터 처리용
from PIL import Image, ImageDraw, ImageFont, ImageOps # [추가] ImageOps(자르기용)
import qrcode

def create_restaurant_card(data):
    """
    맛집 정보를 받아 카드 이미지를 생성하고 경로를 반환
    """
    # 1. 캔버스 설정 (흰색 배경)
    card_width, card_height = 800, 1100 # 높이를 조금 늘림
    img = Image.new('RGB', (card_width, card_height), color='white')
    draw = ImageDraw.Draw(img)

    # 2. 폰트 설정 (서버 나눔고딕 경로)
    font_path_bold = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    
    # 윈도우 대비 예비책
    if not os.path.exists(font_path_bold): font_path_bold = "arial.ttf"
    if not os.path.exists(font_path_reg): font_path_reg = "arial.ttf"

    try:
        # 폰트 크기 약간 조절
        title_font = ImageFont.truetype(font_path_bold, 45) # 제목
        header_font = ImageFont.truetype(font_path_bold, 28) # 소제목(특징, 후기)
        text_font = ImageFont.truetype(font_path_reg, 26)   # 본문
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # 3. [핵심] 상단 이미지 처리
    current_y = 50 # 기본 시작 위치
    photo_url = data.get('사진URL')
    
    if photo_url:
        try:
            print(f"📸 이미지 다운로드 시도: {photo_url[:30]}...")
            response = requests.get(photo_url, timeout=5)
            response.raise_for_status()
            
            # 이미지 열기
            food_img = Image.open(BytesIO(response.content)).convert("RGB")
            
            # 헤더 이미지 크기 설정 (가로 꽉 차게, 세로 400픽셀)
            header_height = 400
            
            # 이미지 비율 유지하며 중앙 중심 자르기 (Center Crop)
            food_img = ImageOps.fit(food_img, (card_width, header_height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            
            # 상단에 붙여넣기
            img.paste(food_img, (0, 0))
            
            # 글자 시작 위치를 이미지 아래로 내림
            current_y = header_height + 40 
            print("✅ 이미지 부착 완료")
            
        except Exception as e:
            print(f"❌ 이미지 처리 실패 (글자만 출력합니다): {e}")
            # 실패하면 그냥 기본 위치(50)부터 글자 시작

    # 4. 텍스트 그리기
    
    # 식당 이름
    name = data.get('식당이름', '알 수 없는 식당')
    wrapped_title = textwrap.wrap(name, width=20)
    for line in wrapped_title:
        # 그림자가 있는 것처럼 살짝 두껍게 표현 (검은색)
        draw.text((50, current_y), line, font=title_font, fill="#2c3e50") 
        current_y += 55
    
    current_y += 15

    # [수정] 이모티콘 -> 심플한 기호로 변경 (엑스박스 방지)
    # 평점 (⭐ -> ★)
    rating = data.get('평점', 0.0)
    draw.text((50, current_y), f"★ 구글 평점: {rating}점", font=text_font, fill="#d35400") # 진한 주황
    current_y += 45

    # 특징 (💡 -> ▶)
    draw.text((50, current_y), "▶ 특징:", font=header_font, fill="#2980b9") # 파랑
    current_y += 40
    
    desc = data.get('특징', '특징 정보 없음')
    desc_lines = textwrap.wrap(desc, width=38) # 본문 너비
    for line in desc_lines:
        draw.text((50, current_y), line, font=text_font, fill="#34495e") # 진한 회색
        current_y += 35

    current_y += 25

    # 후기 요약 (🗣️ -> ▶)
    draw.text((50, current_y), "▶ 후기 요약:", font=header_font, fill="#27ae60") # 초록
    current_y += 40
    
    review = data.get('리뷰요약', '리뷰 정보 없음')
    review_lines = textwrap.wrap(review, width=38)
    for line in review_lines:
        draw.text((50, current_y), line, font=text_font, fill="#34495e")
        current_y += 35

    # 5. QR 코드 (우측 하단)
    try:
        map_link = data.get('지도링크', 'https://google.com')
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(map_link)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((160, 160))
        
        # 우측 하단 배치
        img.paste(qr_img, (card_width - 200, card_height - 200))
    except Exception as e:
        print(f"QR 실패: {e}")
    
    # 6. 테두리 그리기 (심미적 완성도 UP)
    draw.rectangle([(0,0), (card_width-1, card_height-1)], outline="#bdc3c7", width=5)

    # 7. 저장
    filename = "restaurant_card.png"
    img.save(filename)
    return filename
