"""
성능 모니터링 모듈
- CPU 사용률 기반 동적 FPS 조절
- 프레임 드롭 감지
- 성능 메트릭 수집
"""
import psutil
import os
import time
from logger import get_logger

logger = get_logger("PerformanceMonitor")


class PerformanceMonitor:
    """
    성능 모니터링 및 동적 FPS 조절 클래스

    개선사항:
    - 스무스한 FPS 조절 (급격한 변화 방지)
    - CPU 사용률 이동 평균 적용
    - 프레임 드롭 카운터
    """

    def __init__(self, target_fps=30, min_fps=15, max_fps=60):
        """
        Args:
            target_fps: 초기 목표 FPS
            min_fps: 최소 FPS (이하로 내려가지 않음)
            max_fps: 최대 FPS (이상으로 올라가지 않음)
        """
        self.target_fps = target_fps
        self.original_target_fps = target_fps
        self.min_fps = min_fps
        self.max_fps = max_fps

        # CPU 모니터링
        self.cpu_check_interval = 2.0  # 2초마다 체크
        self.last_cpu_check_time = time.time()
        self.cpu_history = []  # CPU 사용률 이력 (이동 평균용)
        self.cpu_history_size = 5

        # 성능 메트릭
        self.frame_drop_count = 0
        self.total_frames = 0
        self.last_fps_change_time = time.time()
        self.fps_change_cooldown = 3.0  # FPS 변경 후 3초 대기

        # 동적 FPS 활성화 여부
        self.dynamic_fps_enabled = True

        # 프로세스 CPU 모니터링 (전체 시스템 CPU가 아닌 우리 프로세스만)
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent(interval=None)  # 첫 호출 초기화

        logger.info(f"PerformanceMonitor initialized: target={target_fps}, range=[{min_fps}, {max_fps}]")

    def get_cpu_usage(self):
        """
        CPU 사용률 이동 평균 계산 (우리 프로세스만)

        Returns:
            float: CPU 사용률 (0-100)
        """
        # 우리 프로세스의 CPU만 측정 (Non-blocking)
        cpu = self.process.cpu_percent(interval=None)
        self.cpu_history.append(cpu)

        # 이동 평균 유지
        if len(self.cpu_history) > self.cpu_history_size:
            self.cpu_history.pop(0)

        return sum(self.cpu_history) / len(self.cpu_history)

    def should_adjust_fps(self):
        """
        FPS 조절이 필요한지 확인

        Returns:
            bool: FPS 조절 필요 여부
        """
        if not self.dynamic_fps_enabled:
            return False

        current_time = time.time()

        # CPU 체크 간격 확인
        if current_time - self.last_cpu_check_time < self.cpu_check_interval:
            return False

        # FPS 변경 쿨다운 확인
        if current_time - self.last_fps_change_time < self.fps_change_cooldown:
            return False

        self.last_cpu_check_time = current_time
        return True

    def adjust_fps(self):
        """
        CPU 사용률 기반 동적 FPS 조절

        Returns:
            tuple: (new_fps, changed) - 새로운 FPS와 변경 여부
        """
        if not self.should_adjust_fps():
            return self.target_fps, False

        cpu_avg = self.get_cpu_usage()
        old_fps = self.target_fps
        new_fps = old_fps

        # CPU 부하가 높으면 FPS 낮춤
        if cpu_avg > 80:
            new_fps = max(self.min_fps, old_fps - 5)
            if new_fps != old_fps:
                logger.warning(f"High CPU usage ({cpu_avg:.1f}%) - Lowering FPS: {old_fps} -> {new_fps}")

        # CPU 여유 있으면 원래 FPS로 복구
        elif cpu_avg < 30 and old_fps < self.original_target_fps:
            new_fps = min(self.original_target_fps, old_fps + 5)
            if new_fps != old_fps:
                logger.info(f"CPU usage normalized ({cpu_avg:.1f}%) - Restoring FPS: {old_fps} -> {new_fps}")

        # FPS 변경 시
        if new_fps != old_fps:
            self.target_fps = new_fps
            self.last_fps_change_time = time.time()
            return new_fps, True

        return old_fps, False

    def record_frame(self, dropped=False):
        """
        프레임 통계 기록

        Args:
            dropped: 프레임 드롭 여부
        """
        self.total_frames += 1
        if dropped:
            self.frame_drop_count += 1

    def get_stats(self):
        """
        성능 통계 반환

        Returns:
            dict: 성능 메트릭
        """
        drop_rate = (self.frame_drop_count / self.total_frames * 100) if self.total_frames > 0 else 0
        return {
            'target_fps': self.target_fps,
            'total_frames': self.total_frames,
            'dropped_frames': self.frame_drop_count,
            'drop_rate': drop_rate,
            'cpu_avg': sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
        }

    def set_target_fps(self, fps):
        """
        목표 FPS 설정

        Args:
            fps: 새로운 목표 FPS
        """
        fps = max(self.min_fps, min(self.max_fps, fps))
        self.target_fps = fps
        self.original_target_fps = fps
        logger.info(f"Target FPS set to: {fps}")

    def enable_dynamic_fps(self, enabled=True):
        """
        동적 FPS 조절 활성화/비활성화

        Args:
            enabled: 활성화 여부
        """
        self.dynamic_fps_enabled = enabled
        logger.info(f"Dynamic FPS adjustment: {'enabled' if enabled else 'disabled'}")
