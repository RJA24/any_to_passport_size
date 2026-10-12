"""Streamlit entry point for the Philippine ID-photo maker."""

import hashlib
import io

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from photo_utils import (
    DEFAULT_HEAD_RATIO,
    DEFAULT_TOP_MARGIN_RATIO,
    PRINT_DPI,
    add_name_strip,
    detect_primary_face,
    render_passport_photo,
)

MAX_UPLOAD_MB = 15
MAX_IMAGE_PIXELS = 25_000_000


@st.cache_resource(show_spinner=False)
def get_background_removal_session():
    """Load the model once per app process, rather than once per photo."""
    from rembg import new_session

    return new_session("u2net")


def make_background_white(image: Image.Image) -> Image.Image:
    from rembg import remove

    subject = remove(image, session=get_background_removal_session())
    if isinstance(subject, bytes):
        subject = Image.open(io.BytesIO(subject))
    subject_rgba = subject.convert("RGBA")
    white = Image.new("RGBA", subject_rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, subject_rgba).convert("RGB")


def read_uploaded_photo(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as opened:
        if opened.width * opened.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image is too large. Please upload a photo under 25 megapixels.")
        corrected = ImageOps.exif_transpose(opened)
        rgba = corrected.convert("RGBA")
        return Image.alpha_composite(
            Image.new("RGBA", rgba.size, "white"), rgba
        ).convert("RGB")


def jpeg_download(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95, subsampling=0, dpi=PRINT_DPI)
    return buffer.getvalue()


def build_preview(source_image: Image.Image, face_box, name_text: str):
    standard = render_passport_photo(
        source_image,
        face_box=face_box,
        zoom=st.session_state.get("frame_zoom", 1.0),
        x_shift=st.session_state.get("frame_x_shift", 0.0),
        y_shift=st.session_state.get("frame_y_shift", 0.0),
        head_ratio=st.session_state.get("frame_head_ratio", DEFAULT_HEAD_RATIO),
        top_margin_ratio=st.session_state.get("frame_top_margin", DEFAULT_TOP_MARGIN_RATIO),
    )
    named = add_name_strip(standard, name_text) if name_text.strip() else None
    return standard, named


st.set_page_config(page_title="PH ID Photo Maker", page_icon="", layout="centered")
st.title("PH ID Photo Generator")
st.markdown(
    "Create a **35 × 45 mm (413 × 531 px at 300 DPI)** ID-photo template, "
    "with optional white-background removal and a name strip. "
    "The app now uses smarter face-based framing plus manual fine-tuning. "
    "Photo requirements vary by agency—check the rules for your application."
)
st.divider()

with st.form("photo_settings"):
    st.subheader("1. Upload & Settings")
    uploaded_file = st.file_uploader(
        "Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"]
    )
    name_input = st.text_input(
        "Name strip (optional)", placeholder="e.g. JUAN DELA CRUZ", max_chars=100
    )
    remove_bg = st.checkbox("Remove background and replace with white", value=True)
    generate_button = st.form_submit_button(
        "Generate Photo", type="primary", use_container_width=True
    )

upload_data = uploaded_file.getvalue() if uploaded_file is not None else None
upload_fingerprint = hashlib.sha256(upload_data).hexdigest() if upload_data else None
if (
    "photo_result" in st.session_state
    and st.session_state.photo_result["upload_fingerprint"] != upload_fingerprint
):
    del st.session_state.photo_result

if generate_button:
    if not upload_data:
        st.warning("Please upload a photo first.")
    elif len(upload_data) > MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"Please upload a file smaller than {MAX_UPLOAD_MB} MB.")
    else:
        st.session_state.pop("photo_result", None)
        try:
            with st.spinner("Processing your photo..."):
                original = read_uploaded_photo(upload_data)
                face_box = detect_primary_face(original)
                processed_source = original
                bg_warning = None
                if remove_bg:
                    try:
                        processed_source = make_background_white(original)
                    except Exception:
                        bg_warning = (
                            "Background removal was unavailable. The photo was generated "
                            "with its original background instead."
                        )

                st.session_state.frame_zoom = 1.0
                st.session_state.frame_x_shift = 0.0
                st.session_state.frame_y_shift = 0.0
                st.session_state.frame_head_ratio = DEFAULT_HEAD_RATIO
                st.session_state.frame_top_margin = DEFAULT_TOP_MARGIN_RATIO

                st.session_state.photo_result = {
                    "original": original,
                    "processed_source": processed_source,
                    "face_box": face_box,
                    "face_found": face_box is not None,
                    "bg_warning": bg_warning,
                    "upload_fingerprint": upload_fingerprint,
                    "name_input": name_input,
                }
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            st.error(f"Unable to read this photo: {exc}")
        except Exception as exc:
            st.error(f"Could not generate the photo: {exc}")

result = st.session_state.get("photo_result")
if result:
    st.success("Photo generated successfully!")
    if not result["face_found"]:
        st.info("No frontal face was detected; a centered crop is being used. Fine-tuning controls are limited in this case.")
    else:
        st.info("Auto-framing has been applied. You can fine-tune the framing below if needed.")
    if result["bg_warning"]:
        st.warning(result["bg_warning"])

    st.subheader("2. Fine-tune Framing")
    st.caption("Adjust the framing if the auto crop is too tight, too low, or slightly off-center.")

    c1, c2 = st.columns(2)
    with c1:
        st.slider(
            "Zoom",
            min_value=0.70,
            max_value=1.35,
            value=float(st.session_state.get("frame_zoom", 1.0)),
            step=0.01,
            key="frame_zoom",
            help="Higher values zoom in more; lower values zoom out for more shoulders/background.",
            disabled=not result["face_found"],
        )
        st.slider(
            "Move left / right",
            min_value=-0.20,
            max_value=0.20,
            value=float(st.session_state.get("frame_x_shift", 0.0)),
            step=0.005,
            key="frame_x_shift",
            help="Negative = move crop left, positive = move crop right.",
            disabled=not result["face_found"],
        )
        st.slider(
            "Move up / down",
            min_value=-0.20,
            max_value=0.20,
            value=float(st.session_state.get("frame_y_shift", 0.0)),
            step=0.005,
            key="frame_y_shift",
            help="Negative = move crop up, positive = move crop down.",
            disabled=not result["face_found"],
        )
    with c2:
        st.slider(
            "Estimated head size",
            min_value=0.56,
            max_value=0.72,
            value=float(st.session_state.get("frame_head_ratio", DEFAULT_HEAD_RATIO)),
            step=0.005,
            key="frame_head_ratio",
            help="Larger values make the head occupy more of the photo height.",
            disabled=not result["face_found"],
        )
        st.slider(
            "Top headroom",
            min_value=0.04,
            max_value=0.14,
            value=float(st.session_state.get("frame_top_margin", DEFAULT_TOP_MARGIN_RATIO)),
            step=0.005,
            key="frame_top_margin",
            help="Controls empty space above the head.",
            disabled=not result["face_found"],
        )
        if st.button("Reset framing", use_container_width=True, disabled=not result["face_found"]):
            st.session_state.frame_zoom = 1.0
            st.session_state.frame_x_shift = 0.0
            st.session_state.frame_y_shift = 0.0
            st.session_state.frame_head_ratio = DEFAULT_HEAD_RATIO
            st.session_state.frame_top_margin = DEFAULT_TOP_MARGIN_RATIO

    standard_photo, named_photo = build_preview(
        result["processed_source"], result["face_box"], result["name_input"]
    )

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Original photo")
        st.image(result["original"], use_container_width=True)
    with col2:
        st.caption("Final 35 × 45 mm preview")
        st.image(standard_photo, use_container_width=True)

    st.download_button(
        "⬇️ Download 35 × 45 mm Photo (JPG)",
        data=jpeg_download(standard_photo),
        file_name="ph_id_photo_35x45mm.jpg",
        mime="image/jpeg",
        type="primary",
        use_container_width=True,
    )

    if named_photo is not None:
        st.divider()
        st.caption("Name-tag version (413 × 611 px: taller than the 35 × 45 mm photo)")
        st.image(named_photo, width=300)
        st.download_button(
            "⬇️ Download Photo With Name Strip (JPG)",
            data=jpeg_download(named_photo),
            file_name="ph_id_photo_with_name.jpg",
            mime="image/jpeg",
            use_container_width=True,
        )



