"""
설정 GUI 모듈
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import config
import os

class SettingsWindow:
    def __init__(self, parent=None):
        self.root = tk.Tk() if parent is None else tk.Toplevel(parent)
        self.root.title("Wallpaper Player - 설정")
        self.root.geometry("600x650")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')

        self.selected_video = None
        self.result = None
        self.volume_changed = False
        self.mute_changed = False
        self.quit_app = False  # 프로그램 종료 플래그

        # 원래 설정값 백업 (취소 시 복원용)
        self.original_volume = config.get_volume()
        self.original_muted = config.get_muted()
        self.original_opacity = config.get_icon_opacity()

        self.create_widgets()
        self.center_window()

    def center_window(self):
        """창을 화면 중앙에 배치합니다."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """UI 위젯을 생성합니다."""
        # 제목
        title_label = tk.Label(
            self.root,
            text="🎬 배경화면 동영상 설정",
            font=("맑은 고딕", 16, "bold"),
            bg='#f0f0f0',
            fg='#333333'
        )
        title_label.pack(pady=20)

        # 현재 설정된 비디오 표시
        current_video = config.get_video_path()
        if current_video and os.path.exists(current_video):
            video_name = os.path.basename(current_video)

            current_frame = tk.Frame(self.root, bg='#e8f4f8', relief='groove', borderwidth=2)
            current_frame.pack(pady=10, padx=30, fill='x')

            current_title = tk.Label(
                current_frame,
                text="📂 현재 동영상:",
                font=("맑은 고딕", 10, "bold"),
                bg='#e8f4f8',
                fg='#0066cc'
            )
            current_title.pack(anchor='w', padx=10, pady=(5, 0))

            current_label = tk.Label(
                current_frame,
                text=video_name,
                font=("맑은 고딕", 9),
                bg='#e8f4f8',
                fg='#666666'
            )
            current_label.pack(anchor='w', padx=10, pady=(0, 5))

        # 파일 선택 영역
        file_frame = tk.Frame(self.root, bg='#f0f0f0')
        file_frame.pack(pady=20, padx=30)

        select_label = tk.Label(
            file_frame,
            text="🎥 새 동영상 선택:",
            font=("맑은 고딕", 11, "bold"),
            bg='#f0f0f0',
            fg='#333333'
        )
        select_label.pack(anchor='w', pady=(0, 5))

        input_frame = tk.Frame(file_frame, bg='#f0f0f0')
        input_frame.pack(fill='x')

        self.file_label = tk.Label(
            input_frame,
            text="선택된 파일 없음",
            width=45,
            anchor="w",
            relief="sunken",
            bg='white',
            font=("맑은 고딕", 9),
            padx=10,
            pady=8
        )
        self.file_label.pack(side=tk.LEFT, padx=(0, 10))

        browse_btn = tk.Button(
            input_frame,
            text="📁 찾아보기",
            command=self.browse_file,
            width=12,
            font=("맑은 고딕", 10, "bold"),
            bg='#0078d4',
            fg='white',
            relief='flat',
            cursor='hand2',
            pady=8
        )
        browse_btn.pack(side=tk.LEFT)

        # 구분선
        separator1 = tk.Frame(self.root, bg='#cccccc', height=1)
        separator1.pack(pady=15, padx=30, fill='x')

        # 음량 설정 영역
        volume_frame = tk.Frame(self.root, bg='#f0f0f0')
        volume_frame.pack(pady=10, padx=30, fill='x')

        volume_title = tk.Label(
            volume_frame,
            text="🔊 음량 설정",
            font=("맑은 고딕", 11, "bold"),
            bg='#f0f0f0',
            fg='#333333'
        )
        volume_title.pack(anchor='w', pady=(0, 5))

        # 현재 볼륨 값 가져오기 (0.0~1.0을 1~100으로 변환)
        current_volume = config.get_volume()
        volume_percent = int(current_volume * 100)

        # 음량 슬라이더와 값 표시
        volume_slider_frame = tk.Frame(volume_frame, bg='#f0f0f0')
        volume_slider_frame.pack(fill='x', pady=5)

        self.volume_value_label = tk.Label(
            volume_slider_frame,
            text=f"음량: {volume_percent}%",
            font=("맑은 고딕", 10),
            bg='#f0f0f0',
            fg='#333333',
            width=12,
            anchor='w'
        )
        self.volume_value_label.pack(side=tk.LEFT, padx=(0, 10))

        self.volume_slider = tk.Scale(
            volume_slider_frame,
            from_=1,
            to=100,
            orient=tk.HORIZONTAL,
            bg='#f0f0f0',
            fg='#333333',
            highlightthickness=0,
            length=400,
            command=self.on_volume_change
        )
        self.volume_slider.set(volume_percent)
        self.volume_slider.pack(side=tk.LEFT, fill='x', expand=True)

        # Mute 체크박스
        mute_frame = tk.Frame(volume_frame, bg='#f0f0f0')
        mute_frame.pack(anchor='w', pady=5)

        current_muted = config.get_muted()
        self.mute_var = tk.BooleanVar(value=current_muted)
        self.mute_checkbox = tk.Checkbutton(
            mute_frame,
            text="🔇 음소거",
            variable=self.mute_var,
            font=("맑은 고딕", 10),
            bg='#f0f0f0',
            fg='#333333',
            activebackground='#f0f0f0',
            selectcolor='white'
        )
        self.mute_checkbox.pack(side=tk.LEFT)

        # 구분선
        separator2 = tk.Frame(self.root, bg='#cccccc', height=1)
        separator2.pack(pady=15, padx=30, fill='x')

        # 아이콘 투명도 설정 영역
        opacity_frame = tk.Frame(self.root, bg='#f0f0f0')
        opacity_frame.pack(pady=10, padx=30, fill='x')

        opacity_title = tk.Label(
            opacity_frame,
            text="👁 아이콘 투명도 설정",
            font=("맑은 고딕", 11, "bold"),
            bg='#f0f0f0',
            fg='#333333'
        )
        opacity_title.pack(anchor='w', pady=(0, 5))

        # 현재 투명도 값 가져오기
        current_opacity = config.get_icon_opacity()

        # 투명도 슬라이더와 값 표시
        opacity_slider_frame = tk.Frame(opacity_frame, bg='#f0f0f0')
        opacity_slider_frame.pack(fill='x', pady=5)

        self.opacity_value_label = tk.Label(
            opacity_slider_frame,
            text=f"투명도: {current_opacity}%",
            font=("맑은 고딕", 10),
            bg='#f0f0f0',
            fg='#333333',
            width=12,
            anchor='w'
        )
        self.opacity_value_label.pack(side=tk.LEFT, padx=(0, 10))

        self.opacity_slider = tk.Scale(
            opacity_slider_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            bg='#f0f0f0',
            fg='#333333',
            highlightthickness=0,
            length=400,
            command=self.on_opacity_change
        )
        self.opacity_slider.set(current_opacity)
        self.opacity_slider.pack(side=tk.LEFT, fill='x', expand=True)

        # 설명 텍스트
        opacity_desc = tk.Label(
            opacity_frame,
            text="※ 0%는 약간 투명, 100%는 완전 불투명",
            font=("맑은 고딕", 8),
            bg='#f0f0f0',
            fg='#666666'
        )
        opacity_desc.pack(anchor='w', pady=(0, 5))

        # 버튼 영역
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=20)

        # 저장 버튼 (비디오 변경 + 설정 저장 통합)
        save_settings_btn = tk.Button(
            button_frame,
            text="💾 저장",
            command=self.save_settings,
            width=13,
            font=("맑은 고딕", 11, "bold"),
            bg='#4CAF50',
            fg='white',
            relief='flat',
            cursor='hand2',
            pady=10
        )
        save_settings_btn.pack(side=tk.LEFT, padx=5)

        # 취소 버튼
        cancel_btn = tk.Button(
            button_frame,
            text="✖ 취소",
            command=self.cancel,
            width=13,
            font=("맑은 고딕", 11, "bold"),
            bg='#757575',
            fg='white',
            relief='flat',
            cursor='hand2',
            pady=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # 종료 버튼
        quit_btn = tk.Button(
            button_frame,
            text="🚪 종료",
            command=self.quit_application,
            width=13,
            font=("맑은 고딕", 11, "bold"),
            bg='#f44336',
            fg='white',
            relief='flat',
            cursor='hand2',
            pady=10
        )
        quit_btn.pack(side=tk.LEFT, padx=5)

    def on_volume_change(self, value):
        """볼륨 슬라이더가 변경될 때 실시간으로 적용합니다."""
        volume_percent = int(float(value))
        self.volume_value_label.config(text=f"음량: {volume_percent}%")

        # 실시간 미리보기를 위해 임시로 설정에 저장
        volume_ratio = volume_percent / 100.0
        config.set_volume(volume_ratio)

    def on_opacity_change(self, value):
        """투명도 슬라이더가 변경될 때 실시간으로 적용합니다."""
        opacity_percent = int(float(value))
        self.opacity_value_label.config(text=f"투명도: {opacity_percent}%")

        # 실시간 미리보기를 위해 임시로 설정에 저장
        config.set_icon_opacity(opacity_percent)

    def browse_file(self):
        """비디오 파일을 선택합니다."""
        filetypes = (
            ("동영상 파일", "*.mp4 *.avi *.mkv *.mov *.wmv"),
            ("모든 파일", "*.*")
        )

        filename = filedialog.askopenfilename(
            title="배경화면 동영상 선택",
            filetypes=filetypes
        )

        if filename:
            self.selected_video = filename
            video_name = os.path.basename(filename)
            self.file_label.config(text=video_name)

    def save_settings(self):
        """음량, mute, 투명도, 비디오 설정을 저장합니다."""
        # 슬라이더에서 현재 값 가져오기
        volume_value = self.volume_slider.get()
        opacity_value = self.opacity_slider.get()

        # 0.0~1.0 범위로 변환
        volume_ratio = volume_value / 100.0

        # 설정 저장
        config.set_volume(volume_ratio)
        config.set_muted(self.mute_var.get())
        config.set_icon_opacity(opacity_value)

        self.volume_changed = True
        self.mute_changed = True

        # 비디오가 선택되었으면 비디오 경로도 저장
        if self.selected_video:
            if not os.path.exists(self.selected_video):
                messagebox.showerror("오류", "선택한 파일이 존재하지 않습니다.")
                return

            config.set_video_path(self.selected_video)
            self.result = self.selected_video
            video_name = os.path.basename(self.selected_video)
            messagebox.showinfo("저장 완료", f"설정이 저장되었습니다!\n\n음량: {volume_value}%\n음소거: {'예' if self.mute_var.get() else '아니오'}\n아이콘 투명도: {opacity_value}%\n\n배경화면: {video_name}")
        else:
            messagebox.showinfo("저장 완료", f"설정이 저장되었습니다!\n\n음량: {volume_value}%\n음소거: {'예' if self.mute_var.get() else '아니오'}\n아이콘 투명도: {opacity_value}%")

        self.root.destroy()

    def cancel(self):
        """창을 닫고 원래 설정으로 복원합니다."""
        # 원래 설정값으로 복원
        config.set_volume(self.original_volume)
        config.set_muted(self.original_muted)
        config.set_icon_opacity(self.original_opacity)

        self.root.destroy()

    def quit_application(self):
        """프로그램을 완전히 종료합니다."""
        from tkinter import messagebox

        # 종료 확인
        if messagebox.askyesno("종료 확인", "정말로 Wallpaper Player를 종료하시겠습니까?"):
            self.quit_app = True
            self.root.destroy()

    def update_window(self):
        """창을 업데이트합니다. main.py의 루프에서 호출됩니다."""
        if self.root.winfo_exists():
            try:
                self.root.update()
                return True
            except tk.TclError:
                return False
        return False

    def is_open(self):
        """창이 열려있는지 확인합니다."""
        try:
            return self.root.winfo_exists()
        except:
            return False

    def get_result(self):
        """결과를 반환합니다."""
        return self.result


def show_first_time_setup():
    """첫 시작 시 동영상 선택 창을 표시합니다."""
    root = tk.Tk()
    root.withdraw()  # 메인 창 숨기기

    messagebox.showinfo(
        "Wallpaper Player",
        "배경화면으로 사용할 동영상을 선택해주세요."
    )

    filetypes = (
        ("동영상 파일", "*.mp4 *.avi *.mkv *.mov *.wmv"),
        ("모든 파일", "*.*")
    )

    filename = filedialog.askopenfilename(
        title="배경화면 동영상 선택",
        filetypes=filetypes
    )

    root.destroy()

    if filename and os.path.exists(filename):
        config.set_video_path(filename)
        return filename
    else:
        messagebox.showerror("오류", "동영상 파일을 선택하지 않았습니다.\n프로그램을 종료합니다.")
        return None


def show_settings_window():
    """설정 창을 생성하고 반환합니다 (non-blocking)."""
    window = SettingsWindow()
    return window


if __name__ == "__main__":
    # 테스트
    result = show_settings_window()
    print(f"선택된 파일: {result}")
