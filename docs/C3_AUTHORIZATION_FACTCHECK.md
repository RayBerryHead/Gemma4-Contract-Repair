# C3 Authorization：產品契約、RFC 與已觀測行為

查核日／accessed：2026-10-27。只讀官方來源及 GB10；未重跑模型或案例、未修改正式 case／runner／selection／run artifacts。文件由最新 fetched `origin/main` `2ed886d0338a54669f6f0468ce6b13760d5509d7` 的獨立 worktree 建立。

**結論：僅跳過 Django 本地儲存的候選，不符合上游新增的 Vary 行為；但沒有 Vary、private 或 no-store，本身不足以證明跨使用者洩漏，也不足以說它違反 RFC 的 authenticated-response 保護。** 現有兩次回應內容隔離成功與 outgoing-header 不相符，應分開報。

## 已核查的第一手證據

1. [Django fixed commit](https://github.com/django/django/commit/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9)：parent 是 `d618d7ae4fec727d5b582bd24f803c28d17bf7cd`；修補主旨為非 public 回應依 Authorization 區分。未用目前 main 代替此版本。
2. [固定版產品程式](https://github.com/django/django/blob/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9/django/middleware/cache.py#L136)：在既有可儲存路徑，對非空 Authorization 且非 public 回應加入 Vary，後續依其建立 key。private/no-cache/no-store、streaming 等早退條件仍存在，故不能概括成所有回應必須加 Vary。
3. [固定版文件](https://github.com/django/django/blob/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9/docs/topics/cache.txt#L1406)：同一修補明說 varying on Authorization 並非嚴格必要（原文 “not strictly necessary”），Django 是為了簡化 cache-key 建構而加此欄。這直接否定「無 Vary 必然表示下游沒有保護」的推論。
4. [固定版測試](https://github.com/django/django/blob/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9/tests/cache/tests.py#L2883)：`test_vary_on_authorization_for_authorization_header` 明確檢查回應 Vary；另測 empty header 與 public 例外。原碼／測試註解說 Django 未實作 RFC 的 s-maxage、must-revalidate 例外；這是產品邊界，不可誤寫成 RFC 不承認它們。[發布說明](https://github.com/django/django/blob/a2faa8e895926ac5d63f72879b5ccf671b5b4ba9/docs/releases/6.0.6.txt#L56)亦把 Vary 與現有 key 機制連結。
5. [RFC 9111 §3](https://httpwg.org/specs/rfc9111.html#storing.responses.in.caches)、[§3.5](https://httpwg.org/specs/rfc9111.html#storing.authenticated.responses)、[§4.1](https://httpwg.org/specs/rfc9111.html#caching.negotiated.responses)、[§5.2.2](https://httpwg.org/specs/rfc9111.html#cache-response-directive)：本輪讀取相關儲存／重用條件及指令定義。Authorization 預設限制 shared cache；public、s-maxage、must-revalidate 是例外，max-age 本身只是 freshness。Vary 是另一層 key matching；private/no-store 可施加額外限制，但 RFC 不要求每個 authenticated response 必須宣告三者之一。

## 現有候選與證據的精確讀法

由主 agent 提供的觀測（本核查未獨立重跑）：自然 M patch 對帶 Authorization、非 public／未 Vary 的 request 在 response 階段早退；兩次 body 為 alice、bob，`origin_calls=2`，回應是 `Cache-Control: max-age=300`、無 Vary。

| 判斷 | 此時支持的範圍 |
|---|---|
| 兩次本地請求隔離 | 支持提供序列的內容正確且兩次到 origin；沒有展示該序列跨身份重播。不能由此證明所有 warm state／路徑都正確。 |
| 與 upstream 行為的差異 | 對這條適用路徑，候選沒有產生上游新增的 Authorization Vary，因此可記為 outgoing-header／產品契約差異。這不是只因 helper 名稱不同而拒絕。 |
| RFC-compliant downstream shared cache | 若完整回應指令只有 max-age，且原請求有 Authorization，就不能僅因沒有 Vary 推論可共享重播；§3／§3.5 的預設限制仍生效。若實際還有 public、s-maxage、must-revalidate，則需依其規則另判，不能從本觀測補造。 |
| 本地 bypass 是否安全等價 | 現有有限行為與 RFC 分析不足以證明全域等價，也不足以自動判為不安全。要區分本研究是否要求精確產品 header 行為，及較寬的安全／功能行為等價；兩個問題不可混成一個 privacy 指標。 |
| private/no-store 是否「必需」 | 上游選的是 Vary，而非強制這兩個指令。它們可能是較保守替代，但能否接受仍依事前宣告的功能契約；不能憑本候選沒有它們就判洩漏。 |

RFC 的規則不保證任意 application cache 都會實作完整 HTTP 行為；[§6](https://httpwg.org/specs/rfc9111.html#applications)也區分 application cache。反過來，不能憑空假定一個忽略 Authorization 的 downstream cache 存在並已被攻擊。此例沒有提供下游快取重播的觀測。

## 稿件與結果標籤

可用措辭：

> 這個自然修補以略過本地 cache insertion 取得所測 alice/bob 序列的內容隔離，卻未產生上游指定的 Authorization Vary。這是嚴格產品契約與較寬安全行為判準可能分歧的例子；我們未在此觀測到 downstream 跨使用者重播。

若 frozen checker 將它判為失敗，原始 receipt 與既定分數保持原樣；論文可補充分開的 **header-contract mismatch** 與 **observed cross-identity disclosure** 分類，並明說該例屬前者。不能事後靜默改 oracle 來讓某方法獲利，也不能把 header-only failure 計為已證明 privacy leakage。

不支持的句子：

- 「max-age=300 且無 Vary，所以任何 shared cache 都會重播另一人的資料。」
- 「RFC 要求此回應必須有 Vary: Authorization、private 或 no-store。」
- 「M 已出現跨使用者洩漏」或「本地 bypass 已被證明完全正確」。

本次不新增實驗或 gate。最有決策價值的來源是**同一 fixed commit 的文件承認 Vary 非嚴格必要**，以及 RFC §3／§3.5 的 Authorization 預設限制；不需要依靠推測的攻擊來判斷稿件可說的範圍。

## 對目前 C3 task card 的 oracle 修正建議

主 agent 在本次核查中提供的 C3 card 原文為：

> Non-public responses to nonempty Authorization requests must remain isolated by Authorization. Explicit public responses may be shared.

此文字要求身份隔離與 public 例外，**沒有規定必須複製 upstream 的 Vary 實作**。因此對 body 正確、兩次到 origin、無 Vary 且僅 max-age 的候選，原 strict/header predicate 判 false 可能拒絕合法替代修補。上游確實新增 outgoing Vary 是可觀測產品行為，但在這份較寬的研究 card 下，不能只因缺此 header 就把候選當成安全違約；這是本次建議對上一節的進一步限定。

| 項目 | 原 frozen formal-v1 | 建議的 scoped amendment（主 agent 負責，本文未執行） |
|---|---|---|
| C3 裁決 | 保留原 strict/header 判分、原 prompt／自然 patch／receipts，完整可回溯。 | 以 actor body isolation 加上**同一 public U**重新評估，容許安全 bypass；Vary 的缺少另作產品行為差異描述。 |
| 初始候選與續修 | 原兩個 initial draws 及已執行分支不覆寫。 | 重用同兩個 original initial draws，在獨立 amendment lineage 分支續修；若 initial 已滿足則不生成額外 revision。 |
| 結果與成本 | 原被拒候選與已發生的 API 呼叫／token／成本不刪除。 | 分開報 amended verdict／後續結果與舊 strict verdict；原多花成本仍計入歷史資源說明，不能呈現成從未發生。 |
| 可作的解釋 | 原 classifier 的 false 不自動等於 observed privacy disclosure。 | 若 amended oracle 接受，報為原 oracle 過窄與合法替代修補，不稱模型在本例造成已證實洩漏。 |

以上是針對已辨識的 contract–oracle mismatch 做窄修正；不挑有利方法、不修改其他 roots／selection／模型設定，也不藉結果改寫 card。修正前後的 source／oracle SHA 與各分母應明示。即使所有既有 actor 序列通過，也只支持所測契約範圍，不保證所有可能 warm state 安全。
