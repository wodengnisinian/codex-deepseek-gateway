$ErrorActionPreference = "Stop"

$body = @{
    model = "deepseek-v4-flash"
    input = "Count from one to three."
    stream = $true
} | ConvertTo-Json -Depth 20

$Bearer = if ($env:GATEWAY_AUTH_TOKEN) { $env:GATEWAY_AUTH_TOKEN } else { $env:DEEPSEEK_API_KEY }

Invoke-WebRequest `
    -Uri "http://127.0.0.1:3688/v1/responses" `
    -Method Post `
    -Headers @{
        "Authorization" = "Bearer $Bearer"
        "Content-Type" = "application/json"
    } `
    -Body $body
