import re
import urllib.request
import json
import time

url = 'https://www.rctiplus.com/tv/rcti'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://www.rctiplus.com/',
}

print("Fetching RCTI+...")
try:
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode('utf-8', errors='ignore')
    
    print(f"Downloaded HTML size: {len(html)}")
    
    # RCTI may be putting its config into a script block, such as window.__INITIAL_STATE__
    # Search for common data structures
    scripts = re.findall(r'<script.*?>\s*(.*?)\s*</script>', html, re.DOTALL)
    print(f"Found {len(scripts)} scripts. Looking for tokens...")
    
    token_patterns = [
        r'accessToken', r'auth_key', r'm3u8', r'__PRELOADED_STATE__'
    ]
    
    for i, s in enumerate(scripts):
        for pattern in token_patterns:
            if re.search(pattern, s, re.IGNORECASE):
                print(f"-> Script {i} contains {pattern} (length: {len(s)})")
                if len(s) < 20000:
                    print(s[:500] + '...')

    urls = re.findall(r'https?://[^\s\"\'<>]+?\.m3u8[^\s\"\'<>]*', html)
    print("\nFound M3U8 inline:", urls)
    
except Exception as e:
    print("Error:", e)
