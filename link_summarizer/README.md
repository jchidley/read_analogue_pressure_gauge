# Link Summarizer Tool

A tool for fetching and summarizing content from multiple URLs in parallel. It extracts links from markdown files, processes them concurrently, and generates concise summaries using AI.

## Features

- Extracts URLs from markdown files
- Fetches and processes multiple URLs in parallel
- Generates basic summaries using built-in text extraction techniques
- Outputs results in a clean markdown format
- Supports both command line and script usage

## Requirements

- Python 3.7+
- Required Python packages:
  - aiohttp
  - beautifulsoup4
  - certifi

## Installation

1. Ensure you have the required packages installed:

```bash
pip install aiohttp beautifulsoup4 certifi
```

## Usage

### Direct Python Usage

```bash
python link_summarizer.py <path_to_file_with_links> [--api basic] [--output <output_file>]
```

Example:
```bash
python link_summarizer.py ~/Documents/my_links.md --output summaries.md
```

### Bash Script (Linux/Mac)

```bash
./summarize_links.sh <path_to_file_with_links> [api] [output_file]
```

Example:
```bash
./summarize_links.sh ~/OneDrive/history_logs/open_tabs.md basic summaries.md
```

### PowerShell Script (Windows)

```powershell
.\Summarize-Links.ps1 -FilePath <path_to_file_with_links> [-Api <api>] [-OutputFile <output_file>]
```

Example:
```powershell
.\Summarize-Links.ps1 -FilePath "$env:OneDrive\history_logs\open_tabs.md" -OutputFile summaries.md
```

## Input Format

The input file should contain markdown-style links:

```markdown
- [Link Title](https://example.com)
- [Another Link](https://another-example.com)
```

## Output Format

The script generates a markdown file with summaries:

```markdown
# URL Summaries

Generated on: 2025-05-19 14:30:45

## 1. [https://example.com](https://example.com)

This is a summary of the content from example.com.

---

## 2. [https://another-example.com](https://another-example.com)

This is a summary of the content from another-example.com.

---
```

## Summarization Method

- `basic` (default): Uses built-in text extraction techniques without external API calls

## Troubleshooting

- If you encounter SSL certificate errors, ensure your Python installation has proper SSL certificates
- For timeouts, increase the timeout value in the `fetch_url_content` function
- If summaries are too short or long, adjust the `max_tokens` parameter in the API call functions