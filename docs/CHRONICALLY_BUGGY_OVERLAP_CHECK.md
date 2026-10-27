# Chronically Buggy 全文取得與 Time 稿重疊查核

查核／accessed：**2026-10-27**。僅第一手公開來源、Web 與 GB10 輕量文字處理；未付費、未聯絡作者、未呼叫研究模型、未運行第三方實驗或修改 case／runner／正式資料。工作分支從當次最新 fetched `origin/main` `456fb3e92366802ff8dc4a3d414e3a4fd4f5faab` 建立。

**結果：本輪仍未取得 Chronically Buggy 全文或作者 accepted manuscript，不能完成對其逐節閱讀，也不能聲稱已排除與 Time repair／policy ablation 的重疊。** 可確認的是作者接受公告，以及公開 precursor／dt-fuzz artifact 中更具體的既有語意差異。本文將三者分開，沒有把舊 MSR paper 或一頁 dt-fuzz 圖冒充 EMSE 完整稿。

## 1. 全文入口查核台帳

| 第一手入口與完整 URL | 本輪可觀測結果與限制 |
|---|---|
| 作者：https://www.shreytiwari.com/ | October 2026 News 公告 EMSE 接受；Publications 有 Chronically Buggy 題名、七位作者及 EMSE 2026，但條目沒有 paper／artifact 連結。相鄰 MSR2025 的 PDF／Code 不屬此條目。 |
| 共同作者：https://leyicui-angel.github.io/publications.html | 同樣列 2026 EMSE，該條目無全文／artifact URL。沒有採用其「可寄信索取」選項。 |
| Rohan Padhye：https://rohan.padhye.org/ ；PASTA：https://pastalab.org/ | 本輪讀出版清單，時間研究可見 MSR2025 precursor；沒有看到 Chronically Buggy 連結。這只表示所讀頁面未提供，不表示未接受／未發表。 |
| arXiv 精確題名：https://export.arxiv.org/api/query?search_query=ti:%22Chronically%20Buggy%22&max_results=5 | Web 搜尋頁先 timeout；GB10 合法公開 API 後成功回 XML，`totalResults=0`。只對此題名查詢成立，不排除不同題名／尚未上傳稿。 |
| Crossref：https://api.crossref.org/works?query.title=Chronically%20Buggy&rows=5&select=title,DOI,URL,link | 前五筆無 exact title match；沒有取得 DOI 或全文連結。搜尋排序不是完整不存在證明。 |
| Springer：https://link.springer.com/search?query=%22Chronically+Buggy%22 | Web reader 無法存取搜尋入口；另以精確題名、作者與 EMSE 限定 publisher domain 搜尋未得到文章紀錄。本輪沒有拿到可判定 paywall／OA 狀態的 exact article page；不能把工具存取失敗寫成確認 paywall。 |
| CMU KiltHub：https://kilthub.cmu.edu/search?q=%22Chronically%20Buggy%22 | Web reader 不可存取該搜尋頁；站點限定精確題名搜尋未找到稿件。不是所有 institution holdings 的完整查核。 |
| 公開 GitHub 候選 artifacts：下節兩個 repos | 已檢查公開 branches 與 PDF／TeX／Bib／Markdown 路徑，沒有找到 EMSE 完整稿。不能證明它們就是 accepted 論文完整的正式 artifact。 |

精確題名與 author/publisher/institution 限定搜尋皆只得到作者列目或 MSR precursor；沒有採用未授權鏡像或繞過存取限制。以上是有界搜尋的完整缺口記錄，不再以摘要推論「該論文沒有某實驗」。

## 2. 已取得且能精確定位的 precursor

[It's About Time: An Empirical Study of Date and Time Bugs in Open-Source Python Software](https://rohan.padhye.org/files/datetimebugs-msr25.pdf)，MSR2025，13頁。**本輪是針對下列問題讀指定段落，不宣稱重新完整讀了13頁。** 頁碼以 PDF 從1起算；不是 Chronically Buggy 的頁碼。

| 精確位置 | Observed 內容 | 對本稿的直接限制 |
|---|---|---|
| PDF p.5，§III-C（分析結果與一致性） | 151 個確定日期／時間 bugs、102 個不同 projects；先分析260 issues／144 repos。 | 151 是該 precursor 的 bugs，不是 EMSE 更新後數字，也不能直接當151個可執行 repair roots。 |
| PDF pp.2–3，§II-A、Fig.1 | GPT-4o 產生的「到明日本地17時有多少hours」例子；文中已說全部改UTC也會把本地日期弄錯，須區分 local calendar target 與 elapsed difference。 | 不可把「一律UTC不是通用修補」或 calendar／elapsed 分離當首次洞見。此示例不是一個完整自然 repo LLM repair 實驗。 |
| PDF pp.7–8，§IV-B/C、Fig.5 | 已討論 datetime arithmetic、Pendulum duration components 與 unintuitive arithmetic 等根因。 | Duration／單位相關錯誤這個大類已有；未因此確認有我們特指的 constructor unit-origin preservation 對照。 |
| PDF p.11，§VII–VIII | 公開 annotated bug/fix dataset 與 CodeQL 分析，並將自動修補列為潛力／假說。 | 不能因這幾段沒出現修補迴圈就推論 EMSE 擴充稿不存在自然 LLM repair、cross-operation regression 或 policy ablation。 |

前作根因／repo數的唯一可核查答案目前是上述 **MSR2025** 數字；**Chronically Buggy 的相應數字仍 unknown**。不要把兩篇可能的擴充關係自行補成已證實的資料沿用。

## 3. 公開 artifact 的可核查重疊

### 3.1 自然 bugs 與 fix 分析資源

- Repo：https://github.com/cmu-pasta/date-time 。main 本輪 API ref：`e45bfbc870301d42158dd067d8a6697a965e9d05`，公開 branch 清單僅 main。
- 讀取：[README](https://github.com/cmu-pasta/date-time/blob/e45bfbc870301d42158dd067d8a6697a965e9d05/README.md) 全文與 recursive tree 中的文稿類路徑。README 表示 `analysis` 是標記資料、`benchmarks` 是根據真實 bug/smell 建的 CodeQL 程式、`codeql` 是查詢，不等同完整 repo-level repair benchmark。
- 本輪未分析全部 benchmark／annotated rows，沒有從目錄大小臆測新的 bug 數。這個 repo 經 MSR paper §VII 明確連結；未找到 Chronically Buggy 將它指定為完整 accepted artifact 的聲明。

### 3.2 dt-fuzz：可以證成的是生成／差分，不是已證成的 repair-loop 結論

Repo：https://github.com/cmu-pasta/date-time-genai 。main `b700998b909165063c660f19a46b9109a7315deb`，另有公開 dev `e6b9345787f24327d52eb351f31a65c2b42b30d4`。

本輪沿用前輪完整 README 與 test runner/helper 閱讀，再新增完整讀取 main 的 `run.py`、`sample_llm/sample_code.py`、`example/README.md`、`example/dt_code.py`、`example/pd_code.py` 及兩份短 manual TSV；檢查 main／dev 文稿類 tree、dev README 的文稿線索。**未重新逐檔讀所有 repo，也沒有運行程式或下載大型 logs。**

| 精確固定來源 | Observed 內容 | 可以／不可以說什麼 |
|---|---|---|
| [run.py L199–276](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/run.py#L199) | 階段為想法、獨立 library code generation、建 diff tests、執行 diff tests、分析。已讀完整入口，不見把語意失敗重新餵回原 patch 的 stage。 | 可說「此 main 公開入口呈現生成與差分流程」；不能說整篇 Chronically Buggy 從未做 repair。 |
| [sample_code.py L53–129](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/sample_llm/sample_code.py#L53) | `validate_computations` 只檢單一 code block／entry point。重試重新使用既有 prompt，未加入 semantic test feedback。 | 這個 retry 不是 counterexample-guided repair；不把產生格式失敗重試當修補迴圈。 |
| [example/dt_code.py](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/example/dt_code.py)、[pd_code.py](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/example/pd_code.py) | 表面相同的 `abs((dt2-dt1).days)` 以不同庫執行並輸出 logs。 | 已有 duration/day 表示差異的檢查示例；這不是由自然 repo patch 造成另一 public operation regression 的實驗。 |
| [manual reliability TSV L18–21](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/manual_analysis/reliability_results.tsv#L18)、[divergence TSV](https://github.com/cmu-pasta/date-time-genai/blob/b700998b909165063c660f19a46b9109a7315deb/manual_analysis/divergence_results.tsv) | 已標記 Feb29→Feb28／Mar1、endpoint inclusion、days部分處理、interface與precision差異。 | 這些政策／語意家族已重疊，不能聲稱首次發現。兩份 TSV 有 unresolved merge-conflict markers 與重複區塊，故本輪不自行彙總比例或視為清理完成的最新資料。 |
| [dt-fuzz.pdf](https://raw.githubusercontent.com/cmu-pasta/date-time-genai/b700998b909165063c660f19a46b9109a7315deb/dt-fuzz.pdf) | GB10 `pdfinfo` 確認1頁；`pdftotext` 全文只有 task/code generation → fuzzing／differential → manual analysis 的流程標籤。main／dev tree 中其餘PDF是結果圖，不是完整稿。 | **沒有取得一篇獨立 dt-fuzz 全文論文。** 此PDF不是 Chronically Buggy 全文；一頁圖不可能支持整篇沒有 repair-loop 結論的否定主張。 |

## 4. 問題逐項判定

| 要核對的核心問題 | 目前能支持的最強答案 |
|---|---|
| Chronically Buggy 自然 bugs／根因／repo數 | **未知**。151 bugs／102 projects 只可附MSR2025來源與頁碼；不能挪作EMSE數字。 |
| 已有 calendar vs elapsed？ | **語意家族已重疊**：MSR Fig.1 明確區分 local date target／elapsed subtraction；dt-fuzz有跨庫day差異。對EMSE全文涵蓋深度仍未知。 |
| 已有 unit-origin 差異？ | 已有duration components／days／library表示相關討論；**未核實**與我們特指 construction單位保留、且投射到其他public operation 的相同實驗。不能因此宣稱沒有。 |
| 修補引發其他 public operation regression？ | 已讀公開 dt-fuzz入口與sample code沒有此測量設計；**EMSE是否已做未知**，MSR fix分析亦不能代替generated-patch regression study。 |
| 自然 LLM repair？ | MSR有LLM生成motivation示例，不等於自然repo repair campaign。dt-fuzz所讀main入口是snippet generation＋差分；**EMSE的自然repair研究未知**。 |
| policy／reproducer ablation？ | 所讀artifact程式沒有可識別的此類semantic-feedback arms；**EMSE是否有獨立實驗未知**。單靠摘要或缺少stage名稱不能排除。 |
| dt-fuzz已得到同樣repair-loop結論？ | **本輪沒有可取得的全文支持這句話**。main入口可見範圍也不是同類repair loop；這是有界的artifact觀察，不能推廣成整篇不存在。 |

## 5. Time 稿可採用的定位

已足以排除的過寬新意：自然時間bugs分類、LLM日期錯誤、需求歧義、月底政策、duration語意與「一律UTC無法通用」均不能作首次發現。

若正式資料支持，可將窄貢獻寫為：**在固定歷史repo、來源支持的政策與既定模型設定下，觀察自然修補是否保持不同public operations的語意，並比較正式預定的資訊／回饋條件。** 是否只有回饋表示不同、或額外給了需求資訊，要按實際arms說明；這些是我們能由自己的資料支持的結果，不是聲稱 Chronically Buggy 沒做過。

建議 related-work 句型：

> MSR2025 的自然 bug 研究與公開 dt-fuzz artifact 已指出日期程式對 library conventions、local/elapsed semantics 及需求歧義的敏感性。我們針對所選 repository repairs 量測來源契約與跨 operation 行為。作者另公告 Chronically Buggy 獲 EMSE 接受，但本研究查核日尚未取得其完整稿，故不宣稱已排除該擴充稿的所有實驗重疊。

這項全文缺口不新增實驗 gate、不改目前正式資料。保留文獻風險與窄claim，比將未取得內容寫成「不存在」更可供評審檢查。
