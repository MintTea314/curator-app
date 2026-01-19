import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# [수정] Noto Sans 폰트 경로 설정 (Regular와 Bold 두 가지 사용)
FONT_PATH_REG = os.path.join("fonts", "NotoSansKR-Regular.ttf")
FONT_PATH_BOLD = os.path.join("fonts", "NotoSansKR-Bold.ttf")

def load_font(size, is_bold=False):
    """폰트 로드 함수 (Bold 옵션 추가)"""
    font_path = FONT_PATH_BOLD if is_bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        # 폰트 파일이 없을 경우 기본 폰트 사용 (경고 메시지는 생략)
        return ImageFont.load_default()

def generate_qr_code(link):
    """QR코드 생성 (120px)"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((120, 120))

def wrap_text_smart(text, font, max_width):
    """
    [핵심 수정] 단어(띄어쓰기) 단위로 안전하게 줄바꿈하는 함수
    """
    if not text: return ""
    
    # 1. 텍스트를 단어 단위로 쪼갭니다.
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        # 현재 줄에 단어를 더했을 때의 길이를 예측해봅니다.
        test_line_words = current_line + [word]
        test_line_str = ' '.join(test_line_words)
        
        try: width = font.getlength(test_line_str)
        except AttributeError: width = font.getsize(test_line_str)[0]
        
        # 허용 폭 이내라면 현재 줄에 단어 추가
        if width <= max_width:
            current_line.append(word)
        else:
            # 폭을 초과하면, 지금까지 만든 줄을 완성하고 새 줄 시작
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word] # 현재 단어가 새 줄의 첫 단어가 됨
            
    # 마지막 줄 처리
    if current_line:
        lines.append(' '.join(current_line))
        
    return "\n".join(lines)

def draw_list_item(draw, x, y, icon, text, font, color, max_width):
    """항목 그리기 (스마트 줄바꿈 적용)"""
    # 1. 하이픈
    draw.text((x, y), "-", font=font, fill=color)
    try: hyphen_width = font.getlength("-")
    except AttributeError: hyphen_width = font.getsize("-")[0]
    text_x = x + hyphen_width - 4
    
    # 2. 본문 (스마트 줄바꿈 함수 사용)
    full_text = f"{icon} {text}" if icon else text
    wrapped_text = wrap_text_smart(full_text, font, max_width - (text_x - x))
    draw.text((text_x, y), wrapped_text, font=font, fill=color)
    
    # 다음 줄 높이 계산
    lines_count = wrapped_text.count('\n') + 1
    # Noto Sans는 줄 간격이 조금 더 필요할 수 있어서 30 -> 32로 미세 조정
    return y + (lines_count * 32) + 10 

def create_restaurant_card(restaurant_data):
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # [수정] 용도에 맞게 폰트 로드 (제목은 Bold, 본문은 Regular)
    font_title = load_font(38, is_bold=True)
    font_text = load_font(22, is_bold=False)

    margin = 30
    text_start_y = 430
    
    # 가로폭 (QR코드가 하단으로 갔으므로 넓게 사용)
    full_text_width = canvas_width - (margin * 2)

    # --- 상단 이미지 ---
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
        except:
            draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
            draw.text((200, 180), "사진 없음", font=font_text, fill=(100,100,100))
    else:
        draw.rectangle([(0,0), (canvas_width, 400)], fill=(230, 230, 230))
        draw.text((250, 180), "사진 없음", font=font_text, fill=(100,100,100))

    # --- 정보 가져오기 ---
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    review_summ = restaurant_data.get('리뷰요약', '')
    map_link = restaurant_data.get('지도링크')

    # 색상 설정
    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    fill_blue = (30, 100, 200)
    
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = fill_blue = None

    # --- 하단 QR코드 (우측 구석) ---
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))

    # --- 텍스트 그리기 (차곡차곡 쌓기) ---
    
    # 1. 식당 이름 (Bold 폰트 사용)
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    current_y = text_start_y + 50
    
    # 2. 평점
    if rating > 0:
        current_y = draw_list_item(
            draw, margin, current_y, "⭐", 
            f"구글 평점: {rating}점", 
            font_text, fill_orange, full_text_width
        )
    
    # 3. 특징
    if description:
        current_y = draw_list_item(
            draw, margin, current_y, "💡", 
            f"특징: {description}", 
            font_text, fill_gray, full_text_width
        )

    # 4. 후기 요약
    if review_summ:
        draw_list_item(
            draw, margin, current_y, "🗣️", 
            f"후기: {review_summ}", 
            font_text, fill_blue, full_text_width
        )

    return card
