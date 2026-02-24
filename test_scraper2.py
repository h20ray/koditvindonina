import re
import urllib.request
import json

url = 'https://www.rctiplus.com/tv/rcti'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.rctiplus.com/',
}

req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode('utf-8', errors='ignore')

scripts = re.findall(r'<script.*?>\s*(.*?)\s*</script>', html, re.DOTALL)
access_token = None
for s in scripts:
    if 'accessToken' in s:
        # Example: accessToken: 'xxxx' or accessToken = 'xxxx'
        match = re.search(r'accessToken[\"\':\s]+([a-zA-Z0-9\-\_\.]+)', s)
        if match:
            access_token = match.group(1)
            break

print('Extracted Access Token:', access_token)

if access_token:
    api_url = 'https://api.rctiplus.com/api/v1/live/url/rcti'
    api_headers = headers.copy()
    api_headers['Authorization'] = access_token
    
    try:
        req2 = urllib.request.Request(api_url, headers=api_headers)
        resp2 = urllib.request.urlopen(req2, timeout=10)
        data = json.loads(resp2.read().decode('utf-8'))
        print('API Response:', json.dumps(data, indent=2))
        
        # If API gives us the link with the auth_key, we want to see it!
        if data.get('data') and data['data'].get('url'):
            print("Successfully extracted streaming URL:", data['data']['url'])
            
    except Exception as e:
        print('API Error:', e)
