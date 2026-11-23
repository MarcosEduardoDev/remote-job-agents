# Abre um formulário de candidatura no navegador do Orca e lista os campos (rótulos e controles).
# Uso: .\pesquisa\ler_formulario.ps1 -Pagina <browserPageId> -Url <url> [-Max 60]
param(
    [Parameter(Mandatory)] [string] $Pagina,
    [Parameter(Mandatory)] [string] $Url,
    [int] $Max = 60
)
orca goto --page $Pagina --url $Url --json | Out-Null
orca wait --page $Pagina --load load --json 2>$null | Out-Null
orca wait --page $Pagina --selector 'input, textarea, select' --timeout 15000 --json 2>$null | Out-Null
$snap = orca snapshot --page $Pagina --interactive
$controles = $snap | Where-Object { $_ -notmatch '^\s+- option' } |
    Select-String -Pattern 'textbox|combobox|checkbox|radio|button "(Upload|Attach|Submit|Apply|Send|Next|Continue)' |
    ForEach-Object { ($_.Line.Trim() -replace ' hint=.*', '') } |
    Where-Object { $_ -notmatch 'Race|White \(|Black or|Hawaiian|Asian \(|American Indian|Two or More|Veteran|Disability|cookie' }
$captcha = [bool]($snap | Select-String -Pattern 'captcha|recaptcha|hcaptcha|turnstile' -Quiet)
$login = [bool]($snap | Select-String -Pattern 'Sign in|Log in|Create account|Password' -Quiet)
"### $Url"
"captcha: $captcha | pede login/senha: $login | controles: $($controles.Count)"
$controles | Select-Object -First $Max | ForEach-Object { $_.Substring(0, [Math]::Min(150, $_.Length)) }
