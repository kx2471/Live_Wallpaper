"""
UI 관리 모듈
- 아이콘, 버튼, 음량 슬라이더 관리
- 호버 효과, 투명도 처리
- Idle 시 자동 숨김/표시
"""
import pygame
import os
import sys
import time
from logger import get_logger

logger = get_logger("UIManager")


class UIManager:
    """
    UI 요소 관리 클래스

    주요 기능:
    1. 아이콘 로드 및 캐싱
    2. 버튼 렌더링 및 호버 효과
    3. 음량 슬라이더 렌더링
    4. 폰트 캐싱
    """

    def __init__(self, screen_width, screen_height):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # UI 상태
        self.show_icons = True
        self.hovered_button = None  # 'mute', 'settings', None
        self.icon_opacity = 1.0  # 0.2 ~ 1.0

        # 버튼 위치 및 크기 (아이콘 로드보다 먼저 설정)
        self.button_size = 60
        self._calculate_positions()

        # 아이콘 로드 (button_size가 필요하므로 나중에)
        self._load_icons()

        # 폰트 캐싱
        self.cached_font = pygame.font.Font(None, 24)

        # Idle 타이머
        self.last_mouse_move_time = time.time()
        self.icon_show_duration = 10.0  # 10초

        logger.info("UIManager initialized")

    def _load_icons(self):
        """아이콘 파일 로드"""
        try:
            # 실행 파일 경로 확인
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            icon_dir = os.path.join(base_path, "icon")

            # 아이콘 로드 및 크기 조정
            self.volume_icon = pygame.image.load(os.path.join(icon_dir, "volume.png")).convert_alpha()
            self.volume_icon = pygame.transform.scale(self.volume_icon, (self.button_size, self.button_size))

            self.mute_icon = pygame.image.load(os.path.join(icon_dir, "mute.png")).convert_alpha()
            self.mute_icon = pygame.transform.scale(self.mute_icon, (self.button_size, self.button_size))

            self.settings_icon = pygame.image.load(os.path.join(icon_dir, "setting.png")).convert_alpha()
            self.settings_icon = pygame.transform.scale(self.settings_icon, (self.button_size, self.button_size))

            logger.info("Icons loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load icons: {e}", exc_info=True)
            raise

    def _calculate_positions(self):
        """버튼 및 슬라이더 위치 계산"""
        # 음량 조절바
        self.volume_slider_width = 150
        self.volume_slider_height = 10
        self.volume_slider_x = self.screen_width - self.volume_slider_width - 80
        self.volume_slider_y = self.screen_height - 35

        # 버튼 위치
        self.mute_button_x = self.volume_slider_x - self.button_size - 20
        self.mute_button_y = self.screen_height - self.button_size - 20

        self.settings_button_x = self.mute_button_x - self.button_size - 10
        self.settings_button_y = self.screen_height - self.button_size - 20

    def set_icon_opacity(self, opacity):
        """
        아이콘 투명도 설정

        Args:
            opacity: 투명도 (0.2 ~ 1.0)
        """
        self.icon_opacity = max(0.2, min(1.0, opacity))

    def update_hover(self, mouse_x, mouse_y):
        """
        마우스 호버 상태 업데이트

        Args:
            mouse_x: 마우스 X 좌표
            mouse_y: 마우스 Y 좌표

        Returns:
            bool: 아이콘 영역에 마우스가 있는지 여부
        """
        # 음소거 버튼 호버
        if (self.mute_button_x <= mouse_x <= self.mute_button_x + self.button_size and
            self.mute_button_y <= mouse_y <= self.mute_button_y + self.button_size):
            self.hovered_button = 'mute'
            return True

        # 설정 버튼 호버
        elif (self.settings_button_x <= mouse_x <= self.settings_button_x + self.button_size and
              self.settings_button_y <= mouse_y <= self.settings_button_y + self.button_size):
            self.hovered_button = 'settings'
            return True

        # 음량 슬라이더 호버
        elif (self.volume_slider_x <= mouse_x <= self.volume_slider_x + self.volume_slider_width and
              self.volume_slider_y - 10 <= mouse_y <= self.volume_slider_y + self.volume_slider_height + 10):
            self.hovered_button = None
            return True

        else:
            self.hovered_button = None
            return False

    def check_idle(self):
        """
        Idle 상태 체크

        Returns:
            bool: Idle 상태 여부
        """
        current_time = time.time()
        if current_time - self.last_mouse_move_time > self.icon_show_duration:
            self.show_icons = False
            return True
        return False

    def on_mouse_move(self):
        """마우스 이동 이벤트 처리"""
        self.last_mouse_move_time = time.time()
        self.show_icons = True

    def render(self, screen, muted, volume):
        """
        UI 요소 렌더링

        Args:
            screen: pygame 화면 객체
            muted: 음소거 상태
            volume: 현재 볼륨 (0.0 ~ 1.0)
        """
        if not self.show_icons:
            return

        alpha_value = int(self.icon_opacity * 255)
        hover_scale = 1.15

        # 음소거/볼륨 버튼
        icon_to_draw = self.mute_icon.copy() if muted else self.volume_icon.copy()
        icon_to_draw.set_alpha(alpha_value)

        if self.hovered_button == 'mute':
            self._draw_hover_button(screen, icon_to_draw, self.mute_button_x, self.mute_button_y, hover_scale, alpha_value)
        else:
            screen.blit(icon_to_draw, (self.mute_button_x, self.mute_button_y))

        # 설정 버튼
        settings_icon_copy = self.settings_icon.copy()
        settings_icon_copy.set_alpha(alpha_value)

        if self.hovered_button == 'settings':
            self._draw_hover_button(screen, settings_icon_copy, self.settings_button_x, self.settings_button_y, hover_scale, alpha_value)
        else:
            screen.blit(settings_icon_copy, (self.settings_button_x, self.settings_button_y))

        # 음량 슬라이더
        self._draw_volume_slider(screen, volume, muted, alpha_value)

    def _draw_hover_button(self, screen, icon, x, y, scale, alpha):
        """호버 효과가 있는 버튼 그리기"""
        scaled_size = int(self.button_size * scale)
        scaled_icon = pygame.transform.scale(icon, (scaled_size, scaled_size))
        offset = (self.button_size - scaled_size) // 2

        # 반투명 원형 배경
        glow_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        glow_alpha = int(80 * self.icon_opacity)
        pygame.draw.circle(glow_surface, (255, 255, 255, glow_alpha), (scaled_size // 2, scaled_size // 2), scaled_size // 2)
        screen.blit(glow_surface, (x + offset, y + offset))
        screen.blit(scaled_icon, (x + offset, y + offset))

    def _draw_volume_slider(self, screen, volume, muted, alpha):
        """음량 슬라이더 그리기"""
        slider_surface = pygame.Surface((self.volume_slider_width + 80, 40), pygame.SRCALPHA)

        # 배경 바
        slider_bg_rect = pygame.Rect(0, 15, self.volume_slider_width, self.volume_slider_height)
        bg_color = (100, 100, 100, alpha)
        pygame.draw.rect(slider_surface, bg_color, slider_bg_rect, border_radius=5)

        # 채워진 부분
        filled_width = int(self.volume_slider_width * volume)
        if filled_width > 0:
            filled_rect = pygame.Rect(0, 15, filled_width, self.volume_slider_height)
            filled_color = (150, 150, 150, alpha) if muted else (255, 255, 255, alpha)
            pygame.draw.rect(slider_surface, filled_color, filled_rect, border_radius=5)

        # 슬라이더 핸들
        handle_x = filled_width
        handle_y = 15 + self.volume_slider_height // 2
        handle_radius = 8
        handle_color = (255, 255, 255, alpha)
        pygame.draw.circle(slider_surface, handle_color, (handle_x, handle_y), handle_radius)

        # 볼륨 퍼센트 표시 (폰트 캐싱)
        volume_percent = int(volume * 100)
        volume_text = self.cached_font.render(f"{volume_percent}%", True, (255, 255, 255))
        volume_text.set_alpha(alpha)
        slider_surface.blit(volume_text, (self.volume_slider_width + 10, 10))

        # 화면에 그리기
        screen.blit(slider_surface, (self.volume_slider_x, self.volume_slider_y - 15))
