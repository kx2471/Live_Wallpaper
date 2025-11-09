import cv2
import pygame
import win32gui
import win32con
import win32api
import ctypes
import os
import threading
import sys
import config
import settings_gui

# moviepy import for audio extraction
from moviepy.editor import VideoFileClip

# pygame 초기화
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

# 임시 오디오 파일 디렉토리
import tempfile
temp_dir = tempfile.gettempdir()

def extract_audio(video_path):
    """비디오에서 오디오를 추출하여 임시 파일로 저장"""
    try:
        print(f"Extracting audio from: {os.path.basename(video_path)}")

        # 비디오 파일명 기반으로 임시 오디오 파일명 생성
        video_basename = os.path.splitext(os.path.basename(video_path))[0]
        audio_temp_path = os.path.join(temp_dir, f"wallpaper_audio_{video_basename}.mp3")

        # 이미 추출된 파일이 있으면 재사용
        if os.path.exists(audio_temp_path):
            print(f"Using cached audio file: {audio_temp_path}")
            return audio_temp_path

        # moviepy로 오디오 추출
        video_clip = VideoFileClip(video_path)

        if video_clip.audio is None:
            print("Warning: Video has no audio track")
            video_clip.close()
            return None

        video_clip.audio.write_audiofile(audio_temp_path, logger=None, verbose=False)
        video_clip.close()

        print(f"Audio extracted successfully: {audio_temp_path}")
        return audio_temp_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        import traceback
        traceback.print_exc()
        return None

# 첫 실행 확인 및 동영상 선택
video_path = config.get_video_path()

if not video_path or not os.path.exists(video_path):
    print("First time setup...")
    video_path = settings_gui.show_first_time_setup()

    if not video_path:
        sys.exit(0)

print(f"Loading video: {video_path}")

# 화면 및 작업표시줄 크기 가져오기
screen_info = pygame.display.Info()
screen_width = screen_info.current_w
screen_height = screen_info.current_h

# 작업 영역 크기 가져오기 (작업표시줄 제외)
class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]

rect = RECT()
ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
work_area_height = rect.bottom - rect.top
work_area_width = rect.right - rect.left

# pygame 창 생성 (작업표시줄 제외한 영역만)
screen = pygame.display.set_mode((work_area_width, work_area_height), pygame.NOFRAME)
pygame.display.set_caption("Wallpaper Player")

# pygame 창 핸들 가져오기
hwnd = pygame.display.get_wm_info()['window']

# 창 위치를 작업 영역 시작점으로 이동
win32gui.SetWindowPos(hwnd, 0, rect.left, rect.top, work_area_width, work_area_height, 0)

# WorkerW 윈도우를 찾기 위한 콜백 함수
workerw = None
def enum_windows_callback(hwnd_check, _):
    global workerw
    p = win32gui.FindWindowEx(hwnd_check, 0, "SHELLDLL_DefView", None)
    if p != 0:
        workerw = win32gui.FindWindowEx(0, hwnd_check, "WorkerW", None)
    return True

# Progman 찾기 및 메시지 전송
progman = win32gui.FindWindow("Progman", None)
win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

# WorkerW 찾기
win32gui.EnumWindows(enum_windows_callback, 0)

if workerw is not None:
    # pygame 창을 WorkerW의 자식으로 설정
    win32gui.SetParent(hwnd, workerw)
else:
    print("WorkerW not found. Running in normal window mode.")

# 음소거 상태 (설정에서 로드)
muted = config.get_muted()
mouse_clicked = False
last_click_time = 0
settings_clicked = False
reload_video = False  # 동영상 재로드 플래그
settings_window = None  # 설정 창 객체

# 아이콘 표시 상태
import time
show_icons = True
last_mouse_move_time = time.time()  # 현재 시간으로 초기화하여 시작시 아이콘 표시
icon_show_duration = 10.0  # 10초

# 호버 상태 추적
hovered_button = None  # 'mute', 'settings', or None

# 실행 파일 경로 확인
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 실행 파일
    base_path = sys._MEIPASS
else:
    # 일반 Python 스크립트
    base_path = os.path.dirname(os.path.abspath(__file__))

# 버튼 위치 및 크기 (작업 영역 기준)
button_size = 60

# 아이콘 로드 및 크기 조정
icon_dir = os.path.join(base_path, "icon")
volume_icon = pygame.image.load(os.path.join(icon_dir, "volume.png")).convert_alpha()
volume_icon = pygame.transform.scale(volume_icon, (button_size, button_size))

mute_icon = pygame.image.load(os.path.join(icon_dir, "mute.png")).convert_alpha()
mute_icon = pygame.transform.scale(mute_icon, (button_size, button_size))

settings_icon = pygame.image.load(os.path.join(icon_dir, "setting.png")).convert_alpha()
settings_icon = pygame.transform.scale(settings_icon, (button_size, button_size))

# 음량 조절바 설정
volume_slider_width = 150
volume_slider_height = 10
volume_slider_x = work_area_width - volume_slider_width - 80  # 오른쪽 여백 증가 (20 -> 80)
volume_slider_y = work_area_height - 35

# 버튼 위치 (음량 조절바 왼쪽으로 이동)
mute_button_x = volume_slider_x - button_size - 20
mute_button_y = work_area_height - button_size - 20

settings_button_x = mute_button_x - button_size - 10
settings_button_y = work_area_height - button_size - 20

# 음량 조절 상태
current_volume = config.get_volume()
dragging_volume = False

# 아이콘 투명도 (설정에서 로드)
icon_opacity = config.get_actual_icon_opacity()  # 0.2-1.0

# 설정 파일 체크 최적화 (매 프레임마다 읽지 않고 주기적으로 체크)
last_config_check_time = time.time()
config_check_interval = 0.1  # 0.1초마다만 설정 파일 체크

# 마우스 클릭 감지 스레드
def check_mouse_click():
    global mouse_clicked, muted, last_click_time, settings_clicked, show_icons, last_mouse_move_time, hovered_button
    global current_volume, dragging_volume, hwnd
    import time

    # 마우스 왼쪽 버튼 상태 확인 (VK_LBUTTON = 0x01)
    VK_LBUTTON = 0x01
    prev_state = False

    while True:
        try:
            # pygame 창의 실제 위치 가져오기 (WorkerW 자식으로 설정된 후에도 정확한 위치 추적)
            try:
                # hwnd 유효성 검증
                if win32gui.IsWindow(hwnd):
                    window_rect = win32gui.GetWindowRect(hwnd)
                    window_left = window_rect[0]
                    window_top = window_rect[1]
                else:
                    # hwnd가 유효하지 않으면 기본값 사용
                    window_left = rect.left
                    window_top = rect.top
            except Exception as e:
                # Win32 API 호출 실패 시 기본값 사용 (절전 모드 후 등)
                print(f"Warning: Failed to get window position: {e}")
                window_left = rect.left
                window_top = rect.top

            # 마우스 커서 위치 가져오기
            try:
                cursor_pos = win32api.GetCursorPos()
                x, y = cursor_pos
            except Exception as e:
                # 마우스 위치 가져오기 실패 시 스킵
                print(f"Warning: Failed to get cursor position: {e}")
                time.sleep(0.1)
                continue

            # 화면 좌표를 pygame 창 기준으로 변환
            rel_x = x - window_left
            rel_y = y - window_top

            # 아이콘 영역 정의 (버튼들과 음량 조절바를 포함하는 영역) - 더 넓게 설정
            icon_area_x = settings_button_x - 20
            icon_area_y = volume_slider_y - 20
            icon_area_width = (volume_slider_x + volume_slider_width) - icon_area_x + 40
            icon_area_height = button_size + 50

            # 마우스가 아이콘 영역에 있는지 확인
            if (icon_area_x <= rel_x <= icon_area_x + icon_area_width and
                icon_area_y <= rel_y <= icon_area_y + icon_area_height):
                # 아이콘 영역에 마우스가 있으면 타이머 갱신 및 아이콘 표시
                last_mouse_move_time = time.time()
                show_icons = True

                # 각 버튼별 호버 상태 확인
                if (mute_button_x <= rel_x <= mute_button_x + button_size and
                    mute_button_y <= rel_y <= mute_button_y + button_size):
                    hovered_button = 'mute'
                elif (settings_button_x <= rel_x <= settings_button_x + button_size and
                      settings_button_y <= rel_y <= settings_button_y + button_size):
                    hovered_button = 'settings'
                else:
                    hovered_button = None
            else:
                hovered_button = None

            # 현재 마우스 버튼 상태
            current_state = win32api.GetAsyncKeyState(VK_LBUTTON) & 0x8000

            # 음량 조절바 드래그 처리
            if current_state:
                # 아이콘이 표시되어 있거나 이미 드래그 중일 때만 처리
                if show_icons or dragging_volume:
                    # 음량 조절바 영역 확인 (세로로 좀 더 넓게)
                    if (volume_slider_x <= rel_x <= volume_slider_x + volume_slider_width and
                        volume_slider_y - 10 <= rel_y <= volume_slider_y + volume_slider_height + 10):
                        dragging_volume = True
                        # 음량 계산 (0.0 ~ 1.0)
                        volume_ratio = (rel_x - volume_slider_x) / volume_slider_width
                        volume_ratio = max(0.0, min(1.0, volume_ratio))
                        current_volume = volume_ratio
                        config.set_volume(current_volume)
                        mouse_clicked = True  # 볼륨 업데이트 트리거
            else:
                dragging_volume = False

            # 버튼이 눌렸다가 떼어졌을 때 (클릭)
            if prev_state and not current_state:
                # 디바운싱
                current_time = time.time()
                if current_time - last_click_time > 0.3:  # 300ms

                    # 아이콘이 표시되어 있을 때만 버튼 클릭 처리
                    if show_icons:
                        # 음소거 버튼 클릭 확인
                        if (mute_button_x <= rel_x <= mute_button_x + button_size and
                            mute_button_y <= rel_y <= mute_button_y + button_size):

                            muted = not muted
                            config.set_muted(muted)
                            last_click_time = current_time
                            mouse_clicked = True

                        # 설정 버튼 클릭 확인
                        elif (settings_button_x <= rel_x <= settings_button_x + button_size and
                              settings_button_y <= rel_y <= settings_button_y + button_size):

                            settings_clicked = True
                            last_click_time = current_time

            prev_state = current_state

        except Exception as e:
            # 예외 발생 시 스레드가 종료되지 않도록 처리 (절전 모드 복귀 등)
            print(f"Error in mouse detection thread: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(0.1)  # 에러 발생 시 잠시 대기 후 재시도
            continue

        time.sleep(0.01)  # CPU 사용률 줄이기 (~100Hz, 더 빠른 반응성)

# 마우스 감지 스레드 시작
mouse_thread = threading.Thread(target=check_mouse_click, daemon=True)
mouse_thread.start()

# 동영상 및 오디오 재생 준비
print("Loading video with audio...")
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Failed to open video: {video_path}")
    pygame.quit()
    sys.exit(1)

# 오디오 추출 및 로드
audio_file_path = extract_audio(video_path)
has_audio = False

if audio_file_path and os.path.exists(audio_file_path):
    try:
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.set_volume(0.0 if muted else current_volume)
        pygame.mixer.music.play(loops=-1)  # 무한 반복 재생
        has_audio = True
        print(f"Audio loaded and playing. Muted: {muted}, Volume: {int(current_volume * 100)}%")
    except Exception as e:
        print(f"Warning: Failed to load audio: {e}")
        has_audio = False
else:
    print("No audio track available for this video")

# 비디오 FPS 가져오기
video_fps = cap.get(cv2.CAP_PROP_FPS)
if video_fps <= 0 or video_fps > 120:  # 유효하지 않은 FPS 값 처리
    video_fps = 30.0
    print(f"Warning: Invalid FPS detected, using default 30 FPS")
else:
    print(f"Video FPS: {video_fps}")

# 비디오 길이 계산 (초 단위)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
video_duration = total_frames / video_fps if video_fps > 0 else 0
print(f"Video duration: {video_duration:.2f} seconds ({total_frames} frames)")

clock = pygame.time.Clock()
running = True

try:
    import time
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 설정 버튼 클릭 처리
        if settings_clicked:
            settings_clicked = False

            # 설정 창이 이미 열려있지 않으면 새로 열기
            if settings_window is None or not settings_window.is_open():
                print("Opening settings window...")

                # 오디오/비디오 싱크 문제 해결: 설정 창 열 때 처음부터 재시작
                print("Restarting video and audio for sync...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 비디오 처음으로
                if has_audio:
                    pygame.mixer.music.rewind()  # 오디오 처음으로
                print("Video and audio restarted successfully")

                settings_window = settings_gui.show_settings_window()

        # 설정 창이 열려있으면 업데이트
        if settings_window is not None and settings_window.is_open():
            settings_window.update_window()
        elif settings_window is not None and not settings_window.is_open():
            # 설정 창이 닫혔을 때 처리

            # 종료 플래그 확인
            if settings_window.quit_app:
                print("User requested to quit application")
                running = False
                settings_window = None
                continue

            result = settings_window.get_result()
            if result:
                # 새 동영상이 선택되면 동영상 재로드
                print(f"Video change requested: {result}")
                reload_video = True

            # 설정이 변경되었을 수 있으므로 볼륨, mute, 투명도 상태 다시 로드
            new_volume = config.get_volume()
            new_muted = config.get_muted()
            new_icon_opacity = config.get_actual_icon_opacity()

            if new_volume != current_volume or new_muted != muted or new_icon_opacity != icon_opacity:
                current_volume = new_volume
                muted = new_muted
                icon_opacity = new_icon_opacity
                mouse_clicked = True  # 볼륨 업데이트 트리거
                print(f"Settings updated - Volume: {int(current_volume * 100)}%, Muted: {muted}, Icon Opacity: {int(config.get_icon_opacity())}%")

            settings_window = None  # 설정 창 객체 정리

        # 음소거 상태 또는 볼륨이 변경되었으면 볼륨 조절
        if mouse_clicked:
            if has_audio:
                if muted:
                    pygame.mixer.music.set_volume(0.0)
                else:
                    pygame.mixer.music.set_volume(current_volume)
            mouse_clicked = False

        # 동영상 재로드 처리
        if reload_video:
            reload_video = False
            new_video_path = config.get_video_path()

            if new_video_path and os.path.exists(new_video_path):
                print(f"\n{'='*50}")
                print(f"Changing video to: {os.path.basename(new_video_path)}")
                print(f"{'='*50}")

                # 기존 리소스 정리
                print("Releasing current video resources...")
                cap.release()
                if has_audio:
                    pygame.mixer.music.stop()

                # 새 동영상 로드
                print(f"Loading new video: {new_video_path}")
                cap = cv2.VideoCapture(new_video_path)

                if not cap.isOpened():
                    print(f"ERROR: Failed to open video: {new_video_path}")
                else:
                    print("Video loaded successfully!")

                    # 새 비디오의 FPS 가져오기
                    video_fps = cap.get(cv2.CAP_PROP_FPS)
                    if video_fps <= 0 or video_fps > 120:
                        video_fps = 30.0
                        print(f"Warning: Invalid FPS detected, using default 30 FPS")
                    else:
                        print(f"New video FPS: {video_fps}")

                    # 비디오 길이 계산
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    video_duration = total_frames / video_fps if video_fps > 0 else 0
                    print(f"New video duration: {video_duration:.2f} seconds ({total_frames} frames)")

                    # 비디오 경로 업데이트
                    video_path = new_video_path

                    # 새 오디오 추출 및 로드
                    try:
                        print("Extracting and loading audio from new video...")
                        audio_file_path = extract_audio(new_video_path)

                        if audio_file_path and os.path.exists(audio_file_path):
                            pygame.mixer.music.load(audio_file_path)
                            volume = config.get_volume()
                            pygame.mixer.music.set_volume(0.0 if muted else volume)
                            pygame.mixer.music.play(loops=-1)
                            has_audio = True
                            print(f"Audio loaded successfully! (Muted: {muted}, Volume: {int(volume * 100)}%)")
                        else:
                            print("Warning: New video has no audio track")
                            has_audio = False

                        print(f"{'='*50}")
                        print("Video change completed successfully!")
                        print(f"{'='*50}\n")
                    except Exception as e:
                        print(f"ERROR: Failed to load audio from new video: {e}")
                        import traceback
                        traceback.print_exc()
                        has_audio = False
            else:
                print(f"ERROR: Video file not found: {new_video_path}")

        # 아이콘 표시 타이머 체크
        current_time = time.time()
        if current_time - last_mouse_move_time > icon_show_duration:
            show_icons = False

        # 설정 변경 감지 및 실시간 업데이트 (주기적으로만 체크)
        if current_time - last_config_check_time > config_check_interval:
            last_config_check_time = current_time

            new_volume = config.get_volume()
            new_muted = config.get_muted()
            new_icon_opacity = config.get_actual_icon_opacity()

            # 볼륨이나 음소거 상태가 변경되었으면 오디오 볼륨 업데이트
            if new_volume != current_volume or new_muted != muted:
                current_volume = new_volume
                muted = new_muted
                if has_audio:
                    if muted:
                        pygame.mixer.music.set_volume(0.0)
                    else:
                        pygame.mixer.music.set_volume(current_volume)

            # 투명도가 변경되었으면 업데이트
            if new_icon_opacity != icon_opacity:
                icon_opacity = new_icon_opacity

        ret, frame = cap.read()
        if not ret:
            # 영상이 끝났으므로 비디오와 오디오를 동시에 재시작 (싱크 유지)
            print("Video ended, looping...")
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if has_audio:
                pygame.mixer.music.rewind()  # 오디오도 처음부터 재시작
            continue

        # OpenCV는 BGR, pygame은 RGB 사용
        # INTER_LINEAR: 빠르고 품질도 좋은 보간 방법 (기본값이지만 명시적으로 설정)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (work_area_width, work_area_height), interpolation=cv2.INTER_LINEAR)

        # numpy 배열을 pygame surface로 변환
        # swapaxes는 view를 반환하므로 메모리 복사 없음
        frame = frame.swapaxes(0, 1)  # (height, width, 3) -> (width, height, 3)
        surface = pygame.surfarray.make_surface(frame)

        # 화면에 그리기
        screen.blit(surface, (0, 0))

        # 아이콘이 표시되어야 할 때만 렌더링
        if show_icons:
            # 호버 효과: 스케일 및 밝기 증가
            hover_scale = 1.15

            # 투명도를 alpha 값으로 변환 (0.2-1.0 → 51-255)
            alpha_value = int(icon_opacity * 255)

            # 음소거 버튼 아이콘
            if muted:
                icon_to_draw = mute_icon.copy()
            else:
                icon_to_draw = volume_icon.copy()

            icon_to_draw.set_alpha(alpha_value)

            if hovered_button == 'mute':
                # 호버 시 크기 증가 및 백그라운드 추가
                scaled_size = int(button_size * hover_scale)
                scaled_icon = pygame.transform.scale(icon_to_draw, (scaled_size, scaled_size))
                offset = (button_size - scaled_size) // 2

                # 반투명 원형 배경 (투명도 적용)
                glow_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
                glow_alpha = int(80 * icon_opacity)
                pygame.draw.circle(glow_surface, (255, 255, 255, glow_alpha), (scaled_size // 2, scaled_size // 2), scaled_size // 2)
                screen.blit(glow_surface, (mute_button_x + offset, mute_button_y + offset))

                screen.blit(scaled_icon, (mute_button_x + offset, mute_button_y + offset))
            else:
                screen.blit(icon_to_draw, (mute_button_x, mute_button_y))

            # 설정 버튼 아이콘
            settings_icon_copy = settings_icon.copy()
            settings_icon_copy.set_alpha(alpha_value)

            if hovered_button == 'settings':
                # 호버 시 크기 증가 및 백그라운드 추가
                scaled_size = int(button_size * hover_scale)
                scaled_icon = pygame.transform.scale(settings_icon_copy, (scaled_size, scaled_size))
                offset = (button_size - scaled_size) // 2

                # 반투명 원형 배경 (투명도 적용)
                glow_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
                glow_alpha = int(80 * icon_opacity)
                pygame.draw.circle(glow_surface, (255, 255, 255, glow_alpha), (scaled_size // 2, scaled_size // 2), scaled_size // 2)
                screen.blit(glow_surface, (settings_button_x + offset, settings_button_y + offset))

                screen.blit(scaled_icon, (settings_button_x + offset, settings_button_y + offset))
            else:
                screen.blit(settings_icon_copy, (settings_button_x, settings_button_y))

            # 음량 조절바 렌더링 (투명도 적용)
            # 투명한 Surface 생성
            slider_surface = pygame.Surface((volume_slider_width + 80, 40), pygame.SRCALPHA)

            # 배경 바 (회색)
            slider_bg_rect = pygame.Rect(0, 15, volume_slider_width, volume_slider_height)
            bg_color = (100, 100, 100, alpha_value)
            pygame.draw.rect(slider_surface, bg_color, slider_bg_rect, border_radius=5)

            # 채워진 부분 (흰색 또는 음소거 시 회색)
            filled_width = int(volume_slider_width * current_volume)
            if filled_width > 0:
                filled_rect = pygame.Rect(0, 15, filled_width, volume_slider_height)
                if muted:
                    filled_color = (150, 150, 150, alpha_value)
                else:
                    filled_color = (255, 255, 255, alpha_value)
                pygame.draw.rect(slider_surface, filled_color, filled_rect, border_radius=5)

            # 슬라이더 핸들 (원형)
            handle_x = filled_width
            handle_y = 15 + volume_slider_height // 2
            handle_radius = 8
            handle_color = (255, 255, 255, alpha_value)
            pygame.draw.circle(slider_surface, handle_color, (handle_x, handle_y), handle_radius)

            # 음량 퍼센트 표시
            font = pygame.font.Font(None, 24)
            volume_percent = int(current_volume * 100)
            volume_text = font.render(f"{volume_percent}%", True, (255, 255, 255))
            volume_text.set_alpha(alpha_value)
            slider_surface.blit(volume_text, (volume_slider_width + 10, 10))

            # 완성된 슬라이더를 화면에 그리기
            screen.blit(slider_surface, (volume_slider_x, volume_slider_y - 15))

        pygame.display.flip()

        # 비디오 FPS에 맞춰 재생 속도 조절
        clock.tick(video_fps)

except KeyboardInterrupt:
    print("Program terminated by user.")
finally:
    cap.release()
    if has_audio:
        pygame.mixer.music.stop()
    pygame.quit()
