# PDF Image Attacher Web App

A web-based tool to attach PNG images to PDF files.

## Local Testing

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Streamlit Cloud (FREE)

1. Create a GitHub account (if you don't have one)
2. Create a new repository and upload these files:
   - streamlit_app.py
   - requirements.txt
   - README.md

3. Go to https://streamlit.io/cloud
4. Sign in with GitHub
5. Click "New app"
6. Select your repository
7. Set main file path: streamlit_app.py
8. Click "Deploy"

Your app will be live at: https://[your-app-name].streamlit.app

## Deploy to Other Platforms

### Hugging Face Spaces (FREE)
1. Go to https://huggingface.co/spaces
2. Create new Space
3. Select "Streamlit" as SDK
4. Upload files
5. Your app will be live!

### Replit (FREE)
1. Go to https://replit.com
2. Create new Repl
3. Choose "Python" template
4. Upload files
5. Run with: `streamlit run streamlit_app.py --server.port 8080`

## Features

- Upload multiple PDFs at once
- Customize image position (9 presets + custom)
- Adjust image size (fixed dimensions or scale factor)
- Set margins and positioning
- Choose which pages to modify (all, first, last)
- Download individually or as ZIP file
- Preview image before processing
