{ ============================================================
  帥大叔 診斷版（XQ 警示腳本）
  用途：找出「帥大叔」為什麼沒有觸發
  每檔股票都會觸發一次，訊息列出每個條件的實際數值
  策略雷達的執行商品請只放幾檔股票（例如 6226、1528、2330），
  不要用「普通股全部」，否則會跳出上千則
  ------------------------------------------------------------
  訊息欄位：
    股本 = 讀到的股本(億)，0 代表讀不到 → 股本濾網把全部擋掉
    K棒 = 實際讀到幾根日K，太少代表資料讀取不足
    突破 = 今天是否突破前3天高點（1=是）
    翻紅 = 寶塔翻紅條件 condA（1=成立）
    爆量 = 爆量+均線多頭 condB（1=成立）
    量 / 預估量 / 昨量 = 單位：張
  ============================================================ }

input: BreakLen(3, "突破區間天數");
input: LookBack(100, "回溯天數");
input: VolRatio(1.5, "量增倍數");
input: MA1Len(5, "MA1天數");
input: MA2Len(10, "MA2天數");
input: EstMinMins(10, "開盤幾分鐘後才用預估量");

variable: upSig(false), dnSig(false);
variable: sUp(99999), sDn(99999);
variable: prevUp(0), prevDn(0);
variable: condA(false), condB(false);
variable: cap(0), vol(0), t(0), mins(0);
variable: nA(0), nB(0), nU(0);

SetTotalBar(LookBack + MA2Len + 20);

vol = Volume;
if Date = CurrentDate then begin
    t = CurrentTime;
    mins = (IntPortion(t / 10000) - 9) * 60 + Mod(IntPortion(t / 100), 100);
    if mins >= EstMinMins and mins < 270 then vol = Volume * 270 / mins;
end;

upSig = Close > Highest(High, BreakLen)[1];
dnSig = Close < Lowest(Low, BreakLen)[1];

prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);

condA = upSig and
        (prevUp > LookBack or (prevDn <= LookBack and prevDn < prevUp));

condB = vol > Volume[1] * VolRatio
        and Average(Close, MA1Len) > Average(Close, MA2Len);

if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

cap = GetField("股本(億)", "D");

nU = 0; if upSig then nU = 1;
nA = 0; if condA then nA = 1;
nB = 0; if condB then nB = 1;

{ 無條件觸發，用來看數值 }
if Close > 0 then begin
    RetMsg = "股本" + NumToStr(cap, 2)
           + " K棒" + NumToStr(CurrentBar, 0)
           + " 突破" + NumToStr(nU, 0)
           + " 翻紅" + NumToStr(nA, 0)
           + " 爆量" + NumToStr(nB, 0)
           + " 量" + NumToStr(Volume, 0)
           + " 預估量" + NumToStr(vol, 0)
           + " 昨量" + NumToStr(Volume[1], 0);
    ret = 1;
end;
