import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import cv2
import numpy as np
from rembg import remove

def auto_crop_face(image_pil):
    # Convert the PIL image to an OpenCV array
    img_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    
    # Load OpenCV's built-in facial recognition tool
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    # Convert image to grayscale for the detector
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
    
    # If no face is found, fallback to the standard center crop
    if len(faces) == 0:
        return ImageOps.fit(image_pil, (413, 531), Image.Resampling.LANCZOS)
        
    # Grab the largest face detected in the photo
    faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
    x, y, w, h = faces[0]
    
    # Target Philippine Passport Dimensions (413x531 px)
    target_w, target_h = 413, 531
    
    # The detector finds the face (eyes to chin). The true head (chin to crown) is about 1.3x taller.
    true_head_h = h * 1.3
    
    # The head must cover ~75% of the total height to meet the 70-80% PH requirement
    target_head_h = target_h * 0.75
    
    # Calculate how much we need to zoom in
    scale = target_head_h / true_head_h
    
    # Resize the entire image by the zoom scale
    new_size = (int(image_pil.width * scale), int(image_pil.height * scale))
    img_scaled = image_pil.resize(new_size, Image.Resampling.LANCZOS)
    
    # Scale the face coordinates to match the new zoomed image
    sx, sy, sw, sh = int(x * scale), int(y * scale), int(w * scale), int(h * scale)
    
    # Estimate the top of the hair and add a 5mm gap (~59 pixels at 300 DPI) above it
    top_of_hair = sy - int(sh * 0.25)
    crop_top = top_of_hair - 59
    
    # Center the face horizontally
    face_center_x = sx + (sw // 2)
    crop_left = face_center_x - (target_w // 2)
    
    # Create a massive padded white canvas so we don't accidentally crop outside the image boundaries
    padded_img = Image.new("RGB", (new_size[0] + target_w*2, new_size[1] + target_h*2), "white")
    padded_img.paste(img_scaled, (target_w, target_h))
    
    # Apply the final precise crop
    final_left = crop_left + target_w
    final_top = crop_top + target_h
    final_crop = padded_img.crop((final_left, final_top, final_left + target_w, final_top + target_h))
    
    return final_crop

def create_ph_passport_photo(image, name):
    # Run the smart auto-zoom instead of the blind center crop
    img_cropped = auto_crop_face(image)
    
    if name:
        final_img = Image.new('RGB', (413, 611), 'white')
        final_img.paste(img_cropped, (0, 0))
        draw = ImageDraw.Draw(final_img)
        
        try:
            # Try to load Windows font
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            # FIX: If Arial fails, use Pillow's modern default scalable font so the text isn't tiny
            font = ImageFont.load_default(size=30)
            
        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (413 - text_width) / 2
        y = 531 + (80 - text_height) / 2 - 5 
        
        draw.text((x, y), name.upper(), fill="black", font=font)
    else:
        final_img = img_cropped
        
    return final_img

# --- Streamlit Web App Interface ---

st.set_page_config(page_title="PH ID Photo Maker", page_icon="📸", layout="centered")

st.title("📸 ID Photo Generator Pro")
st.markdown("Instantly format photos to the official **35mm x 45mm** Philippine requirement. Features AI background removal and smart biometric face scaling.")
st.divider()

with st.form("photo_settings"):
    st.subheader("1. Upload & Settings")
    
    uploaded_file = st.file_uploader("Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"])
    name_input = st.text_input("Name Tag (Optional)", placeholder="e.g. JUAN DELA CRUZ")
    
    remove_bg = st.checkbox("Automatically remove background and make it pure white", value=True)
    
    generate_button = st.form_submit_button("Generate Photo", type="primary", use_container_width=True)

if uploaded_file is not None and generate_button:
    
    with st.spinner("Processing your photo..."):
        original_image = Image.open(uploaded_file).convert("RGB")
        image_to_process = original_image
        
        if remove_bg:
            subject_only = remove(original_image)
            white_background = Image.new("RGB", subject_only.size, "white")
            white_background.paste(subject_only, (0, 0), subject_only)
            image_to_process = white_background
            
        processed_image = create_ph_passport_photo(image_to_process, name_input)
    
    st.success("Photo formatted successfully!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Original Image")
        st.image(original_image, use_container_width=True)
        
    with col2:
        st.caption("Official 35x45mm Size (Auto-Zoomed)")
        st.image(processed_image, use_container_width=True)
        
    st.divider()
    
    buf = io.BytesIO()
    processed_image.save(buf, format="JPEG", quality=100)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="⬇️ Download Ready-to-Print Photo",
        data=byte_im,
        file_name="ph_passport_photo_pro.jpg",
        mime="image/jpeg",
        type="primary",
        use_container_width=True
    )
