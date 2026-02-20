import os
import http.server
import sys
import threading
import time

# 1. Railway Port Ayarı
PORT = int(os.environ.get("PORT", 8000))

# 2. Tarayıcı açma hatasını engelle (Sunucuda ekran yoktur)
import webbrowser
webbrowser.open = lambda x: None 

# 3. HTTPServer'ı Railway'e göre yamala
# Bu kısım senin trading_bot içindeki 'localhost'u geçersiz kılar
class RailwayServer(http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Orijinal kod ne isterse istesin, biz 0.0.0.0:PORT veriyoruz
        super().__init__(('0.0.0.0', PORT), RequestHandlerClass, bind_and_activate)

http.server.HTTPServer = RailwayServer

# 4. Orijinal botu içe aktar
try:
    import trading_bot
except Exception as e:
    print(f"Bot yüklenirken hata oluştu: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print(f"--- Railway Başlatılıyor ---")
    print(f"Port: {PORT}")
    # Orijinal main() fonksiyonunu çalıştır
    trading_bot.main()
