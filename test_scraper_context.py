import re
import urllib.request

url = 'https://www.rctiplus.com/tv/rcti'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.rctiplus.com/',
}

print("Fetching...")
req = urllib.request.Request(url, headers=headers)
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode('utf-8', errors='ignore')

scripts = re.findall(r'<script.*?>\s*(.*?)\s*</script>', html, re.DOTALL)
for s in scripts:
    if 'accessToken' in s:
        idx = s.find('accessToken')
        print("FOUND CONTEXT:\n", s[max(0, idx-50):min(len(s), idx+200)])
