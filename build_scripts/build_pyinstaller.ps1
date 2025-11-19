# Build script for slides_editor using PyInstaller
# Usage: .\build_scripts\build_pyinstaller.ps1

Write-Host "Building Slides Editor with PyInstaller..." -ForegroundColor Cyan

# Clean previous builds
if (Test-Path "dist") {
    Write-Host "Cleaning previous build..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "dist"
}

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

# Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
pyinstaller slides_editor.spec

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
