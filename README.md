# PrivateCacheWitness 與 CivilTimeGuard 重現資源

本資源包含兩篇研究的固定案例、Gemma 4 31B 自然修補、對照結果與圖表。先讀 [Cache 稿件](papers/private-cache-witness.md)／[Time 稿件](papers/civil-time-guard.md)。兩篇各8個自然修補lineage、每個2次initial；同一initial分叉B/M，既定4個root/r01另有F完整測試庫對照。兩篇共用runner，不把這份基礎程式當兩次創新。

**重播現有patch不需要API或模型權重，也不會發送模型請求。** 原推論使用hosted免費Gemma API；不是離線模型速度或consumer GPU成本實測。沒有訓練模型。原實驗／分析均在GB10執行，未使用其GPU。

## 最短重現

實測環境為Linux aarch64、conda Python 3.12.15、Node 26.2.0、npm 11.13.0；相依版本見requirements.txt、environment.json及Node lock。使用conda環境，不使用系統Python。

```bash
conda create -n gemma_contract_replay python=3.12.15 pip -y
conda activate gemma_contract_replay
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
python tools/configure_public.py
npm ci --prefix artifacts/node-runtime
python tools/prepare_sources.py --artifact-root "$PWD/artifacts" --ids C1 T5 T7 T8
python tools/replay_cases.py --artifact-root "$PWD/artifacts" --ids C1 T5 T7 T8
python tools/replay_published.py --ids C1 T5 T7 T8
```

此入口先重播兩個主文案例及兩個JavaScript時間案例；完整自然案例則移除最後三行的`--ids ...`。來源按public GitHub的固定SHA下載，保留各自授權；不依賴研究者機器上的原始路徑。`configure_public.py`只設定本機artifact／conda interpreter路徑與可選GCP project reference，不改模型或實驗參數。Node esbuild從本地config讀取，也可用PAPER_ESBUILD指定同版本執行檔。

`replay_published.py`重套用主研究／模型篩選的initial、最終保留patch與所有資訊消融patch，重做同一Q0/U/V/E裁決，將結果與公布verdict比較。輸出在artifacts/results/published-replay/receipt.json。無法套用的提案仍計失敗，不以reference patch代換。這是固定patch行為重播；重新抽樣hosted模型不保證得到相同patch。

## 結果與研究邊界

- artifacts/results/formal-v1/analysis.json、report.json與root_outcomes.csv：根因／draw／paired branch分母、對照、用量；缺格不填零。
- artifacts/runs/formal-v1：供主表使用的完整資料。C3採source-backed語意修正，其他case沿用原formal-v1；PUBLIC_ARTIFACT_STATUS.json記錄source SHA及路徑adapter。
- historical/strict-C3：C3原過窄header判分及續修資料。修正沿用同initial，保留額外已花API成本；不能把原false verdict算成觀測到的privacy leak。原因見[來源查核](docs/C3_AUTHORIZATION_FACTCHECK.md)。
- artifacts/runs/transfer-initials-26b-v1：既定C1/C3、T1/T6四root的免費26B A4B單次初始提案檢查，與主31B分母分開。看到C1滿32K思考額度仍無patch後，選配B/M擴張縮為四root initial-only；原initial與任何已花續修保留於historical/secondary-full-attempts，不變更主研究。
- artifacts/runs/time-information-v1：事先規劃的政策卡／Q0資訊消融，各條件只生成一次，不續修；source/docstring／U仍保留。
- artifacts/receipts/T5_fractional_duration_exploration.json：同一T5修補的公用縮放操作探查，原凍結分數不變；可用tools/duration_scaling_audit.py重現。
- artifacts/results/time-contrast-v1：看過T5/r01後的30點探索性輸入，只有1個自然lineage、沒有新增模型生成，不當30個獨立bugs。
- artifacts/published-patches.json：可直接重播的自然patch清單；artifacts/response-provenance.json保留原response hashes。公開response僅保留function arguments或已抽出的diff、usage與model version，移除內部思考及簽章。

C1與T1曾用於transport／patch compiler技術smoke，該些回應不計formal新draw；此資源不是工程過程中完全未見的holdout。先前另有20次準備生成attempt（包含2次小型tool smoke），主表與論文用量另列正式、資訊消融與模型轉移。

各task的contract／可見Q0／功能U／V／獨立E位於configs/cases；E在研究完成後公開以便重現，當時未回傳模型。定位、policy cards與adapter由作者手工策展，人工工時未計時；T5的縮放consumer也不在原source片段中，該額外錯誤反映有限context／test設定。

本資源評估已知要求下的focused repair，不是全repo導航、使用者意圖發現或全部輸入的正確性保證。C2是origin integrity，與其餘7個cache privacy lineages分開。

## 重新生成表格與圖

```bash
python tools/analyze_campaign.py --artifact-root "$PWD/artifacts" --source-root "$PWD" --require-complete
python tools/report_campaign.py --artifact-root "$PWD/artifacts" --require-complete
```

圖另需Matplotlib／NumPy（原分析環境版本見requirements-figures.txt）；它們不影響patch裁決：

```bash
python -m pip install -r requirements-figures.txt
python tools/render_paper_figures.py --artifact-root "$PWD/artifacts" --source-root "$PWD" --output papers/assets
```

## 重新抽樣模型（選用）

在自己的device-local secret store設定GEMINI_API_KEY或GOOGLE_API_KEY，再另開run root。請先確認當時供應商免費模型／quota仍可用；程式禁止paid fallback，不會轉付費模型。不要覆寫公布的historical records。

```bash
python -m gemma_paper.runner --cases C1 T5 --replicate new-r01 --arms B M --run-root "$PWD/artifacts/runs/new-sampling-v1"
```

無API key的固定patch重播不受這一段影響。完整source refs在docs/plans/20261023_research_ready/case_index.json；自有程式Apache-2.0，第三方上下文與diff片段依各上游授權，詳見THIRD_PARTY_NOTICES.md與third-party-licenses/。此包不含Kaggle competition data、私有聊天、帳號credential或模型權重。

## Kaggle 貼入版本

[PrivateCacheWitness](kaggle/private-cache-witness.md)／[CivilTimeGuard](kaggle/civil-time-guard.md)已將圖連結固定到公開asset commit，字數各2240／2411。submission-metadata.json記錄READY_NOT_SUBMITTED；本repo發布不等於Kaggle已按Submit。
