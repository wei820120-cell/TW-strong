{ ============================================================
  小強 對照版（XQ 選股腳本）
  用途：跟財富守護星的結果逐檔比對，找出兩邊差在哪個條件
  BranchMode：0 = 翻紅 或 爆量（原公式）
              1 = 只看寶塔翻紅
              2 = 只看爆量 + 均線多頭
              3 = 今天突破 且 (翻紅 或 爆量)  ← 測試財富守護星的實際解讀
  輸出欄位會標示每檔是哪個條件成立，方便對照
  ============================================================ }

input: BranchMode(0, "條件(0=兩者,1=只翻紅,2=只爆量,3=突破且兩者)");
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
variable: condA(false), condB(false), pass(false);
variable: ma1(0), ma2(0), cap(0), volX(0), nA(0), nB(0), nU(0), chg(0);

SetTotalBar(LookBack + MA2Len + 20);

upSig = Close > Highest(High, BreakLen)[1];
dnSig = Close < Lowest(Low, BreakLen)[1];

prevUp = MinList(sUp[1] + 1, 99999);
prevDn = MinList(sDn[1] + 1, 99999);

condA = upSig and
        (prevUp > LookBack or (prevDn <= LookBack and prevDn < prevUp));

ma1 = Average(Close, MA1Len);
ma2 = Average(Close, MA2Len);
condB = Volume > Volume[1] * VolRatio and ma1 > ma2;

if upSig then sUp = 0 else sUp = prevUp;
if dnSig then sDn = 0 else sDn = prevDn;

if BranchMode = 1 then pass = condA
else if BranchMode = 2 then pass = condB
else if BranchMode = 3 then pass = upSig and (condA or condB)
else pass = condA or condB;

cap = GetField("股本(億)", "D");

volX = 0;
if Volume[1] > 0 then volX = Volume / Volume[1];
nA = 0; if condA then nA = 1;
nB = 0; if condB then nB = 1;
nU = 0; if upSig then nU = 1;
chg = 0;
if Close[1] > 0 then chg = (Close - Close[1]) / Close[1] * 100;

if pass and cap > 0 and cap <= CapLimit and Volume > MinVol then ret = 1;

OutputField(1, nA, 0, "翻紅");
OutputField(2, nB, 0, "爆量");
OutputField(3, volX, 2, "量比");
OutputField(4, ma1, 2, "MA1");
OutputField(5, ma2, 2, "MA2");
OutputField(6, cap, 2, "股本(億)");
OutputField(7, nU, 0, "突破");
OutputField(8, chg, 2, "漲幅");
