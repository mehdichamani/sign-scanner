import os
import sys
from pathlib import Path
import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as pyzbar_decode, ZBarSymbol
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False

from src.config import SCANS_DIR, SIGNATURES_OUTPUT_DIR

# Set console encoding for Windows Persian/Emoji support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def remove_background(crop_img: np.ndarray, thresh_val: int = 200) -> np.ndarray:
    """Remove white paper background and convert to transparent PNG."""
    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
    _, alpha = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((2, 2), np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)

    b, g, r = cv2.split(crop_img)
    return cv2.merge([b, g, r, alpha])


def extract_qr_codes(img: np.ndarray, method: str = "smart"):
    """
    Find QR Codes using specified detection method/pass:
      - 'smart' (Priority Recommended): Starts with 0.5x, then direct 1.0x, then adaptive threshold only if needed (<12)
      - 'pass1_scale_half' (Priority 1): Fast PyZbar downscaled 0.5x (~60-140ms)
      - 'pass2_direct' (Priority 2): PyZbar direct grayscale 1.0x (~250-450ms)
      - 'pass3_threshold' (Priority 3): PyZbar with 3 binary thresholds [140, 180, 215] (~750-1000ms)
      - 'pass4_multi_scale' (Priority 4): PyZbar with 4 scales [0.5, 0.75, 1.25, 1.5] (~1400-2200ms)
      - 'pass5_opencv' (Priority 5): OpenCV QRCodeDetector multi-scale (~500-1100ms)
      - 'all_passes': Exhaustive combination of all methods (safest, slowest)
    """
    results = {}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    def _scan_pyzbar(image_to_scan, scale_factor=1.0):
        if not HAS_PYZBAR:
            return
        for d in pyzbar_decode(image_to_scan, symbols=[ZBarSymbol.QRCODE]):
            code = d.data.decode("utf-8", errors="ignore").strip()
            if code and code not in results:
                if scale_factor == 1.0:
                    results[code] = (int(d.rect.left), int(d.rect.top), int(d.rect.width), int(d.rect.height))
                else:
                    results[code] = (
                        int(d.rect.left / scale_factor),
                        int(d.rect.top / scale_factor),
                        int(d.rect.width / scale_factor),
                        int(d.rect.height / scale_factor),
                    )

    def _scan_opencv(image_to_scan, scale_factor=1.0):
        qr_detector = cv2.QRCodeDetector()
        ret, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(image_to_scan)
        if ret and decoded_info:
            for info, pt in zip(decoded_info, points):
                code = str(info).strip()
                if code and code not in results:
                    orig_pts = pt / scale_factor
                    x_min = int(np.min(orig_pts[:, 0]))
                    y_min = int(np.min(orig_pts[:, 1]))
                    x_max = int(np.max(orig_pts[:, 0]))
                    y_max = int(np.max(orig_pts[:, 1]))
                    results[code] = (x_min, y_min, x_max - x_min, y_max - y_min)

    # 1. Smart Adaptive Strategy (Default & Best)
    if method == "smart":
        # Step A: Fast 0.5x scale (filters scan noise, detects 90-100% in ~100ms)
        half_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        _scan_pyzbar(half_gray, scale_factor=0.5)

        # Step B: If < 12, try direct 1.0x grayscale
        if len(results) < 12:
            _scan_pyzbar(gray, scale_factor=1.0)

        # Step C: If still < 12, try thresholding
        if len(results) < 12:
            for th in [160, 200]:
                _, bin_img = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
                _scan_pyzbar(bin_img, scale_factor=1.0)
                if len(results) >= 12:
                    break

    # 2. Pass 1: PyZbar Downscaled 0.5x
    elif method == "pass1_scale_half":
        half_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        _scan_pyzbar(half_gray, scale_factor=0.5)

    # 3. Pass 2: PyZbar Direct Grayscale 1.0x
    elif method == "pass2_direct":
        _scan_pyzbar(gray, scale_factor=1.0)

    # 4. Pass 3: PyZbar Multi-threshold
    elif method == "pass3_threshold":
        for th in [140, 180, 215]:
            _, bin_img = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            _scan_pyzbar(bin_img, scale_factor=1.0)

    # 5. Pass 4: PyZbar 4-Scale Resizing
    elif method == "pass4_multi_scale":
        for scale in [0.5, 0.75, 1.25, 1.5]:
            scaled = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
            _scan_pyzbar(scaled, scale_factor=scale)

    # 6. Pass 5: OpenCV QRCodeDetector
    elif method == "pass5_opencv":
        _scan_opencv(img, scale_factor=1.0)
        if len(results) < 12:
            for scale in [1.5, 2.0]:
                scaled = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                _scan_opencv(scaled, scale_factor=scale)

    # 7. All Passes combined (Exhaustive)
    elif method == "all_passes":
        _scan_pyzbar(gray, scale_factor=1.0)
        for th in [140, 180, 215]:
            _, bin_img = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            _scan_pyzbar(bin_img, scale_factor=1.0)
        for scale in [0.5, 0.75, 1.25, 1.5]:
            scaled = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
            _scan_pyzbar(scaled, scale_factor=scale)
        _scan_opencv(img, scale_factor=1.0)

    formatted_results = [
        {"code": code, "qr_rect": rect} for code, rect in results.items()
    ]
    return formatted_results


def find_signature_boxes(img: np.ndarray):
    """Detect signature box contours."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    boxes = []

    h_img, w_img = img.shape[:2]
    # Expected box size ranges relative or absolute
    min_dim = int(min(h_img, w_img) * 0.04)   # ~100-150px
    max_dim = int(min(h_img, w_img) * 0.35)   # ~700-900px

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / h if h > 0 else 0
        if 0.7 <= aspect_ratio <= 1.4 and min_dim <= w <= max_dim and min_dim <= h <= max_dim:
            boxes.append((x, y, w, h))

    unique_boxes = []
    for b in sorted(boxes, key=lambda item: item[0] * 10000 + item[1]):
        if not any(
            abs(b[0] - u[0]) < 30 and abs(b[1] - u[1]) < 30 for u in unique_boxes
        ):
            unique_boxes.append(b)

    return unique_boxes


def get_box_for_qr(qr_rect: tuple, img_shape: tuple) -> tuple:
    """Compute exact 300DPI signature box crop rectangle anchored to the QR code position."""
    qx, qy, qw, qh = qr_rect
    h_img, w_img = img_shape[:2]

    # In 300DPI standard sheet (2550x3507) with 3x4 grid:
    # QR is at top-left of cell.
    # Signature box width is ~705px, height is ~622px.
    # Box offset from QR top-left: dx ≈ +24px, dy ≈ +212px.
    # We dynamically scale offsets if image resolution differs from standard 2550x3507.
    scale_x = w_img / 2550.0
    scale_y = h_img / 3507.0

    target_bw = int(650 * scale_x)
    target_bh = int(580 * scale_y)
    offset_x = int(18 * scale_x)
    offset_y = int(177 * scale_y)

    bx = max(0, qx + offset_x)
    by = max(0, qy + offset_y)
    bw = min(target_bw, w_img - bx)
    bh = min(target_bh, h_img - by)

    return (bx, by, bw, bh)


def process_scanned_file(
    image_path: str, output_dir=SIGNATURES_OUTPUT_DIR, debug: bool = True
) -> int:
    """Process a single scanned sheet image to extract signatures with debug logging."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ خطا در خواندن فایل: {image_path}")
        return 0

    h_img, w_img = img.shape[:2]

    # Step 1: Detect QR codes
    qr_list = extract_qr_codes(img)
    qr_count = len(qr_list)
    qr_codes = [q["code"] for q in qr_list]

    if debug:
        filename = Path(image_path).name
        print(f"🔍 [دیباگ] برگه '{filename}': {qr_count} کد QR شناسایی شد ➔ کدهای پرسنلی: {', '.join(qr_codes) if qr_codes else 'هیچ‌کدام'}")

    if qr_count == 0:
        if debug:
            print(f"⚠️ [دیباگ] هیچ کد QR در فایل '{Path(image_path).name}' خوانده نشد.")
        return 0

    # Step 2: Sort QR codes logically by row and column (Top to Bottom, Right to Left)
    # Row threshold approx 200px
    qr_list.sort(key=lambda item: (round(item["qr_rect"][1] / 200.0) * 200, item["qr_rect"][0]))

    # Step 3: Match each QR code directly to its signature box anchored to QR
    matched_results = []
    for q in qr_list:
        code = q["code"]
        box_rect = get_box_for_qr(q["qr_rect"], img.shape)
        matched_results.append((code, box_rect))

    # Step 4: Extract and save signatures
    extracted_count = 0
    for emp_code, (x, y, w, h) in matched_results:
        pad = 6
        crop_x1 = max(0, x + pad)
        crop_y1 = max(0, y + pad)
        crop_x2 = min(w_img, x + w - pad)
        crop_y2 = min(h_img, y + h - pad)

        sig_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
        if (
            sig_crop.size == 0
            or sig_crop.shape[0] < 20
            or sig_crop.shape[1] < 20
        ):
            continue

        transparent_sig = remove_background(sig_crop)
        out_path = output_dir / f"{emp_code}.png"
        cv2.imwrite(str(out_path), transparent_sig)
        extracted_count += 1

    return extracted_count


def extract_signatures(
    scans_dir=SCANS_DIR, output_dir=SIGNATURES_OUTPUT_DIR, debug: bool = True
) -> int:
    """Process all scanned sheets in scans_dir and save to output_dir."""
    scans_dir = Path(scans_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")
    files = [
        f for f in os.listdir(scans_dir) if f.lower().endswith(valid_exts)
    ] if scans_dir.exists() else []

    if not files:
        print(f"⚠️ هیچ فایل تصویری در پوشه '{scans_dir}' پیدا نشد.")
        return 0

    print(
        f"🔍 تعداد {len(files)} فایل اسکن پیدا شد. در حال پردازش و استخراج امضاها...\n"
    )

    total_extracted = 0
    for idx, filename in enumerate(files, 1):
        img_path = scans_dir / filename
        count = process_scanned_file(img_path, output_dir=output_dir, debug=debug)
        total_extracted += count
        print(
            f"[{idx}/{len(files)}] پردازش '{filename}' ➔ {count} امضا با موفقیت استخراج شد.\n"
        )

    print("=" * 45)
    print("🎉 عملیات با موفقیت پایان یافت!")
    print(
        f"📁 کل امضاهای موجود در پوشه خروجی: {len(list(output_dir.glob('*.png')))} امضا"
    )
    print(f"📂 مسیر خروجی: {output_dir.resolve()}")
    print("=" * 45)

    return total_extracted

