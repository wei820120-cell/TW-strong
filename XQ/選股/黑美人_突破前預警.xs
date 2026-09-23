{ ============================================================
  黑美人 突破前預警（XQ 警示腳本，搭配「策略雷達」使用）
  用途：股價「快要」寶塔翻紅時先通知，並顯示突破價，
        讓你提前掛好觸價買單，突破瞬間就成交
  條件：
    1. 下一次突破會是「寶塔翻紅」（回溯期間沒突破過，或最近是跌破）
    2. 現價距離突破價（前3天最高價）在 NearPct% 以內，但還沒突破
    3. 股本 <= 20 億、昨量 >= 500 張
  ------------------------------------------------------------
  策略雷達設定同「黑美人_盤中警示」：頻率「日」、逐筆洗價、
  執行商品「台股上市櫃類股-普通股全部」
  ============================================================ }

input: BreakLen(3, "突破區間天數");
input: LookBack(100, "回溯天數");
input: NearPct(2, "距突破價幾%內預警");
input: CapLimit(20, "股本上限(億)");
input: MinPrevVol(500, "昨量下限(張)");

variable: upSig(false), dnSig(false);
variable: sUp(99999), sDn(99999);
variable: prevUp(0), prevDn(0);
variable: setupOK(false), hh(0), cap(0);

SetTotalBar(LookBack + 20);

hh = Highest(High, BreakLen)[1];

upSig = Close > hh;
dnSig = Close < Lowest(Low, BreakLen)[1];

prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);

{ 如果現在突破，會不會是「寶塔翻紅」 }
setupOK = prevUp > LookBack or (prevDn <= LookBack and prevDn < prevUp);

if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

cap = GetField("股本(億)", "D");

if setupOK
   and Close <= hh
   and Close >= hh * (1 - NearPct / 100)
   and Volume[1] >= MinPrevVol
   and cap > 0 and cap <= CapLimit
then begin
    RetMsg = "接近寶塔翻紅 突破價 " + NumToStr(hh, 2);
    ret = 1;
end;
