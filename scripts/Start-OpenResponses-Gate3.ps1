[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$UpstreamUrl,

    [string]$AllowedUpstreamHost,

    [string]$Model = 'gpt-6.1-sol',

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [ValidateRange(1, 300)]
    [int]$TimeoutSeconds = 60,

    [string]$Output = 'docs\evidence\openresponses-gate3.json',

    [string]$AuthHeader = 'Authorization',

    [string]$AuthScheme = 'Bearer'
)

$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'
$runner = Join-Path $repo 'scripts\run_openresponses_gate3.py'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python virtual environment not found at $python"
}
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "Gate 3 runner not found at $runner"
}

$uri = [System.Uri]$UpstreamUrl
if ($uri.Scheme -ne 'https') {
    throw 'Upstream URL must use https.'
}
if ($uri.Query -or $uri.Fragment -or $uri.UserInfo) {
    throw 'Upstream URL must not contain credentials, a query, or a fragment.'
}
if ([string]::IsNullOrWhiteSpace($AllowedUpstreamHost)) {
    $AllowedUpstreamHost = $uri.Host
}
if ($AllowedUpstreamHost -ne $uri.Host) {
    throw 'Allowed upstream host must match the upstream URL host.'
}

if (-not [System.IO.Path]::IsPathRooted($Output)) {
    $Output = Join-Path $repo $Output
}

$conflictingVariables = @(
    'OPENAI_API_KEY',
    'OPENRESPONSES_API_KEY',
    'ANTHROPIC_API_KEY',
    'AZURE_OPENAI_API_KEY',
    'OPENCODE_API_KEY',
    'GOOGLE_API_KEY',
    'GEMINI_API_KEY',
    'MISTRAL_API_KEY'
) | Where-Object { Test-Path "Env:$_" }

if ($conflictingVariables) {
    throw "Clear these environment variables before Gate 3: $($conflictingVariables -join ', ')"
}

Remove-Item Env:OPENRESPONSES_UPSTREAM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:OPENRESPONSES_COMPACTION_KEY -ErrorAction SilentlyContinue

$secureKey = Read-Host -AsSecureString 'Enter the Console API key (input hidden)'
if ($secureKey.Length -eq 0) {
    throw 'No Console API key was entered.'
}

$bstr = [IntPtr]::Zero
try {
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $secureKey.Dispose()
}

$keyBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $rng.GetBytes($keyBytes)
    $compactionKey = [Convert]::ToBase64String($keyBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
finally {
    $rng.Dispose()
    [Array]::Clear($keyBytes, 0, $keyBytes.Length)
}

$gatewayUrl = "http://127.0.0.1:$Port"
$adapter = $null
$exitCode = 1

try {
    $env:OPENRESPONSES_UPSTREAM_API_KEY = $plainKey
    $env:OPENRESPONSES_COMPACTION_KEY = $compactionKey

    try {
        $adapterArguments = @(
            '-m',
            'transformation_workbench.openresponses_adapter.runtime',
            '--upstream-url',
            $UpstreamUrl,
            '--host',
            '127.0.0.1',
            '--port',
            "$Port",
            '--timeout',
            "$TimeoutSeconds",
            '--allow-hosted-upstream',
            '--allowed-upstream-host',
            $AllowedUpstreamHost,
            '--upstream-auth-header',
            $AuthHeader,
            '--upstream-auth-scheme',
            $AuthScheme
        )
        $adapter = Start-Process -FilePath $python -ArgumentList $adapterArguments -WorkingDirectory $repo -PassThru -NoNewWindow
    }
    finally {
        Remove-Item Env:OPENRESPONSES_UPSTREAM_API_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:OPENRESPONSES_COMPACTION_KEY -ErrorAction SilentlyContinue
        $plainKey = $null
        $compactionKey = $null
    }

    $ready = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        if ($adapter.HasExited) {
            throw "Adapter exited before becoming ready with code $($adapter.ExitCode)."
        }
        try {
            $health = Invoke-RestMethod -Uri "$gatewayUrl/__local/health" -TimeoutSec 2 -UseBasicParsing
            if ($health.status -eq 'ok') {
                $ready = $true
                break
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        throw 'Adapter did not become ready within 30 seconds.'
    }

    & $python $runner --gateway-url $gatewayUrl --model $Model --output $Output
    $exitCode = $LASTEXITCODE
}
finally {
    if ($adapter -and -not $adapter.HasExited) {
        Stop-Process -Id $adapter.Id -Force
        $adapter.WaitForExit(5000) | Out-Null
    }
}

exit $exitCode
