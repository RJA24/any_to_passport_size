import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from photo_utils import (
    DEFAULT_HEAD_RATIO,
    DEFAULT_TOP_MARGIN_RATIO,
    PHOTO_SIZE,
    add_name_strip,
    auto_crop_face,
    compute_crop_box,
    create_ph_passport_photo,
    detect_primary_face,
    render_passport_photo,
)


class PhotoUtilitiesTest(unittest.TestCase):
    def test_explicit_none_skips_detection_and_uses_center_crop(self):
        source = Image.new("RGB", (700, 800), (3, 44, 88))
        result = auto_crop_face(source, face_box=None)
        self.assertEqual(result.size, PHOTO_SIZE)
        self.assertEqual(result.getpixel((10, 10)), (3, 44, 88))

    def test_center_crop_without_detectable_face(self):
        source = Image.new("RGB", (900, 900), (11, 55, 99))
        result = auto_crop_face(source)
        self.assertEqual(result.size, PHOTO_SIZE)
        self.assertEqual(result.getpixel((0, 0)), (11, 55, 99))

    def test_portrait_with_tiny_source_and_face_box_never_adds_white_borders(self):
        source = Image.new("RGB", (170, 220), (70, 80, 90))
        result = render_passport_photo(source, face_box=(1, 15, 55, 70))
        self.assertEqual(result.size, PHOTO_SIZE)
        self.assertEqual(result.getpixel((0, 0)), (70, 80, 90))
        self.assertEqual(result.getpixel((412, 530)), (70, 80, 90))

    def test_landscape_with_face_close_to_edge_does_not_add_padding(self):
        source = Image.new("RGB", (750, 300), (15, 40, 60))
        result = render_passport_photo(source, face_box=(690, 40, 50, 65))
        self.assertEqual(result.size, PHOTO_SIZE)
        self.assertEqual(result.getpixel((0, 0)), (15, 40, 60))

    def test_compute_crop_box_stays_inside_image(self):
        box = compute_crop_box((500, 600), (450, 10, 40, 60))
        left, top, right, bottom = box
        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(right, 500)
        self.assertLessEqual(bottom, 600)

    def test_manual_adjustments_change_crop(self):
        source = Image.new("RGB", (900, 1200), "gray")
        base = render_passport_photo(
            source,
            face_box=(300, 250, 200, 260),
            zoom=1.0,
            x_shift=0.0,
            y_shift=0.0,
            head_ratio=DEFAULT_HEAD_RATIO,
            top_margin_ratio=DEFAULT_TOP_MARGIN_RATIO,
        )
        adjusted = render_passport_photo(
            source,
            face_box=(300, 250, 200, 260),
            zoom=1.2,
            x_shift=0.1,
            y_shift=0.05,
            head_ratio=0.68,
            top_margin_ratio=0.06,
        )
        self.assertEqual(base.size, PHOTO_SIZE)
        self.assertEqual(adjusted.size, PHOTO_SIZE)

    def test_invalid_box_uses_center_crop(self):
        source = Image.new("RGB", (500, 600), "blue")
        self.assertEqual(auto_crop_face(source, (0, 0, 0, 0)).size, PHOTO_SIZE)

    def test_name_strip_and_plain_photo_have_distinct_sizes(self):
        photo = Image.new("RGB", PHOTO_SIZE, "gray")
        tagged = add_name_strip(photo, "  Juan  Dela  Cruz ")
        self.assertEqual(photo.size, PHOTO_SIZE)
        self.assertEqual(tagged.size, (413, 611))
        self.assertEqual(tagged.getpixel((10, 520)), (128, 128, 128))
        self.assertEqual(tagged.getpixel((10, 601)), (255, 255, 255))

    def test_extremely_long_name_does_not_fail(self):
        photo = Image.new("RGB", PHOTO_SIZE, "gray")
        result = add_name_strip(photo, "REALLY-LONG-NAME" * 20)
        self.assertEqual(result.size, (413, 611))

    def test_face_detection_blank_image_returns_none(self):
        self.assertIsNone(detect_primary_face(Image.new("RGB", (400, 500), "white")))

    def test_backwards_compatibility_plain(self):
        source = Image.new("RGB", (600, 800), "gray")
        result = create_ph_passport_photo(source, "")
        self.assertEqual(result.size, PHOTO_SIZE)


if __name__ == "__main__":
    unittest.main()
