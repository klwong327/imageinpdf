import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image
import zipfile
import pandas as pd  # New import for .numbers conversion
import tempfile  # New import for temp files
import os  # New import for path handling
import xml.etree.ElementTree as ET  # New import for .numbers XML parsing

st.set_page_config(
    page_title="PDF Image Attacher",
    page_icon="📎",
    layout="wide",
    initial_sidebar_state="auto"  # Auto-collapse on mobile
)

# [Existing CSS styles unchanged - omitted for brevity]

st.title("📎 PDF Image Attachment Tool")
st.markdown("""
Upload your PDFs (or .numbers files - they'll auto-convert to PDF), and an image, 
then download modified PDFs with the image attached. Supports PNG, JPG, JPEG image formats.
""")

st.info("👈 Mobile Users: Tap the arrow top-left for settings. Works on Chrome & Safari!")

# [Existing sidebar configuration unchanged - omitted for brevity]

st.header("📁 Upload Files")

st.caption("💡 iPhone users: Tap 'Browse files' button to select files from your device.")

col1, col2 = st.columns([1, 1])

# Existing PDF uploader
with col1:
    st.subheader("📄 PDF Files")
    pdf_files = st.file_uploader(
        "Upload PDF files", 
        type=['pdf'], 
        accept_multiple_files=True, 
        key="pdfs",
        help="Select one or more PDF files from your device"
    )
    if pdf_files:
        st.success(f"✅ {len(pdf_files)} PDF(s) uploaded")

# New .numbers uploader and converter
with col2:
    st.subheader("📊 Numbers Files (.numbers)")
    numbers_files = st.file_uploader(
        "Upload .numbers files (auto-converts to PDF)", 
        type=['numbers'], 
        accept_multiple_files=True, 
        key="numbers",
        help="Select .numbers files to convert to PDF first, then attach image"
    )
    if numbers_files:
        st.success(f"✅ {len(numbers_files)} .numbers file(s) uploaded - will convert to PDF")

# Existing image uploader
st.subheader("🖼️ Image File")
image_file = st.file_uploader(
    "Upload Image (PNG/JPG/JPEG)", 
    type=['png', 'jpg', 'jpeg'], 
    key="image",
    help="Select an image file to attach to PDFs"
)
if image_file:
    st.success("✅ Image uploaded")
    img_preview = Image.open(image_file)
    st.image(img_preview, caption="Image Preview", use_column_width=True)
    image_file.seek(0)  # Reset file pointer

st.markdown("---")  # Spacer

# New function: Convert .numbers to PDF
@st.cache_data
def convert_numbers_to_pdf(numbers_bytes, original_name):
    """Convert Apple .numbers file (ZIP) to PDF using sheet data."""
    try:
        with zipfile.ZipFile(BytesIO(numbers_bytes)) as z:
            # Find index.xml.gz or content.xml (common in .numbers ZIP)
            xml_files = [f for f in z.namelist() if 'Index/index.xml' in f or 'sheet.xml' in f or 'content.xml' in f]
            if not xml_files:
                return None, "No sheet data found in .numbers file"
            
            # Extract first relevant XML
            xml_data = z.read(xml_files[0])
            root = ET.fromstring(xml_data)
            
            # Simple parsing: extract table data (basic cells - extend for complex sheets)
            tables = []
            for table in root.findall('.//table'):
                rows = []
                for row in table.findall('.//row'):
                    cells = [cell.text or '' for cell in row.findall('cell')]
                    rows.append(cells)
                if rows:
                    df = pd.DataFrame(rows[1:], columns=rows[0] if rows[0] else None)  # Header row
                    tables.append(df)
            
            if not tables:
                return None, "No table data extracted from sheets"
            
            # Create PDF with reportlab (first table for simplicity; extend for multi-sheet)
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(800, 600))
            width, height = 800, 600
            y_pos = height - 50
            
            for df in tables[:1]:  # First table
                for _, row in df.iterrows():
                    can.drawString(50, y_pos, str(row.to_dict()))
                    y_pos -= 20
                    if y_pos < 50:
                        can.showPage()
                        can.setFont("Helvetica", 10)
                        y_pos = height - 50
            can.save()
            packet.seek(0)
            
            return packet.getvalue(), None
    except Exception as e:
        return None, str(e)

# [Existing helper functions unchanged: calculate_image_dimensions, calculate_position, create_image_overlay, process_pdf]

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 Process PDFs", type="primary", use_container_width=True):
    if not pdf_files and not numbers_files:
        st.error("❌ Please upload at least one PDF or .numbers file")
    elif not image_file:
        st.error("❌ Please upload an image file")
    else:
        image_bytes = image_file.read()
        
        # Map pages option (existing)
        pages_map = {
            "All Pages": "all",
            "First Page Only": "first", 
            "Last Page Only": "last"
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
            "pages": pages_map[pages_option]
        }
        
        processed_files = []
        progress_bar = st.progress(0)
        
        # Process original PDFs (existing)
        for idx, pdf_file in enumerate(pdf_files or []):
            with st.spinner(f"Processing {pdf_file.name}..."):
                pdf_bytes = pdf_file.read()
                result_bytes, error = process_pdf(pdf_bytes, image_bytes, params, pdf_file.name)
                if result_bytes:
                    st.success(f"✅ {pdf_file.name} processed successfully")
                    processed_files.append((pdf_file.name, result_bytes))
                else:
                    st.error(f"❌ Error processing {pdf_file.name}: {error}")
            progress_bar.progress((idx + 1) / max(1, len(pdf_files)))
        
        # New: Process .numbers files - convert then attach image
        numbers_count = len(numbers_files or [])
        for idx, numbers_file in enumerate(numbers_files or []):
            with st.spinner(f"Converting & processing {numbers_file.name}..."):
                numbers_bytes = numbers_file.read()
                conv_bytes, conv_error = convert_numbers_to_pdf(numbers_bytes, numbers_file.name)
                if conv_bytes:
                    # Now process the converted PDF with image
                    result_bytes, error = process_pdf(conv_bytes, image_bytes, params, numbers_file.name)
                    if result_bytes:
                        new_name = numbers_file.name.replace('.numbers', '_converted.pdf')
                        st.success(f"✅ {numbers_file.name} → PDF processed successfully")
                        processed_files.append((new_name, result_bytes))
                    else:
                        st.error(f"❌ Error attaching image to {numbers_file.name}: {error}")
                else:
                    st.error(f"❌ Conversion failed for {numbers_file.name}: {conv_error}")
            progress_bar.progress(1 - (numbers_count - idx - 1) / max(1, numbers_count))
        
        if processed_files:
            st.success(f"🎉 Successfully processed {len(processed_files)} file(s)!")
            
            st.header("⬇️ Download Processed PDFs")
            
            if len(processed_files) == 1:
                filename = processed_files[0][0].replace('.pdf', '_withimage.pdf')
                st.download_button(
                    label=f"📥 Download {filename}",
                    data=processed_files[0][1],
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                # ZIP multiple (existing logic)
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for orig_name, file_bytes in processed_files:
                        new_filename = orig_name.replace('.pdf', '_withimage.pdf')
                        zip_file.writestr(new_filename, file_bytes)
                zip_buffer.seek(0)
                st.download_button(
                    label=f"📦 Download All ({len(processed_files)} PDFs) as ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="processed_pdfs.zip",
                    mime="application/zip",
                    use_container_width=True
                )

st.markdown("---")
st.markdown("✅ **Tested & Working:** Windows/Mac, Chrome/Safari, iPad Safari/Chrome, iPhone Safari/Chrome")[file:1]
