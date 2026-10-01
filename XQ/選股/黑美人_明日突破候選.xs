{ ============================================================
  黑美人 明日突破候選（XQ 選股腳本，免費版可用）
  用途：收盤後選出「明天只要突破，就會觸發黑美人訊號」的股票，
        並列出突破價，隔天用到價提醒或自己盯盤
  ------------------------------------------------------------
  類型 1 = 寶塔翻紅候選：明天收盤突破「突破價」就是寶塔翻紅
  類型 2 = 爆量候選（IncludeB=1 才會列出）：均線多頭，
           明天突破突破價且量 > 爆量門檻，就是爆量+均線多頭訊號
  ------------------------------------------------------------
  突破價 = 最近 3 天（含判斷日）的最高價，明天股價「超過」它才算突破
  距離%  = 判斷日收盤價要再漲幾 % 才會突破
  DaysAgo = 1 可驗證：用前一天的資料選候選，看「隔日最高破」「隔日收盤破」
  ============================================================ }

input: DaysAgo(0, "判斷日(0=今天收盤,1=前一天)");
input: NearPct(5, "距突破價幾%內");
input: IncludeB(0, "納入爆量候選(1=是,0=否)");
input: BreakLen(3, "突破區間天數");
input: LookBack(100, "回溯天數");
input: VolRatio(1.5, "量增倍數");
input: MA1Len(5, "MA1天數");
input: MA2Len(10, "MA2天數");
input: CapLimit(20, "股本上限(億)");
input: MinVol(500, "判斷日成交量下限(張)");

variable: upSig(false), dnSig(false);
variable: sUp(99999), sDn(99999);
variable: prevUp(0), prevDn(0);
variable: hh(0), ma1(0), ma2(0);
variable: d(0), bp(0), nUp(0), nDn(0), dist(0), typ(0), cap(0);
variable: setupA(false), maBull(false);
variable: hitHigh(0), hitClose(0);

SetTotalBar(LookBack + MA2Len + DaysAgo + 20);

{ ---- 每根K棒：突破／跌破狀態（與盤中警示同一套邏輯） ---- }
upSig = Close > Highest(High, BreakLen)[1];
dnSig = Close < Lowest(Low, BreakLen)[1];

prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);
if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

hh = Highest(High, BreakLen);
ma1 = Average(Close, MA1Len);
ma2 = Average(Close, MA2Len);

{ ---- 站在判斷日收盤，推算「下一個交易日」 ---- }
d = DaysAgo;
bp = hh[d];                                  { 下一日的突破價 }
nUp = MinList(sUp[d] + 1, 99999);            { 下一日時，距上次突破幾根 }
nDn = MinList(sDn[d] + 1, 99999);            { 下一日時，距上次跌破幾根 }

{ 下一日若突破，是否符合寶塔翻紅 }
setupA = nUp > LookBack or (nDn <= LookBack and nDn < nUp);
maBull = ma1[d] > ma2[d];

typ = 0;
if setupA then typ = 1
else if IncludeB = 1 and maBull then typ = 2;

dist = 0;
if Close[d] > 0 then dist = (bp - Close[d]) / Close[d] * 100;

cap = GetField("股本(億)", "D");

{ 驗證用：判斷日的下一天，最高價／收盤價有沒有超過突破價 }
hitHigh = 0;
hitClose = 0;
if d >= 1 then begin
    if High[d - 1] > bp then hitHigh = 1;
    if Close[d - 1] > bp then hitClose = 1;
end;

if typ > 0
   and dist <= NearPct
   and Volume[d] >= MinVol
   and cap > 0 and cap <= CapLimit
then ret = 1;

OutputField(1, bp, 2, "突破價");
OutputField(2, dist, 2, "距離%");
OutputField(3, typ, 0, "類型");
OutputField(4, Volume[d] * VolRatio, 0, "爆量門檻(張)");
OutputField(5, cap, 2, "股本(億)");
OutputField(6, hitHigh, 0, "隔日最高破");
OutputField(7, hitClose, 0, "隔日收盤破");
