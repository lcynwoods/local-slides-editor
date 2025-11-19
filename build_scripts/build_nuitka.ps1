# Build script for slides_editor using Nuitka
# Usage: .\build_scripts\build_nuitka.ps1

Write-Host "Building Slides Editor with Nuitka..." -ForegroundColor Cyan
Write-Host "Note: This may take 10-20 minutes for the first build" -ForegroundColor Yellow

# Clean previous builds
if (Test-Path "dist") {
    Write-Host "Cleaning previous build..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "dist"
}

# Run Nuitka
Write-Host "Running Nuitka compiler..." -ForegroundColor Cyan

python -m nuitka `
    --standalone `
    --onefile `
    --windows-disable-console `
    --enable-plugin=tk-inter `
    --include-package=app `
    --include-package=nicegui `
    --include-package=aiohttp `
    --output-dir=dist `
    --output-filename=SlidesEditor.exe `
    --assume-yes-for-downloads `
    slides_editor.py

# Check if build was successful
if (Test-Path "dist\SlidesEditor.exe") {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host "Executable location: dist\SlidesEditor.exe" -ForegroundColor Green
    
    # Get file size
    $fileSize = (Get-Item "dist\SlidesEditor.exe").Length / 1MB
    Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
