import urllib.request
import urllib.error
import concurrent.futures
import time
import argparse
import sys
import ssl
import os

# Abaikan error sertifikat SSL
ssl._create_default_https_context = ssl._create_unverified_context

def check_url(url, user_agent=None, referrer=None, timeout=10):
    # Lewati pemisah grup channel (misalnya: https:///// MOVIES /////)
    if url.startswith("https://///") or url.startswith("http://///") or url.strip() == "":
        return False, "Grup Pemisah / URL Kosong"

    req = urllib.request.Request(url, method='GET')
    
    # Tambahin User-Agent (pake yang ada di file, atau default browser biar gak diblokir 403)
    if user_agent:
        req.add_header('User-Agent', user_agent)
    else:
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    # Tambahin Referrer kalo diset di file m3u
    if referrer:
        req.add_header('Referer', referrer)

    try:
        # Jalanin request
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            if status_code in (200, 206, 301, 302, 307, 308):
                return True, f"Online ({status_code})"
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Error: {e}"
        
    return False, "Error Gak Jelas"


def parse_m3u(file_path):
    """
    Parse file M3U dan balikin:
    - daftar channel (nama, url, UA, referrer, index, dan raw lines per channel)
    - header_lines global (misalnya #EXTM3U dan komentar sebelum channel pertama)
    """
    channels = []
    header_lines = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_lines = f.readlines()
        
    current_name = ""
    current_ua = None
    current_ref = None
    current_block_lines = []
    seen_first_channel = False
    channel_index = 0
    
    for raw_line in raw_lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        
        # Kumpulin header global sebelum channel pertama
        if not seen_first_channel:
            if stripped.startswith("#EXTINF:") or (stripped and not stripped.startswith("#")):
                seen_first_channel = True
            else:
                header_lines.append(line)
                continue
        
        if not stripped:
            continue
            
        if stripped.startswith("#EXTINF:"):
            # Kalau ada block channel sebelumnya yang belum disimpan (tanpa URL valid), reset saja
            if current_block_lines and current_name and current_block_lines:
                current_block_lines = []
            
            current_block_lines = [line]
            parts = stripped.split(",", 1)
            if len(parts) > 1:
                current_name = parts[1].strip()
            else:
                current_name = ""
            current_ua = None
            current_ref = None
            
        elif stripped.startswith("#EXTVLCOPT:http-user-agent="):
            current_ua = stripped.split("=", 1)[1].strip()
            if current_block_lines is not None:
                current_block_lines.append(line)
            
        elif stripped.startswith("#EXTVLCOPT:http-referrer="):
            current_ref = stripped.split("=", 1)[1].strip()
            if current_block_lines is not None:
                current_block_lines.append(line)
            
        elif not stripped.startswith("#"):
            url = stripped
            
            # Abaikan URL yang cuma marker kategori
            if url.startswith("https://///") or url.startswith("http://///") or url.strip() == "":
                current_name = ""
                current_ua = None
                current_ref = None
                current_block_lines = []
                continue
                
            # Kalo gak ada namanya (biasanya gara-gara lupa dikasih #EXTINF), kita skip aja biar daftar tetep rapi
            if not current_name:
                current_block_lines = []
                continue
            
            if current_block_lines is not None:
                current_block_lines.append(line)
            
            channels.append({
                'index': channel_index,
                'name': current_name,
                'url': url,
                'user_agent': current_ua,
                'referrer': current_ref,
                'lines': list(current_block_lines),
            })
            channel_index += 1
            
            # Reset setelah dapet URL buat siap-siap ke channel berikutnya
            current_name = ""
            current_ua = None
            current_ref = None
            current_block_lines = []
            
    return channels, header_lines


def process_channel(idx, total, channel):
    is_online, status_msg = check_url(channel['url'], channel['user_agent'], channel['referrer'])
    status_str = "ONLINE " if is_online else "OFFLINE"
    
    # Kasih warna dikit ke terminal biar cakep
    indicator = "\x1b[92m[+]\x1b[0m" if is_online else "\x1b[91m[-]\x1b[0m"
    try:
        sys.stdout.write(f"[{idx}/{total}] {indicator} {status_str} | {channel['name']} | {status_msg}\n")
    except UnicodeEncodeError:
        # Jaga-jaga kalo terminalnya gak support karakter aneh di nama channel
        name_ascii = channel['name'].encode('ascii', 'ignore').decode('ascii')
        sys.stdout.write(f"[{idx}/{total}] [+] {status_str} | {name_ascii} | {status_msg}\n")
        
    return channel, is_online, status_msg


def update_readme(results, total, online, offline):
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return
        
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start_marker = "<!-- STATUS_START -->"
    end_marker = "<!-- STATUS_END -->"
    
    if start_marker not in content or end_marker not in content:
        print("Gak nemu marker <!-- STATUS_START --> atau <!-- STATUS_END --> di README.md")
        return
        
    # Bikin teks laporan buat README
    report = f"**Terakhir Diupdate: {time.strftime('%Y-%m-%d %H:%M:%S')}**\n\n"
    report += f"- **Total Channel:** {total}\n"
    report += f"- **Online:** 🟢 {online}\n"
    report += f"- **Offline:** 🔴 {offline}\n\n"
    
    report += "### Daftar Channel Online\n"
    for r in results:
        if r[1]: # Jika online
            report += f"- 🟢 {r[0]['name']}\n"
            
    report += "\n### Daftar Channel Offline\n"
    for r in results:
        if not r[1]: # Jika offline
            report += f"- 🔴 {r[0]['name']}\n"
            
    # Ganti teks di antara marker
    before = content.split(start_marker)[0]
    after = content.split(end_marker)[1]
    
    new_content = before + start_marker + "\n" + report + "\n" + end_marker + after
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def derive_offline_filename(m3u_path):
    root, ext = os.path.splitext(m3u_path)
    if not ext:
        ext = ".m3u"
    return f"{root}_offline{ext}"


def write_split_m3u(input_m3u, header_lines, channels, status_by_index, online_file=None, offline_file=None):
    """
    Tulis ulang playlist:
    - file online: cuma channel yang statusnya online
    - file offline: cuma channel yang statusnya offline
    Struktur per channel (EXTINF, EXTVLCOPT, URL) dipertahankan.
    """
    if online_file is None:
        online_file = input_m3u
    if offline_file is None:
        offline_file = derive_offline_filename(input_m3u)
    
    # Pastikan ada minimal satu header, dan jaga #EXTM3U di paling atas
    def normalize_header(lines):
        if not lines:
            return ["#EXTM3U"]
        if not any(l.strip().upper().startswith("#EXTM3U") for l in lines):
            return ["#EXTM3U"] + lines
        return lines
    
    header_lines = normalize_header(header_lines)
    
    online_channels = []
    offline_channels = []
    for ch in sorted(channels, key=lambda c: c.get('index', 0)):
        idx = ch.get('index', 0)
        is_online = status_by_index.get(idx, False)
        if is_online:
            online_channels.append(ch)
        else:
            offline_channels.append(ch)
    
    def write_playlist(path, chan_list):
        with open(path, "w", encoding="utf-8") as f:
            for hl in header_lines:
                f.write(hl.rstrip("\n") + "\n")
            for ch in chan_list:
                for ln in ch.get('lines', []):
                    f.write(ln.rstrip("\n") + "\n")
    
    write_playlist(online_file, online_channels)
    write_playlist(offline_file, offline_channels)


def main():
    parser = argparse.ArgumentParser(description="M3U Channel Status Checker (Versi Indo)")
    parser.add_argument("m3u_file", nargs='?', default="indonina.m3u", help="Path ke file M3U")
    parser.add_argument("--workers", type=int, default=15, help="Jumlah worker buat ngecek barengan (default 15)")
    parser.add_argument("--output", type=str, default="status_report.txt", help="File output buat nyimpen hasil laporan")
    parser.add_argument("--online-file", type=str, default=None, help="File output untuk channel ONLINE saja (default: overwrite m3u_file)")
    parser.add_argument("--offline-file", type=str, default=None, help="File output untuk channel OFFLINE saja (default: <nama>_offline.m3u)")
    args = parser.parse_args()
    
    # Coba aktifin escape codes VT100 di Windows biar warnanya muncul
    if os.name == 'nt':
        os.system('')
    
    print(f"Lagi baca file '{args.m3u_file}'...")
    try:
        channels, header_lines = parse_m3u(args.m3u_file)
    except FileNotFoundError:
        print(f"Yah, filenya gak ketemu: {args.m3u_file}")
        return
        
    total_channels = len(channels)
    if total_channels == 0:
        print("Gak ada channel yang ketemu di file M3U ini.")
        return
        
    print(f"Mantap, nemu {total_channels} channel. Mulai ngecek status pake {args.workers} worker...\n")
    
    results = []
    start_time = time.time()
    
    # Cek URL barengan biar cepet
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_channel, i, total_channels, channel): channel 
            for i, channel in enumerate(channels, 1)
        }
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            
    elapsed_time = time.time() - start_time
    print(f"\nSelesai ngecek semuanya dalam {elapsed_time:.2f} detik.")
    
    # Bikin rekap statistik
    online_count = sum(1 for r in results if r[1])
    offline_count = total_channels - online_count
    print(f"Total Channel: {total_channels} | Online: {online_count} | Offline: {offline_count}")
    
    # Tulis laporannya ke file teks
    with open(args.output, "w", encoding='utf-8') as f:
        f.write(f"Laporan Status Channel M3U - {args.m3u_file}\n")
        f.write(f"Dibuat tanggal: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total: {total_channels} | Online: {online_count} | Offline: {offline_count}\n")
        f.write("=" * 60 + "\n\n")
        
        # Urutin hasilnya: yang Online duluan, abis itu urut abjad
        results_sorted = sorted(results, key=lambda x: (not x[1], x[0]['name'].lower()))
        
        for channel, is_online, status_msg in results_sorted:
            status = "ONLINE" if is_online else "OFFLINE"
            f.write(f"[{status}] {channel['name']}\n")
            f.write(f"URL:    {channel['url']}\n")
            f.write(f"Status: {status_msg}\n")
            f.write("-" * 60 + "\n")
        
    print(f"Sip! Laporan teks lengkapnya udah disimpen ke '{args.output}'")
    
    # Update README
    print("Lagi update README.md biar dinamis...")
    try:
        update_readme(results_sorted, total_channels, online_count, offline_count)
        print("Sip, README.md udah beres diupdate!")
    except Exception as e:
        print(f"Waduh, gagal update README.md: {e}")
    
    # Tulis ulang M3U: online only + offline companion
    print("Lagi split playlist jadi online & offline...")
    try:
        status_by_index = {}
        for ch, is_online, _msg in results:
            idx = ch.get("index", 0)
            # Kalau channel dengan index sama dicek lebih dari sekali, terakhir yang kepake
            status_by_index[idx] = is_online
        
        online_file = args.online_file if args.online_file else args.m3u_file
        offline_file = args.offline_file if args.offline_file else derive_offline_filename(args.m3u_file)
        
        write_split_m3u(args.m3u_file, header_lines, channels, status_by_index, online_file=online_file, offline_file=offline_file)
        print(f"Sip! '{online_file}' sekarang cuma isi channel ONLINE, dan '{offline_file}' isi channel OFFLINE.")
    except Exception as e:
        print(f"Waduh, gagal split playlist online/offline: {e}")


if __name__ == "__main__":
    main()
