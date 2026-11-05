param(
  [Parameter(Mandatory=$true)][string]$DocxPath,
  [Parameter(Mandatory=$true)][string]$PdfPath
)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $null
try {
  $doc = $word.Documents.Open((Resolve-Path $DocxPath).Path, $false, $true)
  $doc.ExportAsFixedFormat((Resolve-Path (Split-Path $PdfPath -Parent)).Path + "\" + (Split-Path $PdfPath -Leaf), 17)
} finally {
  if ($doc -ne $null) { $doc.Close($false) }
  $word.Quit()
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
Write-Output $PdfPath
