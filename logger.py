"""
로깅 설정 모듈
- 표준화된 로깅 인프라 제공
- 파일 + 콘솔 동시 출력
- 디버그/정보/경고/오류 레벨 분리
"""
import logging
import os
import sys
from datetime import datetime

def setup_logger(name="WallpaperPlayer", level=logging.INFO):
    """
    로거 설정 및 반환

    Args:
        name: 로거 이름
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)

    Returns:
        logging.Logger: 설정된 로거 객체
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 중복 방지
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 포맷터 설정
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적)
    try:
        if getattr(sys, 'frozen', False):
            # 실행 파일인 경우
            log_dir = os.path.dirname(sys.executable)
        else:
            # 개발 환경인 경우
            log_dir = os.path.dirname(os.path.abspath(__file__))

        log_file = os.path.join(log_dir, "wallpaper_player.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 파일은 모든 레벨 기록
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 파일 핸들러 실패해도 콘솔 로깅은 계속
        print(f"Warning: Could not create file logger: {e}")

    return logger

# 기본 로거 생성
default_logger = setup_logger()

def get_logger(name=None):
    """
    로거 가져오기

    Args:
        name: 로거 이름 (None이면 기본 로거 반환)

    Returns:
        logging.Logger: 로거 객체
    """
    if name:
        return logging.getLogger(f"WallpaperPlayer.{name}")
    return default_logger
