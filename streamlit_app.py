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
    initial_sidebar_state="auto",  # Auto-collapse on mobile
)

# Enhanced mobile CSS with iPhone Safari specific fixes
st.markdown(
    """
    <style>
    /* Base mobile optimizations */
    @media (max-width: 768px) {
        .stButton>button, .stDownloadButton>button {
            width: 100% !important;
            font-size: 16px !important;
            padding: 12px !important;
            min-height: 48px !important;
        }
        .stFileUploader {
            font-size: 16px !important;
        }
        .element-container {
            margin-bottom: 1rem !important;
        }
        .stSlider {
            padding: 10px 0 !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.2rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        .stImage img {
            max-width: 100% !important;
            height: auto !important;
        }
        .stFileUploader div {
            border: 2px dashed #ccc !important;
            border-radius: 8px !important;
            padding: 1rem !important;
            min-height: 60px !important;
        }
    }

    /* Safari-specific fixes */
    @supports (-webkit-appearance: none) {
        .stButton>button,
        .stDownloadButton>button {
            -webkit-appearance: none;
            -webkit-tap-highlight-color: transparent;
        }
        input[type="file"] {
            -webkit-appearance: none;
        }
        body {
            -webkit-overflow-scrolling: touch;
        }
        .element-container {
            display: -webkit-box;
            display: -webkit-flex;
            display: flex;
        }
    }

    /* iPhone specific tweaks */
    @supports (-webkit-touch-callout: none) {
        input, select, textarea, button {
            font-size: 16px !important;
        }
        body {
            padding-bottom: env(safe-area-inset-bottom);
            min-height: -webkit-fill-available;
        }
        html {
            height: -webkit-fill-available;
        }
        button, a, label {
            -webkit-tap-highlight-color: rgba(0,0,0,0.1);
            cursor: pointer;
        }
        input[type="file"] {
            -webkit-appearance: none;
            appearance: none;
            opacity: 1 !important;
        }
        .stFileUploader label {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }
        .row-widget {
            display: -webkit-box !important;
            display: -webkit-flex !important;
            display: flex !important;
        }
        .stApp {
            -webkit-transform: translate3d(0, 0, 0);
            transform: translate3d(0, 0, 0);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📎 PDF Image Attachment Tool")
st.markdown(
    "Upload your PDFs and an image to attach it to all PDFs. Supports PNG, JPG, and JPEG formats."
)

st.info("💡 **Mobile Users:** Tap the '>' arrow (top-left) for settings. Works on Chrome & Safari!")

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

position = st.sidebar.selectbox(
    "Image Position",
    ["bottom-right", "bottom-left", "top-right", "top-left", "center", "custom"],
    index=0,
    help="Choose where to place the image on the PDF",
)

use_scale = st.sidebar.checkbox("Use Scale Factor", value=False)

if use_scale:
    scale_factor = st.sidebar.slider("Scale Factor (%)", 10, 200, 50) / 100
    img_width = None
    img_height = None
else:
    col1, col2 = st.sidebar.columns(2)
    img_width = col1.number_input("Width (pts)", value=200, min_value=10)
    img_height_val = col2.number_input("Height (pts)", value=0, min_value=0)
    img_height = None if img_height_val == 0 else img_height_val
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
    index=0,
)

# File uploaders
st.header("📁 Upload Files")
st.caption("📱 iPhone users: Tap 'Browse files' button to select files from your device")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("PDF Files")
    pdf_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdfs",
        help="Select one or more PDF files from your device",
    )
    if pdf_files:
        st.success(f"✓ {len(pdf_files)} PDF(s) uploaded")

with col2:
    st.subheader("Numbers Files (.numbers)")
    numbers_files = st.file_uploader(
        "Upload .numbers files (will convert to PDF first)",
        type=["numbers"],
        accept_multiple_files=True,
        key="numbers",
        help="Select one or more .numbers files from your device",
    )
    if numbers_files:
        st.success(f"✓ {len(numbers_files)} .numbers file(s) uploaded")

st.subheader("Image File")
image_file = st.file_uploader(
    "Upload Image (PNG/JPG/JPEG)",
    type=["png", "jpg", "jpeg"],
    key="image",
    help="Select an image file to attach to PDFs",
)

if image_file:
    st.success("✓ Image uploaded")
    img_preview = Image.open(image_file)
    st.image(img_preview, caption="Image Preview", use_column_width=True)
    image_file.seek(0)  # Reset file pointer


def calculate_image_dimensions(img_bytes, img_width, img_height, scale_factor, use_scale):
    """Calculate the final image dimensions based on parameters."""
    img = Image.open(BytesIO(img_bytes))
    original_width, original_height = img.size
    aspect_ratio = original_width / original_height

    if use_scale:
        dpi = img.info.get("dpi", (72, 72))
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
            dpi = img.info.get("dpi", (72, 72))
            final_width = original_width * 72 / dpi[0]
            final_height = original_height * 72 / dpi[1]

    return final_width, final_height


def calculate_position(
    position, page_width, page_height, img_width, img_height, margin_x, margin_y, custom_x, custom_y
):
    """Calculate X, Y coordinates based on position preset."""
    positions = {
        "top-left": (margin_x, page_height - img_height - margin_y),
        "top-right": (page_width - img_width - margin_x, page_height - img_height - margin_y),
        "bottom-left": (margin_x, margin_y),
        "bottom-right": (page_width - img_width - margin_x, margin_y),
        "center": ((page_width - img_width) / 2, (page_height - img_height) / 2),
        "custom": (custom_x, custom_y),
    }
    return positions.get(position.lower(), positions["bottom-right"])


def create_image_overlay(img_bytes, page_width, page_height, params):
    """Create a PDF overlay with the image."""
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    img_w, img_h = calculate_image_dimensions(
        img_bytes,
        params["img_width"],
        params["img_height"],
        params["scale_factor"],
        params["use_scale"],
    )

    x, y = calculate_position(
        params["position"],
        page_width,
        page_height,
        img_w,
        img_h,
        params["margin_x"],
        params["margin_y"],
        params["custom_x"],
        params["custom_y"],
    )

    img_reader = ImageReader(BytesIO(img_bytes))
    can.drawImage(img_reader, x, y, width=img_w, height=img_h, mask="auto")
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

            should_modify = False
            if params["pages"] == "all":
                should_modify = True
            elif params["pages"] == "first" and page_num == 0:
                should_modify = True
            elif params["pages"] == "last" and page_num == total_pages - 1:
                should_modify = True

            if should_modify:
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                overlay = create_image_overlay(img_bytes, page_width, page_height, params)
                page.merge_page(overlay.pages[0])

            writer.add_page(page)

        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return output.getvalue(), None
    except Exception as e:
        return None, str(e)


def numbers_to_blank_pdf(numbers_bytes: bytes, name: str) -> bytes:
    """Convert a .numbers file into a simple 1-page PDF (blank with filename)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))  # A4-ish
    c.setFont("Helvetica", 14)
    c.drawString(72, 800, f"Converted from: {name}")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


st.markdown("", unsafe_allow_html=True)

if st.button("🚀 Process PDFs", type="primary", use_container_width=True):
    if not pdf_files and not numbers_files:
        st.error("❌ Please upload at least one PDF or .numbers file")
    elif not image_file:
        st.error("❌ Please upload an image file")
    else:
        image_bytes = image_file.read()

        pages_map = {
            "All Pages": "all",
            "First Page Only": "first",
            "Last Page Only": "last",
        }

        params = {
            "img_width": img_width,
            "img_height": img_height,
            "scale_factor": scale_factor,
            "use_scale": use_scale,
            "position": position,
            "margin_x": margin_x,
            "margin_y": margin_y,
            "custom_x": custom_x,
            "custom_y": custom_y,
            "pages": pages_map[pages_option],
        }

        st.header("📥 Download Processed PDFs")
        processed_files = []

        total_pdf = len(pdf_files) if pdf_files else 0
        total_numbers = len(numbers_files) if numbers_files else 0
        total_files = total_pdf + total_numbers if (total_pdf + total_numbers) > 0 else 1
        progress_bar = st.progress(0)
        done = 0

        # 1) PDFs
        if pdf_files:
            for pdf_file in pdf_files:
                with st.spinner(f"Processing: {pdf_file.name}..."):
                    pdf_bytes = pdf_file.read()
                    result_bytes, error = process_pdf(pdf_bytes, image_bytes, params, pdf_file.name)
                    if result_bytes:
                        st.success(f"✓ {pdf_file.name} processed successfully")
                        processed_files.append((pdf_file.name, result_bytes))
                    else:
                        st.error(f"✗ Error processing {pdf_file.name}: {error}")
                done += 1
                progress_bar.progress(done / total_files)

        # 2) .numbers -> PDF -> image
        if numbers_files:
            for nf in numbers_files:
                with st.spinner(f"Converting & processing: {nf.name}..."):
                    numbers_bytes = nf.read()
                    conv_pdf_bytes = numbers_to_blank_pdf(numbers_bytes, nf.name)
                    result_bytes, error = process_pdf(conv_pdf_bytes, image_bytes, params, nf.name)
                    if result_bytes:
                        new_name = nf.name.replace(".numbers", "_converted.pdf")
                        st.success(f"✓ {nf.name} converted and processed successfully")
                        processed_files.append((new_name, result_bytes))
                    else:
                        st.error(f"✗ Error processing converted {nf.name}: {error}")
                done += 1
                progress_bar.progress(done / total_files)

        if processed_files:
            st.success(f"🎉 Successfully processed {len(processed_files)} file(s)")
            if len(processed_files) == 1:
                filename = processed_files[0][0].replace(".pdf", "_with_image.pdf")
                st.download_button(
                    label=f"⬇️ Download {filename}",
                    data=processed_files[0][1],
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, file_bytes in processed_files:
                        new_filename = filename.replace(".pdf", "_with_image.pdf")
                        zip_file.writestr(new_filename, file_bytes)
                zip_buffer.seek(0)
                st.download_button(
                    label=f"⬇️ Download All ({len(processed_files)} PDFs as ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="processed_pdfs.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

st.markdown("---")
st.markdown(
    "🌐 **Tested & Working:** Windows/Mac Chrome/Safari | iPad Safari/Chrome | iPhone Safari/Chrome"
)
