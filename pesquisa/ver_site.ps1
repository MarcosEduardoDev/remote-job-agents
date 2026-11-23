# Abre uma página no navegador do Orca e mostra só as linhas relevantes para candidatura.
# Uso: .\pesquisa\ver_site.ps1 -Pagina <browserPageId> -Url <url> [-Max 60] [-Tudo]
param(
    [Parameter(Mandatory)] [string] $Pagina,
    [Parameter(Mandatory)] [string] $Url,
    [int] $Max = 60,
    [switch] $Tudo
)
$padrao = 'support|suporte|customer|client|success|service|junior|entry|associate|operations|moderat|french|fran[cç]|portugu|remote|anywhere|europe|emea|@|apply|application|talent|spontan|general|interest|future|vaga|position|opening|recrut|recruit|candidat'
orca goto --page $Pagina --url $Url --json | Out-Null
orca wait --page $Pagina --load load --json 2>$null | Out-Null
$json = (orca exec --page $Pagina --command "read" --json) -join "`n" | ConvertFrom-Json
$linhas = $json.result.content -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne '-' }
"### $Url  ($($linhas.Count) linhas)"
if ($Tudo) { $linhas | Select-Object -First $Max }
else { $linhas | Where-Object { $_ -match $padrao -and $_.Length -lt 300 } | Select-Object -Unique -First $Max }
