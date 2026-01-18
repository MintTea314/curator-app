import qrcode
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# [수정 1] 새로운 폰트 파일 경로 지정
# (반드시 fonts 폴더 안에 Hakgyoansim_OcarinaR.ttf 파일이 있어야 합니다!)
FONT_PATH = os.path.join("fonts", "Hakgyoansim_OcarinaR.ttf")

def load_font(size):
    """폰트를 불러오는 헬퍼 함수"""
    try:
        # Pillow 최신 버전에서는 getlength를 사용하기 위해 레이아웃 엔진을 지정하는 것이 좋습니다.
        return ImageFont.truetype(FONT_PATH, size, layout_engine=ImageFont.LAYOUT_BASIC)
    except IOError:
        print(f"\n⚠️ [경고] 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
        print("👉 'fonts' 폴더에 새 폰트 파일이 있는지 확인해주세요.")
        return ImageFont.load_default()

def generate_qr_code(link):
    """QR코드 이미지 생성 (크기 180x180)"""
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((180, 180))

def wrap_text_pixel_based(text, font, max_width):
    """
    [핵심 기능] 주어진 픽셀 너비(max_width)를 넘어가지 않도록
    글자 단위로 계산해서 줄바꿈을 해주는 함수입니다.
    (한글/영어 혼용 시에도 정확하게 작동합니다.)
    """
    if not text:
        return ""
        
    lines = []
    current_line = ""
    
    for char in text:
        # 현재 라인에 글자 하나를 더해봅니다.
        test_line = current_line + char
        # 그 길이가 허용된 최대 너비보다 작은지 확인합니다.
        if font.getlength(test_line) <= max_width:
            current_line = test_line
        else:
            # 너비를 초과하면, 지금까지 만든 라인을 저장하고
            lines.append(current_line)
            # 현재 글자부터 새로운 라인을 시작합니다.
            current_line = char
            
    # 마지막 남은 라인도 추가합니다.
    lines.append(current_line)
    return "\n".join(lines)

def create_restaurant_card(restaurant_data):
    # 1. 캔버스 준비
    canvas_width = 600
    canvas_height = 800
    background_color = (255, 255, 255)
    card = Image.new('RGB', (canvas_width, canvas_height), background_color)
    draw = ImageDraw.Draw(card)

    # [수정 2] 폰트 크기를 요청하신 대로 2pt씩 줄였습니다.
    font_title = load_font(38) # 40 -> 38
    font_text = load_font(22)  # 24 -> 22
    font_small = load_font(16) # 18 -> 16

    # 기본 레이아웃 설정
    margin = 30
    text_start_y = 430
    qr_size = 180
    # 텍스트가 QR코드를 침범하지 않도록 안전한 최대 너비를 계산합니다.
    # (전체 너비 - 왼쪽 마진 - QR코드 너비 - QR코드와 텍스트 사이 간격 약간)
    safe_text_width = canvas_width - margin - qr_size - 20 

    # --- (이미지 다운로드 영역은 기존과 동일) ---
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

    # --- 텍스트 그리기 ---
    
    # 데이터 가져오기
    name = restaurant_data.get('식당이름', '이름 모름')
    rating = restaurant_data.get('평점', 0)
    description = restaurant_data.get('특징', '')
    address = restaurant_data.get('주소', '')
    map_link = restaurant_data.get('지도링크')

    # 폰트 색상 설정 (기본 폰트로 로딩되었을 경우 대비)
    fill_black = (0, 0, 0)
    fill_orange = (255, 165, 0)
    fill_gray = (50, 50, 50)
    fill_light_gray = (100, 100, 100)
    
    if font_title.getname()[0] == "Default": 
        fill_black = fill_orange = fill_gray = fill_light_gray = None

    # 1. 식당 이름 (상단은 넓게 씁니다)
    draw.text((margin, text_start_y), name, font=font_title, fill=fill_black)
    
    # 2. 평점
    current_y = text_start_y + 50
    if rating > 0:
        draw.text((margin, current_y), f"⭐ 구글 평점: {rating}점", font=font_text, fill=fill_orange)
    
    # 3. [수정 3] 특징 (QR코드 피해서 스마트 줄바꿈)
    current_y += 50
    if description:
        # '특징:' 라벨 먼저 그리기
        draw.text((margin, current_y), "💡 특징:", font=font_text, fill=fill_gray)
        current_y += 30 # 라벨 아래로 이동
        
        # 본문 내용을 계산된 안전 너비에 맞춰서 줄바꿈합니다.
        wrapped_desc = wrap_text_pixel_based(description, font_text, safe_text_width)
        draw.text((margin, current_y), wrapped_desc, font=font_text, fill=fill_gray)

    # 4. QR코드 배치 (우측 하단 고정)
    if map_link:
        qr_img = generate_qr_code(map_link)
        qr_x = canvas_width - qr_img.width - margin
        qr_y = canvas_height - qr_img.height - margin
        card.paste(qr_img, (qr_x, qr_y))

    # 5. [수정 4] 주소 (좌측 하단, QR코드 옆 공간에 맞춤)
    if address:
        # 주소가 들어갈 공간의 y좌표 계산 (QR코드 하단 라인에 맞춤)
        address_y = canvas_height - margin - 20
        
        # 주소 텍스트도 안전 너비에 맞춰서 자릅니다.
        final_address = address
        # 만약 전체 주소의 길이가 안전 너비보다 길다면
        if font_small.getlength("📍 " + address) > safe_text_width:
            # 한 글자씩 줄여가며 맞을 때까지 반복하고 '...'을 붙입니다.
            for i in range(len(address), 0, -1):
                temp_addr = "📍 " + address[:i] + "..."
                if font_small.getlength(temp_addr) <= safe_text_width:
                    final_address = address[:i] + "..."
                    break
        else:
            final_address = "📍 " + address

        draw.text((margin, address_y), final_address, font=font_small, fill=fill_light_gray)

    return card
