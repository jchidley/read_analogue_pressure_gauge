#!/usr/bin/env python3
"""
Link Summarizer Tool - Fetches and summarizes content from multiple URLs in parallel

This script processes a list of URLs from a specified file, fetches the content
in parallel using asyncio and aiohttp, and generates concise summaries using
OpenAI or Claude APIs.

Usage:
    python link_summarizer.py <path_to_file_with_links> [--api {openai,claude}] [--output <output_file>]

Example:
    python link_summarizer.py /path/to/links.md --api claude --output summaries.md
"""

import os
import re
import sys
import json
import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import ssl
import certifi

import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Regular expression to extract URLs from markdown links
URL_PATTERN = r'\[.*?\]\((https?://[^\s\)]+)\)'

# Create a secure SSL context
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

async def extract_urls_from_file(file_path: str) -> List[str]:
    """Extract URLs from a markdown file containing links."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Extract URLs using regex
        urls = re.findall(URL_PATTERN, content)
        return urls
    except Exception as e:
        print(f"Error extracting URLs from file: {e}")
        return []

async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> Tuple[str, Optional[str]]:
    """Fetch the content of a URL and return the HTML content."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Handle PDF URLs differently
        if url.lower().endswith('.pdf'):
            return url, f"<html><body><p>PDF document at {url}</p></body></html>"
            
        # Use SSL context for secure connections
        async with session.get(url, headers=headers, timeout=30, ssl=SSL_CONTEXT) as response:
            if response.status == 200:
                try:
                    html = await response.text()
                    return url, html
                except UnicodeDecodeError:
                    # For binary content like PDFs
                    return url, f"<html><body><p>Binary content at {url}</p></body></html>"
            else:
                print(f"Error fetching {url}: HTTP {response.status}")
                return url, None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return url, None

async def parse_html_to_text(html: str) -> str:
    """Parse HTML content to plain text using BeautifulSoup."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit text length (APIs have context limits)
        return text[:10000]  # Limit to first 10000 characters
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return "Could not parse content."

def extract_title(soup: BeautifulSoup) -> str:
    """Extract the title from a webpage."""
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.text.strip()
    return "No title found"

def extract_meta_description(soup: BeautifulSoup) -> str:
    """Extract meta description from a webpage."""
    meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'].strip()
    return ""

def extract_main_content(soup: BeautifulSoup) -> str:
    """Extract main content elements from a webpage."""
    # Try to find main content areas
    main_content = ""
    
    # Check for article tags
    article = soup.find('article')
    if article:
        main_content += article.get_text(separator=' ', strip=True) + " "
    
    # Check for main tag
    main = soup.find('main')
    if main:
        main_content += main.get_text(separator=' ', strip=True) + " "
    
    # Check for content divs by common class/id names
    for selector in ['#content', '.content', '#main', '.main', '.post', '.article']:
        content_div = soup.select_one(selector)
        if content_div:
            main_content += content_div.get_text(separator=' ', strip=True) + " "
    
    # If GitHub, get the README content
    if "github.com" in soup.text:
        readme = soup.select_one('.markdown-body')
        if readme:
            main_content += readme.get_text(separator=' ', strip=True) + " "
    
    # If no structured content found, try to get the first few paragraphs
    if not main_content:
        paragraphs = soup.find_all('p', limit=5)
        for p in paragraphs:
            main_content += p.get_text(separator=' ', strip=True) + " "
    
    return main_content.strip()

def extract_domain(url: str) -> str:
    """Extract the domain name from a URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain

def generate_basic_summary(html: str, url: str) -> str:
    """Generate a basic summary without using external APIs."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract key elements
        title = extract_title(soup)
        meta_desc = extract_meta_description(soup)
        domain = extract_domain(url)
        
        # If we have a good meta description, use it
        if meta_desc and len(meta_desc) > 50:
            return meta_desc
        
        # For GitHub repos, create a special summary
        if "github.com" in url:
            repo_name = url.split("/")[-1].split("?")[0]
            about_section = soup.select_one('.f4.my-3')
            about_text = about_section.get_text(strip=True) if about_section else "No description available"
            
            # Try to get the language
            language_tag = soup.select_one('[itemprop="programmingLanguage"]')
            language = language_tag.get_text(strip=True) if language_tag else "various languages"
            
            return f"{repo_name} is a {language} repository that {about_text.lower() if about_text[0].isupper() else about_text}"
        
        # For documentation pages
        if any(x in url for x in ['docs.', 'documentation', 'readthedocs']):
            return f"Documentation page about {title} from {domain}, providing technical information and guidance."
        
        # Extract main content and create a simple summary
        main_content = extract_main_content(soup)
        
        # If we have substantial content, create a summary based on the first few sentences
        if main_content and len(main_content) > 100:
            sentences = main_content.replace(".", ". ").split(". ")
            key_sentences = sentences[:2]
            summary = ". ".join(key_sentences)
            
            # Limit the length
            if len(summary) > 200:
                summary = summary[:197] + "..."
                
            return summary
        
        # Fallback to a generic summary with the title
        return f"Webpage titled '{title}' from {domain}."
    
    except Exception as e:
        print(f"Error generating basic summary: {e}")
        return f"Content from {url} (could not generate summary)"

async def process_url(session: aiohttp.ClientSession, url: str, api: str) -> Dict[str, Any]:
    """Process a single URL: fetch, parse, and summarize."""
    result = {"url": url, "summary": "", "timestamp": datetime.now().isoformat(), "success": False}
    
    url_content = await fetch_url_content(session, url)
    
    if url_content[1]:
        # Generate a basic summary without external APIs
        summary = generate_basic_summary(url_content[1], url)
        result["summary"] = summary
        result["success"] = True
    else:
        result["summary"] = "Failed to fetch content from URL."
    
    print(f"Processed: {url}")
    return result

async def process_urls(urls: List[str], api: str = "claude") -> List[Dict[str, Any]]:
    """Process multiple URLs in parallel."""
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_url(session, url, api) for url in urls]
        results = await asyncio.gather(*tasks)
    
    return results

def format_markdown_output(results: List[Dict[str, Any]]) -> str:
    """Format the results as a markdown file."""
    output = f"# URL Summaries\n\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for i, result in enumerate(results, 1):
        output += f"## {i}. [{result['url']}]({result['url']})\n\n"
        output += f"{result['summary']}\n\n"
        output += "---\n\n"
    
    return output

async def main():
    """Main function to run the tool."""
    parser = argparse.ArgumentParser(description="Fetch and summarize content from multiple URLs in parallel.")
    parser.add_argument("file_path", help="Path to the file containing markdown links")
    parser.add_argument("--api", choices=["basic"], default="basic", help="Method to use for summarization")
    parser.add_argument("--output", help="Output file path for the summaries (default: summaries_YYYY-MM-DD.md)")
    
    args = parser.parse_args()
    
    # Extract URLs from the file
    urls = await extract_urls_from_file(args.file_path)
    
    if not urls:
        print("No URLs found in the file.")
        sys.exit(1)
    
    print(f"Found {len(urls)} URLs to process.")
    
    # Process URLs in parallel
    results = await process_urls(urls, args.api)
    
    # Format output
    markdown_output = format_markdown_output(results)
    
    # Determine output file name
    output_file = args.output if args.output else f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_output)
    
    print(f"Summaries written to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())