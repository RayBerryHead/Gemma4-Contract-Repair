# C1 warm-store witness：上游來源與主張範圍

查核／accessed：2026-10-27。從當次最新 fetched `origin/main` `fce1e78bf6f229cdcb371337f750b305b383e22d` 建立獨立文件分支。僅 Web／GB10 文字閱讀，未執行新 API 實驗、模型或修改 bank／runner／正式資料。

**結論：same-store private→shared 的 warm 前置不是作者自行猜測；C1 fixed commit 的新增上游 regression test 明確採用相同配置。** 最準確說法是「公開 API 可表達、且上游測試明採的既存 entry fixture」，而不是「所有一般部署都如此」或「跨 type 共用 store 是建議的部署方式」。

## 1. 固定版本與最直接的證據

已讀 project `docs/plans/20261023_research_ready/case_index.json` 的 C1：buggy `6d583124e7cf60b640097d64144ed633cc450584`，fixed `cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a`。本輪讀 [fixed diff](https://github.com/nodejs/undici/commit/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a)、下列固定版相關 code／tests／docs，不以目前 main 取代。

| 第一手來源 | Observed 內容與可支持範圍 |
|---|---|
| [test/interceptors/cache.js L102–162](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/test/interceptors/cache.js#L102) | 新測試 `shared cache does not serve existing entries with Set-Cookie` 建立**同一 store**，privateClient／sharedClient 各設 type。private client 以user-a寫入，再以user-a命中而origin仍1；shared client以user-b讀取，預期origin2、user-b cookie及body。這與所問warm前置直接對應，不只是缺乏禁止文字。 |
| [lib/interceptor/cache.js L423–431](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/lib/interceptor/cache.js#L423) | read guard 的明文動機是 shared store 可能比寫入它的 Undici版本存活更久。shared reader若看到entry帶Set-Cookie，就清掉entry並走uncached origin路徑；不是只剪掉header仍供應舊body。 |
| [同檔 L550–579](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/lib/interceptor/cache.js#L550)、[types/cache-interceptor.d.ts](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/types/cache-interceptor.d.ts) | store與type是獨立options，type預設shared，可選private；傳入store經interface驗證。所讀type declarations沒有每種type必須專屬store的約束。這不等於所有組合都獲production安全保證；具體可觀測要求來自上面的test。 |
| [CacheStore.md](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/docs/docs/api/CacheStore.md)、[Interceptors.md cache段](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/docs/docs/api/Interceptors.md#L324) | 已完整讀CacheStore文件與cache段。文件將store定義為可傳入的storage backend，說明get/write/delete及Vary選取；未見禁止同store跨private/shared client，也未見每type獨立store的明文假設。未聲稱搜完所有外部文件。 |
| [MemoryCacheStore實作 L93–131](https://github.com/nodejs/undici/blob/cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a/lib/cache/memory-cache-store.js#L93) | 所讀get/write使用origin/path及entry matching；沒有type參數作儲存分區。這解釋fixture為何可表達，沒有因此證明任意跨identity store共用都合理。 |

`CacheStorage.md` 是另一個 Service Worker CacheStorage／Cache介面，**不是**本題 MemoryCacheStore interceptor 的authority；不拿它的同名cache共用行為作證。

## 2. 上游既存 entry 的來源，哪些有明文、哪些沒有

- **有明文實作動機：**read guard的註解指向跨Undici版本存活的shared-store entry。可說它防護先前已寫入、仍可被讀到的entry；不能自行補出特定migration流程／發生率。
- **有明確測試建構：**上游以private client透過公開API合法填入store，作為existing-entry情境；private重用仍須正常。這是fixture的來源，不是證明所有production既存entry都由private client寫入。
- **本研究的memory fixture不是已實測版本升級：**同process的MemoryCacheStore可重用，足以重播既存entry的read path；不能寫成已測持久化、跨process重啟或版本升級。
- **沒有在所讀文件找到：**禁止上述same-store fixture、每type獨立store的必須條件、此配置在真實部署的普及程度。不得把「沒看到」擴大為作者對所有deployments的保證。

## 3. 官方 advisory 的支持與限制

[GHSA-2jfj-6hjv-fm6j](https://github.com/nodejs/undici/security/advisories/GHSA-2jfj-6hjv-fm6j)（本輪讀Description／Patches／Workarounds）說明shared模式預設、修補涵蓋previously cached entries與revalidation，private模式保留；workaround也允許shared cache在**before caching**移除Set-Cookie。

因此不能宣稱任何「移除Set-Cookie」修法本身都非法，也不能把此產品防護擴成RFC普遍禁止所有Set-Cookie response caching的規則。固定C1測試的具體要求更可查：在該warm fixture中，shared Bob必須重新到origin拿Bob body，而非只刪cached cookie後回Alice body。

## 4. 稿件可以精確說什麼

由主agent提供的本研究觀測（本核查未獨立重跑）：自然候選只移除cached Set-Cookie，Bob仍取得Alice body；reference因shared-read guard重新取回Bob。與上述上游fixture合併後，可用：

> 在一個上游回歸測試同樣採用的warm-state配置中，Alice的private client先將帶Set-Cookie的回應寫入MemoryCacheStore，Bob的shared client隨後讀取同一store。自然修補雖移除了cached cookie，仍重播Alice的body；reference修補拒絕該既存entry並重新向origin取得Bob的回應。這揭露了此配置下header移除與整筆entry拒絕之間的行為差異。

此句須由正式patch／trace receipt補證實測部分。若稱body disclosure，限於所測actor-tagged body，不推論實際使用者憑證遭竊。最短trace可省去upstream用於確認private hit的重複Alice讀，但稿件／artifact應保留「entry確已合法填入且可被重用」的現有證據。

不支持：普通empty/cold cache必定同樣失敗、所有合法部署都會洩漏、private/shared共享store為建議架構、部署頻率或新CVE／未知upstream漏洞。這是對既知修補lineage的候選patch行為研究；不新增實驗或gate。

## 5. PatchEval-Verified 230-CVE exact-instance overlap

查核日2026-10-27；本節是上述C1來源核查的相依補充，不改研究方法或結果。完整取得並串流解析官方 [patcheval_verified.json](https://raw.githubusercontent.com/bytedance/PatchEval/b43285cdde80cc04608d5f1178a330b740c91c2d/patcheval/datasets/patcheval_verified.json)，僅1,741,624 bytes metadata，沒有拉取Docker image／repo source／大型logs。查核時官方main仍為 `b43285cdde80cc04608d5f1178a330b740c91c2d`；[GitHub contents metadata](https://api.github.com/repos/bytedance/PatchEval/contents/patcheval/datasets/patcheval_verified.json)的Git blob SHA為 `dc201f860cb8ae4b09508e3ba8d64f2a78d0c601`。

JSON完整parse為230筆、230個不同`cve_id`、0筆缺少ID；比對的是所有ID與`patch_url`，不是網路搜尋miss。

| 本研究instance | 第一手識別關係 | 這份完整230筆清單的結果 |
|---|---|---|
| C1 | [GitHub官方advisory API](https://api.github.com/advisories/GHSA-2jfj-6hjv-fm6j)將 `CVE-2026-84933`／`GHSA-2jfj-6hjv-fm6j` 與fixed `cb75bbb34224a968b4ad80cab8b7aba5e0b3b28a`連結；另有backport `b6c5a00252c37da9dd2db9bead053bb843e1f988`。 | CVE ID無match；本研究原fix SHA在全部`patch_url`無match。**可確認C1未列於此固定版Verified 230-CVE metadata。** |
| C7（順手核對） | [官方advisory API](https://api.github.com/advisories/GHSA-4cwx-7wf7-3272)將 `CVE-2026-13697`／`GHSA-4cwx-7wf7-3272` 與fixed `4fe5bc5fefe5ac81a200fc8e1cf84b8bf8464451`連結。 | CVE ID與原fix SHA皆無match，限於同一完整230筆清單。 |
| C2（僅部分核對） | 已讀原fix `26c2bfb3def0b67241ce878e80657ed5d6c3efa8` 的commit主旨cross-origin redirect cache confusion。**本節沒有核實其CVE／所有alias**。 | 原fix SHA在所有`patch_url`無match；不以此單項推論完整bug-identity／alias已排除。不要誤將whitespace-bypass `CVE-2026-9678`當作此redirect根因。 |

這份metadata中，`repo`為 `https://github.com/nodejs/undici` 的完整子集僅兩筆：

- `CVE-2022-35949`：`patch_url`為 [124f7ebf705366b2e1844dff721928d270f87895](https://github.com/nodejs/undici/commit/124f7ebf705366b2e1844dff721928d270f87895)；metadata描述是path/pathname URL處理造成SSRF，非C1 Set-Cookie cache instance。
- `CVE-2024-30260`：`patch_url`為 [64e3402da4e032e68de46acb52800c9a06aaea3f](https://github.com/nodejs/undici/commit/64e3402da4e032e68de46acb52800c9a06aaea3f) 與 [6805746680d27a5369d7fb67bc05f95a28247d75](https://github.com/nodejs/undici/commit/6805746680d27a5369d7fb67bc05f95a28247d75)；metadata描述是request與fetch對Authorization／Proxy-Authorization清除不一致，非C1 instance。

**測量邊界：**只確認目前官方repo中可讀的Verified 230-CVE清單。沒有取得／逐一比對原論文1,000-CVE靜態資料集、所有舊版230清單或容器內部tests，故對那些範圍仍unknown。metadata不列本案，不代表其方法無法處理、沒有相似安全契約，或我們有方法優勢。C1 warm fixture本來就在Undici上游測試中，仍不能宣稱由我們發明或是新CVE。
