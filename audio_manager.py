"""
오디오 관리 모듈
- 비디오에서 오디오 추출 및 캐싱
- pygame.mixer 기반 오디오 재생 관리
- 비디오/오디오 싱크 유지
- Context Manager로 안전한 리소스 관리
"""
import os
import tempfile
import pygame
from moviepy.editor import VideoFileClip
from logger import get_logger

logger = get_logger("AudioManager")


class AudioManager:
    """
    오디오 추출 및 재생 관리 클래스

    개선사항:
    1. 오디오 추출 캐싱 (temp 폴더 활용)
    2. 싱크 유지를 위한 volume 조절 (stop 대신)
    3. Context Manager 패턴으로 안전한 리소스 정리
    4. 재시작/루프 시 싱크 유지
    """

    def __init__(self):
        """AudioManager 초기화"""
        # pygame.mixer 초기화
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            logger.info("pygame.mixer initialized")

        # 오디오 상태
        self.audio_file_path = None
        self.has_audio = False
        self.volume = 1.0
        self.muted = False

        # 캐시 디렉토리
        self.temp_dir = tempfile.gettempdir()

        logger.info("AudioManager initialized")

    def extract_audio(self, video_path):
        """
        비디오에서 오디오 추출 (캐싱 포함)

        Args:
            video_path: 비디오 파일 경로

        Returns:
            str: 추출된 오디오 파일 경로 (None이면 오디오 없음)
        """
        try:
            logger.info(f"Extracting audio from: {os.path.basename(video_path)}")

            # 캐시된 오디오 파일 경로 생성
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            audio_temp_path = os.path.join(self.temp_dir, f"wallpaper_audio_{video_basename}.mp3")

            # 이미 추출된 파일이 있으면 재사용
            if os.path.exists(audio_temp_path):
                logger.info(f"Using cached audio file: {audio_temp_path}")
                return audio_temp_path

            # moviepy로 오디오 추출
            with VideoFileClip(video_path) as video_clip:
                if video_clip.audio is None:
                    logger.warning("Video has no audio track")
                    return None

                video_clip.audio.write_audiofile(
                    audio_temp_path,
                    logger=None,  # moviepy 로그 비활성화
                    verbose=False
                )

            logger.info(f"Audio extracted successfully: {audio_temp_path}")
            return audio_temp_path

        except Exception as e:
            logger.error(f"Failed to extract audio: {e}", exc_info=True)
            return None

    def load_audio(self, video_path, volume=1.0, muted=False):
        """
        오디오 로드 및 재생 시작

        Args:
            video_path: 비디오 파일 경로
            volume: 초기 볼륨 (0.0 ~ 1.0)
            muted: 음소거 여부

        Returns:
            bool: 성공 여부
        """
        try:
            # 오디오 추출
            self.audio_file_path = self.extract_audio(video_path)

            if not self.audio_file_path or not os.path.exists(self.audio_file_path):
                logger.warning("No audio track available")
                self.has_audio = False
                return False

            # 오디오 로드
            pygame.mixer.music.load(self.audio_file_path)

            # 볼륨 및 음소거 설정
            self.volume = volume
            self.muted = muted

            # 재생 시작 (음소거 시에도 싱크 유지를 위해 재생)
            pygame.mixer.music.set_volume(0.0 if muted else volume)
            pygame.mixer.music.play(loops=-1)  # 무한 반복

            self.has_audio = True
            logger.info(f"Audio loaded and playing. Muted: {muted}, Volume: {int(volume * 100)}%")
            return True

        except Exception as e:
            logger.error(f"Failed to load audio: {e}", exc_info=True)
            self.has_audio = False
            return False

    def set_volume(self, volume):
        """
        볼륨 설정

        Args:
            volume: 볼륨 (0.0 ~ 1.0)
        """
        if not self.has_audio:
            return

        self.volume = max(0.0, min(1.0, volume))

        # 음소거 상태가 아니면 볼륨 적용
        if not self.muted:
            pygame.mixer.music.set_volume(self.volume)
            logger.debug(f"Volume set to {int(self.volume * 100)}%")

    def set_muted(self, muted):
        """
        음소거 토글

        Args:
            muted: 음소거 여부

        참고:
        - stop() 대신 set_volume()을 사용하여 싱크 유지
        - 음소거 시에도 오디오는 백그라운드에서 계속 재생
        """
        if not self.has_audio:
            return

        self.muted = muted

        if muted:
            pygame.mixer.music.set_volume(0.0)  # 싱크 유지를 위해 재생은 계속
            logger.info("Audio muted")
        else:
            pygame.mixer.music.set_volume(self.volume)
            logger.info(f"Audio unmuted (volume: {int(self.volume * 100)}%)")

    def toggle_mute(self):
        """음소거 토글"""
        self.set_muted(not self.muted)

    def rewind(self):
        """
        오디오를 처음부터 재시작

        비디오와 싱크를 맞추기 위해 사용
        """
        if not self.has_audio:
            return

        try:
            pygame.mixer.music.rewind()
            logger.debug("Audio rewound")
        except Exception as e:
            logger.error(f"Failed to rewind audio: {e}")

    def stop(self):
        """오디오 정지"""
        if not self.has_audio:
            return

        try:
            pygame.mixer.music.stop()
            logger.info("Audio stopped")
        except Exception as e:
            logger.error(f"Failed to stop audio: {e}")

    def get_busy(self):
        """
        오디오가 재생 중인지 확인

        Returns:
            bool: 재생 중 여부
        """
        try:
            return pygame.mixer.music.get_busy()
        except:
            return False

    def cleanup(self):
        """리소스 정리"""
        logger.info("Cleaning up audio resources")

        try:
            if self.has_audio:
                pygame.mixer.music.stop()
        except Exception as e:
            logger.error(f"Error stopping audio: {e}")

        self.has_audio = False
        self.audio_file_path = None

        logger.info("Audio resources cleaned up")

    # Context Manager 패턴 지원
    def __enter__(self):
        """Context Manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        self.cleanup()
        return False  # 예외를 전파함
