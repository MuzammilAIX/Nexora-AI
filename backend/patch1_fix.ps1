$ErrorActionPreference = "Stop"
$p1 = "C:\Users\IBS TRADER\Nexora-AI\backend\app\workflows\orchestrator.py"

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item $p1 "$p1.bak_$stamp" -Force
Write-Host "Backup: $p1.bak_$stamp" -ForegroundColor Cyan

$lines = [System.IO.File]::ReadAllLines($p1, [System.Text.Encoding]::UTF8)

$anchor = 'r"\b(?:schedule|calendar|agenda)\b.*\b(?:until|till|through|to|by|before|next|this|coming|upcoming)\b)"'

$idx = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -eq $anchor) { $idx = $i; break }
}

if ($idx -lt 0) {
    Write-Host "[ABORT] anchor not found verbatim." -ForegroundColor Red
    return
}
Write-Host "Anchor found at line $($idx + 1)" -ForegroundColor Cyan

$lines[$idx] = $lines[$idx].Substring(0, $lines[$idx].Length - 2) + '|"'

$newPatterns = @(
    '    r"\b\d{1,2}\s+days?\s+(?:schedule|calendar|agenda|plan)\b|"',
    '    r"\b(?:nxt|nx|upcom\w*)\b.*\b(?:schedule|calendar|agenda)\b|"',
    '    r"\b(?:schedule|calendar|agenda)\s+(?:for\s+)?\d{1,2}\s+days?\b|"',
    '    r"\b\d{1,2}\s+days?\s+(?:schedule|calendar|agenda)\b)"'
)

$before = if ($idx -gt 0) { $lines[0..($idx - 1)] } else { @() }
$anchorLine = $lines[$idx]
$after  = if ($idx + 1 -lt $lines.Count) { $lines[($idx + 1)..($lines.Count - 1)] } else { @() }
$new = @($before) + @($anchorLine) + $newPatterns + @($after)

[System.IO.File]::WriteAllLines($p1, $new, [System.Text.Encoding]::UTF8)
Write-Host "[OK] patch applied (file now has $($new.Count) lines, was $($lines.Count))" -ForegroundColor Green
