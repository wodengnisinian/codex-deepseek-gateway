$ErrorActionPreference = "Stop"

$body = @{
    model = "deepseek-v4-pro"
    input = "Use the tool to get the current time in Asia/Shanghai."
    stream = $false
    tools = @(
        @{
            type = "function"
            name = "get_current_time"
            description = "Get the current time for a timezone."
            parameters = @{
                type = "object"
                properties = @{
                    timezone = @{
                        type = "string"
                        description = "IANA timezone name."
                    }
                }
                required = @("timezone")
                additionalProperties = $false
            }
            strict = $true
        }
    )
} | ConvertTo-Json -Depth 30

$Bearer = if ($env:GATEWAY_AUTH_TOKEN) { $env:GATEWAY_AUTH_TOKEN } else { $env:DEEPSEEK_API_KEY }

Invoke-RestMethod `
    -Uri "http://127.0.0.1:3688/v1/responses" `
    -Method Post `
    -Headers @{
        "Authorization" = "Bearer $Bearer"
        "Content-Type" = "application/json"
    } `
    -Body $body
