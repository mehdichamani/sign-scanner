import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Persian encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from pyzbar.pyzbar import decode as pyzbar_decode, ZBarSymbol
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

from src.config import SCANS_DIR


def benchmark_image(img_path: str):
    filename = Path(img_path).name
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"❌ خطا در خواندن {filename}")
        return

    h, w = img.shape[:2]
    print(f"\n=======================================================")
    print(f"📄 تست فایل: {filename} (ابعاد: {w}x{h})")
    print(f"=======================================================")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # --- Pass 1: PyZbar Direct Grayscale ---
    t0 = time.perf_counter()
    res_direct = {}
    if HAS_PYZBAR:
        for d in pyzbar_decode(gray, symbols=[ZBarSymbol.QRCODE]):
            c = d.data.decode("utf-8", errors="ignore").strip()
            if c:
                res_direct[c] = d.rect
    t_direct = (time.perf_counter() - t0) * 1000
    print(f"1️⃣  [PyZbar - مستقیم Grayscale]   : {len(res_direct):2d} کیوآرکد | زمان: {t_direct:6.1f} ms")

    # --- Pass 2: PyZbar Downscaled (0.5x) ---
    t0 = time.perf_counter()
    res_scaled_half = {}
    if HAS_PYZBAR:
        half_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        for d in pyzbar_decode(half_gray, symbols=[ZBarSymbol.QRCODE]):
            c = d.data.decode("utf-8", errors="ignore").strip()
            if c:
                res_scaled_half[c] = d.rect
    t_scaled_half = (time.perf_counter() - t0) * 1000
    print(f"2️⃣  [PyZbar - کوچک‌شده 0.5x]     : {len(res_scaled_half):2d} کیوآرکد | زمان: {t_scaled_half:6.1f} ms")

    # --- Pass 3: PyZbar Binary Thresholds ---
    t0 = time.perf_counter()
    res_thresh = {}
    if HAS_PYZBAR:
        for th in [140, 180, 215]:
            _, bin_img = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            for d in pyzbar_decode(bin_img, symbols=[ZBarSymbol.QRCODE]):
                c = d.data.decode("utf-8", errors="ignore").strip()
                if c:
                    res_thresh[c] = d.rect
    t_thresh = (time.perf_counter() - t0) * 1000
    print(f"3️⃣  [PyZbar - ۳ آستانه Binarize]   : {len(res_thresh):2d} کیوآرکد | زمان: {t_thresh:6.1f} ms")

    # --- Pass 4: PyZbar All Scales (0.5, 0.75, 1.25, 1.5) ---
    t0 = time.perf_counter()
    res_all_scales = {}
    if HAS_PYZBAR:
        for scale in [0.5, 0.75, 1.25, 1.5]:
            scaled = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
            for d in pyzbar_decode(scaled, symbols=[ZBarSymbol.QRCODE]):
                c = d.data.decode("utf-8", errors="ignore").strip()
                if c:
                    res_all_scales[c] = d.rect
    t_all_scales = (time.perf_counter() - t0) * 1000
    print(f"4️⃣  [PyZbar - تغییر سایز ۴ مرحله]: {len(res_all_scales):2d} کیوآرکد | زمان: {t_all_scales:6.1f} ms")

    # --- Pass 5: OpenCV QRCodeDetector (Multi) ---
    t0 = time.perf_counter()
    res_cv = {}
    qr_detector = cv2.QRCodeDetector()
    ret, decoded_info, _, _ = qr_detector.detectAndDecodeMulti(img)
    if ret and decoded_info:
        for info in decoded_info:
            c = str(info).strip()
            if c:
                res_cv[c] = True
    t_cv = (time.perf_counter() - t0) * 1000
    print(f"5️⃣  [OpenCV QRCodeDetector]       : {len(res_cv):2d} کیوآرکد | زمان: {t_cv:6.1f} ms")

    # --- Smart Adaptive Pipeline ---
    t0 = time.perf_counter()
    res_adaptive = {}
    # Step A: fast direct
    if HAS_PYZBAR:
        for d in pyzbar_decode(gray, symbols=[ZBarSymbol.QRCODE]):
            c = d.data.decode("utf-8", errors="ignore").strip()
            if c:
                res_adaptive[c] = d.rect

    # Step B: Only if less than 12 detected, try 0.5x scale
    if len(res_adaptive) < 12 and HAS_PYZBAR:
        half_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        for d in pyzbar_decode(half_gray, symbols=[ZBarSymbol.QRCODE]):
            c = d.data.decode("utf-8", errors="ignore").strip()
            if c:
                res_adaptive[c] = d.rect

    # Step C: Fallback only if still < 12
    if len(res_adaptive) < 12 and HAS_PYZBAR:
        for th in [160, 200]:
            _, bin_img = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            for d in pyzbar_decode(bin_img, symbols=[ZBarSymbol.QRCODE]):
                c = d.data.decode("utf-8", errors="ignore").strip()
                if c:
                    res_adaptive[c] = d.rect
            if len(res_adaptive) >= 12:
                break

    t_adaptive = (time.perf_counter() - t0) * 1000
    print(f"⚡  [خط لوله پیشنهادی هوشمند]     : {len(res_adaptive):2d} کیوآرکد | زمان: {t_adaptive:6.1f} ms")


def main():
    scans_dir = Path(SCANS_DIR)
    files = list(scans_dir.glob("*.png")) + list(scans_dir.glob("*.jpg"))
    if not files:
        print(f"هیچ فایلی در {scans_dir} یافت نشد.")
        return

    print("🚀 در حال ارزیابی و بنچمارک سرعت و دقت مراحل مختلف تشخیص QR...")
    for f in sorted(files):
        benchmark_image(f)


if __name__ == "__main__":
    main()
