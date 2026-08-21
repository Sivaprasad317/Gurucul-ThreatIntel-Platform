$ErrorActionPreference = "Stop"

$appFile = ".\src\App.tsx"
$cssFile = ".\src\App.css"

if (-not (Test-Path $appFile)) {
    throw "Cannot find $appFile"
}

if (-not (Test-Path $cssFile)) {
    throw "Cannot find $cssFile"
}

# Backup
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Copy-Item $appFile ".\src\App.tsx.$timestamp.backup" -Force
Copy-Item $cssFile ".\src\App.css.$timestamp.backup" -Force

$app = Get-Content $appFile -Raw

# Replace the image logo with text-only branding.
$app = [regex]::Replace(
    $app,
    '<img\s+src="/gurucul-logo\.png"\s+alt="Gurucul"\s+className="brand-logo-image"\s*/>',
    '<div className="text-brand"><strong>Gurucul</strong><span>THREATINTEL</span></div>'
)

# Replace the large login logo with text-only branding.
$app = [regex]::Replace(
    $app,
    '<img\s+src="/gurucul-logo\.png"\s+alt="Gurucul"\s+className="brand-logo-image large"\s*/>',
    '<div className="text-brand login-brand"><strong>Gurucul</strong><span>THREATINTEL</span></div>'
)

Set-Content $appFile $app -Encoding UTF8

# Add text-brand styling.
$css = Get-Content $cssFile -Raw

$css += @'

/* =========================================================
   TEXT-ONLY GURUCUl BRANDING
   ========================================================= */

.text-brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  line-height: 1;
  min-width: 130px;
}

.text-brand strong {
  color: #ffffff;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.4px;
}

.text-brand span {
  margin-top: 5px;
  color: #9b4dcc;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.8px;
}

.login-brand {
  margin-bottom: 18px;
}

.login-brand strong {
  font-size: 30px;
}

.login-brand span {
  font-size: 11px;
  letter-spacing: 2px;
}


/* Remove any old image-logo sizing */
.brand-logo-image {
  display: none !important;
}
'@

Set-Content $cssFile $css -Encoding UTF8

Write-Host ""
Write-Host "======================================" -ForegroundColor Magenta
Write-Host " Gurucul text branding applied" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Image logo removed." -ForegroundColor Green
Write-Host "Text branding added." -ForegroundColor Green
Write-Host ""
Write-Host "App.tsx backup created." -ForegroundColor Yellow
Write-Host "App.css backup created." -ForegroundColor Yellow
Write-Host ""