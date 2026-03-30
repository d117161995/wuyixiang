$seen = @{}
$end = (Get-Date).AddSeconds(50)
while ((Get-Date) -lt $end) {
    $procs = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match 'cmd\.exe') -and
        -not $seen.ContainsKey($_.ProcessId) -and
        $_.CommandLine -notmatch 'ps-script|trace_proc'
    }
    foreach ($p in $procs) {
        $seen[$p.ProcessId] = $true
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -EA SilentlyContinue
        $gp = if ($parent) { Get-CimInstance Win32_Process -Filter "ProcessId=$($parent.ParentProcessId)" -EA SilentlyContinue } else { $null }
        $ts = Get-Date -Format 'HH:mm:ss.fff'
        Write-Output "$ts | cmd.exe(pid$($p.ProcessId)) cmd=[$($p.CommandLine)]"
        Write-Output "       parent=$($parent.Name)(pid$($p.ParentProcessId)) parentCmd=[$($parent.CommandLine)]"
        if ($gp) {
            Write-Output "       grandparent=$($gp.Name)(pid$($gp.ProcessId)) gpCmd=[$($gp.CommandLine)]"
        }
        Write-Output "---"
    }
    Start-Sleep -Milliseconds 100
}
