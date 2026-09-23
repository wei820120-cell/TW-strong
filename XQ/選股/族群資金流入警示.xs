{ ============================================================
  族群資金流入警示（XQ 警示腳本，搭配「策略雷達」使用）
  監控對象：類股指數（不是個股）
    策略雷達 → 執行商品選「組合」→「台股指數」→ 上市櫃類股指數
  觸發條件（同時成立）：
    1. 類股預估成交量 >= 近 N 日均量 × VolRatio（資金明顯湧入）
    2. 類股漲幅 >= MinChg%
    3. 類股漲幅比大盤多 RelChg% 以上（強於大盤，不是跟著大盤漲）
  訊息範例：「資金流入 漲2.35% 強於大盤1.60% 量比1.8倍」
  ============================================================ }

input: VolRatio(1.5, "量比門檻(倍)");
input: AvgDays(5, "均量天數");
input: MinChg(1.5, "類股漲幅下限%");
input: UseRel(1, "要強於大盤(1=是,0=否)");
input: RelChg(1, "比大盤多漲幾%");
input: EstMinMins(15, "開盤幾分鐘後才判斷");

variable: t(0), mins(0), estVol(0), avgVol(0), volX(0);
variable: chg(0), mkt(0), mktPrev(0), mktChg(0), rel(0);

SetTotalBar(AvgDays + 10);

{ ---- 已開盤分鐘數（09:00~13:30 共 270 分鐘） ---- }
mins = 270;
if Date = CurrentDate then begin
    t = CurrentTime;
    mins = (IntPortion(t / 10000) - 9) * 60 + Mod(IntPortion(t / 100), 100);
    if mins > 270 then mins = 270;
end;

{ ---- 預估全日成交量 與 量比 ---- }
estVol = Volume;
if mins > 0 and mins < 270 then estVol = Volume * 270 / mins;
avgVol = Average(Volume, AvgDays)[1];
volX = 0;
if avgVol > 0 then volX = estVol / avgVol;

{ ---- 類股漲幅 ---- }
chg = 0;
if Close[1] > 0 then chg = (Close - Close[1]) / Close[1] * 100;

{ ---- 大盤（加權指數）漲幅 ---- }
rel = chg;
if UseRel = 1 then begin
    mkt = GetSymbolField("TSE.TW", "收盤價");
    mktPrev = GetSymbolField("TSE.TW", "收盤價")[1];
    mktChg = 0;
    if mktPrev > 0 then mktChg = (mkt - mktPrev) / mktPrev * 100;
    rel = chg - mktChg;
end;

if mins >= EstMinMins
   and volX >= VolRatio
   and chg >= MinChg
   and (UseRel = 0 or rel >= RelChg)
then begin
    RetMsg = "資金流入 漲" + NumToStr(chg, 2) + "%"
             + " 強於大盤" + NumToStr(rel, 2) + "%"
             + " 量比" + NumToStr(volX, 1) + "倍";
    ret = 1;
end;
