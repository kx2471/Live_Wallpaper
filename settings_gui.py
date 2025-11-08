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
        self.root.geometry("600x300")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')

        self.selected_video = None
        self.result = None

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

        # 버튼 영역
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=20)

        save_btn = tk.Button(
            button_frame,
            text="🔄 동영상 변경",
            command=self.change_video,
            width=18,
            font=("맑은 고딕", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            relief='flat',
            cursor='hand2',
            pady=10
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            button_frame,
            text="✖ 취소",
            command=self.cancel,
            width=18,
            font=("맑은 고딕", 11, "bold"),
            bg='#757575',
            fg='white',
            relief='flat',
            cursor='hand2',
            pady=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

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

    def change_video(self):
        """동영상을 변경합니다."""
        if not self.selected_video:
            messagebox.showwarning("동영상 선택 필요", "새로운 동영상 파일을 먼저 선택해주세요.\n\n'📁 찾아보기' 버튼을 눌러 동영상을 선택하세요.")
            return

        if not os.path.exists(self.selected_video):
            messagebox.showerror("오류", "선택한 파일이 존재하지 않습니다.")
            return

        # 설정 저장
        if config.set_video_path(self.selected_video):
            self.result = self.selected_video
            video_name = os.path.basename(self.selected_video)
            messagebox.showinfo("변경 완료", f"동영상이 변경되었습니다!\n\n📹 {video_name}\n\n새로운 동영상이 곧 재생됩니다.")
            self.root.destroy()
        else:
            messagebox.showerror("오류", "설정 저장에 실패했습니다.")

    def cancel(self):
        """창을 닫습니다."""
        self.root.destroy()

    def show(self):
        """창을 표시하고 결과를 반환합니다."""
        self.root.mainloop()
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
    """설정 창을 표시합니다."""
    window = SettingsWindow()
    return window.show()


if __name__ == "__main__":
    # 테스트
    result = show_settings_window()
    print(f"선택된 파일: {result}")
