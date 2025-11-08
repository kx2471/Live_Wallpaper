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

# 마우스 클릭 감지 스레드
def check_mouse_click():
    global mouse_clicked, muted, last_click_time, settings_clicked, show_icons, last_mouse_move_time, hovered_button
    global current_volume, dragging_volume
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

        # 아이콘 영역 정의 (버튼들과 음량 조절바를 포함하는 영역)
        icon_area_x = settings_button_x - 10
        icon_area_y = volume_slider_y - 10
        icon_area_width = (volume_slider_x + volume_slider_width) - icon_area_x + 20
        icon_area_height = button_size + 30

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
audio_path = None
has_audio = False

try:
    video_clip = VideoFileClip(video_path)

    if video_clip.audio is not None:
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        audio_path = audio_file.name
        audio_file.close()

        video_clip.audio.write_audiofile(audio_path, logger=None)
        pygame.mixer.music.load(audio_path)

        # 저장된 볼륨 적용
        volume = config.get_volume()
        pygame.mixer.music.set_volume(0 if muted else volume)

        pygame.mixer.music.play(-1)  # 무한 반복
        has_audio = True
        print(f"Audio loaded successfully. Muted: {muted}, Volume: {volume}")
    else:
        print("No audio in video.")

    video_clip.close()
except Exception as e:
    print(f"Error loading audio: {e}")
    import traceback
    traceback.print_exc()

# 동영상 재생
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Failed to open video: {video_path}")
    pygame.quit()
    sys.exit(1)

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

# 동기화를 위한 시작 시간 기록
video_start_time = time.time()
sync_check_interval = 5.0  # 5초마다 동기화 체크
last_sync_check = video_start_time

try:
    import time
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 설정 버튼 클릭 처리
        if settings_clicked:
            settings_clicked = False
            print("Opening settings window...")
            result = settings_gui.show_settings_window()
            if result:
                # 새 동영상이 선택되면 동영상 재로드
                print(f"Video change requested: {result}")
                reload_video = True

            # 설정이 변경되었을 수 있으므로 볼륨과 mute 상태 다시 로드
            new_volume = config.get_volume()
            new_muted = config.get_muted()

            if new_volume != current_volume or new_muted != muted:
                current_volume = new_volume
                muted = new_muted
                mouse_clicked = True  # 볼륨 업데이트 트리거
                print(f"Settings updated - Volume: {int(current_volume * 100)}%, Muted: {muted}")

        # 음소거 상태 또는 볼륨이 변경되었으면 볼륨 조절
        if mouse_clicked:
            if has_audio:
                if muted:
                    pygame.mixer.music.set_volume(0)
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
                    pygame.mixer.music.unload()
                    if audio_path and os.path.exists(audio_path):
                        try:
                            os.unlink(audio_path)
                            print("Temporary audio file deleted.")
                        except:
                            pass

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
                    # 새 오디오 추출
                    try:
                        print("Extracting audio from new video...")
                        video_clip = VideoFileClip(new_video_path)

                        if video_clip.audio is not None:
                            audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                            audio_path = audio_file.name
                            audio_file.close()

                            video_clip.audio.write_audiofile(audio_path, logger=None)
                            pygame.mixer.music.load(audio_path)
                            volume = config.get_volume()
                            pygame.mixer.music.set_volume(0 if muted else volume)
                            pygame.mixer.music.play(-1)
                            has_audio = True
                            print(f"Audio loaded successfully! (Muted: {muted}, Volume: {volume})")

                            # 새 동영상 시작 시간 재설정
                            video_start_time = time.time()
                            last_sync_check = video_start_time
                        else:
                            print("No audio track found in new video.")
                            has_audio = False
                            audio_path = None

                        video_clip.close()
                        print(f"{'='*50}")
                        print("Video change completed successfully!")
                        print(f"{'='*50}\n")
                    except Exception as e:
                        print(f"ERROR: Failed to load audio from new video: {e}")
                        import traceback
                        traceback.print_exc()
                        has_audio = False
                        audio_path = None
            else:
                print(f"ERROR: Video file not found: {new_video_path}")

        # 아이콘 표시 타이머 체크
        current_time = time.time()
        if current_time - last_mouse_move_time > icon_show_duration:
            show_icons = False

        ret, frame = cap.read()
        if not ret:
            # 영상이 끝났으므로 비디오와 오디오 모두 재시작
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            if has_audio:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(-1)
                print("Video loop: Restarting audio for sync")
            # 시작 시간 재설정
            video_start_time = time.time()
            last_sync_check = video_start_time
            continue

        # 주기적인 동기화 체크 (5초마다)
        current_time = time.time()
        if has_audio and current_time - last_sync_check >= sync_check_interval:
            # 비디오의 현재 재생 시간 계산 (초 단위)
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            video_position = current_frame / video_fps

            # 실제 경과 시간
            elapsed_time = current_time - video_start_time
            elapsed_time_in_video = elapsed_time % video_duration  # 루프 고려

            # 시간 차이 계산
            time_diff = abs(video_position - elapsed_time_in_video)

            # 0.5초 이상 차이나면 동기화 조정
            if time_diff > 0.5:
                print(f"Sync check: Video at {video_position:.2f}s, Expected {elapsed_time_in_video:.2f}s (diff: {time_diff:.2f}s)")
                # 오디오 재시작으로 동기화
                pygame.mixer.music.stop()
                pygame.mixer.music.play(-1)
                # 비디오 위치도 조정
                target_frame = int(elapsed_time_in_video * video_fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                print(f"Resynced: Adjusted to frame {target_frame}")

            last_sync_check = current_time

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

            # 음량 조절바 렌더링
            # 배경 바 (회색)
            slider_bg_rect = pygame.Rect(volume_slider_x, volume_slider_y, volume_slider_width, volume_slider_height)
            pygame.draw.rect(screen, (100, 100, 100), slider_bg_rect, border_radius=5)

            # 채워진 부분 (흰색 또는 음소거 시 회색)
            filled_width = int(volume_slider_width * current_volume)
            if filled_width > 0:
                filled_rect = pygame.Rect(volume_slider_x, volume_slider_y, filled_width, volume_slider_height)
                if muted:
                    pygame.draw.rect(screen, (150, 150, 150), filled_rect, border_radius=5)
                else:
                    pygame.draw.rect(screen, (255, 255, 255), filled_rect, border_radius=5)

            # 슬라이더 핸들 (원형)
            handle_x = volume_slider_x + filled_width
            handle_y = volume_slider_y + volume_slider_height // 2
            handle_radius = 8
            pygame.draw.circle(screen, (255, 255, 255), (handle_x, handle_y), handle_radius)

            # 음량 퍼센트 표시
            font = pygame.font.Font(None, 24)
            volume_percent = int(current_volume * 100)
            volume_text = font.render(f"{volume_percent}%", True, (255, 255, 255))
            text_rect = volume_text.get_rect()
            text_rect.midleft = (volume_slider_x + volume_slider_width + 10, volume_slider_y + volume_slider_height // 2)
            screen.blit(volume_text, text_rect)

        pygame.display.flip()

        # 비디오의 실제 FPS 사용
        clock.tick(video_fps)

except KeyboardInterrupt:
    print("Program terminated by user.")
finally:
    cap.release()
    if has_audio:
        pygame.mixer.music.stop()
    pygame.quit()

    # 임시 오디오 파일 삭제
    if audio_path and os.path.exists(audio_path):
        try:
            os.unlink(audio_path)
        except:
            pass
