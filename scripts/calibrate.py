#!/usr/bin/env python3

import cv2
import json
import sys
import numpy as np

class CalibratorTool:
    def __init__(self):
        self.points = []
        self.image = None
        self.window_name = "Calibration Tool - انقر 4 نقاط"

    def click_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append([x, y])
            cv2.circle(self.image, (x, y), 8, (0, 255, 0), -1)
            cv2.circle(self.image, (x, y), 10, (255, 255, 255), 2)

            cv2.putText(self.image, str(len(self.points)),
                       (x + 15, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            if len(self.points) >= 2:
                pts = np.array(self.points, np.int32)
                cv2.polylines(self.image, [pts], False, (255, 255, 0), 2)

            if len(self.points) == 4:
                pts = np.array(self.points + [self.points[0]], np.int32)
                cv2.polylines(self.image, [pts], True, (255, 0, 255), 2)
                cv2.putText(self.image, "اضغط ENTER للحفظ أو ESC للإلغاء",
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
                           1.0, (0, 255, 255), 2)

            cv2.imshow(self.window_name, self.image)

    def calibrate(self, video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"خطأ: لا يمكن فتح الفيديو {video_path}")
            return None

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("خطأ: لا يمكن قراءة الإطار من الفيديو")
            return None

        self.image = frame.copy()
        original = frame.copy()

        cv2.imshow(self.window_name, self.image)
        cv2.setMouseCallback(self.window_name, self.click_event)

        print("\n" + "="*60)
        print("  🎯 أداة المعايرة - تعليمات")
        print("="*60)
        print("  1. انقر على 4 نقاط بالترتيب التالي:")
        print("     النقطة 1: أسفل-يسار الشارع")
        print("     النقطة 2: أسفل-يمين الشارع")
        print("     النقطة 3: أعلى-يسار الشارع")
        print("     النقطة 4: أعلى-يمين الشارع")
        print("  2. اضغط ENTER لحفظ النقاط")
        print("  3. اضغط ESC أو 'r' لإعادة التعيين")
        print("  4. اضغط 'q' للخروج بدون حفظ")
        print("="*60 + "\n")

        while True:
            key = cv2.waitKey(0) & 0xFF

            if key == 13:
                if len(self.points) == 4:
                    print("\n✅ تم حفظ 4 نقاط بنجاح!")
                    print(f"   النقاط: {self.points}")
                    cv2.destroyAllWindows()
                    return self.points
                else:
                    print(f"\n⚠️  تحتاج 4 نقاط بالضبط. حالياً: {len(self.points)}")

            elif key == 27 or key == ord('q'):
                print("\n❌ تم الإلغاء")
                cv2.destroyAllWindows()
                return None

            elif key == ord('r'):
                self.points = []
                self.image = original.copy()
                cv2.imshow(self.window_name, self.image)
                print("\n🔄 تم إعادة التعيين")


def main():
    video_path = sys.argv[1] if len(sys.argv) > 1 else "your_traffic_video.mp4"

    tool = CalibratorTool()
    src_points = tool.calibrate(video_path)

    if src_points is None:
        print("لم يتم حفظ أي نقاط.")
        return

    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    if 'calibration' not in config:
        config['calibration'] = {}

    config['calibration']['src_points'] = src_points

    if 'dst_meters' not in config['calibration']:
        config['calibration']['dst_meters'] = [
            [0, 20],
            [10, 20],
            [0, 0],
            [10, 0]
        ]

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print("  ✅ تم تحديث config.json بنجاح!")
    print("="*60)
    print(f"  src_points: {src_points}")
    print(f"  dst_meters: {config['calibration']['dst_meters']}")
    print("\n  ⚠️  تذكر تعديل dst_meters في config.json")
    print("     لتعكس الأبعاد الحقيقية لشارعك بالأمتار")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
