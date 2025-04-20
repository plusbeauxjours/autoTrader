import time

class RiskManager:
    def __init__(self, max_daily=5, max_streak=3, cooldown_m=30, risk=0.02):
        self.max_daily = max_daily
        self.max_streak = max_streak
        self.cooldown = cooldown_m*60
        self.risk = risk
        self.trades = 0
        self.streak = 0
        self.last = {}
        self.start = time.time()

    def can_trade(self, sym):
        now = time.time()
        if now - self.start > 86400:
            self.trades=0; self.streak=0; self.start=now
        if self.trades>=self.max_daily or self.streak>=self.max_streak: return False
        if sym in self.last and now<self.last[sym]+self.cooldown: return False
        return True

    def register(self, pnl, sym):
        if pnl<0: self.streak+=1
        else: self.streak=0
        self.trades+=1
        self.last[sym]=time.time()

    def size_leverage(self, bal, entry, stop):
        risk_amt=bal*self.risk
        diff=abs(entry-stop)
        qty=risk_amt/diff
        pct=diff/entry*100
        lev=10 if pct<=1 else (5 if pct<=2 else 2)
        return qty, lev
