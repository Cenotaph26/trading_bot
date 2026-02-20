#!/usr/bin/env python3
"""AI Trading Bot v4.0 — Professional Dashboard"""

import random, time, json, threading, webbrowser, requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── BINANCE CLIENT ────────────────────────────────────────────
class BinanceClient:
    BASE = "https://fapi.binance.com"
    def __init__(self):
        self.symbols=[]
        self.ticker={}
        self.prices={}
        self._fetch_symbols()
        self._fetch_tickers()

    def _fetch_symbols(self):
        PRIORITY=['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT',
            'ADAUSDT','DOGEUSDT','DOTUSDT','MATICUSDT','AVAXUSDT',
            'LINKUSDT','UNIUSDT','LTCUSDT','BCHUSDT','ATOMUSDT',
            'ETCUSDT','APTUSDT','ARBUSDT','OPUSDT','NEARUSDT',
            'ICPUSDT','VETUSDT','INJUSDT','STXUSDT','THETAUSDT',
            'ALGOUSDT','FTMUSDT','SANDUSDT','MANAUSDT','AXSUSDT',
            'GALAUSDT','CHZUSDT','SUSHIUSDT','AAVEUSDT','COMPUSDT',
            'GRTUSDT','CRVUSDT','RUNEUSDT','SNXUSDT','1INCHUSDT',
            'FILUSDT','ROSEUSDT','ENJUSDT','BATUSDT','BALUSDT',
            'MKRUSDT','YFIUSDT','KSMUSDT','KNCUSDT','BANDUSDT',
            'SUIUSDT','SXPUSDT','ZILUSDT','QNTUSDT','EGLDUSDT',
            'FLOWUSDT','HBARUSDT','XLMUSDT','XTZUSDT','EOSUSDT',
            'TRXUSDT','DASHUSDT','ONTUSDT','CELOUSDT','LRCUSDT',
            'OCEANUSDT','STORJUSDT','RENUSDT','SKLUSDT','FETUSDT']
        try:
            r=requests.get(f"{self.BASE}/fapi/v1/exchangeInfo",timeout=10)
            valid={s['symbol'] for s in r.json()['symbols']
                   if s['symbol'].endswith('USDT')
                   and s['contractType']=='PERPETUAL'
                   and s['status']=='TRADING'}
            self.symbols=[s for s in PRIORITY if s in valid]
            rest=[s for s in valid if s not in self.symbols]
            self.symbols+=rest[:20]
            print(f"✓ {len(self.symbols)} pairs loaded")
        except Exception as e:
            print(f"symbols error: {e}")
            self.symbols=PRIORITY[:10]

    def _fetch_tickers(self):
        try:
            r=requests.get(f"{self.BASE}/fapi/v1/ticker/24hr",timeout=10)
            for t in r.json():
                s=t['symbol']
                if s in self.symbols:
                    self.ticker[s]={
                        'price':float(t['lastPrice']),
                        'change':float(t['priceChangePercent']),
                        'volume':float(t['volume']),
                        'high':float(t['highPrice']),
                        'low':float(t['lowPrice']),
                        'quoteVolume':float(t['quoteVolume']),
                    }
                    self.prices[s]=float(t['lastPrice'])
            print(f"✓ {len(self.ticker)} prices loaded")
        except Exception as e:
            print(f"ticker error: {e}")

    def refresh_prices(self):
        try:
            r=requests.get(f"{self.BASE}/fapi/v1/ticker/price",timeout=5)
            for t in r.json():
                if t['symbol'] in self.symbols:
                    p=float(t['price'])
                    self.prices[t['symbol']]=p
                    if t['symbol'] in self.ticker:
                        self.ticker[t['symbol']]['price']=p
        except: pass

    def refresh_tickers(self):
        try:
            r=requests.get(f"{self.BASE}/fapi/v1/ticker/24hr",timeout=10)
            for t in r.json():
                s=t['symbol']
                if s in self.symbols:
                    self.ticker[s].update({
                        'price':float(t['lastPrice']),
                        'change':float(t['priceChangePercent']),
                        'volume':float(t['volume']),
                        'high':float(t['highPrice']),
                        'low':float(t['lowPrice']),
                    })
                    self.prices[s]=float(t['lastPrice'])
        except: pass

    def klines(self, symbol, interval='5m', limit=60):
        try:
            r=requests.get(f"{self.BASE}/fapi/v1/klines",
                params={'symbol':symbol,'interval':interval,'limit':limit},timeout=10)
            return [{'t':k[0],'o':float(k[1]),'h':float(k[2]),
                     'l':float(k[3]),'c':float(k[4]),'v':float(k[5])}
                    for k in r.json()]
        except: return []

    def price(self,s): return self.prices.get(s,0)
    def info(self,s): return self.ticker.get(s,{})

# ── TECHNICAL ANALYSIS ───────────────────────────────────────
class TA:
    @staticmethod
    def rsi(p,n=14):
        if len(p)<n+1: return 50
        d=[p[i]-p[i-1] for i in range(1,len(p))]
        g=[x if x>0 else 0 for x in d[-n:]]
        l=[-x if x<0 else 0 for x in d[-n:]]
        ag,al=sum(g)/n,sum(l)/n
        if al==0: return 100
        return 100-(100/(1+ag/al))

    @staticmethod
    def ema(p,n):
        if len(p)<n: return p[-1]
        m=2/(n+1); e=p[-n]
        for x in p[-n+1:]: e=(x-e)*m+e
        return e

    @staticmethod
    def macd(p):
        if len(p)<26: return 0,0
        m=TA.ema(p,12)-TA.ema(p,26)
        return m, m*0.85

    @staticmethod
    def bb(p,n=20):
        if len(p)<n: return p[-1],p[-1],p[-1]
        r=p[-n:]; mid=sum(r)/n
        std=(sum((x-mid)**2 for x in r)/n)**0.5
        return mid+2*std,mid,mid-2*std

    @staticmethod
    def atr(klines,n=14):
        if len(klines)<n+1: return 0
        trs=[]
        for i in range(1,len(klines)):
            h,l,pc=klines[i]['h'],klines[i]['l'],klines[i-1]['c']
            trs.append(max(h-l,abs(h-pc),abs(l-pc)))
        return sum(trs[-n:])/n

# ── AI AGENT ─────────────────────────────────────────────────
class Agent:
    def __init__(self,bc):
        self.bc=bc
        self.balance=10000
        self.start_balance=10000
        self.positions={}
        self.history=[]
        self.trades=0
        self.wins=0
        self.pnl_curve=[10000]
        self.strategies={'Trend Following':1.0,'Mean Reversion':1.0,'Breakout':1.0,'Scalping':1.0}
        self._klines_cache={}

    def _get_klines(self,sym):
        k=self.bc.klines(sym,'5m',60)
        if k: self._klines_cache[sym]=k
        return self._klines_cache.get(sym,[])

    def analyze(self,sym):
        try:
            kl=self._get_klines(sym)
            if len(kl)<30: return None
            c=[k['c'] for k in kl]
            v=[k['v'] for k in kl]
            price=c[-1]
            rsi=TA.rsi(c)
            macd,msig=TA.macd(c)
            e20,e50=TA.ema(c,20),TA.ema(c,50)
            bbu,bbm,bbl=TA.bb(c)
            atr=TA.atr(kl)
            avg_v=sum(v[-20:])/20
            vr=v[-1]/avg_v if avg_v>0 else 1

            score=0; reasons=[]

            # RSI
            if rsi<25: score+=3; reasons.append(f"RSI asiri satim {rsi:.0f}")
            elif rsi<32: score+=2; reasons.append(f"RSI satim bolgesi {rsi:.0f}")
            elif rsi>75: score-=3; reasons.append(f"RSI asiri alim {rsi:.0f}")
            elif rsi>68: score-=2; reasons.append(f"RSI alim bolgesi {rsi:.0f}")

            # MACD
            if macd>msig and macd>0: score+=2; reasons.append("MACD guclu yukari")
            elif macd>msig: score+=1; reasons.append("MACD yukari donuyor")
            elif macd<msig and macd<0: score-=2; reasons.append("MACD guclu asagi")
            elif macd<msig: score-=1; reasons.append("MACD asagi donuyor")

            # EMA
            if price>e20>e50: score+=1; reasons.append("EMA yukari trend")
            elif price<e20<e50: score-=1; reasons.append("EMA asagi trend")

            # Bollinger
            if price<bbl*1.001: score+=2; reasons.append("Alt Bollinger kirilmasi")
            elif price>bbu*0.999: score-=2; reasons.append("Ust Bollinger kirilmasi")

            # Volume
            if vr>2.5: score+=1; reasons.append(f"Hacim patlamasi x{vr:.1f}")

            # Pattern: hammer-like
            body=abs(c[-1]-c[-2])
            wick=kl[-1]['h']-kl[-1]['l']
            if wick>0 and body/wick<0.3 and c[-1]>c[-2]: score+=1; reasons.append("Hammer formasyonu")

            conf=min(abs(score)/9*100,96)
            return dict(sym=sym,price=price,score=score,conf=conf,
                        rsi=round(rsi,1),macd=round(macd,6),
                        e20=round(e20,6),e50=round(e50,6),
                        bbu=round(bbu,6),bbl=round(bbl,6),
                        atr=round(atr,6),vr=round(vr,2),
                        reasons=reasons,klines=kl[-40:])
        except: return None

    def decide(self,sym):
        if sym in self.positions: return None
        a=self.analyze(sym)
        if not a: return None
        if a['score']>=3: action='LONG'
        elif a['score']<=-3: action='SHORT'
        else: return None
        if a['conf']<45: return None
        strat=self._pick_strat()
        lev=random.choice([2,3,5])
        return dict(action=action,sym=sym,price=a['price'],
                    conf=a['conf'],reasons=a['reasons'],strat=strat,
                    lev=lev,atr=a['atr'],ind=dict(
                        rsi=a['rsi'],macd=a['macd'],e20=a['e20'],
                        e50=a['e50'],bbu=a['bbu'],bbl=a['bbl'],vr=a['vr']),
                    klines=a['klines'])

    def _pick_strat(self):
        t=sum(self.strategies.values()); r=random.uniform(0,t); c=0
        for s,v in self.strategies.items():
            c+=v
            if r<=c: return s
        return 'Trend Following'

    def open(self,d):
        p,lev=d['price'],d['lev']
        sz=self.balance*0.08
        if d['action']=='LONG':
            tp=p*(1+0.018*lev/3); sl=p*(1-0.007*lev/3)
        else:
            tp=p*(1-0.018*lev/3); sl=p*(1+0.007*lev/3)
        self.positions[d['sym']]=dict(
            type=d['action'],entry=p,cur=p,tp=tp,sl=sl,sz=sz,
            lev=lev,pnl=0,pnl_pct=0,strat=d['strat'],
            reasons=d['reasons'],ind=d['ind'],
            klines=d.get('klines',[]),
            t0=datetime.now().isoformat(),
            conf=d['conf'],max_pnl=0,min_pnl=0)

    def update(self):
        close=[]
        for sym,pos in self.positions.items():
            try:
                p=self.bc.price(sym)
                if p==0: continue
                pos['cur']=p
                m=pos['lev']
                if pos['type']=='LONG':
                    pct=(p-pos['entry'])/pos['entry']*100*m
                else:
                    pct=(pos['entry']-p)/pos['entry']*100*m
                pnl=pos['sz']*pct/100
                pos['pnl']=pnl; pos['pnl_pct']=pct
                pos['max_pnl']=max(pos['max_pnl'],pnl)
                pos['min_pnl']=min(pos['min_pnl'],pnl)
                if pos['type']=='LONG':
                    if p>=pos['tp']: close.append((sym,'TP'))
                    elif p<=pos['sl']: close.append((sym,'SL'))
                else:
                    if p<=pos['tp']: close.append((sym,'TP'))
                    elif p>=pos['sl']: close.append((sym,'SL'))
            except: pass
        for sym,why in close: self.close(sym,why)

    def close(self,sym,why='Manual'):
        if sym not in self.positions: return
        pos=self.positions[sym]
        self.balance+=pos['pnl']
        self.trades+=1
        won=pos['pnl']>0
        if won: self.wins+=1
        s=pos['strat']
        self.strategies[s]=min(3.0,self.strategies[s]+(0.15 if won else -0.05))
        self.strategies[s]=max(0.1,self.strategies[s])
        delta=datetime.now()-datetime.fromisoformat(pos['t0'])
        secs=delta.total_seconds()
        ht=f"{int(secs)}s" if secs<60 else f"{int(secs/60)}m" if secs<3600 else f"{int(secs/3600)}h"
        rec=dict(id=self.trades,sym=sym,type=pos['type'],
                 entry=pos['entry'],exit=pos['cur'],tp=pos['tp'],sl=pos['sl'],
                 pnl=round(pos['pnl'],2),pnl_pct=round(pos['pnl_pct'],2),
                 lev=pos['lev'],strat=pos['strat'],reasons=pos['reasons'],
                 why=why,time=datetime.now().strftime('%H:%M:%S'),
                 ht=ht,won=won)
        self.history.insert(0,rec)
        if len(self.history)>100: self.history.pop()
        self.pnl_curve.append(round(self.balance,2))
        if len(self.pnl_curve)>80: self.pnl_curve.pop(0)
        del self.positions[sym]
        tag="WIN" if won else "LOSS"
        print(f"[{tag}] {sym} {pos['type']} | ${pos['pnl']:.2f} ({pos['pnl_pct']:.2f}%) | {why}")

    def wr(self): return (self.wins/self.trades*100) if self.trades>0 else 50.0
    def total_pnl(self): return round(self.balance-self.start_balance,2)

# ── ENGINE ────────────────────────────────────────────────────
class Engine:
    def __init__(self):
        print("Connecting to Binance...")
        self.bc=BinanceClient()
        self.agent=Agent(self.bc)
        self.running=False
        self.tick=0
        self.events=[]

    def log(self,msg,lvl='info'):
        self.events.insert(0,{'t':datetime.now().strftime('%H:%M:%S'),'msg':msg,'lvl':lvl})
        if len(self.events)>300: self.events.pop()

    def start(self):
        self.running=True
        self.log("Bot baslatildi","success")
        threading.Thread(target=self._bg_prices,daemon=True).start()
        threading.Thread(target=self._bg_tickers,daemon=True).start()
        print(f"\n{'─'*50}\nBot Started | ${self.agent.balance:.0f} | {len(self.bc.symbols)} pairs\n{'─'*50}\n")
        while self.running:
            try:
                self.agent.update()
                if self.tick%5==0:
                    syms=random.sample(self.bc.symbols,min(4,len(self.bc.symbols)))
                    for s in syms:
                        d=self.agent.decide(s)
                        if d and len(self.agent.positions)<6:
                            self.agent.open(d)
                            self.log(f"{s} {d['action']} @ ${d['price']:.4f} | Guven {d['conf']:.0f}% | {', '.join(d['reasons'][:2])}","trade")
                self.tick+=1
                time.sleep(3)
            except Exception as e:
                print(f"tick error: {e}")
                time.sleep(3)

    def stop(self):
        self.running=False
        self.log("Bot durduruldu","warn")

    def _bg_prices(self):
        while self.running:
            self.bc.refresh_prices(); time.sleep(6)

    def _bg_tickers(self):
        while self.running:
            self.bc.refresh_tickers(); time.sleep(25)

    def state(self):
        coins={}
        for s in self.bc.symbols:
            t=self.bc.info(s)
            coins[s]=dict(price=t.get('price',0),change=round(t.get('change',0),2),
                          volume=t.get('volume',0),high=t.get('high',0),low=t.get('low',0))
        pos_out={}
        for s,p in self.agent.positions.items():
            pos_out[s]=dict(type=p['type'],entry=p['entry'],cur=p['cur'],
                            tp=p['tp'],sl=p['sl'],sz=p['sz'],lev=p['lev'],
                            pnl=round(p['pnl'],2),pnl_pct=round(p['pnl_pct'],2),
                            strat=p['strat'],reasons=p['reasons'],ind=p['ind'],
                            t0=p['t0'],conf=p['conf'],
                            klines=p['klines'][-30:])
        return dict(
            balance=round(self.agent.balance,2),
            total_pnl=self.agent.total_pnl(),
            total_pnl_pct=round(self.agent.total_pnl()/self.agent.start_balance*100,2),
            trades=self.agent.trades,wins=self.agent.wins,
            wr=round(self.agent.wr(),1),
            active=len(self.agent.positions),
            positions=pos_out,
            history=self.agent.history[:40],
            strategies=self.agent.strategies,
            coins=coins,
            running=self.running,
            curve=self.agent.pnl_curve,
            events=self.events[:60],
        )

# ── HTML ─────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>AI Trading Bot v4</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=Bebas+Neue&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#040810;--s1:#080f1e;--s2:#0c1628;--s3:#101d33;
  --b:#162035;--b2:#1e2d47;
  --cyan:#00d4ff;--green:#00ff88;--red:#ff3366;
  --yellow:#ffcc00;--purple:#9d4edd;--orange:#ff6b00;
  --text:#c8dff0;--dim:#4a6a8a;
  --mono:'IBM Plex Mono',monospace;--display:'Bebas Neue',sans-serif;
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--mono);
     font-size:13px;min-height:100vh;overflow-x:hidden}

/* SCANLINE EFFECT */
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.03) 2px,rgba(0,0,0,0.03) 4px)}

/* TICKER TAPE */
.ticker-wrap{background:var(--s1);border-bottom:1px solid var(--b);
  overflow:hidden;height:34px;display:flex;align-items:center}
.ticker-inner{display:flex;gap:0;animation:scroll 60s linear infinite;white-space:nowrap}
.ticker-inner:hover{animation-play-state:paused}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.tick-item{padding:0 20px;font-size:11px;border-right:1px solid var(--b);
  display:flex;align-items:center;gap:8px;height:34px}
.tick-sym{color:var(--cyan);font-weight:600;letter-spacing:1px}
.tick-price{color:var(--text)}
.tick-up{color:var(--green)}.tick-dn{color:var(--red)}

/* HEADER */
header{background:var(--s1);border-bottom:1px solid var(--b);
  padding:14px 24px;display:flex;justify-content:space-between;align-items:center;
  position:sticky;top:34px;z-index:100;backdrop-filter:blur(20px)}
.logo{font-family:var(--display);font-size:28px;letter-spacing:3px;
  background:linear-gradient(90deg,var(--cyan),var(--green));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.logo span{font-size:12px;letter-spacing:2px;color:var(--dim);display:block;
  -webkit-text-fill-color:var(--dim);margin-top:-6px}
.hdr-center{display:flex;align-items:center;gap:24px}
.stat-mini{text-align:center}
.stat-mini-v{font-family:var(--display);font-size:22px;letter-spacing:1px}
.stat-mini-l{font-size:9px;letter-spacing:2px;color:var(--dim);text-transform:uppercase}
.hdr-right{display:flex;gap:10px;align-items:center}
.pill{padding:5px 14px;border-radius:2px;font-size:10px;
  font-weight:700;letter-spacing:2px;border:1px solid}
.pill-off{border-color:var(--dim);color:var(--dim)}
.pill-on{border-color:var(--green);color:var(--green);
  box-shadow:0 0 12px rgba(0,255,136,0.2);animation:glowPulse 2s ease infinite}
@keyframes glowPulse{0%,100%{box-shadow:0 0 8px rgba(0,255,136,0.2)}50%{box-shadow:0 0 20px rgba(0,255,136,0.4)}}
.btn{padding:9px 20px;border:1px solid;border-radius:2px;background:none;
  font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:2px;
  cursor:pointer;transition:.15s;text-transform:uppercase}
.btn:hover{filter:brightness(1.3)}
.btn:active{transform:scale(.97)}
.btn:disabled{opacity:.3;cursor:not-allowed}
.btn-go{border-color:var(--green);color:var(--green)}
.btn-stop{border-color:var(--red);color:var(--red)}

/* GRID LAYOUT */
.grid{display:grid;gap:16px;padding:16px;
  grid-template-areas:
    "stats stats stats stats"
    "coins coins coins coins"
    "chart chart strat strat"
    "pos pos hist log";
  grid-template-columns:1fr 1fr 1fr 1fr}
@media(max-width:1200px){.grid{grid-template-areas:"stats stats""coins coins""chart strat""pos hist""log log";grid-template-columns:1fr 1fr}}
@media(max-width:700px){.grid{grid-template-areas:"stats""coins""chart""strat""pos""hist""log";grid-template-columns:1fr}}

/* PANEL */
.panel{background:var(--s1);border:1px solid var(--b);border-radius:4px;overflow:hidden}
.ph{padding:12px 16px;border-bottom:1px solid var(--b);
  display:flex;justify-content:space-between;align-items:center}
.ph-title{font-family:var(--display);font-size:16px;letter-spacing:2px;color:var(--text)}
.ph-badge{background:rgba(0,212,255,.08);border:1px solid rgba(0,212,255,.2);
  color:var(--cyan);padding:3px 10px;border-radius:2px;font-size:10px;
  font-weight:700;letter-spacing:1px}
.ph-badge.green{background:rgba(0,255,136,.08);border-color:rgba(0,255,136,.2);color:var(--green)}
.ph-badge.red{background:rgba(255,51,102,.08);border-color:rgba(255,51,102,.2);color:var(--red)}
.pb{padding:14px;max-height:480px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--b) transparent}
.pb::-webkit-scrollbar{width:3px}
.pb::-webkit-scrollbar-thumb{background:var(--b2)}

/* STATS ROW */
.stats-area{grid-area:stats;display:grid;grid-template-columns:repeat(7,1fr);gap:10px}
.sc{background:var(--s1);border:1px solid var(--b);border-radius:4px;
  padding:14px 16px;position:relative;overflow:hidden;transition:.2s}
.sc:hover{border-color:var(--cyan)}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--cyan),var(--purple))}
.sc-l{font-size:9px;letter-spacing:2px;color:var(--dim);text-transform:uppercase;margin-bottom:6px}
.sc-v{font-family:var(--display);font-size:26px;letter-spacing:1px;line-height:1}
.sc-s{font-size:10px;color:var(--dim);margin-top:3px}
.c-cyan{color:var(--cyan)}.c-green{color:var(--green)}.c-red{color:var(--red)}
.c-yellow{color:var(--yellow)}.c-purple{color:var(--purple)}.c-orange{color:var(--orange)}

/* COINS */
.coins-area{grid-area:coins}
.coins-top{padding:10px 16px;border-bottom:1px solid var(--b);
  display:flex;gap:10px;align-items:center}
.srch{background:var(--s2);border:1px solid var(--b);border-radius:2px;
  padding:7px 12px;color:var(--text);font-family:var(--mono);
  font-size:11px;width:200px;outline:none;letter-spacing:1px}
.srch:focus{border-color:var(--cyan)}
.srch::placeholder{color:var(--dim)}
.coins-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));
  gap:6px;padding:10px;max-height:340px;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:var(--b) transparent}
.coins-grid::-webkit-scrollbar{width:3px}
.coins-grid::-webkit-scrollbar-thumb{background:var(--b2)}
.cc{background:var(--s2);border:1px solid var(--b);border-radius:3px;
  padding:10px;cursor:pointer;transition:.15s;position:relative;overflow:hidden}
.cc:hover{border-color:var(--cyan);transform:translateY(-1px)}
.cc.active{border-color:var(--cyan)}
.cc.active::after{content:'●';position:absolute;top:5px;right:6px;
  font-size:7px;color:var(--cyan);animation:blink2 1s ease infinite}
@keyframes blink2{0%,100%{opacity:1}50%{opacity:.3}}
.cc-s{font-weight:700;font-size:11px;letter-spacing:1px;color:var(--text);margin-bottom:3px}
.cc-p{font-size:10px;color:var(--dim);margin-bottom:4px}
.cc-c{font-size:10px;font-weight:700;padding:1px 6px;border-radius:2px;display:inline-block}
.up-c{background:rgba(0,255,136,.1);color:var(--green)}
.dn-c{background:rgba(255,51,102,.1);color:var(--red)}

/* CHART */
.chart-area{grid-area:chart}
#cv{width:100%;display:block;cursor:crosshair}
.chart-toolbar{padding:8px 12px;border-bottom:1px solid var(--b);
  display:flex;gap:6px;align-items:center}
.tf-btn{padding:3px 10px;background:none;border:1px solid var(--b);
  border-radius:2px;color:var(--dim);font-family:var(--mono);font-size:10px;
  cursor:pointer;transition:.15s;letter-spacing:1px}
.tf-btn.active,.tf-btn:hover{border-color:var(--cyan);color:var(--cyan)}
.chart-info{padding:6px 12px;font-size:10px;color:var(--dim);display:flex;gap:16px}

/* STRATEGIES */
.strat-area{grid-area:strat}
.sr{padding:8px 0;border-bottom:1px solid rgba(255,255,255,.03)}
.sr-top{display:flex;justify-content:space-between;margin-bottom:5px}
.sr-name{font-size:11px;color:var(--text);letter-spacing:.5px}
.sr-val{font-size:11px;font-weight:700;color:var(--cyan)}
.sr-bar{height:3px;background:rgba(255,255,255,.05);border-radius:2px;overflow:hidden}
.sr-fill{height:100%;background:linear-gradient(90deg,var(--cyan),var(--purple));transition:width .6s ease;border-radius:2px}
.sr-badge{font-size:9px;letter-spacing:1px;padding:1px 6px;border-radius:2px;margin-left:6px}
.sr-best{background:rgba(0,255,136,.1);color:var(--green)}

/* POSITIONS */
.pos-area{grid-area:pos}
.pc{background:var(--s2);border-radius:3px;padding:12px;margin-bottom:8px;
  border-left:3px solid;animation:slideIn .3s ease}
@keyframes slideIn{from{opacity:0;transform:translateX(-6px)}}
.pc-long{border-left-color:var(--green)}.pc-short{border-left-color:var(--red)}
.pc-row1{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.pc-sym{font-family:var(--display);font-size:18px;letter-spacing:2px}
.pc-tag{display:inline-flex;align-items:center;gap:4px}
.pc-type{font-size:9px;font-weight:700;padding:2px 8px;border-radius:2px;letter-spacing:1px}
.t-long{background:rgba(0,255,136,.12);color:var(--green);border:1px solid rgba(0,255,136,.2)}
.t-short{background:rgba(255,51,102,.12);color:var(--red);border:1px solid rgba(255,51,102,.2)}
.pc-lev{font-size:9px;color:var(--dim);border:1px solid var(--b);padding:2px 6px;border-radius:2px}
.pc-pnl{text-align:right}
.pc-pnl-v{font-family:var(--display);font-size:20px;letter-spacing:1px}
.pc-pnl-p{font-size:10px;color:var(--dim)}
.pc-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;
  font-size:10px;color:var(--dim);margin-bottom:8px}
.pc-grid span{display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid rgba(255,255,255,.03)}
.pc-grid b{color:var(--text)}

/* PROGRESS BAR */
.prog-wrap{margin:6px 0}
.prog-labels{display:flex;justify-content:space-between;font-size:9px;margin-bottom:3px}
.prog-bg{height:5px;background:rgba(255,255,255,.04);border-radius:2px;overflow:hidden;position:relative}
.prog-fill{height:100%;border-radius:2px;transition:width .5s ease}
.prog-marker{position:absolute;top:-2px;width:2px;height:9px;background:rgba(255,255,255,.4);transition:left .5s ease}

.pc-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.chip{font-size:9px;padding:2px 7px;border-radius:2px;border:1px solid var(--b);color:var(--dim);letter-spacing:.5px}
.chip.lit{border-color:var(--cyan);color:var(--cyan)}
.chip.warn{border-color:var(--yellow);color:var(--yellow)}

.pc-ai{background:rgba(157,78,221,.06);border:1px solid rgba(157,78,221,.2);
  border-radius:3px;padding:7px 10px;margin-top:7px}
.pc-ai-lbl{font-size:9px;letter-spacing:2px;color:var(--purple);margin-bottom:3px;text-transform:uppercase}
.pc-ai-txt{font-size:10px;color:#c4b5fd;line-height:1.6}

/* HISTORY */
.hist-area{grid-area:hist}
.hi{display:flex;align-items:center;gap:10px;padding:8px 0;
  border-bottom:1px solid rgba(255,255,255,.03);animation:slideIn .3s ease}
.hi-badge{width:38px;height:38px;border-radius:3px;display:flex;align-items:center;
  justify-content:center;font-size:10px;font-weight:700;letter-spacing:1px;flex-shrink:0}
.b-win{background:rgba(0,255,136,.1);color:var(--green);border:1px solid rgba(0,255,136,.2)}
.b-loss{background:rgba(255,51,102,.1);color:var(--red);border:1px solid rgba(255,51,102,.2)}
.hi-main{flex:1;min-width:0}
.hi-sym{font-weight:700;font-size:12px;letter-spacing:.5px}
.hi-sub{font-size:10px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hi-pnl{text-align:right;font-size:12px;font-weight:700;flex-shrink:0}

/* LOG */
.log-area{grid-area:log}
.li{padding:6px 0;border-bottom:1px solid rgba(255,255,255,.03);
  font-size:10px;line-height:1.5;animation:slideIn .3s ease}
.lt{color:var(--dim);margin-right:8px}
.lv-info{color:var(--text)}.lv-success{color:var(--green)}
.lv-trade{color:var(--cyan)}.lv-warn{color:var(--yellow)}.lv-error{color:var(--red)}

/* MODAL */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.8);
  z-index:1000;display:none;align-items:center;justify-content:center;
  backdrop-filter:blur(4px)}
.modal-overlay.show{display:flex}
.modal{background:var(--s1);border:1px solid var(--b2);border-radius:4px;
  width:700px;max-width:95vw;max-height:85vh;overflow:auto}
.modal-head{padding:16px 20px;border-bottom:1px solid var(--b);
  display:flex;justify-content:space-between;align-items:center}
.modal-sym{font-family:var(--display);font-size:24px;letter-spacing:3px}
.modal-close{background:none;border:1px solid var(--b);color:var(--dim);
  width:30px;height:30px;border-radius:2px;cursor:pointer;font-size:14px}
.modal-close:hover{border-color:var(--red);color:var(--red)}
.modal-body{padding:16px 20px}
.modal-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.ms{background:var(--s2);border:1px solid var(--b);border-radius:3px;padding:10px}
.ms-l{font-size:9px;color:var(--dim);letter-spacing:1px;margin-bottom:4px;text-transform:uppercase}
.ms-v{font-size:14px;font-weight:700}
#modal-cv{width:100%;border-radius:3px;display:block}

/* EMPTY */
.empty{padding:32px;text-align:center;color:var(--dim);font-size:11px;letter-spacing:1px}

/* TOOLTIP */
.tooltip{position:fixed;background:var(--s2);border:1px solid var(--b2);
  border-radius:3px;padding:6px 10px;font-size:10px;pointer-events:none;
  z-index:200;display:none;line-height:1.6}
</style>
</head>
<body>

<!-- TICKER -->
<div class="ticker-wrap">
  <div class="ticker-inner" id="ticker"></div>
</div>

<!-- HEADER -->
<header>
  <div>
    <div class="logo">AI TRADING BOT <span style="display:inline;font-size:12px;-webkit-text-fill-color:var(--cyan)">V4.0</span></div>
    <div style="font-size:10px;color:var(--dim);letter-spacing:1px;margin-top:2px">BINANCE FUTURES ● SIMULATED TRADING ● REAL DATA</div>
  </div>
  <div class="hdr-center">
    <div class="stat-mini">
      <div class="stat-mini-l">Bakiye</div>
      <div class="stat-mini-v c-cyan" id="hdr-balance">$10,000</div>
    </div>
    <div style="width:1px;height:36px;background:var(--b)"></div>
    <div class="stat-mini">
      <div class="stat-mini-l">PnL</div>
      <div class="stat-mini-v" id="hdr-pnl">$0</div>
    </div>
    <div style="width:1px;height:36px;background:var(--b)"></div>
    <div class="stat-mini">
      <div class="stat-mini-l">Win Rate</div>
      <div class="stat-mini-v" id="hdr-wr">50%</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="pill pill-off" id="status-pill">DURDURULDU</div>
    <button class="btn btn-go" id="btn-s" onclick="startBot()">▶ BASLAT</button>
    <button class="btn btn-stop" id="btn-x" onclick="stopBot()" disabled>■ DURDUR</button>
  </div>
</header>

<!-- TOOLTIP -->
<div class="tooltip" id="tt"></div>

<div class="grid">

  <!-- STATS -->
  <div class="stats-area">
    <div class="sc"><div class="sc-l">Portfoy</div><div class="sc-v c-cyan" id="s-bal">$10,000</div><div class="sc-s">Baslangic: $10,000</div></div>
    <div class="sc"><div class="sc-l">Toplam PnL</div><div class="sc-v" id="s-pnl">$0</div><div class="sc-s" id="s-pnl-pct">0.00%</div></div>
    <div class="sc"><div class="sc-l">Toplam Trade</div><div class="sc-v c-purple" id="s-tr">0</div><div class="sc-s" id="s-wl">W:0 / L:0</div></div>
    <div class="sc"><div class="sc-l">Win Rate</div><div class="sc-v" id="s-wr">50%</div><div class="sc-s">Ogreniyor...</div></div>
    <div class="sc"><div class="sc-l">Acik Poz.</div><div class="sc-v c-cyan" id="s-act">0/6</div><div class="sc-s">Maks 6 pozisyon</div></div>
    <div class="sc"><div class="sc-l">Coins</div><div class="sc-v c-yellow" id="s-coins">0</div><div class="sc-s">Futures Ciftleri</div></div>
    <div class="sc"><div class="sc-l">En Iyi Strat.</div><div class="sc-v c-green" style="font-size:14px" id="s-best">--</div><div class="sc-s">Ogreniyor</div></div>
  </div>

  <!-- COINS -->
  <div class="coins-area panel">
    <div class="coins-top">
      <div class="ph-title" style="font-size:14px">PIYASA</div>
      <input class="srch" id="srch" placeholder="Coin ara..." oninput="filterCoins()">
      <div style="margin-left:auto;font-size:10px;color:var(--dim)" id="coin-count-lbl">0 coin</div>
    </div>
    <div class="coins-grid" id="cg"><div class="empty">Yukleniyor...</div></div>
  </div>

  <!-- CHART -->
  <div class="chart-area panel">
    <div class="ph">
      <div class="ph-title" id="chart-sym">PNL GRAFiGi</div>
      <div class="ph-badge" id="chart-badge">PORTFOY</div>
    </div>
    <div class="chart-toolbar" id="chart-tb" style="display:none">
      <span style="font-size:10px;color:var(--dim);margin-right:4px">ZAMAN:</span>
      <button class="tf-btn active" onclick="setTf('1m',this)">1m</button>
      <button class="tf-btn" onclick="setTf('5m',this)">5m</button>
      <button class="tf-btn" onclick="setTf('15m',this)">15m</button>
      <button class="tf-btn" onclick="setTf('1h',this)">1h</button>
      <button class="tf-btn" onclick="setTf('4h',this)">4h</button>
      <span style="margin-left:auto;font-size:10px;color:var(--dim)" id="chart-ohlc"></span>
    </div>
    <canvas id="cv" height="200"></canvas>
    <div class="chart-info" id="chart-info"></div>
  </div>

  <!-- STRATEGIES -->
  <div class="strat-area panel">
    <div class="ph"><div class="ph-title">STRATEJI OGRENIMI</div><div class="ph-badge">CANLI</div></div>
    <div class="pb" id="strats"></div>
  </div>

  <!-- POSITIONS -->
  <div class="pos-area panel">
    <div class="ph">
      <div class="ph-title">ACIK POZISYONLAR</div>
      <div class="ph-badge" id="pos-badge">0 AKTIF</div>
    </div>
    <div class="pb" id="positions"><div class="empty">Pozisyon bekleniyor...</div></div>
  </div>

  <!-- HISTORY -->
  <div class="hist-area panel">
    <div class="ph">
      <div class="ph-title">TRADE GECMiSi</div>
      <div class="ph-badge" id="hist-badge">0 TRADE</div>
    </div>
    <div class="pb" id="history"><div class="empty">Trade bekleniyor...</div></div>
  </div>

  <!-- LOG -->
  <div class="log-area panel">
    <div class="ph"><div class="ph-title">SiSTEM LOGU</div><div class="ph-badge green">CANLI</div></div>
    <div class="pb" id="log"><div class="empty">Log bekleniyor...</div></div>
  </div>

</div>

<!-- COIN MODAL -->
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-head">
      <div>
        <div class="modal-sym" id="m-sym">--</div>
        <div style="font-size:10px;color:var(--dim);margin-top:2px" id="m-sub">--</div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div class="modal-stats">
        <div class="ms"><div class="ms-l">Fiyat</div><div class="ms-v c-cyan" id="m-price">--</div></div>
        <div class="ms"><div class="ms-l">24s Degisim</div><div class="ms-v" id="m-change">--</div></div>
        <div class="ms"><div class="ms-l">24s Yuksek</div><div class="ms-v c-green" id="m-high">--</div></div>
        <div class="ms"><div class="ms-l">24s Dusuk</div><div class="ms-v c-red" id="m-low">--</div></div>
      </div>
      <canvas id="modal-cv" height="180"></canvas>
    </div>
  </div>
</div>

<script>
// ── STATE ──────────────────────────────────────────────────
let running=false, data={}, curSym=null, curTf='5m', chartMode='pnl';
let tickerCoins=[], rafId=null;

// ── CONTROLS ──────────────────────────────────────────────
function startBot(){
  fetch('/api/start').then(()=>{running=true;syncUI()});
}
function stopBot(){
  fetch('/api/stop').then(()=>{running=false;syncUI()});
}
function syncUI(){
  const on=running;
  document.getElementById('status-pill').textContent=on?'CALISIYOR':'DURDURULDU';
  document.getElementById('status-pill').className='pill '+(on?'pill-on':'pill-off');
  document.getElementById('btn-s').disabled=on;
  document.getElementById('btn-x').disabled=!on;
}

// ── FORMAT ────────────────────────────────────────────────
const f=(n,d=2)=>{
  if(n===undefined||n===null)return'--';
  if(n===0)return'$0';
  if(Math.abs(n)<0.0001)return n.toFixed(8);
  if(Math.abs(n)<0.01)return n.toFixed(6);
  if(Math.abs(n)<1)return n.toFixed(4);
  return n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
};
const fp=(n)=>(n>=0?'+':'')+n.toFixed(2)+'%';
const fPnl=(n)=>(n>=0?'+$':'−$')+Math.abs(n).toFixed(2);
const cl=(n)=>n>=0?'c-green':'c-red';

// ── TICKER TAPE ────────────────────────────────────────────
function buildTicker(){
  const coins=data.coins||{};
  const keys=Object.keys(coins).slice(0,30);
  if(keys.length===0)return;
  let h='';
  // Double for infinite scroll
  for(let pass=0;pass<2;pass++){
    keys.forEach(s=>{
      const c=coins[s];
      const chg=c.change||0;
      h+=`<div class="tick-item">
        <span class="tick-sym">${s.replace('USDT','')}</span>
        <span class="tick-price">$${f(c.price)}</span>
        <span class="${chg>=0?'tick-up':'tick-dn'}">${chg>=0?'+':''}${chg.toFixed(2)}%</span>
      </div>`;
    });
  }
  document.getElementById('ticker').innerHTML=h;
}

// ── COIN GRID ─────────────────────────────────────────────
function buildCoins(){
  const coins=data.coins||{};
  const pos=new Set(Object.keys(data.positions||{}));
  let h='', count=0;
  for(const[s,c]of Object.entries(coins)){
    count++;
    const label=s.replace('USDT','');
    const chg=c.change||0;
    const hasPos=pos.has(s);
    h+=`<div class="cc${hasPos?' active':''}" data-sym="${label}"
          onclick="openCoinModal('${s}')"
          title="${label} / $${f(c.price)} / ${chg.toFixed(2)}%">
      <div class="cc-s">${label}</div>
      <div class="cc-p">$${f(c.price)}</div>
      <div class="cc-c ${chg>=0?'up-c':'dn-c'}">${chg>=0?'+':''}${chg.toFixed(2)}%</div>
    </div>`;
  }
  document.getElementById('cg').innerHTML=h||'<div class="empty">Yukleniyor...</div>';
  document.getElementById('coin-count-lbl').textContent=count+' coin';
  document.getElementById('s-coins').textContent=count;
}
function filterCoins(){
  const q=document.getElementById('srch').value.toUpperCase();
  document.querySelectorAll('.cc').forEach(el=>{
    el.style.display=el.dataset.sym.includes(q)?'':'none';
  });
}

// ── PNL CHART ─────────────────────────────────────────────
function drawPnlChart(curve){
  const cv=document.getElementById('cv');
  const ctx=cv.getContext('2d');
  const DPR=window.devicePixelRatio||1;
  const W=cv.parentElement.offsetWidth;
  const H=200;
  cv.width=W*DPR; cv.height=H*DPR;
  cv.style.width=W+'px'; cv.style.height=H+'px';
  ctx.scale(DPR,DPR);
  ctx.clearRect(0,0,W,H);

  const pad={t:16,r:16,b:24,l:72};
  const cw=W-pad.l-pad.r, ch=H-pad.t-pad.b;

  if(curve.length<2){
    ctx.fillStyle='rgba(74,106,138,0.5)';
    ctx.font='12px IBM Plex Mono';
    ctx.textAlign='center';
    ctx.fillText('Trade baslatildiginda grafik olusacak...',W/2,H/2);
    return;
  }

  const mn=Math.min(...curve), mx=Math.max(...curve);
  const range=mx-mn||100;
  const toX=(i)=>pad.l+(i/(curve.length-1))*cw;
  const toY=(v)=>pad.t+ch-(((v-mn)/range)*ch);

  // Grid lines
  ctx.strokeStyle='rgba(22,32,53,0.8)'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){
    const y=pad.t+(ch/4)*i;
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cw,y); ctx.stroke();
    const val=mx-(range/4)*i;
    ctx.fillStyle='rgba(74,106,138,0.7)'; ctx.font='10px IBM Plex Mono';
    ctx.textAlign='right';
    ctx.fillText('$'+val.toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0}),pad.l-6,y+4);
  }

  // Baseline (10000)
  if(10000>=mn&&10000<=mx){
    const by=toY(10000);
    ctx.strokeStyle='rgba(74,106,138,0.4)'; ctx.lineWidth=1;
    ctx.setLineDash([4,4]);
    ctx.beginPath(); ctx.moveTo(pad.l,by); ctx.lineTo(pad.l+cw,by); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='rgba(74,106,138,0.6)'; ctx.font='9px IBM Plex Mono';
    ctx.textAlign='left';
    ctx.fillText('BASE',pad.l+4,by-4);
  }

  const pts=curve.map((v,i)=>({x:toX(i),y:toY(v)}));
  const isUp=curve[curve.length-1]>=curve[0];
  const lineColor=isUp?'#00ff88':'#ff3366';

  // Area fill
  const grad=ctx.createLinearGradient(0,pad.t,0,pad.t+ch);
  grad.addColorStop(0,isUp?'rgba(0,255,136,0.18)':'rgba(255,51,102,0.18)');
  grad.addColorStop(1,'rgba(0,0,0,0)');
  ctx.beginPath();
  ctx.moveTo(pts[0].x,pad.t+ch);
  pts.forEach(p=>ctx.lineTo(p.x,p.y));
  ctx.lineTo(pts[pts.length-1].x,pad.t+ch);
  ctx.closePath();
  ctx.fillStyle=grad; ctx.fill();

  // Line
  ctx.beginPath();
  pts.forEach((p,i)=>i===0?ctx.moveTo(p.x,p.y):ctx.lineTo(p.x,p.y));
  ctx.strokeStyle=lineColor; ctx.lineWidth=2;
  ctx.shadowColor=lineColor; ctx.shadowBlur=6;
  ctx.stroke();
  ctx.shadowBlur=0;

  // Last dot
  const lp=pts[pts.length-1];
  ctx.beginPath(); ctx.arc(lp.x,lp.y,4,0,Math.PI*2);
  ctx.fillStyle=lineColor; ctx.fill();
  ctx.strokeStyle=var_('--bg'); ctx.lineWidth=2; ctx.stroke();
  ctx.shadowBlur=0;
}

function var_(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

// ── CANDLESTICK CHART ─────────────────────────────────────
function drawCandles(klines, entryPrice, tpPrice, slPrice, posType){
  const cv=document.getElementById('cv');
  const ctx=cv.getContext('2d');
  const DPR=window.devicePixelRatio||1;
  const W=cv.parentElement.offsetWidth;
  const H=240;
  cv.width=W*DPR; cv.height=H*DPR;
  cv.style.width=W+'px'; cv.style.height=H+'px';
  ctx.scale(DPR,DPR);
  ctx.clearRect(0,0,W,H);

  if(!klines||klines.length<2){
    ctx.fillStyle='rgba(74,106,138,0.5)';
    ctx.font='12px IBM Plex Mono';
    ctx.textAlign='center';
    ctx.fillText('Veri yukleniyor...', W/2, H/2);
    return;
  }

  const pad={t:16,r:16,b:24,l:72};
  const cw=W-pad.l-pad.r, ch=H-pad.t-pad.b;

  const mn=Math.min(...klines.map(k=>k.l));
  const mx=Math.max(...klines.map(k=>k.h));
  const extra=(mx-mn)*0.05;
  const lo=mn-extra, hi=mx+extra, rng=hi-lo||1;
  const toY=(v)=>pad.t+ch-((v-lo)/rng)*ch;

  // Grid
  ctx.strokeStyle='rgba(22,32,53,0.8)'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){
    const y=pad.t+(ch/4)*i;
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cw,y); ctx.stroke();
    const val=hi-(rng/4)*i;
    ctx.fillStyle='rgba(74,106,138,0.7)'; ctx.font='9px IBM Plex Mono';
    ctx.textAlign='right';
    ctx.fillText('$'+f(val),pad.l-4,y+3);
  }

  // TP / SL / Entry lines
  const lines=[
    {v:entryPrice,color:'rgba(0,212,255,0.7)',label:'ENTRY',dash:[4,4]},
    {v:tpPrice,color:'rgba(0,255,136,0.7)',label:'TP',dash:[6,3]},
    {v:slPrice,color:'rgba(255,51,102,0.7)',label:'SL',dash:[6,3]},
  ];
  lines.forEach(({v,color,label,dash})=>{
    if(!v||v<lo||v>hi)return;
    const y=toY(v);
    ctx.strokeStyle=color; ctx.lineWidth=1.5;
    ctx.setLineDash(dash);
    ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+cw,y); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle=color; ctx.font='bold 9px IBM Plex Mono'; ctx.textAlign='left';
    ctx.fillText(label, pad.l+4, y-4);
    ctx.textAlign='right';
    ctx.fillText('$'+f(v), pad.l+cw, y-4);
  });

  // Candles
  const n=klines.length;
  const totalW=cw;
  const candleW=Math.max(2, Math.floor(totalW/n)-1);
  const gap=Math.floor(totalW/n);

  klines.forEach((k,i)=>{
    const x=pad.l+i*gap+gap/2;
    const isUp=k.c>=k.o;
    const color=isUp?'#00ff88':'#ff3366';
    const bodyTop=toY(Math.max(k.o,k.c));
    const bodyBot=toY(Math.min(k.o,k.c));
    const bodyH=Math.max(1,bodyBot-bodyTop);

    // Wick
    ctx.strokeStyle=color; ctx.lineWidth=1;
    ctx.beginPath();
    ctx.moveTo(x,toY(k.h)); ctx.lineTo(x,toY(k.l));
    ctx.stroke();

    // Body
    ctx.fillStyle=isUp?'rgba(0,255,136,0.8)':'rgba(255,51,102,0.8)';
    ctx.fillRect(x-candleW/2,bodyTop,candleW,bodyH);
  });

  // Current price line
  const lastClose=klines[klines.length-1].c;
  const lcy=toY(lastClose);
  ctx.strokeStyle='rgba(255,204,0,0.6)'; ctx.lineWidth=1;
  ctx.setLineDash([2,2]);
  ctx.beginPath(); ctx.moveTo(pad.l,lcy); ctx.lineTo(pad.l+cw,lcy); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle='rgba(255,204,0,0.7)'; ctx.font='9px IBM Plex Mono'; ctx.textAlign='left';
  ctx.fillText('CUR $'+f(lastClose), pad.l+4, lcy+10);
}

// ── POSITIONS ─────────────────────────────────────────────
function buildPositions(){
  const pos=data.positions||{};
  const keys=Object.keys(pos);
  document.getElementById('pos-badge').textContent=keys.length+' AKTIF';
  document.getElementById('pos-badge').className='ph-badge'+(keys.length>0?' green':'');

  if(keys.length===0){
    document.getElementById('positions').innerHTML='<div class="empty">Acik pozisyon yok</div>';
    return;
  }

  let h='';
  keys.forEach(sym=>{
    const p=pos[sym];
    const isL=p.type==='LONG';
    const pnlC=p.pnl>=0?'c-green':'c-red';
    const reasons=(p.reasons||[]).join(' · ');
    const ind=p.ind||{};

    // Progress bar
    let prog=50, progColor=p.pnl>=0?'var(--green)':'var(--red)';
    const range=Math.abs(p.tp-p.sl);
    if(range>0){
      if(isL) prog=Math.min(100,Math.max(0,(p.cur-p.sl)/range*100));
      else prog=Math.min(100,Math.max(0,(p.sl-p.cur)/range*100));
    }

    h+=`<div class="pc pc-${isL?'long':'short'}">
      <div class="pc-row1">
        <div>
          <div class="pc-sym">${sym.replace('USDT','')}/USDT</div>
          <div class="pc-tag" style="margin-top:5px">
            <span class="pc-type t-${isL?'long':'short'}">${p.type}</span>
            <span class="pc-lev">${p.lev}x</span>
          </div>
        </div>
        <div class="pc-pnl">
          <div class="pc-pnl-v ${pnlC}">${fPnl(p.pnl)}</div>
          <div class="pc-pnl-p">${fp(p.pnl_pct||0)}</div>
        </div>
      </div>
      <div class="pc-grid">
        <span>Giris <b>$${f(p.entry)}</b></span>
        <span>Anlik <b>$${f(p.cur)}</b></span>
        <span>Take Profit <b style="color:var(--green)">$${f(p.tp)}</b></span>
        <span>Stop Loss <b style="color:var(--red)">$${f(p.sl)}</b></span>
      </div>
      <div class="prog-wrap">
        <div class="prog-labels">
          <span style="color:var(--red)">SL $${f(p.sl)}</span>
          <span style="color:var(--green)">TP $${f(p.tp)}</span>
        </div>
        <div class="prog-bg">
          <div class="prog-fill" style="width:${prog}%;background:${progColor}"></div>
          <div class="prog-marker" style="left:${prog}%"></div>
        </div>
      </div>
      <div class="pc-chips">
        <span class="chip${ind.rsi&&(ind.rsi<32||ind.rsi>68)?' warn':''}">RSI ${ind.rsi||'--'}</span>
        <span class="chip lit">Guven ${(p.conf||0).toFixed(0)}%</span>
        <span class="chip">${p.strat}</span>
        <span class="chip lit" onclick="showCandles('${sym}')" style="cursor:pointer">GRAFIK ▸</span>
      </div>
      <div class="pc-ai">
        <div class="pc-ai-lbl">AI ANALIZ</div>
        <div class="pc-ai-txt">${reasons||'Analiz yukleniyor...'}</div>
      </div>
    </div>`;
  });
  document.getElementById('positions').innerHTML=h;
}

// ── HISTORY ───────────────────────────────────────────────
function buildHistory(){
  const hist=data.history||[];
  document.getElementById('hist-badge').textContent=(data.trades||0)+' TRADE';
  if(!hist.length){
    document.getElementById('history').innerHTML='<div class="empty">Trade bekleniyor...</div>';
    return;
  }
  let h='';
  hist.forEach(t=>{
    h+=`<div class="hi">
      <div class="hi-badge ${t.won?'b-win':'b-loss'}">${t.won?'WIN':'LOSS'}</div>
      <div class="hi-main">
        <div class="hi-sym">${t.sym.replace('USDT','')} ${t.type} ${t.lev}x</div>
        <div class="hi-sub">${t.why} · ${t.ht} · ${t.strat} · ${t.time}</div>
      </div>
      <div class="hi-pnl ${t.won?'c-green':'c-red'}">${fPnl(t.pnl)}</div>
    </div>`;
  });
  document.getElementById('history').innerHTML=h;
}

// ── STRATEGIES ────────────────────────────────────────────
function buildStrategies(){
  const st=data.strategies||{};
  const mx=Math.max(...Object.values(st),1);
  const sorted=Object.entries(st).sort((a,b)=>b[1]-a[1]);
  const best=sorted[0]?.[0]||'--';
  document.getElementById('s-best').textContent=best;

  let h='';
  sorted.forEach(([name,val],i)=>{
    const pct=(val/mx*100).toFixed(0);
    h+=`<div class="sr">
      <div class="sr-top">
        <span class="sr-name">${name}${i===0?'<span class="sr-badge sr-best">EN IYI</span>':''}</span>
        <span class="sr-val">${val.toFixed(2)}</span>
      </div>
      <div class="sr-bar"><div class="sr-fill" style="width:${pct}%"></div></div>
    </div>`;
  });
  document.getElementById('strats').innerHTML=h||'<div class="empty">--</div>';
}

// ── LOG ───────────────────────────────────────────────────
function buildLog(){
  const evts=data.events||[];
  if(!evts.length){
    document.getElementById('log').innerHTML='<div class="empty">Log bekleniyor...</div>';
    return;
  }
  let h='';
  evts.forEach(e=>{
    h+=`<div class="li"><span class="lt">[${e.t}]</span><span class="lv-${e.lvl}">${e.msg}</span></div>`;
  });
  document.getElementById('log').innerHTML=h;
}

// ── STATS ─────────────────────────────────────────────────
function buildStats(){
  const pnl=data.total_pnl||0;
  const pct=data.total_pnl_pct||0;
  const wr=data.wr||50;

  document.getElementById('hdr-balance').textContent='$'+(data.balance||0).toLocaleString('en-US',{minimumFractionDigits:2});
  document.getElementById('hdr-pnl').textContent=fPnl(pnl);
  document.getElementById('hdr-pnl').className='stat-mini-v '+cl(pnl);
  document.getElementById('hdr-wr').textContent=(wr).toFixed(1)+'%';
  document.getElementById('hdr-wr').className='stat-mini-v '+cl(wr-50);

  document.getElementById('s-bal').textContent='$'+(data.balance||0).toLocaleString('en-US',{minimumFractionDigits:2});
  document.getElementById('s-pnl').textContent=fPnl(pnl);
  document.getElementById('s-pnl').className='sc-v '+cl(pnl);
  document.getElementById('s-pnl-pct').textContent=(pct>=0?'+':'')+pct+'%';
  document.getElementById('s-tr').textContent=data.trades||0;
  document.getElementById('s-wl').textContent=`W:${data.wins||0} / L:${(data.trades||0)-(data.wins||0)}`;
  document.getElementById('s-wr').textContent=wr.toFixed(1)+'%';
  document.getElementById('s-wr').className='sc-v '+cl(wr-50);
  document.getElementById('s-act').textContent=(data.active||0)+'/6';
}

// ── CHART MODE ────────────────────────────────────────────
function showPnlChart(){
  chartMode='pnl';
  curSym=null;
  document.getElementById('chart-sym').textContent='PNL GRAFiGi';
  document.getElementById('chart-badge').textContent='PORTFOY';
  document.getElementById('chart-tb').style.display='none';
  document.getElementById('chart-info').textContent='';
  drawPnlChart(data.curve||[]);
}

function showCandles(sym){
  chartMode='candle';
  curSym=sym;
  const pos=data.positions||{};
  const p=pos[sym];
  const coins=data.coins||{};
  const c=coins[sym]||{};
  document.getElementById('chart-sym').textContent=sym.replace('USDT','')+'/USDT';
  document.getElementById('chart-badge').textContent=p?p.type+' '+p.lev+'x':'GRAFIK';
  document.getElementById('chart-tb').style.display='flex';
  const kl=p?p.klines:[];
  drawCandles(kl, p?.entry, p?.tp, p?.sl, p?.type);
  document.getElementById('chart-info').innerHTML=
    `<span>Fiyat: <b style="color:var(--cyan)">$${f(c.price)}</b></span>
     <span>24s: <b class="${cl(c.change)}">${fp(c.change||0)}</b></span>
     <span>Hacim: <b>${((c.volume||0)/1e6).toFixed(1)}M</b></span>`;
}

function setTf(tf,btn){
  curTf=tf;
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  if(curSym) showCandles(curSym);
}

// ── COIN MODAL ────────────────────────────────────────────
function openCoinModal(sym){
  const c=data.coins?.[sym]||{};
  document.getElementById('m-sym').textContent=sym.replace('USDT','')+'/USDT';
  document.getElementById('m-sub').textContent='Binance USDT-M Perpetual Futures';
  document.getElementById('m-price').textContent='$'+f(c.price);
  document.getElementById('m-change').textContent=(c.change>=0?'+':'')+c.change?.toFixed(2)+'%';
  document.getElementById('m-change').className='ms-v '+(c.change>=0?'c-green':'c-red');
  document.getElementById('m-high').textContent='$'+f(c.high);
  document.getElementById('m-low').textContent='$'+f(c.low);
  document.getElementById('modal').classList.add('show');

  // Draw modal candle chart
  const p=data.positions?.[sym];
  setTimeout(()=>{
    const kl=p?.klines||[];
    const mcv=document.getElementById('modal-cv');
    if(kl.length>2){
      const ctx=mcv.getContext('2d');
      const DPR=window.devicePixelRatio||1;
      const W=mcv.parentElement.offsetWidth;
      mcv.width=W*DPR; mcv.height=180*DPR;
      mcv.style.width=W+'px'; mcv.style.height='180px';
      ctx.scale(DPR,DPR);
      ctx.clearRect(0,0,W,180);
      const mn=Math.min(...kl.map(k=>k.l))*0.999;
      const mx=Math.max(...kl.map(k=>k.h))*1.001;
      const rng=mx-mn||1;
      const n=kl.length;
      const cw2=W-80, ch2=140;
      const pl=70,pt=10;
      const toY=v=>pt+ch2-((v-mn)/rng*ch2);
      const gap=Math.floor(cw2/n);
      const bw=Math.max(2,gap-1);
      for(let i=0;i<=3;i++){
        const y=pt+(ch2/3)*i;
        ctx.strokeStyle='rgba(22,32,53,0.8)'; ctx.lineWidth=1;
        ctx.beginPath(); ctx.moveTo(pl,y); ctx.lineTo(pl+cw2,y); ctx.stroke();
        const v=mx-(rng/3)*i;
        ctx.fillStyle='rgba(74,106,138,0.6)'; ctx.font='9px IBM Plex Mono';
        ctx.textAlign='right'; ctx.fillText('$'+f(v),pl-4,y+3);
      }
      kl.forEach((k,i)=>{
        const x=pl+i*gap+gap/2;
        const isU=k.c>=k.o;
        const color=isU?'#00ff88':'#ff3366';
        ctx.strokeStyle=color; ctx.lineWidth=1;
        ctx.beginPath(); ctx.moveTo(x,toY(k.h)); ctx.lineTo(x,toY(k.l)); ctx.stroke();
        const by=toY(Math.max(k.o,k.c));
        const bh=Math.max(1,toY(Math.min(k.o,k.c))-by);
        ctx.fillStyle=isU?'rgba(0,255,136,0.8)':'rgba(255,51,102,0.8)';
        ctx.fillRect(x-bw/2,by,bw,bh);
      });
      if(p){
        [
          {v:p.entry,color:'rgba(0,212,255,0.8)',label:'E'},
          {v:p.tp,color:'rgba(0,255,136,0.8)',label:'TP'},
          {v:p.sl,color:'rgba(255,51,102,0.8)',label:'SL'},
        ].forEach(({v,color,label})=>{
          if(!v)return;
          const y=toY(v);
          ctx.strokeStyle=color; ctx.lineWidth=1; ctx.setLineDash([4,3]);
          ctx.beginPath(); ctx.moveTo(pl,y); ctx.lineTo(pl+cw2,y); ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle=color; ctx.font='bold 9px IBM Plex Mono';
          ctx.textAlign='left'; ctx.fillText(label,pl+3,y-3);
        });
      }
    }
  },50);
}
function closeModal(){document.getElementById('modal').classList.remove('show')}

// ── MAIN LOOP ─────────────────────────────────────────────
async function tick(){
  try{
    const r=await fetch('/api/status');
    data=await r.json();
    if(data.error)return;

    running=data.running||false;
    syncUI();
    buildStats();
    buildTicker();
    buildCoins();
    buildPositions();
    buildHistory();
    buildStrategies();
    buildLog();

    if(chartMode==='pnl') drawPnlChart(data.curve||[]);
    else if(chartMode==='candle'&&curSym) showCandles(curSym);
  }catch(e){console.error(e)}
}

// Init
tick();
setInterval(tick,3000);
window.addEventListener('resize',()=>{
  if(chartMode==='pnl') drawPnlChart(data.curve||[]);
  else if(chartMode==='candle'&&curSym) showCandles(curSym);
});
</script>
</body>
</html>
"""

# ── WEB HANDLER ───────────────────────────────────────────
engine_g = None

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path=='/':
                self.send_response(200)
                self.send_header('Content-type','text/html;charset=utf-8')
                self.end_headers()
                self.wfile.write(HTML.encode('utf-8'))
            elif self.path=='/api/status':
                self.send_response(200)
                self.send_header('Content-type','application/json')
                self.send_header('Access-Control-Allow-Origin','*')
                self.end_headers()
                self.wfile.write(json.dumps(engine_g.state() if engine_g else {}).encode())
            elif self.path=='/api/start':
                self.send_response(200)
                self.send_header('Content-type','text/plain')
                self.end_headers()
                if engine_g and not engine_g.running:
                    threading.Thread(target=engine_g.start,daemon=True).start()
                self.wfile.write(b'ok')
            elif self.path=='/api/stop':
                self.send_response(200)
                self.send_header('Content-type','text/plain')
                self.end_headers()
                if engine_g: engine_g.stop()
                self.wfile.write(b'ok')
        except BrokenPipeError: pass
        except Exception as e: print(f"req err: {e}")
    def log_message(self,*a): pass

def main():
    global engine_g
    print("="*50)
    print("AI TRADING BOT v4.0")
    print("="*50)
    engine_g=Engine()
    srv=HTTPServer(('localhost',8000),H)
    print("\nhttp://localhost:8000")
    time.sleep(1)
    webbrowser.open('http://localhost:8000')
    print("Ctrl+C ile dur\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        if engine_g: engine_g.stop()
        srv.shutdown()
        print("Durduruldu")

if __name__=='__main__':
    main()