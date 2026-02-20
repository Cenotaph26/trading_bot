import os
import http.server

# 1. Railway'in dinamik atadığı portu al
PORT = int(os.environ.get("PORT", 8000))

# 2. Orijinal sunucu sınıfını yedekle
OriginalHTTPServer = http.server.HTTPServer

# 3. 'localhost' ve '8000' değerlerini ezip 0.0.0.0 ve Railway portuna yönlendiren yeni sınıf
class PatchedHTTPServer(OriginalHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Orijinal kodu kandırıp 0.0.0.0 ve dinamik porta yönlendiriyoruz
        super().__init__(('0.0.0.0', PORT), RequestHandlerClass, bind_and_activate)

# 4. Sistemin sunucu sınıfını bizimkiyle değiştir
http.server.HTTPServer = PatchedHTTPServer

# 5. Ana bot kodunu içe aktar ve çalıştır (Hiç değiştirilmemiş haliyle)
import trading_bot

if __name__ == '__main__':
    print(f"🚀 Railway Modu Aktif: Sunucu 0.0.0.0 ve {PORT} portundan ayağa kaldırılıyor...")
    trading_bot.main()
