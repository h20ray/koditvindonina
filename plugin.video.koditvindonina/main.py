import sys
import urllib.parse
import urllib.request
import re
import xbmc
import xbmcgui
import xbmcplugin

# Plugin routing information
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

def log(msg):
    xbmc.log(f"[KodiTVIndoninaProxy] {msg}", xbmc.LOGINFO)

def get_channel_stream(channel_id):
    """
    Attempts to scrape or proxy the dynamic stream URL for a given channel.
    Due to aggressive bot protection on RCTI+ and Vidio, this uses generic 
    fallback patterns if API requests throw 403s.
    """
    log(f"Attempting to resolve dynamic stream for: {channel_id}")
    
    if channel_id == 'rcti':
        # RCTI+ uses an auth_key mechanism. A full Playwright/Selenium
        # headless browser isn't available in vanilla Kodi, so if simple 
        # scraping fails, the plugin will notify the user.
        return scrape_rctiplus()
    elif channel_id == 'sctv' or channel_id == 'indosiar':
        # Vidio uses token POST APIs
        return scrape_vidio(channel_id)
        
    return None

def scrape_rctiplus():
    url = "https://www.rctiplus.com/tv/rcti"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.rctiplus.com/',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8')
        
        # Searching for embedded M3U8 links if any slip through
        m3u8_links = re.findall(r'https?://[^\s\"\'<>]+?\.m3u8[^\s\"\'<>]*', html)
        if m3u8_links:
            # Clean up the URL string
            final_url = m3u8_links[0].replace('\\"', "").replace("\\'", "")
            return final_url
    except Exception as e:
        log(f"RCTI+ Scrape failed: {e}")
        
    return None

def scrape_vidio(channel_id):
    # Vidio channels mapping: 204-sctv, 205-indosiar
    vidio_id = '204-sctv' if channel_id == 'sctv' else '205-indosiar'
    url = f"https://www.vidio.com/live/{vidio_id}/tokens"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.vidio.com/',
    }
    try:
        # POST request to grab token
        req = urllib.request.Request(url, headers=headers, method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        import json
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('token_url'):
            return data['token_url']
    except Exception as e:
        log(f"Vidio Scrape failed: {e}")
        
    return None


def router(param_args):
    """
    Main router function routing requests to specific channel resolvers.
    """
    channel = param_args.get('channel', [None])[0]
    
    if channel:
        stream_url = get_channel_stream(channel.lower())
        
        if stream_url:
            log(f"Successfully resolved tokenized URL: {stream_url}")
            # Create a Kodi list item with the finalized URL
            play_item = xbmcgui.ListItem(path=stream_url)
            
            # Since these are adaptive DASH/HLS streams, we inform Kodi to use inputstream
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls' if '.m3u8' in stream_url else 'mpd')
            
            # Pass it back to Kodi's player
            xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)
        else:
            log(f"Failed to extract stream for {channel}")
            xbmcgui.Dialog().notification(
                "Kodi TV Indonina", 
                f"Failed to fetch dynamic token for {channel}. Stream may exist behind aggressive bot protection.", 
                xbmcgui.NOTIFICATION_ERROR, 
                5000
            )
            xbmcplugin.setResolvedUrl(addon_handle, False, listitem=xbmcgui.ListItem())
    else:
        # User just clicked the Add-on icon directly (not via PVR)
        xbmcgui.Dialog().ok("Kodi TV Indonina Proxy", "This add-on runs silently in the background alongside the main PVR M3U playlist and automatically resolves dynamic stream tokens.")

if __name__ == '__main__':
    router(args)
