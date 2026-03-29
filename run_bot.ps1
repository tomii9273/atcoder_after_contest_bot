[CmdletBinding()]
param(
    [string]$SecretsPath = (Join-Path $env:LOCALAPPDATA "AtCoderAfterContestBot\x_api_secrets.json"),
    [string]$AtCoderCookieBrowser = "firefox"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$utf8Encoding = [System.Text.UTF8Encoding]::new($true)

$repoPath = $PSScriptRoot
$pythonPath = Join-Path $repoPath ".venv\Scripts\python.exe"
$scriptPath = Join-Path $repoPath "check_cases_and_make_tweet.py"
$logDirectory = Join-Path $repoPath "ignore\logs"
$latestLogPath = Join-Path $repoPath "ignore\run_bot_last.log"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDirectory "run_bot_$timestamp.log"

function Write-RunBotLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-RunBotOutputLine -Line $line
}

function Initialize-Utf8LogFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    [System.IO.File]::WriteAllText($Path, "", $utf8Encoding)
}

function Write-RunBotOutputLine {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Line
    )

    Write-Host $Line
    [System.IO.File]::AppendAllText($logPath, "$Line`r`n", $utf8Encoding)
    [System.IO.File]::AppendAllText($latestLogPath, "$Line`r`n", $utf8Encoding)
}

function Convert-ProtectedStringToPlainText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProtectedString
    )

    $secureString = ConvertTo-SecureString -String $ProtectedString
    return [System.Net.NetworkCredential]::new("", $secureString).Password
}

function Get-XApiSecrets {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "secret ファイルが見つかりません: $Path`n初回は .\save_x_api_secrets.ps1 を実行してください。"
    }

    $secretData = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $requiredPropertyNames = @(
        "x_api_consumer_key",
        "x_api_consumer_secret",
        "x_api_access_token",
        "x_api_access_token_secret"
    )
    foreach ($propertyName in $requiredPropertyNames) {
        if ($secretData.PSObject.Properties.Name -notcontains $propertyName) {
            throw "secret ファイルの形式が不正です。足りない項目: $propertyName"
        }
    }

    return @{
        X_API_CONSUMER_KEY = Convert-ProtectedStringToPlainText -ProtectedString $secretData.x_api_consumer_key
        X_API_CONSUMER_SECRET = Convert-ProtectedStringToPlainText -ProtectedString $secretData.x_api_consumer_secret
        X_API_ACCESS_TOKEN = Convert-ProtectedStringToPlainText -ProtectedString $secretData.x_api_access_token
        X_API_ACCESS_TOKEN_SECRET = Convert-ProtectedStringToPlainText -ProtectedString $secretData.x_api_access_token_secret
    }
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
Initialize-Utf8LogFile -Path $logPath
Initialize-Utf8LogFile -Path $latestLogPath

try {
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw "Python が見つかりません: $pythonPath"
    }
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "実行対象の Python スクリプトが見つかりません: $scriptPath"
    }

    $xApiSecrets = Get-XApiSecrets -Path $SecretsPath

    foreach ($envName in $xApiSecrets.Keys) {
        Set-Item -LiteralPath "Env:$envName" -Value $xApiSecrets[$envName]
    }
    $env:ATCODER_COOKIE_BROWSER = $AtCoderCookieBrowser
    $env:PYTHONUTF8 = "1"
    $env:PYTHONUNBUFFERED = "1"

    Write-RunBotLog "実行開始"
    Write-RunBotLog "secret ファイル: $SecretsPath"
    Write-RunBotLog "ATCODER_COOKIE_BROWSER: $AtCoderCookieBrowser"

    Push-Location $repoPath
    try {
        & $pythonPath "-u" $scriptPath "--post-from-env" 2>&1 |
            ForEach-Object {
                Write-RunBotOutputLine -Line "$_"
            }

        if ($LASTEXITCODE -ne 0) {
            throw "Python スクリプトが異常終了しました。終了コード: $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    Write-RunBotLog "実行成功"
}
catch {
    Write-RunBotLog "実行失敗: $($_.Exception.Message)"
    throw
}
finally {
    Remove-Item Env:X_API_CONSUMER_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:X_API_CONSUMER_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:X_API_ACCESS_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:X_API_ACCESS_TOKEN_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONUNBUFFERED -ErrorAction SilentlyContinue
}
