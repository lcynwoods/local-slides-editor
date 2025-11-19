# Copilot Instructions for slides_editor

## Project Overview

NiceGUI desktop application for editing reveal.js slide decks via Slides.com API. Serves Plotly HTML files locally and provides workflow automation for uploading/downloading decks with URL post-processing. Targets Windows users with executable packaging via PyInstaller/Nuitka.

## Architecture

### Application Structure

```
slides_editor.py          # Main entry point, NiceGUI app setup, async server lifecycle
app/
  config.py              # Persistent config using appdirs (JSON in user config dir)
  local_server.py        # aiohttp server serving /plots/<file.html> on localhost
  slides_api.py          # Async Slides.com API client (upload/download ZIP, assets)
  ui/                    # NiceGUI page components (home, plots, advanced)
  utils/                 # File ops, ZIP, find/replace for URL transformations
```

### Key Design Patterns

**1. Configuration Persistence**

- Config stored in user AppData via `appdirs.user_config_dir()`
- Properties: `session_folder`, `deck_id`, `slides_api_token`, `local_server_port`
- Auto-save on property setters using Python `@property` decorators

**2. Async Server Integration**

- Local plot server (aiohttp) started on app startup via `app.on_startup()`
- Routes: `/plots/{filename}` serves HTML, `/plots` lists files as JSON
- Server lifecycle tied to NiceGUI app lifecycle

**3. Multi-Page UI with NiceGUI**

- Pages defined as decorated functions: `@ui.page('/')`, `@ui.page('/plots')`
- Shared header/footer across pages
- Page classes (`HomePage`, `PlotsPage`, `AdvancedPage`) encapsulate rendering logic
- UI state updates via `ui.notify()` and label updates

**4. Slides.com API Workflow**

```python
# Upload: ZIP deck → upload via API → store deck_id
# Download: API export → extract ZIP → find/replace URLs → save locally
```

Post-processing converts `https://slides.com/...` URLs back to `http://localhost:8765/plots/...`

## Development Workflow

### Running Locally

```powershell
conda activate slides_editor  # Conda is default env manager
python slides_editor.py       # Launches native window via NiceGUI
```

For auto-reload during development:

```python
# In slides_editor.py, change:
app.run(reload=True)  # instead of native=True
```

### Building Executable

```powershell
# PyInstaller (recommended)
.\build_scripts\build_pyinstaller.ps1

# Nuitka (alternative, faster runtime)
.\build_scripts\build_nuitka.ps1
```

Output: `dist/SlidesEditor.exe` (50-100MB, all dependencies bundled)

### Testing Components

**Local Server**: Navigate to `http://localhost:8765/` while app is running  
**API Connection**: Use "Test Connection" in Advanced page  
**Diagnostics**: Advanced page → Run Diagnostics for full system report

## Code Conventions

### Type Hints & Async

- All public functions use type hints: `def func(path: Path) -> bool:`
- Async functions for API calls and server ops: `async def upload_deck(...)`
- Use `async with SlidesAPI(token) as api:` for API context management

### Path Handling

- Always use `pathlib.Path` for cross-platform compatibility
- Validate paths exist before operations: `if path.exists():`
- Use `Path.rglob()` for recursive file searches

### Error Handling

- UI operations catch exceptions and show via `ui.notify(message, type='negative')`
- Log errors with `logging.getLogger(__name__)` (configured in `slides_editor.py`)
- Custom exception: `SlidesAPIError` for API failures

### NiceGUI Patterns

```python
# Cards for sections
with ui.card().classes('w-full'):
    ui.label('Title').classes('text-h6')
    # content

# Buttons with callbacks
ui.button('Label', on_click=self._handler, icon='icon_name')

# Async dialogs
with ui.dialog() as dialog, ui.card():
    # dialog content
dialog.open()
```

## Critical Implementation Details

### Session Folder Requirements

Must contain:

- `index.html` (validated by `validate_deck_structure()`)
- `plots/` subfolder with `.html` files for local serving

### URL Transformation Logic

- **Upload**: No URL changes (plots referenced as `localhost:8765/plots/file.html`)
- **Download**: Find/replace to convert Slides.com URLs back to localhost
- See `app/utils/find_replace.py::convert_remote_urls_to_local()`

### API Token Security

- Token NOT compiled into executable (loaded from config at runtime)
- Stored in user config directory: `%APPDATA%\lwoods\slides_editor\config.json`
- Password-masked input field in UI

### Packaging Gotchas

- NiceGUI static files must be included: `('venv/Lib/.../nicegui', 'nicegui')`
- Set `console=False` in `.spec` for GUI-only app (no terminal window)
- `hiddenimports` required for dynamic imports: all `app.*` modules

## Common Tasks

### Adding a New UI Page

1. Create `app/ui/newpage.py` with class containing `render()` method
2. Add route in `slides_editor.py`: `@ui.page('/newpage') def newpage(): ...`
3. Add navigation link in header

### Modifying API Endpoints

Edit `app/slides_api.py`. All methods are async. Use `self._request(method, endpoint, ...)` helper.

### Changing Post-Processing Rules

Edit `app/utils/find_replace.py::convert_remote_urls_to_local()` to adjust regex patterns.

### Adding New Config Properties

1. Add property to `config.py` with `@property` getter/setter
2. Call `self.save()` in setter
3. Update `_default_config()` with default value

## Dependencies

- **NiceGUI**: Web UI framework, runs local web server in native window
- **aiohttp**: Async HTTP for plot server and API client
- **pyperclip**: Clipboard for copy-to-clipboard plot URLs
- **appdirs**: Cross-platform config directory paths

Install: `pip install -r requirements.txt`

## Debugging Tips

- Run with `console=True` in development to see print/logging output
- Use Advanced → Diagnostics to check: folder paths, API token status, server status
- Check `%APPDATA%\lwoods\slides_editor\config.json` for persisted settings
- Local server logs at INFO level show all HTTP requests
