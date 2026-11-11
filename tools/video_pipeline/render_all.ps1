# render_all.ps1 — aerender comps -> AVI lossless -> H.264 crf16 mp4.
#
# Usage (from anywhere):
#   powershell -File G:\crosscorr\tools\video_pipeline\render_all.ps1
#   powershell -File ... -Comps "intro,3,5"     # subset re-render
#
# -Comps items: integers 1..8 (CrossCorr_slide-N -> slide-N.mp4) and/or the
# literal "intro" (CrossCorr_intro -> intro.mp4). Default: all 9.
#
# Prerequisites (checked before starting, abort if missing):
#   - media/video_bg/crosscorr_full.aep   (built by build_full.jsx)
#   - media/video_bg/slide-N_1080.mp4     (8 files, upscale_bg.py)
#   - media/ae_layers/...                 (layer PNGs)
#
# Per comp: aerender -OMtemplate Lossless -> slide-N.avi, VERIFY the
# container is really AVI (gotcha: without -OMtemplate aerender silently
# writes 15 Mbps mp4 per the default output module), then ffmpeg crf 16
# -> slide-N.mp4 and DELETE the AVI master.
#
# Sequential by design: one AE render at a time (GPU/RAM rule).
# Exit code != 0 on first failure; per-comp logs in media/video_final/.

param(
    [string]$Comps = "intro,1,2,3,4,5,6,7,8"
)

$ErrorActionPreference = "Stop"
$AERENDER = "C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\aerender.exe"
$AEP = "G:\crosscorr\media\video_bg\crosscorr_full.aep"
$BG = "G:\crosscorr\media\video_bg"
$OUT = "G:\crosscorr\media\video_final"
$FFPROBE = "C:\Users\FelixR\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
$FFMPEG = "C:\Users\FelixR\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"

function Fail($msg) {
    Write-Host "FAIL: $msg" -ForegroundColor Red
    exit 1
}

# ---- preflight -----------------------------------------------------------
if (-not (Test-Path $AERENDER)) { Fail "aerender.exe not found: $AERENDER" }
if (-not (Test-Path $AEP)) { Fail "project copy missing: $AEP (run build_full.jsx first)" }
New-Item -ItemType Directory -Force -Path $OUT | Out-Null

$items = @()
foreach ($tok in ($Comps -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
    if ($tok -eq "intro") {
        $items += @{ Token = "intro"; Comp = "CrossCorr_intro"; Base = "intro" }
    } elseif ($tok -match "^[1-8]$") {
        $items += @{ Token = $tok; Comp = "CrossCorr_slide-$tok"; Base = "slide-$tok" }
    } else {
        Fail "unknown comp token '$tok' (expected 1..8 or 'intro')"
    }
}
if ($items.Count -eq 0) { Fail "empty -Comps list" }

$missing = @()
1..8 | ForEach-Object {
    if (-not (Test-Path "$BG\slide-$($_)_1080.mp4")) { $missing += "slide-$($_)_1080.mp4" }
}
if ($missing.Count -gt 0) { Fail ("missing upscaled backgrounds: " + ($missing -join ", ")) }

Write-Host "preflight OK: project + 8 upscaled backgrounds present; comps: $($items.Token -join ',')"

# ---- render loop ---------------------------------------------------------
foreach ($it in $items) {
    $comp = $it.Comp
    $base = $it.Base
    $avi = "$OUT\$base.avi"
    $mp4 = "$OUT\$base.mp4"
    $log = "$OUT\render_$base.log"

    Write-Host "=== $comp ===" -ForegroundColor Cyan

    if (Test-Path $avi) { Remove-Item $avi -Force }

    & $AERENDER -project $AEP -comp $comp -output $avi -OMtemplate Lossless 2>&1 |
        Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) { Fail "aerender exit=$LASTEXITCODE for $comp (log: $log)" }
    if (-not (Test-Path $avi)) { Fail "no AVI produced for $comp (log: $log)" }

    # verify really AVI container (default output module would give mp4)
    $fmt = & $FFPROBE -v error -show_entries format=format_name -of csv=p=0 $avi
    if ($fmt -notlike "*avi*") { Fail ("$comp container is '$fmt', expected avi (check -OMtemplate Lossless)") }
    $codec = & $FFPROBE -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 $avi
    Write-Host "  AVI ok (format=$fmt, codec=$codec)"

    # encode crf16
    if (Test-Path $mp4) { Remove-Item $mp4 -Force }
    & $FFMPEG -y -loglevel error -i $avi -c:v libx264 -crf 16 -pix_fmt yuv420p $mp4
    if ($LASTEXITCODE -ne 0) { Fail "ffmpeg exit=$LASTEXITCODE for $base" }

    $probe = & $FFPROBE -v error -select_streams v:0 `
        -show_entries stream=width,height,nb_frames,r_frame_rate `
        -show_entries format=duration -of csv=p=0 $mp4
    Write-Host "  mp4: $probe"

    Remove-Item $avi -Force   # delete lossless master (README step 7)
    Write-Host "  done -> $mp4"
}

Write-Host "RENDER DONE: $($items.Count)/$($items.Count)" -ForegroundColor Green
