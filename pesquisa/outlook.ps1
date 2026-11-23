# Ajudantes para operar o Outlook (novo) pela tela, lendo o índice do elemento na hora de agir.
# O Outlook renumera os elementos com frequência (anúncios na caixa de entrada), então cada ação
# relê a árvore e tenta de novo algumas vezes.
# Uso: . .\pesquisa\outlook.ps1  (carrega as funções)

function Get-OutlookPid { (Get-Process olk | Select-Object -First 1).Id }

function Get-OutlookArvore {
    (orca computer get-app-state --app "pid:$(Get-OutlookPid)" --no-screenshot --json | ConvertFrom-Json).result.snapshot.treeText -split "`r?`n"
}

function Invoke-OutlookAcao([string] $Padrao, [string[]] $Acao, [int] $Tentativas = 8) {
    for ($n = 1; $n -le $Tentativas; $n++) {
        $linha = Get-OutlookArvore | Where-Object { $_ -match $Padrao } | Select-Object -First 1
        if (-not $linha) { throw "Elemento nao encontrado: $Padrao" }
        $i = [int]([regex]::Match($linha, '^\s*(\d+)').Groups[1].Value)
        $r = orca computer @Acao --app "pid:$(Get-OutlookPid)" --element-index $i --no-screenshot --json | ConvertFrom-Json
        if ($r.ok) { return $r.result.action.verification }
        if ($r.error.code -ne 'element_not_found') { throw "$($r.error.code): $($r.error.message)" }
    }
    throw "Elemento instavel depois de $Tentativas tentativas: $Padrao"
}
