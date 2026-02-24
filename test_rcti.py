import urllib.request
import re

url = "https://www.rctiplus.com/tv/rcti"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=10)
    html = resp.read().decode('utf-8')
    
    # Look for NEXT_DATA
    next_data = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html)
    if next_data:
        print("Found __NEXT_DATA__ length:", len(next_data.group(1)))
        import json
        data = json.loads(next_data.group(1))
        # find anything with m3u8
        def find_m3u8(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    find_m3u8(v)
            elif isinstance(d, list):
                for i in d:
                    find_m3u8(i)
            elif isinstance(d, str) and '.m3u8' in d:
                print("Found in JSON:", d)
        find_m3u8(data)
    else:
        print("No __NEXT_DATA__ found. Printing first 500 chars:")
        print(html[:500])

        
except Exception as e:
    print("Error:", e)
