"""Photo sizing and framing helpers used by the Streamlit app.

Face cropping is a visual heuristic, not a biometric compliance assessment.
"""

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

PHOTO_SIZE = (413, 531)  # Approximately 35 x 45 mm at 300 DPI.
PRINT_DPI = (300, 300)
NAME_STRIP_HEIGHT = 80
_AUTO_DETECT = object()

# Tunable defaults for automatic framing.
DEFAULT_HEAD_RATIO = 0.64  # estimated head height as % of total photo height
DEFAULT_TOP_MARGIN_RATIO = 0.08  # target empty space above head as % of photo height
_ESTIMATED_HEAD_TOP_FROM_FACE = 0.35  # forehead/hair above Haar face box
_ESTIMATED_CHIN_FROM_FACE = 1.20  # chin below top of Haar face box as face-box multiples


@lru_cache(maxsize=1)
def _face_cascade():
    """Load OpenCV's bundled cascade, using the repository copy if necessary."""
    paths = [
        Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml",
        Path(__file__).resolve().parent / "haarcascade_frontalface_default.xml",
    ]
    for path in paths:
        if path.is_file():
            detector = cv2.CascadeClassifier(str(path))
            if not detector.empty():
                return detector
    return None


def detect_primary_face(image: Image.Image):
    """Return the largest frontal face bounding box as (x, y, width, height).

    Returns None if no face is found or OpenCV cannot run the detector.
    Always run this on the *original* photo, before background removal.
    """
    try:
        rgb = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        detector = _face_cascade()
        if detector is None:
            return None
        min_side = max(24, min(image.size) // 12)
        faces = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side)
        )
        if len(faces) == 0:
            return None
        return tuple(int(value) for value in max(faces, key=lambda f: f[2] * f[3]))
    except (cv2.error, ValueError, AttributeError):
        return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def compute_crop_box(
    image_size,
    face_box,
    *,
    zoom: float = 1.0,
    x_shift: float = 0.0,
    y_shift: float = 0.0,
    head_ratio: float = DEFAULT_HEAD_RATIO,
    top_margin_ratio: float = DEFAULT_TOP_MARGIN_RATIO,
):
    """Compute a crop box around the detected face.

    Parameters:
    - zoom: >1 zooms in, <1 zooms out.
    - x_shift/y_shift: fraction of crop width/height to move the crop.
    - head_ratio: desired estimated head height as a fraction of output height.
    - top_margin_ratio: desired empty space above the estimated head.
    """
    img_w, img_h = image_size
    target_w, target_h = PHOTO_SIZE
    aspect = target_w / target_h

    if face_box is None:
        return (0, 0, img_w, img_h)

    x, y, w, h = face_box
    if w <= 0 or h <= 0:
        return (0, 0, img_w, img_h)

    head_ratio = _clamp(head_ratio, 0.50, 0.80)
    top_margin_ratio = _clamp(top_margin_ratio, 0.02, 0.18)
    zoom = _clamp(zoom, 0.6, 1.6)
    x_shift = _clamp(x_shift, -0.35, 0.35)
    y_shift = _clamp(y_shift, -0.35, 0.35)

    estimated_head_top = y - (h * _ESTIMATED_HEAD_TOP_FROM_FACE)
    estimated_chin = y + (h * _ESTIMATED_CHIN_FROM_FACE)
    estimated_head_h = max(1.0, estimated_chin - estimated_head_top)

    # Compute crop height from desired head ratio, then apply zoom.
    crop_h = estimated_head_h / head_ratio
    crop_h = crop_h / zoom
    crop_h = min(max(crop_h, 40.0), float(img_h))
    crop_w = crop_h * aspect

    # If the width exceeds the image, fit crop to width instead.
    if crop_w > img_w:
        crop_w = float(img_w)
        crop_h = crop_w / aspect

    crop_h = min(crop_h, float(img_h))
    crop_w = min(crop_w, float(img_w))

    face_center_x = x + (w / 2)

    # Place the estimated top of the head with some headroom.
    crop_left = face_center_x - (crop_w / 2)
    crop_top = estimated_head_top - (top_margin_ratio * crop_h)

    # Manual fine-tune shifts.
    crop_left += x_shift * crop_w
    crop_top += y_shift * crop_h

    # Clamp crop inside the source image.
    max_left = max(0.0, img_w - crop_w)
    max_top = max(0.0, img_h - crop_h)
    crop_left = _clamp(crop_left, 0.0, max_left)
    crop_top = _clamp(crop_top, 0.0, max_top)

    crop_right = crop_left + crop_w
    crop_bottom = crop_top + crop_h
    return (
        int(round(crop_left)),
        int(round(crop_top)),
        int(round(crop_right)),
        int(round(crop_bottom)),
    )


def render_passport_photo(
    image_pil: Image.Image,
    face_box=_AUTO_DETECT,
    *,
    zoom: float = 1.0,
    x_shift: float = 0.0,
    y_shift: float = 0.0,
    head_ratio: float = DEFAULT_HEAD_RATIO,
    top_margin_ratio: float = DEFAULT_TOP_MARGIN_RATIO,
) -> Image.Image:
    """Crop and resize to the standard PH ID photo size."""
    image = image_pil.convert("RGB")
    if face_box is _AUTO_DETECT:
        face_box = detect_primary_face(image)
    if face_box is None:
        return ImageOps.fit(image, PHOTO_SIZE, method=Image.Resampling.LANCZOS)

    box = compute_crop_box(
        image.size,
        face_box,
        zoom=zoom,
        x_shift=x_shift,
        y_shift=y_shift,
        head_ratio=head_ratio,
        top_margin_ratio=top_margin_ratio,
    )
    cropped = image.crop(box)
    return ImageOps.fit(cropped, PHOTO_SIZE, method=Image.Resampling.LANCZOS)


def auto_crop_face(image_pil: Image.Image, face_box=_AUTO_DETECT) -> Image.Image:
    """Backward-compatible alias for the default automatic framing."""
    return render_passport_photo(image_pil, face_box=face_box)


def _load_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _fit_name(draw: ImageDraw.ImageDraw, name: str, max_w: int, max_h: int):
    """Return (multiline_text, font, bbox) that fits the available space."""
    words = name.split()
    for size in range(32, 10, -1):
        font = _load_font(size)
        candidates = [name]
        candidates += [" ".join(words[:i]) + "\n" + " ".join(words[i:]) for i in range(1, len(words))]
        for candidate in candidates:
            bbox = draw.multiline_textbbox((0, 0), candidate, font=font, spacing=2, align="center")
            if bbox[2] - bbox[0] <= max_w and bbox[3] - bbox[1] <= max_h:
                return candidate, font, bbox

    font = _load_font(11)
    shortened = name
    while shortened:
        candidate = shortened + "…"
        bbox = draw.multiline_textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_w:
            return candidate, font, bbox
        shortened = shortened[:-1]
    return "", font, (0, 0, 0, 0)


def add_name_strip(photo: Image.Image, name: str) -> Image.Image:
    """Append a white name strip; the result is taller than 35x45 mm."""
    clean_name = " ".join(name.upper().split())
    if not clean_name:
        return photo.copy()

    width, height = photo.size
    result = Image.new("RGB", (width, height + NAME_STRIP_HEIGHT), "white")
    result.paste(photo.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(result)
    rendered_name, font, bbox = _fit_name(draw, clean_name, width - 24, NAME_STRIP_HEIGHT - 12)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        ((width - text_w) / 2 - bbox[0], height + (NAME_STRIP_HEIGHT - text_h) / 2 - bbox[1]),
        rendered_name,
        font=font,
        fill="black",
        align="center",
        spacing=2,
    )
    return result


def create_ph_passport_photo(image: Image.Image, name: str = "", face_box=_AUTO_DETECT) -> Image.Image:
    """Compatibility helper: crop the photo, optionally adding a name strip."""
    cropped = auto_crop_face(image, face_box=face_box)
    return add_name_strip(cropped, name) if name.strip() else cropped
