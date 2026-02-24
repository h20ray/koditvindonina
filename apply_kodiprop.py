import re

template_file = 'template_kodi_example_playlist.m3u'
target_file = 'indonina.m3u'

# 1. Parsing Template
print(f"Membaca {template_file}...")
with open(template_file, 'r', encoding='utf-8') as f:
    template_lines = f.readlines()

template_channels = {}
current_name = None
current_props = []

for line in template_lines:
    line = line.strip()
    if not line:
        continue
    if line.startswith('#EXTM3U'):
        continue
        
    if line.startswith('#EXTINF:'):
        # Extract name: format is group-title="...",ChannelName
        parts = line.split(',')
        if len(parts) > 1:
            # The channel name is everything after the last comma
            # or sometimes just the last part
            current_name = parts[-1].strip()
            # Bersihkan angka 1/2 dll dari ujung string di template misal "RCTI 1"
            base_name = re.sub(r' \d+$', '', current_name) 
            current_props = []
            
            # Store the current name so we're ready to collect props
            current_name = base_name.lower().replace(" ", "")
    elif line.startswith('#EXTVLCOPT:') or line.startswith('#KODIPROP:'):
        current_props.append(line)
    elif not line.startswith('#'):
        # This is the URL
        url = line
        if current_name:
            # Jika udah ada, kita gak nimpa (biar dapet server utama, bukan yang 1 atau 2)
            if current_name not in template_channels:
                template_channels[current_name] = {
                    'props': current_props,
                    'url': url
                }
        current_name = None
        current_props = []

print(f"Ditemukan {len(template_channels)} channel referensi dari template.")

# 2. Update indonina.m3u
print(f"Mengupdate {target_file}...")
with open(target_file, 'r', encoding='utf-8') as f:
    target_lines = f.readlines()

new_lines = []
current_target_name = None

i = 0
while i < len(target_lines):
    line = target_lines[i].strip()
    
    if line.startswith('#EXTINF:'):
        new_lines.append(line + '\n')
        parts = line.split(',')
        if len(parts) > 1:
            current_target_name = parts[-1].strip().lower().replace(" ", "")
        i += 1
        continue
        
    # Skip old properties because we'll inject new ones
    if line.startswith('#EXTVLCOPT:') or line.startswith('#KODIPROP:'):
        i += 1
        continue
        
    # Valid URL line
    if not line.startswith('#') and line != '':
        url = line
        
        # Check if we have a template override for this channel
        if current_target_name and current_target_name in template_channels:
            print(f"-> Menerapkan resep KODIPROP/DRM untuk {current_target_name}")
            props = template_channels[current_target_name]['props']
            # Override URL with template URL since template URLs support the DRM keys
            template_url = template_channels[current_target_name]['url']
            
            # Inject properties
            for prop in props:
                new_lines.append(prop + '\n')
            new_lines.append(template_url + '\n')
        else:
            # Not in template, let's inject default KODIPROP for generic m3u8 if it's an m3u8 stream
            # The template uses inputstream.adaptive for basically everything.
            if '.m3u8' in url:
                new_lines.append('#KODIPROP:inputstream=inputstream.adaptive\n')
                new_lines.append('#KODIPROP:inputstreamaddon=inputstream.adaptive\n')
                new_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=hls\n')
            elif '.mpd' in url:
                new_lines.append('#KODIPROP:inputstream=inputstream.adaptive\n')
                new_lines.append('#KODIPROP:inputstreamaddon=inputstream.adaptive\n')
                new_lines.append('#KODIPROP:inputstream.adaptive.manifest_type=mpd\n')
                
            new_lines.append(url + '\n')
            
        current_target_name = None
        i += 1
    else:
        new_lines.append(line + '\n')
        i += 1

with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("Proses refactor selesai! File m3u sekarang memakai KODIPROP.")
