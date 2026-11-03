param([string]$Root = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$markdownPath = Join-Path $rootPath 'D2_data_note.md'
$htmlPath = Join-Path $rootPath 'd2_eda\D2_data_note_print.html'
$pdfPath = Join-Path $rootPath 'D2_data_note.pdf'
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (!(Test-Path -LiteralPath $edge)) { throw 'Microsoft Edge is required to print the note to PDF on this system.' }

function InlineHtml([string]$value) {
    $v = [System.Net.WebUtility]::HtmlEncode($value)
    $v = $v -replace '\[([^\]]+)\]\(([^)]+)\)', '<a href="$2">$1</a>'
    $v = $v -replace '\*\*([^*]+)\*\*', '<strong>$1</strong>'
    $v = $v -replace '`([^`]+)`', '<code>$1</code>'
    return $v
}

$parts = [System.Collections.Generic.List[string]]::new()
$paragraph = [System.Collections.Generic.List[string]]::new()
$listOpen = $false
$pendingImage = $null
function FlushParagraph {
    if ($script:paragraph.Count -gt 0) { $script:parts.Add('<p>' + (InlineHtml ($script:paragraph -join ' ')) + '</p>'); $script:paragraph.Clear() }
}
function CloseList {
    if ($script:listOpen) { $script:parts.Add('</ul>'); $script:listOpen = $false }
}
foreach ($line in Get-Content -LiteralPath $markdownPath -Encoding UTF8) {
    $v = $line.Trim()
    if ($v.Length -eq 0) { FlushParagraph; CloseList; continue }
    if ($v -eq '<!-- PAGE BREAK -->') { FlushParagraph; CloseList; $parts.Add('<div class="pagebreak"></div>'); continue }
    if ($v -match '^!\[([^\]]*)\]\(([^)]+)\)$') { FlushParagraph; CloseList; $pendingImage = @{ Alt=$Matches[1]; Src=$Matches[2] }; continue }
    if ($null -ne $pendingImage) {
        if ($v -notmatch '^\*\*Figure ') { throw "Expected figure caption after image: $($pendingImage.Src)" }
        $class = if ($pendingImage.Src -like '*01_source_coverage*') { 'coverage' } elseif ($pendingImage.Src -like '*04_cmpd_missingness*') { 'missing' } else { 'standard' }
        $imagePath = Join-Path $rootPath $pendingImage.Src
        if (!(Test-Path -LiteralPath $imagePath)) { throw "Missing figure image: $imagePath" }
        $imageUri = ([System.Uri]$imagePath).AbsoluteUri
        $parts.Add('<figure class="' + $class + '"><img src="' + [System.Net.WebUtility]::HtmlEncode($imageUri) + '" alt="' + [System.Net.WebUtility]::HtmlEncode($pendingImage.Alt) + '"><figcaption>' + (InlineHtml $v) + '</figcaption></figure>')
        $pendingImage = $null
        continue
    }
    if ($v -match '^(#{1,3})\s+(.+)$') { FlushParagraph; CloseList; $level = $Matches[1].Length; $parts.Add("<h$level>" + (InlineHtml $Matches[2]) + "</h$level>"); continue }
    if ($v -match '^-\s+(.+)$') { FlushParagraph; if (!$listOpen) { $parts.Add('<ul>'); $listOpen = $true }; $parts.Add('<li>' + (InlineHtml $Matches[1]) + '</li>'); continue }
    CloseList
    $paragraph.Add($v)
}
FlushParagraph; CloseList
if ($null -ne $pendingImage) { throw 'Uncaptioned image at end of Markdown' }
$body = $parts -join "`n"
$css = @'
@page { size: letter; margin: 0.63in 0.72in 0.6in 0.72in; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { color: #263442; font-family: Georgia, 'Times New Roman', serif; font-size: 9.6pt; line-height: 1.31; }
h1, h2, h3 { font-family: 'Segoe UI', Arial, sans-serif; color: #173957; break-after: avoid; }
h1 { font-size: 20pt; line-height: 1.13; margin: 0 0 0.13in; font-weight: 700; }
h2 { font-size: 11.6pt; border-bottom: 1px solid #cad8e2; padding-bottom: 0.045in; margin: 0.17in 0 0.07in; }
h3 { font-size: 10pt; margin: 0.13in 0 0.04in; }
p { margin: 0 0 0.075in; orphans: 2; widows: 2; }
p:nth-of-type(1) { margin-top: 0; }
ul { margin: 0.03in 0 0.1in 0.18in; padding-left: 0.15in; }
li { margin: 0 0 0.06in; padding-left: 0.015in; }
strong { color: #173957; }
code { font-family: Consolas, monospace; font-size: 8.4pt; background: #eef3f6; padding: 0.01in 0.025in; }
a { color: #22618a; text-decoration: none; }
figure { margin: 0.11in 0 0.13in; break-inside: avoid; text-align: center; }
figure img { display: block; object-fit: contain; max-width: 100%; height: auto; margin: 0 auto 0.045in; }
figure.coverage img { width: 5.55in; }
figure.standard img { width: 5.0in; }
figure.missing img { width: 4.75in; }
figcaption { color: #435263; font-size: 8.25pt; line-height: 1.25; text-align: left; border-left: 2px solid #8eb1c7; padding-left: 0.09in; }
.pagebreak { break-before: page; page-break-before: always; height: 0; }
@media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
'@
$html = '<!doctype html><html><head><meta charset="utf-8"><title>D2 data note</title><style>' + $css + '</style></head><body>' + $body + '</body></html>'
$html | Set-Content -LiteralPath $htmlPath -Encoding UTF8

$profilePath = Join-Path $rootPath 'd2_eda\edge_pdf_profile'
New-Item -ItemType Directory -Force -Path $profilePath | Out-Null
$htmlUri = ([System.Uri]$htmlPath).AbsoluteUri
$args = @('--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--no-pdf-header-footer',"--user-data-dir=$profilePath","--print-to-pdf=$pdfPath",$htmlUri)
& $edge @args | Out-Null
if (!(Test-Path -LiteralPath $pdfPath)) { throw 'Edge did not create the PDF' }
Write-Host "Created $pdfPath"
