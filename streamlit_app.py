
"""
PDF Image Attachment Web App
Upload PDFs and an image, then download modified PDFs with the image attached.
Supports PNG, JPG, and JPEG image formats.
Mobile-optimized for iPad and iPhone.
Fully compatible with Chrome and Safari.
"""

import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image
import zipfile

st.set_page_config(
    page_title="PDF Image Attacher",
    page_icon="📎",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on mobile
)

# Mobile-optimized CSS with Safari compatibility
st.markdown("""
<style>
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .stButton button {
            width: 100%;
            font-size: 16px;
            padding: 12px;
            min-height: 48px;
        }

        .stDownloadButton button {
            width: 100%;
            font-size: 16px;
            padding: 12px;
            min-height: 48px;
        }

        /* Larger touch targets */
        .stFileUploader {
            font-size: 16px;
        }

        /* Better spacing on mobile */
        .element-container {
            margin-bottom: 1rem;
        }

        /* Make sliders easier to use on touch */
        .stSlider {
            padding: 10px 0;
        }

        /* Better mobile header */
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.2rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
    }

    /* Responsive images */
    .stImage {
        max-width: 100%;
        height: auto;
    }

    /* Improve file uploader visibility */
    .stFileUploader > div {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 1rem;
    }

    /* Safari-specific fixes */
    @supports (-webkit-appearance: none) {
        /* Better button rendering in Safari */
        .stButton button, .stDownloadButton button {
            -webkit-appearance: none;
            -webkit-tap-highlight-color: transparent;
        }

        /* Fix Safari file input styling */
        input[type="file"] {
            -webkit-appearance: none;
        }

        /* Smooth scrolling for Safari */
        * {
            -webkit-overflow-scrolling: touch;
        }

        /* Fix Safari flexbox issues */
        .element-container {
            display: -webkit-box;
            display: -webkit-flex;
            display: flex;
        }
    }

    /* Safari iOS specific */
    @supports (-webkit-touch-callout: none) {
        /* Prevent zoom on input focus in Safari iOS */
        input, select, textarea {
            font-size: 16px !important;
        }

        /* Fix Safari iOS bottom bar overlap */
        body {
            padding-bottom: env(safe-area-inset-bottom);
        }

        /* Better touch response */
        button, a {
            -webkit-tap-highlight-color: rgba(0, 0, 0, 0.1);
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📎 PDF Image Attachment Tool")
st.markdown("Upload your PDFs and an image to attach it to all PDFs. Supports PNG, JPG, and JPEG formats.")

# Browser compatibility notice
st.info("💡 **Mobile Tip:** Tap the '>' arrow in the top-left to access settings. Works great on Chrome and Safari!")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

position = st.sidebar.selectbox(
    "Image Position",
    ["bottom-right", "bottom-left", "top-right", "top-left", "center", "custom"],
    index=0,
    help="Choose where to place the image on the PDF"
)

use_scale = st.sidebar.checkbox("Use Scale Factor", value=False)

if use_scale:
    scale_factor = st.sidebar.slider("Scale Factor (%)", 10, 200, 50) / 100
    img_width = None
    img_height = None
else:
    col1, col2 = st.sidebar.columns(2)
    img_width = col1.number_input("Width (pts)", value=200, min_value=10)
    img_height = col2.number_input("Height (pts)", value=0, min_value=0)
    img_height = None if img_height == 0 else img_height
    scale_factor = 1.0

margin_x = st.sidebar.slider("Horizontal Margin", 0, 100, 20)
margin_y = st.sidebar.slider("Vertical Margin", 0, 100, 20)

if position == "custom":
    custom_x = st.sidebar.number_input("Custom X Position", value=50)
    custom_y = st.sidebar.number_input("Custom Y Position", value=50)
else:
    custom_x = 50
    custom_y = 50

pages_option = st.sidebar.selectbox(
    "Pages to Modify",
    ["All Pages", "First Page Only", "Last Page Only"],
    index=0
)

# File uploaders
st.header("📁 Upload Files")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("PDF Files")
    pdf_files = st.file_uploader(
        "Upload PDF files",
        type=['pdf'],
        accept_multiple_files=True,
        key="pdfs",
        help="Select one or more PDF files from your device"
    )
    if pdf_files:
        st.success(f"✓ {len(pdf_files)} PDF(s) uploaded")

with col2:
    st.subheader("Image File")
    image_file = st.file_uploader(
        "Upload Image (PNG/JPG/JPEG)",
        type=['png', 'jpg', 'jpeg'],
        key="image",
        help="Select an image file to attach to PDFs"
    )
    if image_file:
        st.success("✓ Image uploaded")
        # Show preview with responsive sizing
        img_preview = Image.open(image_file)
        st.image(img_preview, caption="Image Preview", use_column_width=True)
        image_file.seek(0)  # Reset file pointer


def calculate_image_dimensions(img_bytes, img_width, img_height, scale_factor, use_scale):
    """Calculate the final image dimensions based on parameters."""
    img = Image.open(BytesIO(img_bytes))
    original_width, original_height = img.size
    aspect_ratio = original_width / original_height

    if use_scale:
        dpi = img.info.get('dpi', (72, 72))
        final_width = original_width * scale_factor * 72 / dpi[0]
        final_height = original_height * scale_factor * 72 / dpi[1]
    else:
        if img_width and img_height:
            final_width = img_width
            final_height = img_height
        elif img_width:
            final_width = img_width
            final_height = img_width / aspect_ratio
        elif img_height:
            final_height = img_height
            final_width = img_height * aspect_ratio
        else:
            dpi = img.info.get('dpi', (72, 72))
            final_width = original_width * 72 / dpi[0]
            final_height = original_height * 72 / dpi[1]

    return final_width, final_height


def calculate_position(position, page_width, page_height, img_width, img_height, 
                      margin_x, margin_y, custom_x, custom_y):
    """Calculate X, Y coordinates based on position preset."""
    positions = {
        "top-left": (margin_x, page_height - img_height - margin_y),
        "top-right": (page_width - img_width - margin_x, page_height - img_height - margin_y),
        "bottom-left": (margin_x, margin_y),
        "bottom-right": (page_width - img_width - margin_x, margin_y),
        "center": ((page_width - img_width) / 2, (page_height - img_height) / 2),
        "custom": (custom_x, custom_y)
    }

    return positions.get(position.lower(), positions["bottom-right"])


def create_image_overlay(img_bytes, page_width, page_height, params):
    """Create a PDF overlay with the image."""
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Calculate image dimensions
    img_width, img_height = calculate_image_dimensions(
        img_bytes,
        params['img_width'],
        params['img_height'],
        params['scale_factor'],
        params['use_scale']
    )

    # Calculate position
    x, y = calculate_position(
        params['position'],
        page_width,
        page_height,
        img_width,
        img_height,
        params['margin_x'],
        params['margin_y'],
        params['custom_x'],
        params['custom_y']
    )

    # Draw image from bytes
    img_reader = ImageReader(BytesIO(img_bytes))
    can.drawImage(img_reader, x, y, width=img_width, height=img_height, mask='auto')
    can.save()

    packet.seek(0)
    return PdfReader(packet)


def process_pdf(pdf_bytes, img_bytes, params, filename):
    """Process a single PDF file and attach the image."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter()

        total_pages = len(reader.pages)

        for page_num in range(total_pages):
            page = reader.pages[page_num]

            # Check if this page should be modified
            should_modify = False
            if params['pages'] == "all":
                should_modify = True
            elif params['pages'] == "first" and page_num == 0:
                should_modify = True
            elif params['pages'] == "last" and page_num == total_pages - 1:
                should_modify = True

            if should_modify:
                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                # Create image overlay
                overlay = create_image_overlay(img_bytes, page_width, page_height, params)

                # Merge overlay with original page
                page.merge_page(overlay.pages[0])

            writer.add_page(page)

        # Write to bytes
        output = BytesIO()
        writer.write(output)
        output.seek(0)

        return output.getvalue(), None
    except Exception as e:
        return None, str(e)


# Process button
if st.button("🚀 Process PDFs", type="primary", use_container_width=True):
    if not pdf_files:
        st.error("❌ Please upload at least one PDF file")
    elif not image_file:
        st.error("❌ Please upload an image file")
    else:
        # Read image once
        image_bytes = image_file.read()

        # Map pages option to internal format
        pages_map = {
            "All Pages": "all",
            "First Page Only": "first",
            "Last Page Only": "last"
        }

        # Prepare parameters
        params = {
            'img_width': img_width,
            'img_height': img_height,
            'scale_factor': scale_factor,
            'use_scale': use_scale,
            'position': position,
            'margin_x': margin_x,
            'margin_y': margin_y,
            'custom_x': custom_x,
            'custom_y': custom_y,
            'pages': pages_map[pages_option]
        }

        st.header("📥 Download Processed PDFs")

        processed_files = []

        # Process each PDF
        progress_bar = st.progress(0)
        for idx, pdf_file in enumerate(pdf_files):
            with st.spinner(f"Processing: {pdf_file.name}..."):
                pdf_bytes = pdf_file.read()
                result_bytes, error = process_pdf(pdf_bytes, image_bytes, params, pdf_file.name)

                if result_bytes:
                    st.success(f"✓ {pdf_file.name} processed successfully")
                    processed_files.append((pdf_file.name, result_bytes))
                else:
                    st.error(f"✗ Error processing {pdf_file.name}: {error}")

                progress_bar.progress((idx + 1) / len(pdf_files))

        # Provide downloads
        if processed_files:
            st.success(f"🎉 Successfully processed {len(processed_files)} PDF(s)")

            # Single file download
            if len(processed_files) == 1:
                filename = processed_files[0][0].replace('.pdf', '_with_image.pdf')
                st.download_button(
                    label=f"⬇️ Download {filename}",
                    data=processed_files[0][1],
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                # Multiple files - create ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, file_bytes in processed_files:
                        new_filename = filename.replace('.pdf', '_with_image.pdf')
                        zip_file.writestr(new_filename, file_bytes)

                zip_buffer.seek(0)

                st.download_button(
                    label=f"⬇️ Download All ({len(processed_files)} PDFs as ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="processed_pdfs.zip",
                    mime="application/zip",
                    use_container_width=True
                )

# Footer
st.markdown("---")
st.markdown("🌐 **Fully Compatible:** Desktop Chrome/Safari | iPad Safari/Chrome | iPhone Safari/Chrome")
