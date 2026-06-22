import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io

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
        
        draw.text((x, y), name.upper(), fill="black", font=font) # Forced uppercase for official look
    else:
        final_img = img_resized
        
    return final_img

# --- Streamlit Web App Interface ---

st.set_page_config(page_title="PH ID Photo Maker", page_icon="📸", layout="centered")

st.title("📸 ID Photo Generator")
st.markdown("Instantly format photos to the official **35mm x 45mm** Philippine requirement for PRC, Civil Service, and DFA.")
st.divider()

# Create a clean form to prevent the app from reloading on every keystroke
with st.form("photo_settings"):
    st.subheader("1. Upload & Settings")
    
    uploaded_file = st.file_uploader("Upload a clear, front-facing photo", type=["jpg", "jpeg", "png"])
    name_input = st.text_input("Name Tag (Optional)", placeholder="e.g. JUAN DELA CRUZ")
    
    # The submit button triggers the processing
    generate_button = st.form_submit_button("Generate Photo", type="primary", use_container_width=True)

if uploaded_file is not None and generate_button:
    # Show a loading spinner for better UX
    with st.spinner("Formatting your photo..."):
        original_image = Image.open(uploaded_file).convert("RGB")
        processed_image = create_ph_passport_photo(original_image, name_input)
    
    st.success("Photo formatted successfully!")
    
    # Display images side-by-side for immediate visual comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("Original Image")
        st.image(original_image, use_container_width=True)
        
    with col2:
        st.caption("Official 35x45mm Size")
        st.image(processed_image, use_container_width=True)
        
    st.divider()
    
    # Prepare image for download
    buf = io.BytesIO()
    processed_image.save(buf, format="JPEG", quality=100) # Bumped quality to 100 for printing
    byte_im = buf.getvalue()
    
    # Large, prominent download button
    st.download_button(
        label="⬇️ Download Ready-to-Print Photo",
        data=byte_im,
        file_name="ph_passport_photo.jpg",
        mime="image/jpeg",
        type="primary",
        use_container_width=True
    )
