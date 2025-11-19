# Quick Start Guide - Slides Editor

## 🎯 Goal

Edit reveal.js decks in Slides.com while keeping Plotly charts served locally.

## 📋 Prerequisites

- Python 3.10+ with Conda
- Slides.com account with API access
- A reveal.js deck folder with a `plots/` subfolder

## ⚡ Setup (5 minutes)

### 1. Install Dependencies

```powershell
# Navigate to project
cd slides_editor

# Create/activate conda environment
conda create -n slides_editor python=3.11
conda activate slides_editor

# Install packages
pip install -r requirements.txt
```

### 2. Run Application

```powershell
python slides_editor.py
```

The app will open in a native window.

### 3. Configure Session Folder

1. Click **"Select Folder"** on home page
2. Choose your deck folder (must contain `index.html` and `plots/` subfolder)

### 4. Set Up API Token

1. Go to **Advanced** page
2. Expand **"API Settings"**
3. Paste your Slides.com API token
4. Click **"Save Token"**
5. Click **"Test Connection"** to verify

## 🚀 Workflow

### Upload Deck to Slides.com

1. Home page → **"Upload Base Deck to Slides.com"**
2. Wait for upload (shows deck ID when complete)
3. Click **"Open Deck in Slides.com Editor"**

### Add Plot iframes

1. Go to **Plots** page
2. Click any plot name to copy its iframe code
3. In Slides.com editor, paste the iframe:
   ```html
   <iframe
     src="http://localhost:8765/plots/myplot.html"
     width="100%"
     height="500"
   ></iframe>
   ```
4. Adjust width/height as needed

### Download Edited Deck

1. After editing in Slides.com, save your deck
2. Return to app → Home page
3. Click **"Download Edited Deck"**
4. Edited version saved in your session folder with timestamp

## 🔍 Troubleshooting

### "No plots folder configured"

- Ensure your session folder has a `plots/` subfolder
- Plots must be `.html` files

### "API connection failed"

- Verify API token is correct
- Check internet connection
- Use Advanced → Test Connection

### Plots don't load in Slides.com preview

- This is expected! Plots use localhost URLs
- Keep the app running while editing
- Plots will work in downloaded deck

### Want to create new deck instead of updating?

- Advanced page → **"Force Re-upload Deck (Create New)"**
- Or manually click **"Clear Deck ID"**

## 💡 Tips

- **Keep app running** while editing in Slides.com (serves plots)
- **Use search** on Plots page to find specific charts
- **Check diagnostics** (Advanced page) if something's wrong
- **Session folder persists** - no need to re-select each time

## 📦 Distribution

### Build Executable

```powershell
.\build_scripts\build_pyinstaller.ps1
```

Share `dist/SlidesEditor.exe` with colleagues - no Python needed!

## 🆘 Need Help?

1. **Run Diagnostics**: Advanced page → "Run Diagnostics"
2. **Check README.md**: Full documentation
3. **View logs**: Run with console mode (set `console=True` in spec)

---

**Ready to start?** Run `python slides_editor.py` and select your folder! 🎉
