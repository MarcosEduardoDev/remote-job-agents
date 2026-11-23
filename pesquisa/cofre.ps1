# Cofre de senhas das contas nas plataformas de vagas.
# As senhas ficam em dados\cofre\<site>.txt, criptografadas com DPAPI do Windows (só o usuário do Windows
# que as criou, neste computador, consegue abrir). A pasta dados\cofre está no .gitignore.
# Uso:  . .\pesquisa\cofre.ps1
#       New-SenhaSite -Site himalayas      # cria e guarda uma senha nova (não mostra)
#       Get-SenhaSite -Site himalayas      # devolve a senha em texto (use só para enviar por stdin)
#       Get-SitesNoCofre                   # lista os sites com senha guardada

$script:PastaCofre = Join-Path $PSScriptRoot "..\dados\cofre"

function New-SenhaSite([Parameter(Mandatory)][string] $Site) {
    New-Item -ItemType Directory -Force $script:PastaCofre | Out-Null
    $arquivo = Join-Path $script:PastaCofre "$Site.txt"
    if (Test-Path $arquivo) { throw "Já existe senha para '$Site'. Use Get-SenhaSite." }
    $grupos = @('ABCDEFGHJKLMNPQRSTUVWXYZ', 'abcdefghijkmnopqrstuvwxyz', '23456789', '!@#%*-_+?')
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $byte = New-Object byte[] 1
    $chars = foreach ($i in 0..19) {
        $g = $grupos[$i % 4]
        $rng.GetBytes($byte); $g[$byte[0] % $g.Length]
    }
    $rng.GetBytes($byte)
    $senha = -join ($chars | Sort-Object { Get-Random -SetSeed ([int]$byte[0] + [Environment]::TickCount) })
    ConvertTo-SecureString $senha -AsPlainText -Force | ConvertFrom-SecureString | Set-Content -Path $arquivo -Encoding ascii
    "Senha criada para '$Site' (guardada criptografada)."
}

function Get-SenhaSite([Parameter(Mandatory)][string] $Site) {
    $arquivo = Join-Path $script:PastaCofre "$Site.txt"
    if (-not (Test-Path $arquivo)) { throw "Sem senha para '$Site'." }
    $seguro = Get-Content $arquivo | ConvertTo-SecureString
    [System.Net.NetworkCredential]::new('', $seguro).Password
}

function Get-SitesNoCofre {
    if (Test-Path $script:PastaCofre) { Get-ChildItem $script:PastaCofre -Filter *.txt | ForEach-Object { $_.BaseName } }
}
