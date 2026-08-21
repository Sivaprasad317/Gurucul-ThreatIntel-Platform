$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host " Gurucul ThreatIntel Theme Installer" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

$frontend = (Get-Location).Path
$appFile = Join-Path $frontend "src\App.tsx"
$cssFile = Join-Path $frontend "src\App.css"
$publicDir = Join-Path $frontend "public"
$logoTarget = Join-Path $publicDir "gurucul-logo.png"

if (-not (Test-Path $appFile)) {
    throw "Cannot find src\App.tsx. Make sure you are inside the frontend directory."
}

if (-not (Test-Path $cssFile)) {
    throw "Cannot find src\App.css. Make sure you are inside the frontend directory."
}

New-Item -ItemType Directory -Force $publicDir | Out-Null

# ---------------------------------------------------------
# Find downloaded logo
# ---------------------------------------------------------

$logoCandidates = @(
    (Join-Path $HOME "Downloads\gurucul-logo-transparent.png"),
    (Join-Path $HOME "Downloads\gurucul-logo.png"),
    (Join-Path $HOME "Downloads\gurucul-logo-transparent (1).png")
)

$logoSource = $logoCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $logoSource) {
    throw @"
Gurucul logo was not found.

Please download:
gurucul-logo-transparent.png

and put it here:

$HOME\Downloads\gurucul-logo-transparent.png
"@
}

Copy-Item $logoSource $logoTarget -Force

Write-Host "Logo copied to:" -ForegroundColor Green
Write-Host $logoTarget
Write-Host ""

# ---------------------------------------------------------
# Backup existing files
# ---------------------------------------------------------

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

$appBackup = "$appFile.$timestamp.backup"
$cssBackup = "$cssFile.$timestamp.backup"

Copy-Item $appFile $appBackup -Force
Copy-Item $cssFile $cssBackup -Force

Write-Host "Backups created:" -ForegroundColor Green
Write-Host $appBackup
Write-Host $cssBackup
Write-Host ""

# ---------------------------------------------------------
# APP.TSX
# Replace the hard-coded G logo automatically.
# ---------------------------------------------------------

$app = Get-Content $appFile -Raw

$oldSidebarLogo = '<div className="brand-logo">G</div>'

$newSidebarLogo = @'
<img
  src="/gurucul-logo.png"
  alt="Gurucul"
  className="brand-logo-image"
/>
'@

if ($app.Contains($oldSidebarLogo)) {
    $app = $app.Replace(
        $oldSidebarLogo,
        $newSidebarLogo.Trim()
    )

    Write-Host "Sidebar logo replaced." -ForegroundColor Green
}
else {
    Write-Host "Sidebar logo pattern not found. It may already be changed." -ForegroundColor Yellow
}

$oldLoginLogo = '<div className="brand-logo large">G</div>'

$newLoginLogo = @'
<img
  src="/gurucul-logo.png"
  alt="Gurucul"
  className="brand-logo-image large"
/>
'@

if ($app.Contains($oldLoginLogo)) {
    $app = $app.Replace(
        $oldLoginLogo,
        $newLoginLogo.Trim()
    )

    Write-Host "Login logo replaced." -ForegroundColor Green
}
else {
    Write-Host "Login logo pattern not found. It may already be changed." -ForegroundColor Yellow
}

# ---------------------------------------------------------
# Fix the JSX typo if it somehow still exists.
# ---------------------------------------------------------

$app = $app.Replace(
    '<divclassName="rules">',
    '<div className="rules">'
)

# ---------------------------------------------------------
# Matrix color
# Existing matrix has a hard-coded green rgba().
# Change it to purple.
# ---------------------------------------------------------

$app = $app.Replace(
    'rgba(43,220,171,${n?0.08+(n/max)*0.42:0})',
    'rgba(155,77,204,${n?0.08+(n/max)*0.42:0})'
)

Set-Content $appFile $app -Encoding UTF8

Write-Host ""
Write-Host "App.tsx updated." -ForegroundColor Green

# ---------------------------------------------------------
# APP.CSS
# Add complete Gurucul theme overrides.
# ---------------------------------------------------------

$theme = @'

/* =========================================================
   GURUCUl BRAND THEME
   Added by apply-gurucul-theme.ps1
   ========================================================= */

:root {
  --gurucul-purple: #5a008f;
  --gurucul-purple-dark: #39005c;
  --gurucul-purple-deep: #210034;
  --gurucul-purple-light: #9b4dcc;
  --gurucul-magenta: #c15cff;

  --gurucul-bg: #06030b;
  --gurucul-bg-2: #0b0612;

  --gurucul-panel: #0d0816;
  --gurucul-panel-2: #120a1d;

  --gurucul-border: #2d1940;
  --gurucul-border-light: #4b2863;

  --gurucul-text: #f7effb;
  --gurucul-muted: #9d8baa;

  --gurucul-success: #20c997;
  --gurucul-warning: #f5b942;
  --gurucul-danger: #ff5263;
}


/* =========================================================
   GLOBAL
   ========================================================= */

html,
body,
#root {
  min-height: 100%;
}

body {
  background:
    radial-gradient(
      circle at 50% -15%,
      rgba(90, 0, 143, 0.30),
      transparent 42%
    ),
    radial-gradient(
      circle at 100% 100%,
      rgba(90, 0, 143, 0.12),
      transparent 35%
    ),
    linear-gradient(
      180deg,
      #08030d 0%,
      #040207 100%
    ) !important;

  color: var(--gurucul-text) !important;
}


/* =========================================================
   GURUCUl LOGO
   ========================================================= */

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo-image {
  width: 128px;
  height: auto;
  max-height: 42px;
  display: block;
  object-fit: contain;
}

.brand-logo-image.large {
  width: 175px;
  max-height: 55px;
  margin-bottom: 12px;
}


/* =========================================================
   SIDEBAR
   ========================================================= */

.sidebar {
  background:
    linear-gradient(
      180deg,
      #09040f 0%,
      #050208 100%
    ) !important;

  border-right: 1px solid var(--gurucul-border) !important;
}


/* =========================================================
   SIDEBAR BRAND TEXT
   ========================================================= */

.brand b,
.brand-name {
  color: #ffffff !important;
}

.brand span,
.brand-subtitle {
  color: #9b4dcc !important;
}


/* =========================================================
   NAVIGATION
   ========================================================= */

.nav {
  color: #a994b8 !important;
  background: transparent !important;
}

.nav:hover {
  color: #ffffff !important;

  background:
    linear-gradient(
      90deg,
      rgba(90, 0, 143, 0.22),
      rgba(90, 0, 143, 0.05)
    ) !important;
}

.nav.active {
  color: #d99aff !important;

  background:
    linear-gradient(
      90deg,
      rgba(90, 0, 143, 0.42),
      rgba(90, 0, 143, 0.12)
    ) !important;

  border-color: rgba(155, 77, 204, 0.50) !important;

  box-shadow:
    inset 3px 0 0 #9b4dcc,
    0 0 20px rgba(90, 0, 143, 0.10);
}


/* =========================================================
   MAIN AREA
   ========================================================= */

.shell {
  background: transparent !important;
}

.main,
.content {
  background: transparent !important;
}


/* =========================================================
   TOP HEADER
   ========================================================= */

.topbar {
  background:
    rgba(5, 2, 8, 0.94) !important;

  border-bottom: 1px solid var(--gurucul-border) !important;
}


/* =========================================================
   PAGE TITLES
   ========================================================= */

.crumb {
  color: #a95bd1 !important;
}

.page-title h1 {
  color: #ffffff !important;
}

.page-title p {
  color: var(--gurucul-muted) !important;
}


/* =========================================================
   PANELS
   ========================================================= */

.panel {
  background:
    linear-gradient(
      145deg,
      rgba(18, 10, 29, 0.97),
      rgba(8, 4, 13, 0.97)
    ) !important;

  border-color: var(--gurucul-border) !important;

  box-shadow:
    0 10px 40px rgba(0, 0, 0, 0.22);
}

.panel:hover {
  border-color: rgba(155, 77, 204, 0.45) !important;
}

.panel-head {
  border-bottom-color: var(--gurucul-border) !important;
}

.panel-head h2 {
  color: #ffffff !important;
}

.panel-head span {
  color: var(--gurucul-muted) !important;
}


/* =========================================================
   KPI CARDS
   ========================================================= */

.kpi {
  background:
    linear-gradient(
      145deg,
      #11091b,
      #09050f
    ) !important;

  border-color: var(--gurucul-border) !important;
}

.kpi:hover {
  border-color: rgba(155, 77, 204, 0.55) !important;
}

.kpi-icon {
  color: #b65ce5 !important;
}

.kpi strong {
  color: #ffffff !important;
}

.kpi-label {
  color: #927fa0 !important;
}

.kpi span {
  color: #71627b !important;
}


/* =========================================================
   KPI ACCENT BORDERS
   ========================================================= */

.kpi.green,
.kpi.teal,
.kpi.cyan,
.kpi.blue,
.kpi.purple,
.kpi.yellow,
.kpi.red {
  border-left-color: #9b4dcc !important;
}


/* =========================================================
   ACTOR PROFILE HEADER
   ========================================================= */

.actor-hero,
.actor-header,
.profile-header {
  background:
    linear-gradient(
      135deg,
      rgba(65, 0, 100, 0.62),
      rgba(8, 4, 14, 0.96)
    ) !important;

  border-color: var(--gurucul-border-light) !important;
}


/* =========================================================
   BUTTONS
   ========================================================= */

.primary-button,
button.primary-button {
  background:
    linear-gradient(
      135deg,
      #5a008f,
      #7e18b5
    ) !important;

  border-color: #9b4dcc !important;

  color: #ffffff !important;

  box-shadow:
    0 6px 22px rgba(90, 0, 143, 0.22);
}

.primary-button:hover,
button.primary-button:hover {
  background:
    linear-gradient(
      135deg,
      #7411aa,
      #9e2ed2
    ) !important;

  border-color: #c15cff !important;
}


/* =========================================================
   TEXT BUTTON
   ========================================================= */

.text-button {
  color: #c77bea !important;
}

.text-button:hover {
  color: #e4b4ff !important;
}


/* =========================================================
   STATUS DOT
   ========================================================= */

.status-dot {
  background: #20c997 !important;

  box-shadow:
    0 0 10px rgba(32, 201, 151, 0.35);
}


/* =========================================================
   ACTIVE / RANSOMWARE BADGES
   ========================================================= */

.badge.active,
.status-active {
  background: rgba(32, 201, 151, 0.10) !important;
  border-color: rgba(32, 201, 151, 0.40) !important;
  color: #45dfb1 !important;
}

.badge.ransomware,
.status-ransomware {
  background: rgba(245, 185, 66, 0.09) !important;
  border-color: rgba(245, 185, 66, 0.40) !important;
  color: #f6c65b !important;
}


/* =========================================================
   CHARTS
   ========================================================= */

.chart .bar,
.bar {
  fill: #9b4dcc !important;
}

.chart .gridline {
  stroke: #2d1940 !important;
}

.chart text {
  fill: #907d9d !important;
}


/* =========================================================
   RANK BARS
   ========================================================= */

.rank-track {
  background: #21122d !important;
}

.rank-track i {
  background:
    linear-gradient(
      90deg,
      #5a008f,
      #c15cff
    ) !important;

  box-shadow:
    0 0 10px rgba(155, 77, 204, 0.28);
}

.rank-row {
  color: #ffffff !important;
}


/* =========================================================
   COUNTRY MAP
   ========================================================= */

.map-area {
  background:
    radial-gradient(
      circle at center,
      rgba(90, 0, 143, 0.10),
      transparent 65%
    ) !important;
}

.map-dot {
  background: transparent !important;
}

.map-dot span {
  background: #b04ee2 !important;

  box-shadow:
    0 0 12px rgba(176, 78, 226, 0.55);
}


/* =========================================================
   COVERAGE
   ========================================================= */

.coverage-track {
  background: #21122d !important;
}

.coverage-track i {
  background:
    linear-gradient(
      90deg,
      #5a008f,
      #c15cff
    ) !important;
}

.coverage strong {
  color: #d49aef !important;
}


/* =========================================================
   MATRIX
   ========================================================= */

.matrix {
  border-color: var(--gurucul-border) !important;
}

.matrix th {
  background: #160b20 !important;
  color: #b88bca !important;
}

.matrix td {
  border-color: var(--gurucul-border) !important;
}


/* =========================================================
   VICTIM TABLE
   ========================================================= */

.victim-table {
  border-color: var(--gurucul-border) !important;
}

.v-head {
  background: #13091b !important;
  color: #a98bb8 !important;
}

.v-row {
  background: transparent !important;
  color: #ffffff !important;
  border-bottom-color: var(--gurucul-border) !important;
}

.v-row:hover {
  background:
    rgba(90, 0, 143, 0.16) !important;
}


/* =========================================================
   ACTOR CARDS
   ========================================================= */

.actor-card {
  background:
    linear-gradient(
      145deg,
      #12091c,
      #09050f
    ) !important;

  border-color: var(--gurucul-border) !important;
}

.actor-card:hover,
.actor-card.selected {
  border-color: #9b4dcc !important;

  box-shadow:
    0 0 22px rgba(90, 0, 143, 0.15);
}

.actor-card-mark {
  background:
    linear-gradient(
      135deg,
      #5a008f,
      #a334d4
    ) !important;

  color: #ffffff !important;
}


/* =========================================================
   PROFILE EDITOR
   ========================================================= */

.actor-profile-editor {
  border-color: #3d2053 !important;
}

.profile-form label {
  color: #b99bc7 !important;
}


/* =========================================================
   FORMS
   ========================================================= */

input,
select,
textarea {
  background: #0a0510 !important;

  border-color: #321a45 !important;

  color: #ffffff !important;
}

input::placeholder,
textarea::placeholder {
  color: #6f5a7b !important;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #9b4dcc !important;

  box-shadow:
    0 0 0 2px rgba(155, 77, 204, 0.12) !important;
}


/* =========================================================
   REGISTER PANEL
   ========================================================= */

.register-panel {
  background:
    linear-gradient(
      145deg,
      #12091c,
      #09050f
    ) !important;

  border-color: var(--gurucul-border) !important;
}


/* =========================================================
   LOGIN SCREEN
   ========================================================= */

.login {
  background:
    radial-gradient(
      circle at 50% 20%,
      rgba(90, 0, 143, 0.28),
      transparent 38%
    ),
    linear-gradient(
      180deg,
      #08030d,
      #030207
    ) !important;
}

.login-card {
  background:
    linear-gradient(
      145deg,
      rgba(18, 9, 29, 0.98),
      rgba(7, 3, 11, 0.98)
    ) !important;

  border-color: #3b2050 !important;

  box-shadow:
    0 20px 80px rgba(0, 0, 0, 0.45),
    0 0 50px rgba(90, 0, 143, 0.10);
}

.login-card h1 {
  color: #ffffff !important;
}

.login-card p {
  color: #9d8baa !important;
}

.login-card small {
  color: #75647f !important;
}


/* =========================================================
   ERROR
   ========================================================= */

.error-inline {
  background: rgba(255, 82, 99, 0.10) !important;
  border-color: rgba(255, 82, 99, 0.40) !important;
}


/* =========================================================
   DRAWER
   ========================================================= */

.drawer-backdrop {
  background: rgba(0, 0, 0, 0.70) !important;
}

.drawer {
  background:
    linear-gradient(
      180deg,
      #10071a,
      #07030c
    ) !important;

  border-left-color: #3b2050 !important;
}

.drawer-section {
  border-top-color: var(--gurucul-border) !important;
}


/* =========================================================
   DETAIL
   ========================================================= */

.detail {
  border-color: var(--gurucul-border) !important;
}

.detail span {
  color: #816c8d !important;
}

.detail b {
  color: #ffffff !important;
}


/* =========================================================
   COLLECTION
   ========================================================= */

.health-card,
.collection-list {
  background: #0b0611 !important;
  border-color: var(--gurucul-border) !important;
}

.collection-list > div {
  border-bottom-color: var(--gurucul-border) !important;
}


/* =========================================================
   NOTICE
   ========================================================= */

.notice {
  background: rgba(90, 0, 143, 0.13) !important;
  border-color: rgba(155, 77, 204, 0.35) !important;
  color: #d4a1eb !important;
}


/* =========================================================
   LOADING
   ========================================================= */

.loading {
  background: #5a008f !important;
  color: #ffffff !important;
}


/* =========================================================
   SYSTEM RULES
   ========================================================= */

.rules {
  color: #bca7c7 !important;
}

.rules b {
  color: #c15cff !important;
}


/* =========================================================
   EMPTY STATE
   ========================================================= */

.empty {
  color: #806e8b !important;
}


/* =========================================================
   SCROLLBAR
   ========================================================= */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #08040d;
}

::-webkit-scrollbar-thumb {
  background: #39174e;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: #75159d;
}


/* =========================================================
   GURUCUl-STYLE PURPLE GRID / GLOW
   ========================================================= */

.content {
  position: relative;
}

.content::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;

  background-image:
    linear-gradient(
      rgba(155, 77, 204, 0.025) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(155, 77, 204, 0.025) 1px,
      transparent 1px
    );

  background-size: 42px 42px;

  mask-image:
    linear-gradient(
      to bottom,
      black,
      transparent 75%
    );
}

.content > * {
  position: relative;
  z-index: 1;
}


/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 900px) {
  .brand-logo-image {
    width: 110px;
  }

  .brand-logo-image.large {
    width: 150px;
  }
}
'@

Add-Content $cssFile $theme -Encoding UTF8

Write-Host ""
Write-Host "App.css updated." -ForegroundColor Green

# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

$appCheck = Get-Content $appFile -Raw
$cssCheck = Get-Content $cssFile -Raw

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($appCheck.Contains('/gurucul-logo.png')) {
    Write-Host "Logo reference: OK" -ForegroundColor Green
}
else {
    Write-Host "Logo reference: NOT FOUND" -ForegroundColor Red
}

if ($cssCheck.Contains('--gurucul-purple')) {
    Write-Host "Purple theme: OK" -ForegroundColor Green
}
else {
    Write-Host "Purple theme: NOT FOUND" -ForegroundColor Red
}

if ($appCheck.Contains('<divclassName="rules">')) {
    Write-Host "JSX typo still exists!" -ForegroundColor Red
}
else {
    Write-Host "JSX rules typo: fixed" -ForegroundColor Green
}

if (Test-Path $logoTarget) {
    Write-Host "Logo file: OK" -ForegroundColor Green
}
else {
    Write-Host "Logo file: NOT FOUND" -ForegroundColor Red
}

Write-Host ""
Write-Host "Theme installation complete." -ForegroundColor Green
Write-Host ""
Write-Host "Backups are available if you need to restore the previous files." -ForegroundColor Yellow
Write-Host ""