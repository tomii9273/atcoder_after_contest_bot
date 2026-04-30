[CmdletBinding()]
param(
    [string]$SecretsPath = (Join-Path $env:LOCALAPPDATA "AtCoderAfterContestBot\x_api_secrets.json")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Read-ProtectedSecret {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prompt
    )

    $secureString = Read-Host -Prompt $Prompt -AsSecureString
    return ConvertFrom-SecureString -SecureString $secureString
}

$secretDirectory = Split-Path -Parent $SecretsPath
if ($secretDirectory -ne "" -and -not (Test-Path -LiteralPath $secretDirectory)) {
    New-Item -ItemType Directory -Path $secretDirectory -Force | Out-Null
}

$secretData = [ordered]@{
    schema_version = 1
    updated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    x_api_consumer_key = Read-ProtectedSecret -Prompt "X API の CONSUMER_KEY"
    x_api_consumer_secret = Read-ProtectedSecret -Prompt "X API の CONSUMER_SECRET"
    x_api_access_token = Read-ProtectedSecret -Prompt "X API の ACCESS_TOKEN"
    x_api_access_token_secret = Read-ProtectedSecret -Prompt "X API の ACCESS_TOKEN_SECRET"
}

$secretJson = $secretData | ConvertTo-Json
Set-Content -LiteralPath $SecretsPath -Value $secretJson -Encoding UTF8

Write-Host "暗号化した secret を保存しました: $SecretsPath"
Write-Host "このファイルは、同じ Windows ユーザーかつ同じ PC でのみ復号できます。"
