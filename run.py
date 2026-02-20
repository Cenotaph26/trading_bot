import os
import http.server
import sys
import webbrowser

# 1. Railway'in dinamik portunu al (Bulamazsa varsayılan 8000)
PORT = int(os.environ.get("PORT", 8000))

# 2. Sunucuda olmayan tarayıcıyı açma komutunu iptal et (Hata vermemesi için)
webbrowser.open = lambda x: None 

# 3. KODU DEĞİŞTİRMEDEN 'localhost' ENGELİNİ AŞAN YAMA
class RailwayServer(http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Orijinal kod ('localhost', 8000) gönderse bile biz onu 
        # ('0.0.0.0', PORT) yaparak dış dünyaya açıyoruz.
        super().__init__(('0.0.0.0', PORT), RequestHandlerClass, bind_and_activate)

# Python'ın kendi kütüphanesini bizim yamalı versiyonumuzla değiştiriyoruz
http.server.HTTPServer = RailwayServer

# 4. Orijinal dosyanı şimdi içe aktarabiliriz
try:
    import trading_bot
except Exception as e:
    print(f"Hata: trading_bot.py yüklenirken sorun oluştu: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print(f"--- WEB ARAYÜZÜ HAZIRLANIYOR ---")
    print(f"Sunucu adresi: 0.0.0.0:{PORT}")
    # Senin orijinal main() fonksiyonunu tetikliyoruz
    trading_bot.main()
