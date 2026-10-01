{ ============================================================
  黑美人重建版（XQ 選股腳本）
  條件：今天突破前3天高點，且（寶塔翻紅 或 爆量1.5倍 + 均線多頭）
  濾網：股本 <= 20 億、成交量 > 1000 張
  掃描：判斷日往回 ScanDays 天內，任一天觸發即選出
  ------------------------------------------------------------
  使用方式：
    1. XS 編輯器 → 新增「選股」腳本 → 貼上本檔全部內容 → 編譯
    2. 選股中心 → 自訂選股 → 加入此腳本，頻率選「日」
    3. DaysAgo = 0：今天收盤後跑（選明天的標的）
       DaysAgo = 1：只用到昨天的資料（驗證昨天是否已選得出）
  ============================================================ }

input: DaysAgo(0, "判斷日(0=今天,1=昨天)");
input: ScanDays(4, "掃描天數(含判斷日)");
input: BreakLen(3, "突破區間天數");
input: LookBack(100, "回溯天數");
input: VolRatio(1.5, "量增倍數");
input: MA1Len(5, "MA1天數");
input: MA2Len(10, "MA2天數");
input: CapLimit(20, "股本上限(億)");
input: MinVol(1000, "最低成交量(張)");

variable: upSig(false), dnSig(false);
variable: sUp(99999), sDn(99999);
variable: prevUp(0), prevDn(0);
variable: condA(false), condB(false), sig(false);
variable: k(0), hitK(-1), cap(0);
variable: hitDate(0), chg(0);

SetTotalBar(LookBack + ScanDays + DaysAgo + MA2Len + 20);

{ ---- 每根K棒計算訊號 ---- }
{ 對應 $CLOSE > @MAX(-3,3,HIGH) 與 $CLOSE < @MIN(-3,3,LOW)（前3天，不含今天） }
upSig = Close > Highest(High, BreakLen)[1];
dnSig = Close < Lowest(Low, BreakLen)[1];

{ 最近一次突破／跌破距今幾根K棒（不含今天） }
prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);

{ 寶塔翻紅：今天突破，且 (回溯期間沒突破過 或 最近一次跌破比突破更近) }
condA = upSig and
        (prevUp > LookBack or (prevDn <= LookBack and prevDn < prevUp));

{ 爆量 + 均線多頭：$VOL > $VOL[-1]*1.5 & $MA1 > $MA2 }
condB = Volume > Volume[1] * VolRatio
        and Average(Close, MA1Len) > Average(Close, MA2Len);

{ 對照財富守護星實測：必須當天突破，且(翻紅 或 爆量) }
sig = upSig and (condA or condB) and Volume > MinVol;

{ 更新「距上次訊號幾根」計數 }
if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

{ ---- 判斷日往回 ScanDays 天內找最近一次觸發 ---- }
hitK = -1;
for k = DaysAgo to DaysAgo + ScanDays - 1 begin
    if hitK = -1 and sig[k] then hitK = k;
end;

hitDate = 0;
chg = 0;
if hitK >= 0 then begin
    hitDate = Date[hitK];
    if Close[hitK] > 0 then
        chg = (Close - Close[hitK]) / Close[hitK] * 100;
end;

cap = GetField("股本(億)", "D");

if hitK >= 0 and cap > 0 and cap <= CapLimit then ret = 1;

OutputField(1, hitDate, 0, "觸發日");
OutputField(2, hitK, 0, "幾天前觸發");
OutputField(3, cap, 2, "股本(億)");
OutputField(4, chg, 2, "觸發後至今漲幅%");
