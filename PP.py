import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io

def create_ph_passport_photo(image, name):
    # Philippine passport size: 35mm x 45mm. 
    # At 300 DPI, this equals exactly 413x531 pixels.
    target_size = (413, 531)
    
    # Crop and resize the image to fit the PH dimensions perfectly
    img_resized = ImageOps.fit(image, target_size, Image.Resampling.LANCZOS)
    
    if name:
        # Create a new image with extra height (80 pixels) for the white name tag space
        final_img = Image.new('RGB', (413, 611), 'white')
        final_img.paste(img_resized, (0, 0))
        
        draw = ImageDraw.Draw(final_img)
        
        # Try to load a larger font, fallback to default if not found
        try:
            font = ImageFont.truetype("arial.ttf", 30)
        except IOError:
            font = ImageFont.load_default()
            
        # Calculate text position to center it horizontally and vertically in the white space
        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (413 - text_width) / 2
        y = 531 + (80 - text_height) / 2 - 5 
        
        # Draw the text in black
        draw.text((x, y), name, fill="black", font=font)
    else:
        final_img = img_resized
        
    return final_img

# --- Streamlit Web App Interface ---

st.set_page_config(page_title="PH Passport Photo Maker", page_icon="📸")

st.title("📸 Philippine Passport Photo Maker")
st.write("Upload a photo to instantly crop it to the standard Philippine passport size (**35mm x 45mm**) with an optional name tag.")

# 1. File Uploader
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# 2. Name Input
name_input = st.text_input("Enter name to display at the bottom (optional):")

if uploaded_file is not None:
    # Load the uploaded image and force it into RGB mode to prevent PNG transparency errors
    original_image = Image.open(uploaded_file).convert("RGB")
    
    st.subheader("Preview")
    
    # Process the image
    processed_image = create_ph_passport_photo(original_image, name_input)
    
    # Display the result
    st.image(processed_image, caption="Your PH Passport Photo", use_container_width=False)
    
    # 3. Download Button
    buf = io.BytesIO()
    processed_image.save(buf, format="JPEG", quality=95)
    byte_im = buf.getvalue()
    
    st.download_button(
        label="⬇️ Download Passport Photo",
        data=byte_im,
        file_name="ph_passport_photo.jpg",
        mime="image/jpeg",
    )