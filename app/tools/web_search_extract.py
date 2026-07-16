import os
import sys
import re
from typing import List, Dict, Any
from tavily import TavilyClient

# Initialize the Tavily client.
# Try to get the API key from environment variables first, then fall back to the default one.
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily Search API and return multiple results.
    
    Args:
        query: The search query string.
        max_results: The maximum number of results to return.
        
    Returns:
        A list of dicts, where each dict represents a search result with:
        - title: The title of the page.
        - url: The URL of the page.
        - content: A snippet of the page's content.
        - score: The relevance score of the result.
    """
    try:
        response = tavily_client.search(query=query, max_results=max_results)
        results = response.get("results", [])
        return [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
                "score": r.get("score"),
            }
            for r in results
        ]
    except Exception as e:
        print(f"Error performing web search: {e}", file=sys.stderr)
        return []


def extract_web_content(urls: List[str], format: str = "markdown") -> List[Dict[str, Any]]:
    """
    Extract clean, structured content (e.g., markdown) from specific web pages.
    
    Args:
        urls: A list of page URLs to extract content from.
        format: The format of the returned content (default: 'markdown').
        
    Returns:
        A list of dicts, where each dict represents an extracted page with:
        - url: The URL of the page.
        - title: The title of the page.
        - raw_content: The extracted clean text or markdown content.
    """
    try:
        response = tavily_client.extract(urls=urls, format=format)
        failed_results = response.get("failed_results", [])
        if failed_results:
            for f in failed_results:
                print(f"Warning: Extraction failed for URL: {f.get('url')}. Error: {f.get('error')}", file=sys.stderr)
        
        results = response.get("results", [])
        return [
            {
                "url": r.get("url"),
                "title": r.get("title"),
                "raw_content": r.get("raw_content"),
            }
            for r in results
        ]
    except Exception as e:
        print(f"Error extracting web content: {e}", file=sys.stderr)
        return []


def clean_and_optimize_content(text: str) -> str:
    """
    Remove unnecessary noises, excessive newlines, duplicate spaces, and symbols
    to optimize the content for LLM readability.
    """
    if not text:
        return ""
    
    # 1. Standardize line endings and tabs
    text = text.replace("\r\n", "\n").replace("\t", " ")
    
    # 2. Remove markdown images: ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    
    # 3. Remove HTML images and SVGs
    text = re.sub(r"<img[^>]*>", "", text)
    text = re.sub(r"<svg[^>]*>.*?</svg>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # 4. Remove inline base64 data URIs (can be very long and noisy)
    text = re.sub(r"data:[^;]+;base64,[A-Za-z0-9+/=\s\n]+", "", text)
    
    # 5. Remove duplicate horizontal whitespace
    text = re.sub(r" {2,}", " ", text)
    
    # 6. Clean up line-by-line whitespace
    lines = [line.strip() for line in text.split("\n")]
    
    # 7. Filter lines to reduce noise
    cleaned_lines = []
    for line in lines:
        # Skip lines that are just long rows of dashes, equals, stars, or symbols (typical divider lines)
        if re.match(r"^[=\-\*#_\s\>\+\.\|~:]{3,}$", line):
            continue
        cleaned_lines.append(line)
        
    # Rejoin lines
    text = "\n".join(cleaned_lines)
    
    # 8. Remove "Read More" or "Readmore" indicators
    text = re.sub(r"\bRead\s*More\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bReadmore\b", "", text, flags=re.IGNORECASE)
    
    # 9. Clean up trailing ellipses and general trailing punctuation
    text = re.sub(r"\s*[\.\s…\-]+$", "", text)
    
    # 10. Compress multiple consecutive newlines (3 or more) down to 2 newlines (1 empty line gap)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()



def search_and_extract(query: str, max_results: int = 5, format: str = "markdown") -> List[Dict[str, Any]]:
    """
    Search the web and extract full content for pages that require more details
    (e.g. they end with 'Read More' or similar), then return optimized noise-free content.
    
    Args:
        query: The search query string.
        max_results: The maximum number of search results to retrieve.
        format: The format of extracted content ('markdown' or 'text').
        
    Returns:
        A list of dicts, each containing:
        - url: The URL of the page.
        - content: The optimized, noise-free extracted content or original snippet.
        - score: The relevance score of the result.
        - title: The title of the page.
    """
    # 1. Search the web
    search_results = search_web(query, max_results=max_results)
    if not search_results:
        return []
        
    # 2. Check each result to see if we need to extract full page content
    urls_to_extract = []
    extract_indices = set()
    
    for idx, r in enumerate(search_results):
        snippet = (r.get("content") or "").strip()
        # Check if the snippet ends with "read more" (case-insensitive) or has it at the end
        normalized_snippet = snippet.lower()
        if (
            normalized_snippet.endswith("read more") 
            or normalized_snippet.endswith("readmore") 
            or "read more" in normalized_snippet[-20:]
            or "readmore" in normalized_snippet[-20:]
        ):
            urls_to_extract.append(r["url"])
            extract_indices.add(idx)
            
    # 3. Perform batch extraction if there are any URLs flagged for extraction
    extracted_data_map = {}
    if urls_to_extract:
        print(f"Flagged {len(urls_to_extract)} URL(s) ending with 'Read More' for full extraction...")
        extracted_results = extract_web_content(urls_to_extract, format=format)
        for ext in extracted_results:
            extracted_data_map[ext["url"]] = ext.get("raw_content")
            
    # 4. Construct final list with cleaned and optimized content
    final_results = []
    for idx, r in enumerate(search_results):
        url = r["url"]
        score = r["score"]
        title = r["title"]
        
        # Fetch raw content if it was extracted, otherwise fallback to the original search snippet
        raw_content = None
        if idx in extract_indices:
            raw_content = extracted_data_map.get(url)
            
        content_to_clean = raw_content if raw_content else r.get("content", "")
        optimized_content = clean_and_optimize_content(content_to_clean)
        
        final_results.append({
            "url": url,
            "content": optimized_content,
            "score": score,
            "title": title
        })
        
    return final_results


if __name__ == "__main__":
    # If a query is provided via command line, use it; otherwise, use a default query.
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is cancellation policy of air india?"
    
    print(f"Running combined Search & Extract for: '{query}'...")
    results = search_and_extract(query, max_results=3, format="markdown")
    
    if not results:
        print("No results returned.")
    else:
        print(f"\nCompleted Search & Extract. Returned {len(results)} optimized results:")
        for idx, result in enumerate(results, 1):
            print("=" * 80)
            print(f"Result {idx}: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Score: {result['score']:.4f}")
            print("-" * 80)
            # Print a snippet of the optimized content to keep output readable
            content_preview = result['content']
            if len(content_preview) > 500:
                print(content_preview[:500] + "\n... [TRUNCATED FOR DISPLAY] ...")
            else:
                print(content_preview)
        print("=" * 80)