"""
==============================================================================
Wallpaper Player - 리팩토링 버전
==============================================================================

주요 개선사항:
1. 모듈화 - logger, video_capture, audio_manager, ui_manager, performance_monitor 분리
2. 클래스 기반 구조 - WallpaperApp 클래스로 앱 로직 캡슐화
3. Context Manager - 안전한 리소스 관리
4. 표준 로깅 - logging 모듈 사용
5. 예외 처리 강화 - 절전 모드 복귀 등 대응
6. 성능 최적화 - 프레임 스킵, 동적 FPS, Idle 모드

모듈 구조:
- logger.py: 로깅 설정
- performance_monitor.py: 성능 모니터링 및 동적 FPS 조절
- video_capture.py: ThreadedVideoCapture (멀티스레드 비디오 디코딩)
- audio_manager.py: 오디오 추출 및 재생 관리
- ui_manager.py: UI 요소 (아이콘, 슬라이더) 관리
- config.py: 설정 파일 관리 (기존 유지)
- settings_gui.py: 설정 GUI (기존 유지)
==============================================================================
"""

import cv2
import pygame
import win32gui
import win32con
import win32api
import ctypes
import os
import sys
import time
import threading

# 커스텀 모듈 import
import config
import settings_gui
from logger import get_logger
from performance_monitor import PerformanceMonitor
from video_capture import ThreadedVideoCapture
from audio_manager import AudioManager
from ui_manager import UIManager

# 로거 초기화
logger = get_logger("Main")


class WallpaperApp:
    """
    Wallpaper Player 메인 애플리케이션 클래스

    주요 책임:
    1. 전체 앱 생명주기 관리
    2. 비디오/오디오/UI 모듈 조율
    3. Windows 데스크톱 통합
    4. 사용자 입력 처리
    5. 설정 관리
    """

    def __init__(self):
        """앱 초기화"""
        logger.info("=" * 70)
        logger.info("Wallpaper Player - Initializing (Refactored Version)")
        logger.info("=" * 70)

        # pygame 초기화
        pygame.init()

        # 비디오 경로 로드
        self.video_path = config.get_video_path()
        if not self.video_path or not os.path.exists(self.video_path):
            logger.info("First time setup required")
            self.video_path = settings_gui.show_first_time_setup()
            if not self.video_path:
                logger.warning("No video selected, exiting")
                sys.exit(0)

        # 화면 설정
        self._setup_screen()

        # Windows 데스크톱 통합
        self._setup_desktop_integration()

        # 모듈 초기화
        self.audio_manager = AudioManager()
        self.ui_manager = UIManager(self.work_area_width, self.work_area_height)
        self.performance_monitor = None  # 나중에 초기화 (video_fps 필요)
        self.video_capture = None  # 나중에 초기화

        # 상태 변수
        self.running = True
        self.is_idle = False
        self.last_activity_time = time.time()
        self.idle_threshold = 60.0  # 60초

        # 설정 로드
        self.current_volume = config.get_volume()
        self.muted = config.get_muted()
        self.icon_opacity = config.get_actual_icon_opacity()

        # 설정 창 관리
        self.settings_window = None
        self.reload_video_flag = False

        # 설정 체크 최적화
        self.last_config_check_time = time.time()
        self.config_check_interval = 0.5  # 0.5초마다

        # 마지막 프레임 (idle 모드용)
        self.last_frame_surface = None

        # pygame clock
        self.clock = pygame.time.Clock()

        # 마우스 입력 스레드
        self.mouse_thread = None
        self.mouse_clicked = False
        self.settings_clicked = False
        self.dragging_volume = False

        logger.info("WallpaperApp initialized successfully")

    def _setup_screen(self):
        """화면 설정"""
        # 화면 정보 가져오기
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

        self.work_area_width = rect.right - rect.left
        self.work_area_height = rect.bottom - rect.top
        self.work_area_left = rect.left
        self.work_area_top = rect.top

        logger.info(f"Screen: {screen_width}x{screen_height}, Work area: {self.work_area_width}x{self.work_area_height}")

        # pygame 창 생성
        self.screen = pygame.display.set_mode((self.work_area_width, self.work_area_height), pygame.NOFRAME)
        pygame.display.set_caption("Wallpaper Player")

        # pygame 창 핸들
        self.hwnd = pygame.display.get_wm_info()['window']

        # 창 위치 이동
        win32gui.SetWindowPos(
            self.hwnd, 0,
            self.work_area_left, self.work_area_top,
            self.work_area_width, self.work_area_height,
            0
        )

    def _setup_desktop_integration(self):
        """Windows 데스크톱 통합 (벽지처럼 배경에 표시)"""
        try:
            # WorkerW 윈도우 찾기
            self.workerw = None

            def enum_windows_callback(hwnd_check, _):
                p = win32gui.FindWindowEx(hwnd_check, 0, "SHELLDLL_DefView", None)
                if p != 0:
                    self.workerw = win32gui.FindWindowEx(0, hwnd_check, "WorkerW", None)
                return True

            # Progman에 메시지 전송
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

            # WorkerW 찾기
            win32gui.EnumWindows(enum_windows_callback, 0)

            if self.workerw is not None:
                # pygame 창을 WorkerW의 자식으로 설정
                win32gui.SetParent(self.hwnd, self.workerw)
                logger.info("Desktop integration successful")
            else:
                logger.warning("WorkerW not found, running in normal window mode")

        except Exception as e:
            logger.error(f"Desktop integration failed: {e}", exc_info=True)

    def load_video(self, video_path):
        """
        비디오 로드

        Args:
            video_path: 비디오 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            logger.info(f"Loading video: {os.path.basename(video_path)}")

            # 기존 비디오 캡처 정리
            if self.video_capture:
                self.video_capture.release()

            # 비디오 FPS 및 설정 가져오기
            temp_cap = cv2.VideoCapture(video_path, cv2.CAP_MSMF)
            if not temp_cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return False

            video_fps = temp_cap.get(cv2.CAP_PROP_FPS)
            if video_fps <= 0 or video_fps > 120:
                video_fps = 30.0
                logger.warning("Invalid FPS detected, using default 30")

            total_frames = int(temp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_duration = total_frames / video_fps if video_fps > 0 else 0

            logger.info(f"Video FPS: {video_fps:.2f}, Duration: {video_duration:.2f}s, Frames: {total_frames}")

            temp_cap.release()

            # 목표 FPS
            target_fps = config.get_target_fps()
            logger.info(f"Target FPS: {target_fps}")

            # ThreadedVideoCapture 생성 및 시작
            self.video_capture = ThreadedVideoCapture(
                video_path,
                queue_size=3,
                target_fps=target_fps,
                video_fps=video_fps
            )
            self.video_capture.start()

            # PerformanceMonitor 초기화 (비디오 FPS 기반)
            if self.performance_monitor is None:
                self.performance_monitor = PerformanceMonitor(
                    target_fps=target_fps,
                    min_fps=15,
                    max_fps=int(video_fps)
                )
            else:
                self.performance_monitor.set_target_fps(target_fps)

            # 오디오 로드
            self.audio_manager.load_audio(video_path, volume=self.current_volume, muted=self.muted)

            # 비디오 경로 저장
            self.video_path = video_path

            logger.info("Video and audio loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load video: {e}", exc_info=True)
            return False

    def start_mouse_thread(self):
        """마우스 입력 감지 스레드 시작"""
        self.mouse_thread = threading.Thread(target=self._mouse_input_loop, daemon=True, name="MouseInput")
        self.mouse_thread.start()
        logger.info("Mouse input thread started")

    def _mouse_input_loop(self):
        """
        마우스 입력 감지 루프 (별도 스레드)

        기능:
        1. 마우스 위치 감지 및 버튼 호버
        2. 클릭 감지 (음소거, 설정)
        3. 볼륨 슬라이더 드래그
        4. Idle 타이머 관리
        """
        VK_LBUTTON = 0x01
        prev_state = False
        last_click_time = 0

        while self.running:
            try:
                # 창 위치 가져오기
                try:
                    if win32gui.IsWindow(self.hwnd):
                        window_rect = win32gui.GetWindowRect(self.hwnd)
                        window_left = window_rect[0]
                        window_top = window_rect[1]
                    else:
                        window_left = self.work_area_left
                        window_top = self.work_area_top
                except:
                    window_left = self.work_area_left
                    window_top = self.work_area_top

                # 마우스 커서 위치
                try:
                    cursor_pos = win32api.GetCursorPos()
                    x, y = cursor_pos
                except:
                    time.sleep(0.1)
                    continue

                # 상대 좌표
                rel_x = x - window_left
                rel_y = y - window_top

                # 아이콘 영역 호버 체크
                is_in_icon_area = self.ui_manager.update_hover(rel_x, rel_y)

                if is_in_icon_area:
                    self.ui_manager.on_mouse_move()

                # 바탕화면 내 마우스 움직임 감지 (Idle 타이머 관리)
                # 전략: 다른 앱 창이 최상위(foreground)가 아니면 바탕화면으로 간주
                try:
                    foreground_hwnd = win32gui.GetForegroundWindow()

                    # 최상위 창이 없거나, 바탕화면 관련 창이거나, 우리 앱이면 타이머 리셋
                    if foreground_hwnd == 0 or foreground_hwnd == self.hwnd:
                        self.last_activity_time = time.time()
                    else:
                        # 최상위 창의 클래스 이름 확인
                        try:
                            fg_class = win32gui.GetClassName(foreground_hwnd)
                            # 바탕화면 관련 창이면 타이머 리셋
                            if fg_class in ["Progman", "WorkerW", "Shell_TrayWnd"]:
                                self.last_activity_time = time.time()
                            # 다른 앱 창이 활성화되어 있으면 타이머 리셋 안 함 (idle mode로 진입)
                        except:
                            pass
                except:
                    # 에러 발생 시 안전하게 타이머 리셋
                    self.last_activity_time = time.time()

                # 마우스 버튼 상태
                current_state = win32api.GetAsyncKeyState(VK_LBUTTON) & 0x8000

                # 볼륨 슬라이더 드래그
                if current_state and self.ui_manager.show_icons:
                    # 슬라이더 영역 확인
                    if (self.ui_manager.volume_slider_x <= rel_x <= self.ui_manager.volume_slider_x + self.ui_manager.volume_slider_width and
                        self.ui_manager.volume_slider_y - 10 <= rel_y <= self.ui_manager.volume_slider_y + self.ui_manager.volume_slider_height + 10):
                        self.dragging_volume = True
                        # 볼륨 계산
                        volume_ratio = (rel_x - self.ui_manager.volume_slider_x) / self.ui_manager.volume_slider_width
                        volume_ratio = max(0.0, min(1.0, volume_ratio))
                        self.current_volume = volume_ratio
                        config.set_volume(volume_ratio)
                        self.mouse_clicked = True
                else:
                    self.dragging_volume = False

                # 클릭 감지 (버튼 눌렀다 뗐을 때)
                if prev_state and not current_state:
                    current_time = time.time()
                    if current_time - last_click_time > 0.3:  # 디바운싱
                        if self.ui_manager.show_icons:
                            # 음소거 버튼
                            if (self.ui_manager.mute_button_x <= rel_x <= self.ui_manager.mute_button_x + self.ui_manager.button_size and
                                self.ui_manager.mute_button_y <= rel_y <= self.ui_manager.mute_button_y + self.ui_manager.button_size):
                                self.muted = not self.muted
                                config.set_muted(self.muted)
                                last_click_time = current_time
                                self.mouse_clicked = True

                            # 설정 버튼
                            elif (self.ui_manager.settings_button_x <= rel_x <= self.ui_manager.settings_button_x + self.ui_manager.button_size and
                                  self.ui_manager.settings_button_y <= rel_y <= self.ui_manager.settings_button_y + self.ui_manager.button_size):
                                self.settings_clicked = True
                                last_click_time = current_time

                prev_state = current_state

            except Exception as e:
                logger.error(f"Error in mouse input loop: {e}")
                time.sleep(0.1)
                continue

            time.sleep(0.02)  # ~50Hz

        logger.info("Mouse input thread stopped")

    def handle_settings_window(self):
        """설정 창 처리"""
        if self.settings_clicked:
            self.settings_clicked = False

            if self.settings_window is None or not self.settings_window.is_open():
                logger.info("Opening settings window")

                # 비디오/오디오 싱크를 위해 재시작
                if self.video_capture:
                    self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                if self.audio_manager.has_audio:
                    self.audio_manager.rewind()

                self.settings_window = settings_gui.show_settings_window()

        # 설정 창 업데이트
        if self.settings_window is not None and self.settings_window.is_open():
            self.settings_window.update_window()
        elif self.settings_window is not None and not self.settings_window.is_open():
            # 설정 창이 닫혔을 때 처리

            # 종료 플래그 확인
            if self.settings_window.quit_app:
                logger.info("User requested to quit")
                self.running = False
                self.settings_window = None
                return

            # 새 비디오 선택 확인
            result = self.settings_window.get_result()
            if result:
                logger.info(f"Video change requested: {result}")
                self.reload_video_flag = True

            # 설정 다시 로드
            new_volume = config.get_volume()
            new_muted = config.get_muted()
            new_icon_opacity = config.get_actual_icon_opacity()

            if new_volume != self.current_volume or new_muted != self.muted or new_icon_opacity != self.icon_opacity:
                self.current_volume = new_volume
                self.muted = new_muted
                self.icon_opacity = new_icon_opacity
                self.ui_manager.set_icon_opacity(new_icon_opacity)
                self.mouse_clicked = True
                logger.info(f"Settings updated - Volume: {int(self.current_volume * 100)}%, Muted: {self.muted}")

            self.settings_window = None

    def handle_audio_update(self):
        """오디오 볼륨/음소거 업데이트"""
        if self.mouse_clicked:
            if self.audio_manager.has_audio:
                if self.muted:
                    self.audio_manager.set_muted(True)
                else:
                    self.audio_manager.set_muted(False)
                    self.audio_manager.set_volume(self.current_volume)
            self.mouse_clicked = False

    def handle_video_reload(self):
        """비디오 재로드 처리"""
        if not self.reload_video_flag:
            return

        self.reload_video_flag = False
        new_video_path = config.get_video_path()

        if new_video_path and os.path.exists(new_video_path):
            logger.info(f"Reloading video: {os.path.basename(new_video_path)}")

            # 오디오 정리
            self.audio_manager.cleanup()

            # 비디오 재로드
            if self.load_video(new_video_path):
                logger.info("Video reloaded successfully")
            else:
                logger.error("Failed to reload video")
        else:
            logger.error(f"Video file not found: {new_video_path}")

    def check_config_updates(self):
        """설정 파일 변경 감지 (주기적)"""
        current_time = time.time()
        if current_time - self.last_config_check_time < self.config_check_interval:
            return

        self.last_config_check_time = current_time

        new_volume = config.get_volume()
        new_muted = config.get_muted()
        new_icon_opacity = config.get_actual_icon_opacity()

        # 볼륨/음소거 변경
        if new_volume != self.current_volume or new_muted != self.muted:
            self.current_volume = new_volume
            self.muted = new_muted
            if self.audio_manager.has_audio:
                if self.muted:
                    self.audio_manager.set_muted(True)
                else:
                    self.audio_manager.set_volume(self.current_volume)

        # 투명도 변경
        if new_icon_opacity != self.icon_opacity:
            self.icon_opacity = new_icon_opacity
            self.ui_manager.set_icon_opacity(new_icon_opacity)

    def check_idle_mode(self):
        """
        Idle 모드 체크

        Returns:
            bool: Idle 상태 여부
        """
        current_time = time.time()

        if current_time - self.last_activity_time > self.idle_threshold:
            if not self.is_idle:
                self.is_idle = True
                if self.video_capture:
                    self.video_capture.pause()
                logger.info("Idle mode activated")
            return True
        else:
            if self.is_idle:
                self.is_idle = False
                if self.video_capture:
                    self.video_capture.resume()
                self.last_activity_time = current_time
                logger.info("Idle mode deactivated")
            return False

    def process_frame(self):
        """
        프레임 처리 및 렌더링

        Returns:
            bool: 성공 여부
        """
        # Idle 모드 처리
        if self.check_idle_mode():
            # Idle 상태 - 마지막 프레임 유지
            if self.last_frame_surface:
                self.screen.blit(self.last_frame_surface, (0, 0))
            return True

        # 동적 FPS 조절
        if self.performance_monitor:
            new_fps, changed = self.performance_monitor.adjust_fps()
            if changed and self.video_capture:
                self.video_capture.update_fps(new_fps)

        # 프레임 읽기
        if not self.video_capture:
            return False

        ret, frame = self.video_capture.read(timeout=1.0)

        if not ret or frame is None:
            # 프레임 읽기 실패 - 마지막 프레임 유지
            if self.last_frame_surface:
                self.screen.blit(self.last_frame_surface, (0, 0))
            self.performance_monitor.record_frame(dropped=True)
            return True

        # OpenCV BGR → RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # numpy → pygame surface
        frame = frame.swapaxes(0, 1)  # (height, width, 3) → (width, height, 3)
        surface = pygame.surfarray.make_surface(frame)

        # pygame.transform.scale로 리사이징
        surface = pygame.transform.scale(surface, (self.work_area_width, self.work_area_height))

        # 마지막 프레임 저장
        self.last_frame_surface = surface

        # 화면에 그리기
        self.screen.blit(surface, (0, 0))

        # 성능 기록
        self.performance_monitor.record_frame(dropped=False)

        return True

    def run(self):
        """메인 실행 루프"""
        try:
            logger.info("Starting main loop")

            # 비디오 로드
            if not self.load_video(self.video_path):
                logger.error("Failed to load initial video")
                return

            # 마우스 입력 스레드 시작
            self.start_mouse_thread()

            # 메인 루프
            while self.running:
                # pygame 이벤트 처리
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

                # 설정 창 처리
                self.handle_settings_window()
                if not self.running:
                    break

                # 오디오 업데이트
                self.handle_audio_update()

                # 비디오 재로드
                self.handle_video_reload()

                # 설정 변경 감지
                self.check_config_updates()

                # Idle 체크
                self.ui_manager.check_idle()

                # 프레임 처리
                self.process_frame()

                # UI 렌더링
                self.ui_manager.render(self.screen, self.muted, self.current_volume)

                # 화면 업데이트
                pygame.display.flip()

                # FPS 제어
                if self.performance_monitor:
                    self.clock.tick(self.performance_monitor.target_fps)
                else:
                    self.clock.tick(30)

        except KeyboardInterrupt:
            logger.info("Interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """리소스 정리"""
        logger.info("Cleaning up resources...")

        # 비디오 캡처 정리
        if self.video_capture:
            try:
                self.video_capture.release()
            except Exception as e:
                logger.error(f"Error releasing video capture: {e}")

        # 오디오 정리
        if self.audio_manager:
            try:
                self.audio_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up audio: {e}")

        # pygame 종료
        try:
            pygame.quit()
        except Exception as e:
            logger.error(f"Error quitting pygame: {e}")

        # 성능 통계 출력
        if self.performance_monitor:
            stats = self.performance_monitor.get_stats()
            logger.info("=" * 70)
            logger.info("Performance Statistics:")
            logger.info(f"  Total Frames: {stats['total_frames']}")
            logger.info(f"  Dropped Frames: {stats['dropped_frames']}")
            logger.info(f"  Drop Rate: {stats['drop_rate']:.2f}%")
            logger.info(f"  Final Target FPS: {stats['target_fps']}")
            logger.info(f"  Avg CPU Usage: {stats['cpu_avg']:.1f}%")
            logger.info("=" * 70)

        logger.info("Cleanup complete. Exiting.")


def main():
    """진입점"""
    try:
        app = WallpaperApp()
        app.run()
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
