"""
비디오 캡처 모듈
- ThreadedVideoCapture: 멀티스레드 비디오 디코딩
- 프레임 스킵을 읽기 단계에서 수행하여 CPU 절감
- Idle 모드 지원
- Context Manager 패턴으로 안전한 리소스 관리
"""
import cv2
import threading
import time
from queue import Queue, Empty
from logger import get_logger

logger = get_logger("VideoCapture")


class ThreadedVideoCapture:
    """
    멀티스레드 비디오 캡처 클래스 (개선 버전)

    주요 개선사항:
    1. cap.grab()으로 불필요한 프레임 디코딩 스킵
    2. Context Manager 패턴 지원 (__enter__, __exit__)
    3. 예외 처리 강화 (절전 모드 복귀 등)
    4. Idle 모드 지원
    5. 프레임 재사용으로 메모리 효율 개선
    """

    def __init__(self, video_path, queue_size=60, target_fps=None, video_fps=None):
        """
        Args:
            video_path: 비디오 파일 경로
            queue_size: 프레임 버퍼 크기 (기본 60 = 24fps 기준 2.5초 분량)
            target_fps: 목표 FPS (None이면 원본 FPS)
            video_fps: 원본 비디오 FPS
        """
        self.video_path = video_path
        self.queue_size = queue_size
        self.target_fps = target_fps
        self.video_fps = video_fps

        # VideoCapture 초기화
        try:
            self.cap = cv2.VideoCapture(video_path, cv2.CAP_MSMF)  # Windows Media Foundation
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open video: {video_path}")
        except Exception as e:
            logger.error(f"VideoCapture initialization failed: {e}")
            raise

        # 프레임 큐
        self.queue = Queue(maxsize=queue_size)

        # 스레드 제어 플래그
        self.stopped = False
        self.paused = False
        self.reader_thread = None

        # 프레임 카운터
        self.frame_count = 0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 프레임 스킵 비율 계산
        self._update_skip_ratio()

        # 에러 복구
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10

        # grab() 실패 추적 (무한 루프 방지)
        self.consecutive_grab_fails = 0
        self.max_grab_fails = 50  # 50번 연속 실패 시 경고

        logger.info(
            f"ThreadedVideoCapture initialized: {video_path}, "
            f"video_fps={video_fps}, target_fps={target_fps}, skip_ratio={self.skip_ratio}"
        )

    def _update_skip_ratio(self):
        """프레임 스킵 비율 재계산"""
        if self.target_fps and self.video_fps and self.target_fps < self.video_fps:
            self.skip_ratio = int(self.video_fps / self.target_fps)
        else:
            self.skip_ratio = 1
        logger.debug(f"Skip ratio updated: {self.skip_ratio}")

    def start(self):
        """백그라운드 스레드 시작"""
        if self.reader_thread and self.reader_thread.is_alive():
            logger.warning("Reader thread is already running")
            return self

        self.stopped = False
        self.reader_thread = threading.Thread(target=self._reader, daemon=True, name="VideoReader")
        self.reader_thread.start()
        logger.info("Reader thread started")
        return self

    def _reader(self):
        """
        백그라운드 프레임 디코딩 스레드

        개선사항:
        - cap.grab()으로 불필요한 프레임 스킵
        - 예외 처리로 절전 모드 복귀 등 대응
        - 루프 재시작 시 프레임 카운터 리셋
        """
        loop_count = 0
        last_log_time = time.time()

        while not self.stopped:
            try:
                loop_count += 1

                # 10초마다 상태 로깅 (디버깅용)
                if time.time() - last_log_time > 10:
                    logger.info(f"Reader thread alive: loops={loop_count}, queue={self.queue.qsize()}/{self.queue_size}, paused={self.paused}")
                    last_log_time = time.time()
                    loop_count = 0

                # Idle 모드 처리
                if self.paused:
                    time.sleep(0.1)
                    continue

                # 큐가 가득 차면 대기
                if self.queue.full():
                    time.sleep(0.01)  # 0.001 -> 0.01 (10ms)
                    continue

                self.frame_count += 1

                # 프레임 스킵 처리 (읽기 단계에서 스킵)
                if self.skip_ratio > 1 and self.frame_count % self.skip_ratio != 0:
                    # grab()은 프레임을 디코딩하지 않고 위치만 이동
                    logger.debug(f"Calling cap.grab() (skip frame {self.frame_count})")
                    ret = self.cap.grab()
                    logger.debug(f"cap.grab() returned: {ret}")
                    if not ret:
                        self.consecutive_grab_fails += 1

                        # grab() 실패 추적 (무한 루프 감지)
                        if self.consecutive_grab_fails >= self.max_grab_fails:
                            logger.warning(f"cap.grab() failed {self.consecutive_grab_fails} times consecutively - forcing restart")
                            self._restart_video()
                            self.consecutive_grab_fails = 0
                        else:
                            # 비디오 끝 - 루프 재시작
                            logger.info(f"[GRAB_FAIL] cap.grab() failed (consecutive: {self.consecutive_grab_fails}), restarting video")
                            self._restart_video()
                    else:
                        # grab() 성공 시 카운터 리셋
                        self.consecutive_grab_fails = 0
                    continue

                # 필요한 프레임만 실제로 디코딩
                logger.info(f"[TRACE] Calling cap.read() (frame {self.frame_count})")
                ret, frame = self.cap.read()
                logger.info(f"[TRACE] cap.read() returned: ret={ret}, frame={'valid' if frame is not None else 'None'}")

                if not ret or frame is None:
                    # 비디오 끝 - 루프 재시작
                    logger.debug("Restarting video (EOF or read failed)")
                    self._restart_video()
                    self.consecutive_errors = 0
                    self.consecutive_grab_fails = 0  # read 실패 시에도 grab_fail 리셋
                    continue

                # read() 성공 - 모든 카운터 리셋
                self.consecutive_errors = 0
                self.consecutive_grab_fails = 0

                # 프레임을 큐에 추가
                try:
                    logger.debug(f"Putting frame to queue (size: {self.queue.qsize()}/{self.queue_size})")
                    self.queue.put((True, frame), timeout=0.1)
                    logger.debug("Frame added to queue successfully")
                except:
                    # Queue put timeout - 프레임 드롭
                    logger.warning(f"Queue put timeout (size: {self.queue.qsize()}/{self.queue_size})")

            except Exception as e:
                self.consecutive_errors += 1
                logger.error(f"Error in reader thread: {e} (consecutive: {self.consecutive_errors})")

                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.critical("Too many consecutive errors, stopping reader thread")
                    self.stopped = True
                    break

                time.sleep(0.1)  # 에러 발생 시 잠시 대기 후 재시도

        logger.info("Reader thread stopped")

    def _restart_video(self):
        """비디오 루프 재시작"""
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0
            logger.debug("Video looped")
        except Exception as e:
            logger.error(f"Failed to restart video: {e}")

    def read(self, timeout=1.0):
        """
        큐에서 프레임 가져오기

        Args:
            timeout: 타임아웃 (초)

        Returns:
            tuple: (ret, frame) - ret은 성공 여부, frame은 프레임 데이터
        """
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            logger.warning("Frame queue empty")
            return False, None

    def get(self, prop):
        """VideoCapture 속성 가져오기"""
        try:
            return self.cap.get(prop)
        except Exception as e:
            logger.error(f"Failed to get property {prop}: {e}")
            return 0

    def set(self, prop, value):
        """VideoCapture 속성 설정"""
        try:
            return self.cap.set(prop, value)
        except Exception as e:
            logger.error(f"Failed to set property {prop} to {value}: {e}")
            return False

    def update_fps(self, target_fps):
        """
        목표 FPS 업데이트

        Args:
            target_fps: 새로운 목표 FPS
        """
        self.target_fps = target_fps
        self._update_skip_ratio()
        logger.info(f"Target FPS updated to {target_fps}, new skip_ratio={self.skip_ratio}")

    def pause(self):
        """Idle 모드 - 프레임 디코딩 일시정지"""
        if not self.paused:
            self.paused = True
            logger.info("Video capture paused (idle mode)")

    def resume(self):
        """Idle 모드 해제 - 프레임 디코딩 재개"""
        if self.paused:
            self.paused = False
            logger.info("Video capture resumed")

            # Queue를 즉시 리필 (Idle 복귀 시 빈 queue로 인한 CPU 스파이크 방지)
            # Reader 스레드가 깨어나서 queue를 채울 때까지 대기
            refill_timeout = 1.0  # 최대 1초 대기
            refill_start = time.time()
            while self.queue.qsize() < self.queue_size // 2 and time.time() - refill_start < refill_timeout:
                time.sleep(0.05)

            logger.info(f"Queue refilled: {self.queue.qsize()}/{self.queue_size} frames")

    def isOpened(self):
        """비디오가 열려있는지 확인"""
        try:
            return self.cap is not None and self.cap.isOpened()
        except:
            return False

    def release(self):
        """리소스 정리"""
        logger.info("Releasing video capture resources")

        # 스레드 정지
        self.stopped = True

        # 스레드가 종료될 때까지 대기 (최대 2초)
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)

        # VideoCapture 해제
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                logger.error(f"Error releasing VideoCapture: {e}")

        # 큐 비우기
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Empty:
                break

        logger.info("Video capture resources released")

    # Context Manager 패턴 지원
    def __enter__(self):
        """Context Manager 진입"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        self.release()
        return False  # 예외를 전파함
