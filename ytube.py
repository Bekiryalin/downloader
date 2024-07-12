import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yt_dlp
import urllib.parse
import os
import queue

# Sabit Değerler
DOWNLOAD_TYPES = {
    "Ses + Görüntü": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "Sadece Ses": "bestaudio[ext=m4a]/best[ext=m4a]/best",
    "Sadece Görüntü": "bestvideo[ext=mp4]/best[ext=mp4]/best",
}

# FFmpeg Dosyasının Yolu (Uygulama Klasörü)
ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe")

class DownloadManager:
    def __init__(self, master, ffmpeg_path, progress_bar, progress_label, download_button, stop_button):
        self.master = master
        self.ffmpeg_path = ffmpeg_path
        self.download_thread = None
        self.stop_download_event = threading.Event()
        self.download_queue = queue.Queue()
        self.progress_bar = progress_bar
        self.progress_label = progress_label
        self.download_button = download_button
        self.stop_button = stop_button

    def download_video(self, url, format_selection):
        try:
            self.download_thread = threading.Thread(target=self.download_worker, args=(url, format_selection))
            self.download_thread.start()

            self.download_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)  # "Durdur" butonunu aktifleştir

            self.master.after(100, self.update_progress)

        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu: {e}")
            self.download_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def download_worker(self, url, format_selection):
        try:
            ydl_opts = {
                'format': format_selection,
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': '%(title)s.%(ext)s',
                'progress_hooks': [self.update_progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                video_title = info_dict['title']

                self.download_queue.put(('status', f"{video_title} indiriliyor..."))
                ydl.download([url])

                self.download_queue.put(('status', f"{video_title} başarıyla indirildi!"))

            self.download_queue.put(('status', "İndirme tamamlandı!"))

        except Exception as e:
            self.download_queue.put(('status', f"Bir hata oluştu: {e}"))

    def update_progress_hook(self, download):
        if '_total_bytes' in download and '_bytes_downloaded' in download:
            progress = (download['_bytes_downloaded'] / download['_total_bytes']) * 100
            self.download_queue.put(('progress', progress))
        elif '_total_bytes_estimate' in download and '_bytes_downloaded' in download:
            progress = (download['_bytes_downloaded'] / download['_total_bytes_estimate']) * 100
            self.download_queue.put(('progress', progress))

    def update_progress(self):
        try:
            while not self.download_queue.empty():
                msg = self.download_queue.get_nowait()
                if msg[0] == 'progress':
                    self.progress_bar['value'] = msg[1]
                elif msg[0] == 'status':
                    self.progress_label.config(text=msg[1])
        except queue.Empty:
            pass
        finally:
            if self.download_thread and self.download_thread.is_alive():
                self.master.after(100, self.update_progress)
            else:
                self.progress_bar.stop()
                self.download_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)

    def update_progress_bar(self, progress):
        self.progress_bar['value'] = progress

    def update_status(self, status):
        self.progress_label.config(text=status)

    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.stop_download_event.set()
            self.progress_label.config(text="İndirme durduruluyor...")
            self.download_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.download_thread.join()

class VideoDownloaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("YouTube Video İndirme Aracı")

        self.url_label = tk.Label(self.master, text="Video URL'si:")
        self.url_label.pack(pady=5)
        self.url_entry = tk.Entry(self.master, width=50)
        self.url_entry.pack(pady=5)

        self.analyze_button = tk.Button(self.master, text="Analiz Et", command=self.analyze_video)
        self.analyze_button.pack(pady=5)

        self.quality_label = tk.Label(self.master, text="Çözünürlük Seçimi:")
        self.quality_label.pack(pady=5)
        self.quality_var = tk.StringVar(self.master)
        self.quality_var.set("")
        self.quality_menu = ttk.Combobox(self.master, textvariable=self.quality_var, state='readonly')
        self.quality_menu.pack(pady=5)

        self.download_button = tk.Button(self.master, text="İndir", command=self.start_download, state=tk.DISABLED)
        self.download_button.pack(pady=10)

        self.progress_label = tk.Label(self.master, text="")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        # "Durdur" butonunu tanımla
        self.stop_button = tk.Button(self.master, text="Durdur", command=self.stop_download, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        self.download_manager = DownloadManager(self.master, ffmpeg_path, self.progress_bar, self.progress_label, self.download_button, self.stop_button)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def analyze_video(self):
        url = self.url_entry.get()
        if url:
            try:
                urllib.parse.urlparse(url)
                self.progress_label.config(text="Video analiz ediliyor. Lütfen bekleyin...")
                self.progress_bar.start()

                ydl_opts = {
                    'quiet': True,
                    'format': 'best',
                    'ffmpeg_location': ffmpeg_path,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    formats = info_dict.get('formats', [])

                    # Debugging purposes
                    print("Formats retrieved:", formats)

                quality_options = []
                for format in formats:
                    format_note = format.get('format_note', 'Bilinmiyor')
                    resolution = format.get('resolution')
                    if resolution and resolution.startswith(('360', '720', '1080', '1440', '2160')):
                        quality_label = f"{format_note} - {resolution}"
                        quality_options.append(f"{format['format_id']} - {quality_label}")
                    elif format.get('width') and format.get('height'):
                        width = format.get('width')
                        height = format.get('height')
                        resolution = f"{width}x{height}"
                        quality_label = f"{format_note} - {resolution}"
                        quality_options.append(f"{format['format_id']} - {quality_label}")

                self.quality_var.set("")
                self.quality_menu['values'] = quality_options
                if quality_options:
                    self.quality_var.set(quality_options[0])
                    self.download_button.config(state=tk.NORMAL)
                else:
                    self.quality_var.set("")
                    self.download_button.config(state=tk.DISABLED)

                self.progress_bar.stop()
                self.progress_label.config(text="")

            except ValueError:
                messagebox.showerror("Hata", "Geçersiz bir URL girdiniz.")
                self.progress_bar.stop()
                self.progress_label.config(text="")
                return 
            except Exception as e:
                messagebox.showerror("Hata", f"Kaliteler yüklenirken bir hata oluştu: {e}")
                self.progress_bar.stop()
                self.progress_label.config(text="")

    def start_download(self):
        url = self.url_entry.get()
        selected_quality = self.quality_var.get()

        if not url:
            messagebox.showerror("Hata", "Lütfen bir video URL'si girin!")
            return

        if not selected_quality:
            messagebox.showerror("Hata", "Lütfen bir çözünürlük seçin!")
            return

        self.progress_label.config(text="İndirme başlıyor...")
        self.progress_bar.start()

        format_selection = selected_quality.split(" - ")[0]  # format_id'yi seç
        self.download_manager.download_video(url, format_selection)

        self.download_button.config(state=tk.DISABLED)

    def stop_download(self):
        self.download_manager.stop_download()

    def on_closing(self):
        if hasattr(self.download_manager, 'download_thread') and self.download_manager.download_thread and self.download_manager.download_thread.is_alive():
            messagebox.showwarning("İndirme Devam Ediyor", "Lütfen indirme işlemi tamamlanmadan pencereyi kapatmayın.")
        else:
            self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloaderApp(root)
    root.mainloop()