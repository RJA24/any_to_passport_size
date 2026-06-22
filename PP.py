import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
from rembg import remove # Import the background removal tool

def create_ph_passport_photo(image, name):
    # Philippine passport size: 35mm x 45mm. 
    target_size = (413, 531)
    img_resized = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)
    
    if name:
        final_img = Image.new('RGB', (413, 611), 'white')
        final_img.paste(img_resized, (0, 0))
        draw = ImageDraw.Draw(final_img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (413 - text_width) / 2
        y = 531 + (80 - text_height) / 2 - 5 
        
        draw.text((x, y), name.upper(), fill="black", font=font)
    else:
        final_img = img_resized
        
    return final_img

# --- Streamlit Web App Interface ---

st.set_page_config(page_title="PH ID Photo Maker", page_icon="📸", layout="centered")

st.title("📸 ID Photo Generator Pro")
st.markdown("Instantly format photos to the official **35mm x 45mm** Philippine requirement. Now with AI background removal!")
st.divider()

with st.form("photo_settings"):
    st.subheader("1. Upload & Settings")
    
    uploaded_file = st.file_uploader("Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"])
    name_input = st.text_input("Name Tag (Optional)", placeholder="e.g. JUAN DELA CRUZ")
    
    # New Checkbox for Background Removal
    remove_bg = st.checkbox("Automatically remove background and make it pure white", value=True)
    
    generate_button = st.form_submit_button("Generate Photo", type="primary", use_container_width=True)

if uploaded_file is not None and generate_button:
    
    with st.spinner("Processing your photo (this might take a few seconds)..."):
        # 1. Open the original image
        original_image = Image.open(uploaded_file).convert("RGB")
        image_to_process = original_image
        
        # 2. Handle Background Removal if selected
        if remove_bg:
            # rembg removes the background and returns an image with transparency (RGBA)
            subject_only = remove(original_image)
            
            # Create a brand new pure white image of the same size
            white_background = Image.new("RGB", subject_only.size, "white")
            
            # Paste the subject onto the white background using its own transparency as a mask
            white_background.paste(subject_only, (0, 0), subject_only)
            
            # Set this new white-background image as the one to be cropped
            image_to_process = white_background
            
        # 3. Crop to passport size and add name
        processed_image = create_ph_passport_photo(image_to_process, name_input)
    
    st.success("Photo formatted successfully!")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Original Image")
        st.image(original_image, use_container_width=True)
        
    with col2:
        st.caption("Official 35x45mm Size")
        st.image(processed_image, use_container_width=True)
        
    st.divider()
    
    buf = io.BytesIO()
    processed_image.save(buf, format="JPEG", quality=100)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="⬇️ Download Ready-to-Print Photo",
        data=byte_im,
        file_name="ph_passport_photo.jpg",
        mime="image/jpeg",
        type="primary",
        use_container_width=True
    )
