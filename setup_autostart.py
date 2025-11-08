import os
import sys
import winreg

def add_to_startup():
    """윈도우 시작 프로그램에 등록"""

    # 현재 스크립트의 절대 경로
    if getattr(sys, 'frozen', False):
        # PyInstaller로 만든 exe 파일인 경우
        app_path = sys.executable
    else:
        # Python 스크립트인 경우
        script_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(script_dir, "WallpaperPlayer.exe")

    # 레지스트리 키 경로
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "WallpaperPlayer"

    try:
        # 레지스트리 키 열기
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        # 값 설정
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)

        # 키 닫기
        winreg.CloseKey(key)

        print(f"✓ 시작 프로그램에 등록되었습니다: {app_path}")
        return True

    except Exception as e:
        print(f"✗ 시작 프로그램 등록 실패: {e}")
        return False

def remove_from_startup():
    """윈도우 시작 프로그램에서 제거"""

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "WallpaperPlayer"

    try:
        # 레지스트리 키 열기
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        # 값 삭제
        winreg.DeleteValue(key, app_name)

        # 키 닫기
        winreg.CloseKey(key)

        print("✓ 시작 프로그램에서 제거되었습니다.")
        return True

    except FileNotFoundError:
        print("✓ 이미 시작 프로그램에 등록되어 있지 않습니다.")
        return True
    except Exception as e:
        print(f"✗ 시작 프로그램 제거 실패: {e}")
        return False

def is_in_startup():
    """시작 프로그램에 등록되어 있는지 확인"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "WallpaperPlayer"

    try:
        # 레지스트리 키 열기
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)

        # 값 읽기 시도
        try:
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False

    except Exception as e:
        print(f"레지스트리 확인 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Wallpaper Player - 시작 프로그램 설정")
    print("=" * 50)
    print()
    print("1. 시작 프로그램에 등록")
    print("2. 시작 프로그램에서 제거")
    print()

    choice = input("선택하세요 (1 또는 2): ").strip()

    if choice == "1":
        add_to_startup()
    elif choice == "2":
        remove_from_startup()
    else:
        print("잘못된 선택입니다.")

    input("\n아무 키나 눌러 종료...")
