{ ============================================================
  黑美人 盤中警示版（XQ 警示腳本，搭配「策略雷達」使用）
  條件：寶塔翻紅（首次由空翻多）或 爆量1.5倍 + 均線多頭
  濾網：股本 <= 20 億、成交量 > 1000 張
  ------------------------------------------------------------
  使用方式：
    1. XS 編輯器 → 新增「警示」腳本 → 貼上本檔全部內容 → 編譯
    2. 策略雷達 → 新增策略 → 選此警示腳本
       執行頻率選「日」，商品範圍選「上市櫃普通股」或自選股
       通知方式勾選彈跳視窗／聲音／手機推播 → 啟動
  盤中成交量還沒累積完，UseEstVol=1 時用「預估全日量」判斷量增
  ============================================================ }

input: BreakLen(3, "突破區間天數");
input: LookBack(100, "回溯天數");
input: VolRatio(1.5, "量增倍數");
input: MA1Len(5, "MA1天數");
input: MA2Len(10, "MA2天數");
input: CapLimit(20, "股本上限(億)");
input: MinVol(1000, "最低成交量(張)");
input: UseEstVol(1, "盤中用預估量(1=是,0=否)");

variable: upSig(false), dnSig(false);
variable: sUp(99999), sDn(99999);
variable: prevUp(0), prevDn(0);
variable: condA(false), condB(false);
variable: cap(0), vol(0), t(0), mins(0);

SetTotalBar(LookBack + MA2Len + 20);

{ ---- 盤中預估全日量（09:00~13:30 共 270 分鐘） ---- }
vol = Volume;
if UseEstVol = 1 and Date = CurrentDate then begin
    t = CurrentTime;
    mins = (IntPortion(t / 10000) - 9) * 60 + Mod(IntPortion(t / 100), 100);
    if mins > 0 and mins < 270 then vol = Volume * 270 / mins;
end;

{ ---- 突破／跌破前3天高低點（不含今天） ---- }
upSig = Close > Highest(High, BreakLen)[1];
dnSig = Close < Lowest(Low, BreakLen)[1];

prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);

{ 寶塔翻紅：今天突破，且 (回溯期間沒突破過 或 最近一次跌破比突破更近) }
condA = upSig and
        (prevUp > LookBack or (prevDn <= LookBack and prevDn < prevUp));

{ 爆量 + 均線多頭 }
condB = vol > Volume[1] * VolRatio
        and Average(Close, MA1Len) > Average(Close, MA2Len);

if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

cap = GetField("股本(億)", "D");

if (condA or condB)
   and Volume > MinVol
   and cap > 0 and cap <= CapLimit
then begin
    if condA then
        RetMsg = "寶塔翻紅"
    else
        RetMsg = "爆量+均線多頭";
    ret = 1;
end;
