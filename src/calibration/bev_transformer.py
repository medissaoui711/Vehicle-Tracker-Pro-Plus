import numpy as np
import cv2
from typing import List, Tuple, Optional

class BEVTransformer:

    def __init__(self, src_points: List[List[int]], dst_meters: List[List[float]]):
        if len(src_points) != 4 or len(dst_meters) != 4:
            raise ValueError("يجب توفير 4 نقاط لكل من المصدر والوجهة")

        src = np.array(src_points, dtype=np.float32)
        dst = np.array(dst_meters, dtype=np.float32)

        self.M = cv2.getPerspectiveTransform(src, dst)

        self.inv_M = cv2.getPerspectiveTransform(dst, src)

        self.src_points = src
        self.dst_meters = dst

    def image_to_world(self, x: float, y: float) -> Tuple[float, float]:
        pts = np.array([[[float(x), float(y)]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pts, self.M)
        return float(transformed[0][0][0]), float(transformed[0][0][1])

    def world_to_image(self, x_m: float, y_m: float) -> Tuple[int, int]:
        pts = np.array([[[float(x_m), float(y_m)]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pts, self.inv_M)
        return int(transformed[0][0][0]), int(transformed[0][0][1])

    def get_homography(self) -> np.ndarray:
        return self.M

    def get_inverse_homography(self) -> np.ndarray:
        return self.inv_M

    def get_transformation_matrix(self) -> np.ndarray:
        return self.M

    def get_inverse_matrix(self) -> np.ndarray:
        return self.inv_M

    def is_point_in_roi(self, x: float, y: float, margin: float = 0.1) -> bool:
        world_x, world_y = self.image_to_world(x, y)

        min_x = np.min(self.dst_meters[:, 0])
        max_x = np.max(self.dst_meters[:, 0])
        min_y = np.min(self.dst_meters[:, 1])
        max_y = np.max(self.dst_meters[:, 1])

        margin_x = (max_x - min_x) * margin
        margin_y = (max_y - min_y) * margin

        return (min_x - margin_x <= world_x <= max_x + margin_x and
                min_y - margin_y <= world_y <= max_y + margin_y)
