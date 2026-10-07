# 15m: Dec 2024 - Mar 2025
$months = @(
    @{Year=2024; Month=12; Days=31},
    @{Year=2025; Month=1;  Days=31},
    @{Year=2025; Month=2;  Days=28},
    @{Year=2025; Month=3;  Days=31}
)

$band = "15m"
$total = 0
$skipped = 0
$downloaded = 0
$failed = 0

foreach ($m in $months) {
    for ($d = 1; $d -le $m.Days; $d++) {
        $total++
        $date = "{0}-{1:D2}-{2:D2}" -f $m.Year, $m.Month, $d
        
        $pattern = "wspr_hourly_${date}_${band}.csv"
        $existing = Get-ChildItem "data\raw\wspr\" -Filter $pattern -ErrorAction SilentlyContinue
        
        if ($existing) {
            Write-Host "[$total] [SKIP] $date $band"
            $skipped++
            continue
        }
        
        Write-Host "[$total] [FETCH] $date $band"
        python data/scripts/download_wspr.py --date $date --band $band --mode hourly
        
        if ($LASTEXITCODE -eq 0) {
            $downloaded++
        } else {
            Write-Host "[$total] [FAIL] $date $band"
            $failed++
        }
        
        Start-Sleep -Seconds 1
    }
}

Write-Host ""
Write-Host "=== TOTAL 15m (Dec 2024 - Mar 2025) ==="
Write-Host "Total: $total"
Write-Host "Downloaded: $downloaded"
Write-Host "Skipped: $skipped"
Write-Host "Failed: $failed"