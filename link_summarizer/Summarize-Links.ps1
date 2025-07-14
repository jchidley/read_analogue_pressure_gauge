# Summarize-Links.ps1 - A PowerShell script to summarize links from a file
# 
# Usage: .\Summarize-Links.ps1 -FilePath <path_to_file_with_links> [-Api <api>] [-OutputFile <output_file>]
#
# Example: .\Summarize-Links.ps1 -FilePath "$env:OneDrive\history_logs\open_tabs.md" -Api claude -OutputFile summaries.md

param (
    [Parameter(Mandatory=$true)]
    [string]$FilePath,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("basic")]
    [string]$Api = "basic",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile
)

# Check if file exists
if (-not (Test-Path $FilePath)) {
    Write-Error "Error: File not found at $FilePath"
    exit 1
}

# Build the command
$Command = "python link_summarizer.py `"$FilePath`" --api $Api"

# Add output file if specified
if ($OutputFile) {
    $Command += " --output `"$OutputFile`""
}

# Print the command being executed
Write-Host "Executing: $Command"

# Execute the command
Invoke-Expression $Command