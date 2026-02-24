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
    channels = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    current_name = ""
    current_ua = None
    current_ref = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("#EXTINF:"):
            # Ambil nama channel dari baris EXTINF
            parts = line.split(",", 1)
            if len(parts) > 1:
                current_name = parts[1].strip()
            # Reset header buat channel yang baru
            current_ua = None
            current_ref = None
            
        elif line.startswith("#EXTVLCOPT:http-user-agent="):
            current_ua = line.split("=", 1)[1].strip()
            
        elif line.startswith("#EXTVLCOPT:http-referrer="):
            current_ref = line.split("=", 1)[1].strip()
            
        elif not line.startswith("#"):
            url = line
            
            # Abaikan URL yang cuma marker kategori
            if url.startswith("https://///") or url.startswith("http://///") or url.strip() == "":
                current_name = ""
                current_ua = None
                current_ref = None
                continue
                
            # Kalo gak ada namanya (biasanya gara-gara lupa dikasih #EXTINF), kita skip aja biar daftar tetep rapi
            if not current_name:
                continue
                
            # Ini URL beneran, jadi kita masukin ke daftar channel
            channels.append({
                'name': current_name,
                'url': url,
                'user_agent': current_ua,
                'referrer': current_ref
            })
            # Reset setelah dapet URL buat siap-siap ke channel berikutnya
            current_name = ""
            current_ua = None
            current_ref = None
            
    return channels


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


def main():
    parser = argparse.ArgumentParser(description="M3U Channel Status Checker (Versi Indo)")
    parser.add_argument("m3u_file", nargs='?', default="indonina.m3u", help="Path ke file M3U")
    parser.add_argument("--workers", type=int, default=15, help="Jumlah worker buat ngecek barengan (default 15)")
    parser.add_argument("--output", type=str, default="status_report.txt", help="File output buat nyimpen hasil laporan")
    args = parser.parse_args()
    
    # Coba aktifin escape codes VT100 di Windows biar warnanya muncul
    if os.name == 'nt':
        os.system('')
    
    print(f"Lagi baca file '{args.m3u_file}'...")
    try:
        channels = parse_m3u(args.m3u_file)
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


if __name__ == "__main__":
    main()
