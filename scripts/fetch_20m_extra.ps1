# Дополнить 20m за 4 месяца
$months = @(
    @{Year=2024; Month=11; Days=30},
    @{Year=2024; Month=12; Days=31},
    @{Year=2025; Month=2;  Days=28},
    @{Year=2025; Month=3;  Days=31}
)

$total = 0
$skipped = 0
$downloaded = 0

foreach ($m in $months) {
    for ($d = 1; $d -le $m.Days; $d++) {
        $total++
        $date = "{0}-{1:D2}-{2:D2}" -f $m.Year, $m.Month, $d

        $pattern = "wspr_hourly_${date}_20m.csv"
        $existing = Get-ChildItem "data\raw\wspr\" -Filter $pattern -ErrorAction SilentlyContinue

        if ($existing) {
            Write-Host "[$total] [SKIP] $date (already exists)"
            $skipped++
            continue
        }

        Write-Host "[$total] [FETCH] $date (20m)"
        python data/scripts/download_wspr.py --date $date --band 20m --mode hourly

        if ($LASTEXITCODE -eq 0) {
            $downloaded++
        } else {
            Write-Host "[$total] [FAIL] $date"
        }

        Start-Sleep -Seconds 1
    }
}

Write-Host ""
Write-Host "=== TOTAL ==="
Write-Host "Total: $total"
Write-Host "Downloaded: $downloaded"
Write-Host "Skipped (already exists): $skipped"