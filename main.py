import cv2
import pygame
import win32gui
import win32con
import win32api
import ctypes
import tempfile
import os
import threading
import sys
from moviepy.editor import VideoFileClip
import config
import settings_gui

# pygame 초기화
pygame.init()
pygame.mixer.init()

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

# 아이콘 표시 상태
show_icons = True
import time
last_mouse_move_time = time.time()
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
mute_button_x = work_area_width - button_size - 20
mute_button_y = work_area_height - button_size - 20

settings_button_x = work_area_width - button_size * 2 - 30
settings_button_y = work_area_height - button_size - 20

# 마우스 클릭 감지 스레드
def check_mouse_click():
    global mouse_clicked, muted, last_click_time, settings_clicked, show_icons, last_mouse_move_time, hovered_button
    import time

    # 마우스 왼쪽 버튼 상태 확인 (VK_LBUTTON = 0x01)
    VK_LBUTTON = 0x01
    prev_state = False

    while True:
        # 마우스 커서 위치 가져오기
        cursor_pos = win32api.GetCursorPos()
        x, y = cursor_pos

        # 화면 좌표를 작업 영역 기준으로 변환
        rel_x = x - rect.left
        rel_y = y - rect.top

        # 아이콘 영역 정의 (두 버튼을 포함하는 영역)
        icon_area_x = settings_button_x - 10
        icon_area_y = mute_button_y - 10
        icon_area_width = (mute_button_x + button_size) - icon_area_x + 10
        icon_area_height = button_size + 20

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

        # 버튼이 눌렸다가 떼어졌을 때 (클릭)
        if prev_state and not current_state:
            # 디바운싱
            current_time = time.time()
            if current_time - last_click_time > 0.3:  # 300ms

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
        time.sleep(0.01)  # CPU 사용률 줄이기

# 마우스 감지 스레드 시작
mouse_thread = threading.Thread(target=check_mouse_click, daemon=True)
mouse_thread.start()

# 동영상에서 오디오 추출
print("Extracting audio...")
try:
    video_clip = VideoFileClip(video_path)
    audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    audio_path = audio_file.name
    audio_file.close()

    if video_clip.audio is not None:
        video_clip.audio.write_audiofile(audio_path, logger=None)
        pygame.mixer.music.load(audio_path)

        # 저장된 볼륨 적용
        volume = config.get_volume()
        pygame.mixer.music.set_volume(0 if muted else volume)

        pygame.mixer.music.play(-1)  # 무한 반복
        has_audio = True
    else:
        print("No audio in video.")
        has_audio = False

    video_clip.close()
except Exception as e:
    print(f"Error loading video: {e}")
    has_audio = False

# 동영상 재생
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Failed to open video: {video_path}")
    pygame.quit()
    sys.exit(1)

clock = pygame.time.Clock()
running = True

try:
    import time
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_F1:  # F1 키로 설정 열기
                    settings_clicked = True

        # 설정 버튼 클릭 처리
        if settings_clicked:
            settings_clicked = False
            result = settings_gui.show_settings_window()
            if result:
                # 새 동영상이 선택되면 동영상 재로드
                print(f"Loading new video: {result}")
                reload_video = True

        # 음소거 상태가 변경되었으면 볼륨 조절
        if mouse_clicked:
            if has_audio:
                if muted:
                    pygame.mixer.music.set_volume(0)
                else:
                    pygame.mixer.music.set_volume(config.get_volume())
            mouse_clicked = False

        # 동영상 재로드 처리
        if reload_video:
            reload_video = False
            new_video_path = config.get_video_path()

            if new_video_path and os.path.exists(new_video_path):
                # 기존 리소스 정리
                cap.release()
                if has_audio:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    if os.path.exists(audio_path):
                        try:
                            os.unlink(audio_path)
                        except:
                            pass

                # 새 동영상 로드
                print(f"Loading video: {new_video_path}")
                cap = cv2.VideoCapture(new_video_path)

                if not cap.isOpened():
                    print(f"Failed to open video: {new_video_path}")
                else:
                    # 새 오디오 추출
                    try:
                        video_clip = VideoFileClip(new_video_path)
                        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        audio_path = audio_file.name
                        audio_file.close()

                        if video_clip.audio is not None:
                            video_clip.audio.write_audiofile(audio_path, logger=None)
                            pygame.mixer.music.load(audio_path)
                            pygame.mixer.music.set_volume(0 if muted else config.get_volume())
                            pygame.mixer.music.play(-1)
                            has_audio = True
                        else:
                            print("No audio in video.")
                            has_audio = False

                        video_clip.close()
                    except Exception as e:
                        print(f"Error loading audio: {e}")
                        has_audio = False

        # 아이콘 표시 타이머 체크
        current_time = time.time()
        if current_time - last_mouse_move_time > icon_show_duration:
            show_icons = False

        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 영상 반복
            continue

        # OpenCV는 BGR, pygame은 RGB 사용
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (work_area_width, work_area_height))

        # numpy 배열을 pygame surface로 변환
        frame = frame.swapaxes(0, 1)  # (height, width, 3) -> (width, height, 3)
        surface = pygame.surfarray.make_surface(frame)

        # 화면에 그리기
        screen.blit(surface, (0, 0))

        # 아이콘이 표시되어야 할 때만 렌더링
        if show_icons:
            # 호버 효과: 스케일 및 밝기 증가
            hover_scale = 1.15

            # 음소거 버튼 아이콘
            if muted:
                icon_to_draw = mute_icon
            else:
                icon_to_draw = volume_icon

            if hovered_button == 'mute':
                # 호버 시 크기 증가 및 백그라운드 추가
                scaled_size = int(button_size * hover_scale)
                scaled_icon = pygame.transform.scale(icon_to_draw, (scaled_size, scaled_size))
                offset = (button_size - scaled_size) // 2

                # 반투명 원형 배경
                glow_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (255, 255, 255, 80), (scaled_size // 2, scaled_size // 2), scaled_size // 2)
                screen.blit(glow_surface, (mute_button_x + offset, mute_button_y + offset))

                screen.blit(scaled_icon, (mute_button_x + offset, mute_button_y + offset))
            else:
                screen.blit(icon_to_draw, (mute_button_x, mute_button_y))

            # 설정 버튼 아이콘
            if hovered_button == 'settings':
                # 호버 시 크기 증가 및 백그라운드 추가
                scaled_size = int(button_size * hover_scale)
                scaled_icon = pygame.transform.scale(settings_icon, (scaled_size, scaled_size))
                offset = (button_size - scaled_size) // 2

                # 반투명 원형 배경
                glow_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (255, 255, 255, 80), (scaled_size // 2, scaled_size // 2), scaled_size // 2)
                screen.blit(glow_surface, (settings_button_x + offset, settings_button_y + offset))

                screen.blit(scaled_icon, (settings_button_x + offset, settings_button_y + offset))
            else:
                screen.blit(settings_icon, (settings_button_x, settings_button_y))

        pygame.display.flip()

        clock.tick(30)  # 30 FPS

except KeyboardInterrupt:
    print("Program terminated by user.")
finally:
    cap.release()
    if has_audio:
        pygame.mixer.music.stop()
    pygame.quit()

    # 임시 오디오 파일 삭제
    if has_audio and os.path.exists(audio_path):
        try:
            os.unlink(audio_path)
        except:
            pass
