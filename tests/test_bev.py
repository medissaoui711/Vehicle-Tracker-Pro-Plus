import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from src.calibration.bev_transformer import BEVTransformer


def test_bev_forward_inverse():
    src = [[100, 600], [900, 600], [300, 200], [700, 200]]
    dst = [[0, 30], [15, 30], [0, 0], [15, 0]]
    bev = BEVTransformer(src, dst)

    test_img_points = [(500, 400), (300, 200), (900, 600)]
    for img_x, img_y in test_img_points:
        wx, wy = bev.image_to_world(img_x, img_y)
        ix, iy = bev.world_to_image(wx, wy)
        assert abs(ix - img_x) < 5, f"X mismatch: {ix} vs {img_x}"
        assert abs(iy - img_y) < 5, f"Y mismatch: {iy} vs {img_y}"

    print("test_bev_forward_inverse PASSED")


def test_bev_homography_shape():
    src = [[100, 600], [900, 600], [300, 200], [700, 200]]
    dst = [[0, 30], [15, 30], [0, 0], [15, 0]]
    bev = BEVTransformer(src, dst)

    M = bev.get_homography()
    assert M.shape == (3, 3), f"Expected (3,3), got {M.shape}"
    inv = bev.get_inverse_homography()
    assert inv.shape == (3, 3), f"Expected (3,3), got {inv.shape}"
    print("test_bev_homography_shape PASSED")


if __name__ == "__main__":
    test_bev_forward_inverse()
    test_bev_homography_shape()
    print("All tests passed!")
