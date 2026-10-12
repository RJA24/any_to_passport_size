# PH ID Photo Generator

A Streamlit app that turns a front-facing image into a **35 × 45 mm ID-photo template** (413 × 531 px at 300 DPI). It can optionally remove the background, replace it with white, and add a separate name-strip version.

**Note:** This is a formatting tool, **not a guarantee of compliance** with passport, visa, or agency-specific biometric photo rules. Check the current photo requirements of the receiving agency. Automatic face framing is heuristic.

## What's improved

- Smarter **face-aware framing** based on estimated head size and headroom.
- **Manual framing controls** after generation:
  - Zoom
  - Left / right shift
  - Up / down shift
  - Estimated head size
  - Top headroom
- Detects the face on the **original photo first**, before background removal.
- Optional AI background removal; if it fails, the app keeps the original background and shows a warning.
- Honors phone EXIF rotation and transparency.
- Downloads a **413 × 531 px JPG** with **300 DPI** metadata.
- Optional **separate** name-strip JPG (413 × 611 px, not 35 × 45 mm).

## Run locally

Use **Python 3.11–3.13** and install dependencies:

```bash
python -m pip install -r requirements.txt
streamlit run PP.py
```

## Files

```text
├── PP.py
├── photo_utils.py
├── requirements.txt
├── haarcascade_frontalface_default.xml
└── tests/
    └── test_photo_utils.py
```

## How the framing works

The automatic framing uses the detected face box as a starting point, then estimates:

- approximate full head height
- top headroom
- crop aspect ratio for 35 × 45 mm output

It then builds a crop window and resizes the result to **413 × 531 px**.

If the automatic result is not ideal, the user can fine-tune the framing before downloading.

## Test

```bash
python -m unittest discover -s tests -v
```
