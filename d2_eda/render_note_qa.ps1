param([string]$Root = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$htmlPath = Join-Path $rootPath 'd2_eda\D2_data_note_print.html'
$qaDir = Join-Path $rootPath 'd2_eda\qa'
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
New-Item -ItemType Directory -Force -Path $qaDir | Out-Null
$html = Get-Content -LiteralPath $htmlPath -Raw -Encoding UTF8
$style = [regex]::Match($html,'<style>(.*?)</style>','Singleline').Groups[1].Value
$body = [regex]::Match($html,'<body>(.*?)</body>','Singleline').Groups[1].Value
$pages = [regex]::Split($body,'<div class="pagebreak"></div>')
if ($pages.Count -ne 3) { throw "Expected 3 authored pages, found $($pages.Count)" }
for ($i=0; $i -lt $pages.Count; $i++) {
    $num=$i+1
    $preview=Join-Path $qaDir "page_$num.html"
    $shot=Join-Path $qaDir "page_$num.png"
    $extra='html,body{margin:0!important;padding:0!important;background:#e7eaee!important;}body{width:816px!important;height:1056px!important;overflow:hidden!important;padding:60px 69px 58px!important;background:#fff!important;}figure{break-inside:avoid;}'
    ('<!doctype html><html><head><meta charset="utf-8"><style>'+$style+$extra+'</style></head><body>'+$pages[$i]+'</body></html>') | Set-Content -LiteralPath $preview -Encoding UTF8
    $uri=([System.Uri]$preview).AbsoluteUri
    $profile=Join-Path $qaDir "edge_profile_$num"
    & $edge '--headless' '--disable-gpu' '--no-first-run' '--hide-scrollbars' '--force-device-scale-factor=1' '--window-size=816,1056' "--user-data-dir=$profile" "--screenshot=$shot" $uri | Out-Null
    if (!(Test-Path -LiteralPath $shot)) { throw "Missing preview screenshot $num" }
}
Write-Host 'Rendered three QA page previews.'
