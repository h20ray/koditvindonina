import os

# List all available icons
icon_files = os.listdir('icons')
print(f"Ditemukan {len(icon_files)} icon buat dipacokin.")

m3u_path = 'indonina.m3u'
with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('#EXTINF:'):
        # Bagi baris jadi metadata durasi & atribut, lalu nama channel
        parts = line.split(',', 1)
        if len(parts) > 1:
            channel_name = parts[1].strip()
            
            # Format nama buat pencocokan (hilangin spasi, simbol, lowercase)
            search_name = channel_name.lower().replace(' ', '').replace('.', '').replace('hd', '')
            
            icon_url = ''
            group_title = 'Lainnya'
            
            # Coba cari tau nama file icon yang cocok
            for icon in icon_files:
                icon_base = icon.split('.')[0].lower()
                
                # Spesifik buat TVRI karena formatnya sama semua (tvri.png)
                if 'tvri' in search_name:
                    icon_url = 'https://raw.githubusercontent.com/h20ray/koditvindonina/main/icons/tvri.png'
                    break
                # Cocokin nama file sama nama channel 
                elif search_name == icon_base or search_name.startswith(icon_base) or icon_base.startswith(search_name):
                    icon_url = f'https://raw.githubusercontent.com/h20ray/koditvindonina/main/icons/{icon}'
                    break
            
            metadata = parts[0]
            
            # Ambil group title asli dari file m3u kalo udah didefinisiin sebelumnya
            if 'group-title=' in metadata:
                try:
                    group_title = metadata.split('group-title="')[1].split('"')[0]
                except IndexError:
                    pass
            
            # Kalo gak ada group title asli & nama channelnya ada hubungannya sama TVRI
            if group_title == 'Lainnya' and 'TVRI' in channel_name:
                 if 'Nasional' in channel_name or 'World' in channel_name:
                     group_title = 'Nasional'
                 elif 'Sport' in channel_name:
                     group_title = 'Olahraga'
                 else:
                     group_title = 'Regional'
            
            # Bersihin atribut lama (kayak tvg-logo lama atau group-title biar gak double)
            if ' tvg-' in metadata:
                metadata = metadata.split(' tvg-')[0]
            if ' group-title' in metadata:
                metadata = metadata.split(' group-title')[0]
                
            # Bersihin ID biar aman dipake Kodi
            safe_id = channel_name.replace(' ', '').replace('.', '')
            
            # Rakit ulang pake format Kodi template (#EXTINF:-1 tvg-id="..." tvg-logo="..." group-title="...",Nama Channel)
            new_line = f'{metadata} tvg-id="{safe_id}.id" tvg-logo="{icon_url}" group-title="{group_title}",{channel_name}\n'
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Simpan langsung numpuk ke file asli
with open(m3u_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("Selesai generate format Kodi ke indonina.m3u!")
