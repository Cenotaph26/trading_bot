import os
import http.server
import sys
import webbrowser

# 1. Railway'in dinamik portunu al, yoksa 8000 kullan
PORT = int(os.environ.get("PORT", 8000))

# 2. Sunucuda tarayıcı açmaya çalışıp hata vermesini engelle
webbrowser.open = lambda x: None 

# 3. Orijinal koddaki (localhost, 8000) kısmını ezecek yama
class RailwayServer(http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Orijinal kod ne gönderirse göndersin, biz 0.0.0.0 ve Railway portuna zorluyoruz
        super().__init__(('0.0.0.0', PORT), RequestHandlerClass, bind_and_activate)

# Python'ın standart kütüphanesindeki sınıfı bizim yamalı versiyonumuzla değiştiriyoruz
http.server.HTTPServer = RailwayServer

# 4. Orijinal dosyanı içe aktar
try:
    import trading_bot
except Exception as e:
    print(f"Hata: trading_bot.py yuklenemedi: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print(f"--- BOT AKTIF EDILIYOR ---")
    print(f"Railway Portu: {PORT} dinleniyor...")
    # Senin orijinal dosmandaki main() fonksiyonunu çağırır
    trading_bot.main()
