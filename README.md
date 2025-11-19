# 📊 Slides Editor

A desktop application for editing auto-generated reveal.js slide decks using Slides.com integration. Built with NiceGUI for a clean, modern interface and designed to be packaged as a Windows executable for non-technical users.

## ✨ Features

### 1. **Persistent Session Management**

- Select and remember your working folder containing reveal.js decks
- Automatic detection of Plotly HTML files in subfolder
- Configuration persists between sessions
- Quick access to open folders in Windows Explorer

### 2. **Local Plot Server**

- Built-in HTTP server serves Plotly HTML files locally
- Generate iframe URLs with one click
- Copy-to-clipboard functionality for easy embedding in Slides.com
- Search and filter plot files
- Browse plots directly in your browser

### 3. **Slides.com API Integration**

- Upload reveal.js decks as ZIP files to Slides.com
- Automatic deck ID management (update existing or create new)
- Download edited decks back to your local machine
- Post-processing to convert remote URLs back to local references
- API connection testing and diagnostics

### 4. **User-Friendly Interface**

- **Home Page**: Manage session folder and deck operations
- **Plots Page**: Browse and copy plot iframe URLs
- **Advanced Page**: Diagnostics, configuration, and troubleshooting

### 5. **Windows Executable**

- Package as standalone `.exe` for distribution
- No Python installation required for end users
- All dependencies bundled

## 🚀 Quick Start

### For Users (Using Pre-built Executable)

1. **Download** `SlidesEditor.exe`
2. **Run** the application (may show Windows SmartScreen warning on first run)
3. **Configure**:
   - Select your session folder (containing reveal.js deck + plots subfolder)
   - Enter your Slides.com API token in Advanced settings
4. **Use**:
   - Upload your base deck to Slides.com
   - Copy plot iframe URLs from the Plots page
   - Edit in Slides.com editor
   - Download the edited deck

### For Developers

1. **Clone or navigate to the repository**:

   ```powershell
   cd slides_editor
   ```

2. **Set up Conda environment**:

   ```powershell
   conda create -n slides_editor python=3.11
   conda activate slides_editor
   ```

3. **Install dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```powershell
   python slides_editor.py
   ```

## 📁 Project Structure

```
slides_editor/
├── slides_editor.py          # Main application entry point
├── app/
│   ├── config.py             # Configuration management
│   ├── local_server.py       # Local HTTP server for plots
│   ├── slides_api.py         # Slides.com API wrapper
│   ├── ui/
│   │   ├── home.py          # Home page UI
│   │   ├── plots.py         # Plots page UI
│   │   └── advanced.py      # Advanced settings UI
│   └── utils/
│       ├── zip_utils.py     # ZIP operations
│       ├── file_utils.py    # File operations
│       └── find_replace.py  # URL transformation
├── build_scripts/
│   ├── build_pyinstaller.ps1  # PyInstaller build script
│   ├── build_nuitka.ps1       # Nuitka build script
│   └── README.md              # Build documentation
├── requirements.txt          # Python dependencies
└── slides_editor.spec       # PyInstaller configuration
```

## 🔧 Configuration

### Session Folder Structure

Your session folder should be organized as:

```
my_presentation/
├── index.html              # Main reveal.js deck
├── dist/                   # reveal.js assets
├── plugin/                 # reveal.js plugins
└── plots/                  # Plotly HTML files (required)
    ├── chart1.html
    ├── chart2.html
    └── ...
```

### API Token

Get your Slides.com API token:

1. Log in to Slides.com
2. Go to Account Settings → API
3. Generate a new token
4. Copy and paste into Advanced settings in the app

### Local Server Port

Default: `8765`

To change:

1. Go to Advanced page
2. Update Server Port
3. Restart application

## 📝 Workflow

### 1. Initial Setup

- Launch application
- Select session folder containing your reveal.js deck
- Configure Slides.com API token

### 2. Upload Base Deck

- Click "Upload Base Deck to Slides.com"
- Application creates ZIP and uploads via API
- Deck ID is stored for future updates

### 3. Get Plot URLs

- Navigate to Plots page
- Click any plot to copy its iframe URL
- Paste into Slides.com editor:
  ```html
  <iframe
    src="http://localhost:8765/plots/myplot.html"
    width="100%"
    height="500"
  ></iframe>
  ```

### 4. Edit in Slides.com

- Click "Open Deck in Slides.com Editor"
- Make your edits
- Save in Slides.com

### 5. Download Edited Deck

- Click "Download Edited Deck"
- Application downloads, extracts, and post-processes
- Edited deck saved in session folder with timestamp

## 🔨 Building Executable

### PyInstaller (Recommended)

```powershell
# Quick build
.\build_scripts\build_pyinstaller.ps1

# Or manually
pyinstaller slides_editor.spec
```

Output: `dist/SlidesEditor.exe`

### Nuitka (Alternative - Faster Runtime)

```powershell
.\build_scripts\build_nuitka.ps1
```

See `build_scripts/README.md` for detailed build instructions.

## 🧪 Development

### Running in Development Mode

```powershell
python slides_editor.py
```

For auto-reload during development, edit `slides_editor.py`:

```python
app.run(reload=True)  # Instead of native=True
```

### Testing the Local Server

With the app running, navigate to:

- `http://localhost:8765/` - Server status page
- `http://localhost:8765/plots` - List of available plots (JSON)
- `http://localhost:8765/plots/yourfile.html` - Specific plot

### Adding Features

- **UI Components**: Add to `app/ui/`
- **API Methods**: Extend `app/slides_api.py`
- **Utilities**: Add to `app/utils/`
- **Configuration**: Modify `app/config.py`

## 🐛 Troubleshooting

### Application Won't Start

- Check Python version (requires 3.10+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Run in console mode to see errors: Set `console=True` in `slides_editor.spec`

### Plot Server Not Running

- Ensure session folder has a `plots/` subfolder
- Check Advanced page for server status
- Verify port is not in use by another application

### API Upload/Download Fails

- Test API connection in Advanced page
- Verify API token is correct
- Check internet connection
- Review diagnostics output

### Missing Plots

- Ensure plots are in `plots/` subfolder of session folder
- Verify files have `.html` extension
- Click Refresh on Plots page

### Build Issues

- See `build_scripts/README.md`
- Check `hiddenimports` in `slides_editor.spec`
- Try Nuitka if PyInstaller fails

## 📦 Dependencies

- **NiceGUI** - Modern web-based UI framework
- **aiohttp** - Async HTTP server and client
- **pyperclip** - Clipboard operations
- **appdirs** - Cross-platform config directories

See `requirements.txt` for complete list with versions.

## 🔐 Security Notes

- API tokens are stored in user config directory (NOT in executable)
- Local server binds to `localhost` only (not accessible externally)
- All file operations use path validation to prevent directory traversal

## 📄 License

This project is for internal use. Adjust licensing as needed.

## 🤝 Contributing

For developers working on this project:

1. Follow existing code structure
2. Add type hints to all functions
3. Document new features in this README
4. Test builds before committing
5. Update `copilot-instructions.md` for significant changes

## 📞 Support

For issues or questions:

- Check Advanced → Diagnostics for system information
- Review logs in console mode
- See build documentation for packaging issues

---

**Version**: 1.0.0  
**Author**: lwoods  
**Last Updated**: November 2025
