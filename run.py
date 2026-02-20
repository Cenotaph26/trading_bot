import os
import http.server
import sys
import webbrowser

# 1. Railway'in dinamik portunu al (Bulamazsa 8000 yap)
PORT = int(os.environ.get("PORT", 8000))

# 2. Sunucuda olmayan tarayıcıyı açma komutunu etkisiz hale getir
webbrowser.open = lambda x: None 

# 3. KODU DEĞİŞTİRMEDEN 'localhost' ENGELİNİ AŞMA (YAMA)
# trading_bot.py içindeki HTTPServer çağrısını yakalayıp 0.0.0.0'a zorlar
class RailwayServer(http.server.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        # Orijinal kod ne gönderirse göndersin (localhost, 8000 gibi)
        # biz onu Railway'in dışa açık adresi ve portuyla değiştiriyoruz
        super().__init__(('0.0.0.0', PORT), RequestHandlerClass, bind_and_activate)

# Orijinal kütüphaneyi bizim yama ile değiştiriyoruz
http.server.HTTPServer = RailwayServer

# 4. Orijinal botu çalıştır
try:
    import trading_bot
except Exception as e:
    print(f"Hata oluştu: {e}")
    sys.exit(1)

if __name__ == '__main__':
    print(f"--- BOT BAŞLATILDI ---")
    print(f"Railway Portu: {PORT} üzerinden yayın yapılıyor.")
    trading_bot.main()
