import cv2
import numpy as np
from src.calibration.bev_transformer import BEVTransformer


class CameraCalibrator:
    def __init__(self):
        self.src_points = []
        self.dst_meters = []
        self.current_image = None
        self.window_name = "Calibration - Click 4 points"

    def click_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(self.src_points) < 4:
            self.src_points.append((x, y))
            cv2.circle(self.current_image, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(self.current_image, str(len(self.src_points)),
                        (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(self.window_name, self.current_image)

    def calibrate_from_image(self, image: np.ndarray) -> BEVTransformer | None:
        self.current_image = image.copy()
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.click_event)
        cv2.imshow(self.window_name, self.current_image)
        print("Click 4 source points in order: top-left, top-right, bottom-left, bottom-right")
        print("Then set destination meters or press 'q' to cancel.")

        while len(self.src_points) < 4:
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                cv2.destroyWindow(self.window_name)
                return None

        cv2.destroyWindow(self.window_name)
        print("Enter destination points in meters (format: x y):")
        for i in range(4):
            inp = input(f"  Point {i + 1} (x y): ").strip().split()
            if len(inp) >= 2:
                self.dst_meters.append([float(inp[0]), float(inp[1])])
            else:
                self.dst_meters.append([i * 5, 0])

        return BEVTransformer(self.src_points, self.dst_meters)

    def auto_calibrate(self, width: int, height: int) -> BEVTransformer:
        self.src_points = [
            [width * 0.1, height * 0.9],
            [width * 0.9, height * 0.9],
            [width * 0.3, height * 0.5],
            [width * 0.7, height * 0.5],
        ]
        self.dst_meters = [[0, 30], [15, 30], [0, 0], [15, 0]]
        return BEVTransformer(self.src_points, self.dst_meters)
