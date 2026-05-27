import cv2
import numpy as np


class Camera:
    def __init__(self, source, fps: float = 30.0, width: int = 1280, height: int = 720):
        self.source = source
        self.fps = fps
        self.width = width
        self.height = height
        self.cap = None

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            return False
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or self.fps
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        return True

    def read_frame(self) -> np.ndarray | None:
        if self.cap is None:
            return None
        ret, frame = self.cap.read()
        return frame if ret else None

    def release(self):
        if self.cap:
            self.cap.release()

    @property
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
