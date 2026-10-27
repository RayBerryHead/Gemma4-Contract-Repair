# T5：通過局部契約的修補仍破壞duration縮放

這是看過T5/r01兩個保留patch後的探索性機制查核，不是事前指定的E，不改主表分數，也不將單一root增加成更多自然bugs。

自然initial用normalized `delta._days`當日曆天，使days修好卻把hours=24誤當1天。B修訂新增`_days_passed`保存原days/weeks；M修訂改寫既有`_days=int(days + weeks * 7)`。兩者都通過frozen Q0/U/V/E；另30個跨三zone的day/hour對偶也不會檢查duration自己的其他公用運算。

來源閱讀發現float multiplication與division仍經`_to_microseconds()`使用normalized `_days`。新增最小觀測：`pendulum.duration(hours=24) * 0.5`及`/ 2`，應為43200秒。實測buggy upstream、fixed upstream、B保留patch均為43200秒；M保留patch兩者皆為0秒，雖然原duration的total_seconds仍是86400。

這支持『改變共用內部欄位的意義以修好一條操作，可能破壞另一條公用操作』，不支持M selector造成退步；B/M從相同initial起跑但後續是不同隨機proposal。M的主矩陣pass保留，新增公用運算錯誤獨立列示。之後取得的T5 r02與F也一律用同一probe，不能只挑第一個不利M patch。

可重現工具：tools/duration_scaling_audit.py；raw receipt：artifact root/receipts/T5_fractional_duration_exploration.json。GB10 conda單process、0新增模型生成，不跑無關全套測試。

## Source visibility限定

實際T5/r01 packet中Duration片段3035 chars，沒有_to_microseconds／__mul__／__truediv__。因此這是局部source與有限bundle設定的缺口，不是已測完整repo agent看過這些caller仍忽略。原packet hash與presence核對見T5_context_visibility.json。沒有因這個發現追加模型條件或改主分數。
