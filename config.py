"""
설정 파일 관리 모듈
"""
import json
import os
import sys

# 실행 파일의 디렉토리를 기준으로 설정 파일 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 실행 파일
    app_dir = os.path.dirname(sys.executable)
else:
    # 일반 Python 스크립트
    app_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(app_dir, "wallpaper_config.json")

DEFAULT_CONFIG = {
    "video_path": None,
    "volume": 1.0,
    "muted": False,
    "icon_opacity": 100,  # 0-100 (사용자에게 표시되는 값, 실제로는 20-100%가 적용됨)
    "autostart": False  # 윈도우 시작시 자동 실행
}

def load_config():
    """설정 파일을 로드합니다."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 기본값과 병합
                return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            print(f"설정 파일 로드 실패: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """설정 파일을 저장합니다."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"설정 파일 저장 실패: {e}")
        return False

def get_video_path():
    """저장된 비디오 경로를 반환합니다."""
    config = load_config()
    return config.get("video_path")

def set_video_path(path):
    """비디오 경로를 저장합니다."""
    config = load_config()
    config["video_path"] = path
    return save_config(config)

def get_volume():
    """저장된 볼륨을 반환합니다."""
    config = load_config()
    return config.get("volume", 1.0)

def set_volume(volume):
    """볼륨을 저장합니다."""
    config = load_config()
    config["volume"] = volume
    return save_config(config)

def get_muted():
    """음소거 상태를 반환합니다."""
    config = load_config()
    return config.get("muted", False)

def set_muted(muted):
    """음소거 상태를 저장합니다."""
    config = load_config()
    config["muted"] = muted
    return save_config(config)

def get_icon_opacity():
    """아이콘 투명도를 반환합니다 (0-100)."""
    config = load_config()
    return config.get("icon_opacity", 100)

def set_icon_opacity(opacity):
    """아이콘 투명도를 저장합니다 (0-100)."""
    config = load_config()
    config["icon_opacity"] = max(0, min(100, opacity))  # 0-100 범위로 제한
    return save_config(config)

def get_actual_icon_opacity():
    """실제 적용되는 아이콘 투명도를 반환합니다 (0.2-1.0)."""
    user_value = get_icon_opacity()
    # 사용자 값 0-100을 실제 투명도 20-100%로 변환
    return 0.2 + (user_value / 100.0) * 0.8

def get_autostart():
    """자동 시작 설정을 반환합니다."""
    config = load_config()
    return config.get("autostart", False)

def set_autostart(autostart):
    """자동 시작 설정을 저장합니다."""
    config = load_config()
    config["autostart"] = autostart
    return save_config(config)
