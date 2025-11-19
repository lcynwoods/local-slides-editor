# Build Scripts for Slides Editor

This directory contains scripts for building the application into a Windows executable.

## Prerequisites

1. Install dependencies:

   ```powershell
   conda activate <your-env>
   pip install -r requirements.txt
   ```

2. Install PyInstaller (or Nuitka):
   ```powershell
   pip install pyinstaller
   ```

## Building with PyInstaller

### Quick Build

```powershell
python build_scripts/build_pyinstaller.ps1
```

Or manually:

```powershell
pyinstaller slides_editor.spec
```

The executable will be created in `dist/SlidesEditor.exe`

### Configuration

Edit `slides_editor.spec` to customize:

- **icon**: Path to `.ico` file for application icon
- **console**: Set to `True` for debugging (shows console window)
- **datas**: Additional files to bundle
- **hiddenimports**: Additional modules to include

## Building with Nuitka (Alternative)

Nuitka produces faster executables but takes longer to build:

```powershell
python -m nuitka --standalone --onefile ^
    --enable-plugin=tk-inter ^
    --windows-disable-console ^
    --output-dir=dist ^
    --output-filename=SlidesEditor.exe ^
    slides_editor.py
```

## Testing the Executable

1. Navigate to the `dist` folder
2. Run `SlidesEditor.exe`
3. The application should open in a native window

## Troubleshooting

### Missing Dependencies

If the executable fails to start:

- Check the `hiddenimports` list in `slides_editor.spec`
- Add any missing modules reported in error messages

### API Token

The API token is NOT compiled into the executable. Users will need to:

1. Launch the application
2. Go to Advanced page
3. Enter their Slides.com API token

### Large File Size

To reduce executable size:

- Use `upx=True` in the spec file (already enabled)
- Exclude unused modules in the `excludes` list
- Consider using Nuitka with optimization flags

### Console Window Appears

Set `console=False` in the spec file to hide the console window for GUI apps.

## Distribution

The final executable (`SlidesEditor.exe`) can be distributed to colleagues:

- No Python installation required
- All dependencies bundled
- Users just need to configure their session folder and API token

## Notes

- The build may take 2-5 minutes depending on system
- First run of the built executable may be slow as NiceGUI initializes
- The executable size is typically 50-100MB due to bundled dependencies
