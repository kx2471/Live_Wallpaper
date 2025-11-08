"""
설정 파일 관리 모듈
"""
import json
import os

CONFIG_FILE = "wallpaper_config.json"

DEFAULT_CONFIG = {
    "video_path": None,
    "volume": 1.0,
    "muted": False
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
