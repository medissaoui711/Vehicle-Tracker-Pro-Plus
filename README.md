# 🚗 Vehicle Tracker Pro++

### نظام تتبع مروري احترافي متعدد الطبقات

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Ultralytics](https://img.shields.io/badge/Ultralytics-YOLOv8-purple.svg)](https://ultralytics.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)](https://opencv.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightblue.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📸 نظرة عامة

### 🎬 فيديو توضيحي للتشغيل

[![Vehicle Tracker Pro++ Demo](https://img.shields.io/badge/%F0%9F%8E%AC-%D9%85%D8%B4%D8%A7%D9%87%D8%AF%D8%A9_%D9%81%D9%8A%D8%AF%D9%8A%D9%88_%D8%A7%D9%84%D8%A7%D8%AE%D8%AA%D8%A8%D8%A7%D8%B1-red?style=for-the-badge)](https://youtu.be/output_result.mp4)

نظام متكامل لتتبع المركبات وتحليل الحركة المرورية باستخدام الذكاء الاصطناعي. يحول إحداثيات الكاميرا إلى قياسات حقيقية بالأمتار، ويوفر تحليلات مرورية متقدمة تشمل:

- 🏎️ **قياس السرعة بالأمتار الحقيقية** عبر تحويل منظور (BEV)
- 🚦 **بوابات افتراضية** لقياس سرعة العبور (Trap Speed)
- ⚠️ **كشف المخالفات**: تجاوز السرعة، السير العكسي، التلاحق، التوقف الطارئ
- 📊 **تحليل الكثافة المرورية** ومستوى الخدمة (LoS) وفق معايير HCM
- 💾 **تخزين في قاعدة بيانات SQLite** مع دعم الكتابة غير المتزامنة
- 🎨 **لوحة معلومات مباشرة** على الفيديو

---

## 🏗️ الهيكل المعماري

```text
Vehicle-Tracker-Pro-Plus/
│
├── 📄 config.json                  # ملف الإعدادات الرئيسي
├── 📄 requirements.txt             # المكتبات المطلوبة
│
├── 📂 config/                      # ملفات إعدادات إضافية
│   ├── gates.json                 # تعريف البوابات الافتراضية
│   └── lanes.json                 # تعريف الحارات المرورية
│
├── 📂 src/                         # الكود المصدري
│   ├── 🧠 core/                   # الطبقة الأساسية (YOLO + إدارة المركبات)
│   ├── 📐 calibration/            # تحويل المنظور (BEV)
│   ├── 🚦 gates/                  # البوابات الافتراضية
│   ├── ⚠️  events/                # كاشفات الأحداث (Observer Pattern)
│   ├── 📊 analysis/               # تحليل الحارات والكثافة
│   ├── 💾 storage/                # SQLite + CSV (Async Writer)
│   ├── 🎨 visualization/          # الرسم ولوحة المعلومات
│   └── ⚙️  main.py                # نقطة الدمج النهائية
│
├── 📂 scripts/                     # أدوات مساعدة
│   └── calibrate.py               # أداة المعايرة التفاعلية
│
└── 📂 data/                        # مخرجات
    ├── traffic.db                  # قاعدة البيانات
    ├── reports/                    # تقارير CSV
    └── snapshots/                  # لقطات الأحداث
```

---

## ✨ المميزات الرئيسية

### 🎯 التتبع والقياس

| الميزة | الوصف |
|--------|-------|
| تحويل BEV | تحويل إحداثيات الصورة إلى أمتار حقيقية باستخدام Homography Matrix |
| تتبع متقدم | YOLOv8 + ByteTrack مع إدارة فقدان التتبع (Occlusion) |
| سرعة دقيقة | حساب السرعة بالأمتار/الثانية مع نافذة تجانس (Smoothing Window) |
| اتجاه المركبة | تحديد اتجاه الحركة (مقترب/مبتعد/متوقف) |

### 🚦 البوابات الافتراضية

| الميزة | الوصف |
|--------|-------|
| خطوط عبور | تعريف بوابات في الإحداثيات الحقيقية |
| Trap Speed | حساب السرعة بين أي بوابتين |
| اتجاه العبور | فلترة حسب اتجاه الحركة المسموح |

### ⚠️ كشف الأحداث (Observer Pattern)

| الكاشف | الوصف |
|--------|-------|
| تجاوز السرعة | مع عتبة تسامح ونافذة استقرار |
| السير العكسي | مقارنة اتجاه المركبة بالاتجاه المسموح للحارة |
| التلاحق | حساب المسافة والزمن بين المركبات (قاعدة الثانيتين) |
| التوقف الطارئ | كشف المركبات المتوقفة في حارة المرور |

### 📊 التحليل المروري

| الميزة | الوصف |
|--------|-------|
| تصنيف الحارات | مع نافذة استقرار لمنع التذبذب |
| كثافة مرورية | مركبة/كم/حارة لكل مقطع |
| مستوى الخدمة | LoS (A-F) وفق معايير HCM |
| إحصائيات | تقارير دورية وإحصائيات تراكمية |

### 💾 التخزين

| الميزة | الوصف |
|--------|-------|
| SQLite | 6 جداول (sessions, vehicles, events, density, statistics) |
| Async Writer | طابور + خيط منفصل لمنع حظر المعالجة |
| Batching | تجميع السجلات وكتابتها دفعة واحدة |
| CSV Export | تصدير تلقائي للتقارير اليومية |
| لقطات الأحداث | حفظ صور تلقائية للمخالفات الحرجة |

---

## 🚀 التثبيت والتشغيل

### المتطلبات الأساسية

- Python 3.8+
- pip (مدير حزم Python)

### التثبيت

```bash
# استنساخ المستودع
git clone https://github.com/medissaoui711/Vehicle-Tracker-Pro-Plus.git
cd Vehicle-Tracker-Pro-Plus

# إنشاء بيئة افتراضية (موصى به)
python -m venv venv

# تفعيل البيئة الافتراضية
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# تثبيت المكتبات
pip install -r requirements.txt
```

### التشغيل السريع

```bash
# تشغيل مع فيديو
python src/main.py

# تشغيل بدون عرض مرئي (للاستخدام على الخوادم)
python src/main.py --headless

# حفظ الفيديو الناتج في مسار مخصص
python src/main.py --output results.mp4

# استخدام ملف إعدادات مخصص
python src/main.py --config my_config.json
```

---

## 🎯 المعايرة

لضبط النظام على شارعك، استخدم أداة المعايرة التفاعلية:

```bash
python scripts/calibrate.py your_video.mp4
```

### تعليمات

1. انقر على 4 نقاط على الشارع بالترتيب:
   - **النقطة 1**: أسفل-يسار الشارع (قريب من الكاميرا)
   - **النقطة 2**: أسفل-يمين الشارع (قريب من الكاميرا)
   - **النقطة 3**: أعلى-يسار الشارع (بعيد عن الكاميرا)
   - **النقطة 4**: أعلى-يمين الشارع (بعيد عن الكاميرا)
2. اضغط **ENTER** للحفظ
3. سيتم تحديث `config.json` تلقائياً

---

## ⚙️ الإعدادات

### ملف config.json الرئيسي

```json
{
    "source": "video.mp4",
    "output_video": null,
    "model_path": "yolov8n.pt",
    "confidence": 0.3,
    "iou": 0.45,

    "calibration": {
        "src_points": [[...]],
        "dst_meters": [[...]]
    },

    "events": {
        "speed": { "enabled": true, "limit_kmh": 60 },
        "wrong_way": { "enabled": true },
        "tailgating": { "enabled": true, "time_gap_s": 2.0 },
        "stopped_vehicle": { "enabled": true, "timeout_s": 10.0 }
    },

    "storage": {
        "database_path": "data/traffic.db",
        "async_writer": { "enabled": true }
    },

    "visualization": {
        "show_display": true,
        "show_dashboard": true,
        "show_gates": true
    }
}
```

---

## 📊 نموذج قاعدة البيانات (Schema)

### جدول sessions

| العمود | النوع | الوصف |
|--------|------|-------|
| id | INTEGER | معرف الجلسة |
| start_time | TEXT | وقت البداية |
| end_time | TEXT | وقت النهاية |
| total_vehicles | INTEGER | إجمالي المركبات |
| total_events | INTEGER | إجمالي الأحداث |

### جدول vehicles

| العمود | النوع | الوصف |
|--------|------|-------|
| track_id | INTEGER | معرف التتبع |
| class_name | TEXT | نوع المركبة |
| speed_kmh | REAL | السرعة كم/س |
| direction | TEXT | الاتجاه |
| lane_id | INTEGER | رقم الحارة |

### جدول events

| العمود | النوع | الوصف |
|--------|------|-------|
| event_type | TEXT | نوع الحدث |
| severity | TEXT | مستوى الخطورة |
| details_json | TEXT | تفاصيل JSON |

### جدول density

| العمود | النوع | الوصف |
|--------|------|-------|
| lane_id | INTEGER | رقم الحارة |
| segment_id | INTEGER | رقم المقطع |
| density_vpkpl | REAL | الكثافة (مركبة/كم/حارة) |
| los_level | TEXT | مستوى الخدمة (A-F) |

---

## ⌨️ مفاتيح التحكم أثناء التشغيل

| المفتاح | الوظيفة |
|---------|----------|
| `q` | إيقاف المعالجة والخروج |
| `ESC` | إيقاف المعالجة والخروج |

---

## 📈 نتائج اختبار حقيقي

| المؤشر | القيمة |
|--------|--------|
| 📹 الدقة | 1280×720 |
| ⏱️ معدل الإطارات | 24 FPS |
| 🚗 مركبات مكتشفة | 10 مركبات فريدة |
| 🚦 عبورات البوابة | 9 عبورات |
| 🏎️ أقصى سرعة | 20.1 km/h |
| 📈 متوسط FPS معالجة | 13.0 |
| 💾 حالة التخزين | ✅ ناجح |

---

## 🎨 لقطات من النظام

![لوحة المعلومات](screenshots/dashboard.png)

*لوحة المعلومات المباشرة على الفيديو مع مستويات الخدمة (LoS)*

![كشف الأحداث](screenshots/events.png)

*كشف السير العكسي وتجاوز السرعة مع تنبيهات فورية*

![البوابات الافتراضية](screenshots/gates.png)

*البوابات الافتراضية لقياس Trap Speed بين نقطتين*

---

## 🗺️ خريطة الطريق (Roadmap)

- [x] تحويل BEV للمنظور
- [x] YOLOv8 + ByteTrack
- [x] بوابات افتراضية + Trap Speed
- [x] كاشفات الأحداث (Observer Pattern)
- [x] تحليل الحارات والكثافة
- [x] قاعدة بيانات SQLite + Async Writer
- [x] لوحة معلومات مباشرة
- [x] أداة معايرة تفاعلية
- [ ] دعم الكاميرات المتعددة (Multi-Camera)
- [ ] لوحة تحكم ويب (Flask/FastAPI)
- [ ] كشف الحوادث (Accident Detection)
- [ ] تصدير تقارير PDF

---

## 🤝 المساهمة

مرحب بمساهماتكم! يرجى:

1. عمل Fork للمستودع
2. إنشاء فرع للميزة (`git checkout -b feature/AmazingFeature`)
3. عمل Commit للتغييرات (`git commit -m 'Add AmazingFeature'`)
4. رفع الفرع (`git push origin feature/AmazingFeature`)
5. فتح Pull Request

---

## 📄 الترخيص

هذا المشروع مرخص تحت MIT License - انظر ملف [LICENSE](LICENSE) للتفاصيل.

---

## 👨‍💻 المؤلف

**Eng. Mohamed Alissawi** - [GitHub](https://github.com/medissaoui711)

---

## 📧 الاتصال

- GitHub: [@medissaoui711](https://github.com/medissaoui711)
- البريد الإلكتروني: <contacteinfo71@gmail.com>

---

### ⭐ إذا أعجبك المشروع، لا تنسَ إضافة نجمة على GitHub! ⭐

---

## 📝 ملخص المحادثة (Conversation Summary)

### مراحل بناء المشروع

1. **النواة والمعايرة**: Vehicle, YOLOTracker, VehicleManager, BEVTransformer
2. **البوابات الافتراضية**: VirtualGate, GateManager, Trap Speed
3. **الأحداث (Observer)**: SpeedViolation, WrongWay, Tailgating, StoppedVehicle
4. **التحليل المروري**: LaneAssigner (مع نافذة استقرار), DensityAnalyzer (LoS), StatisticsCollector
5. **التخزين**: DatabaseManager, AsyncDatabaseWriter (Queue + Thread), CSVWriter, SnapshotCapture
6. **التصور**: Renderer, Dashboard (LoS, FPS, أحداث)
7. **الدمج النهائي**: main.py مع 9 مراحل معالجة

### نتائج الاختبار العملي

- ✅ معالجة 416 إطار من فيديو 1280×720
- ✅ اكتشاف 10 مركبات فريدة
- ✅ تسجيل 9 عبورات للبوابات
- ✅ أقصى سرعة: 20.1 km/h
- ✅ تخزين البيانات في SQLite + CSV
- ✅ إنشاء فيديو الناتج مع المربعات ولوحة المعلومات
