# Time：政策與重現例的資訊消融

狀態：預先定義的額外實驗；不修改formal-v1既有資料／runner／結果。本計畫在Time正式結果尚未取得時保存，動機是分辨已知政策與具體reproducer各提供多少修補資訊，而非保護selector一定有效。

固定四root：T1/T4/T5/T6，與既定F子集相同；各r01/r02。主實驗both（來源政策＋Q0＋功能U）的initial直接沿用，不重新生成。新增兩條件：policy-only移除Q0；reproducer-only移除來源政策文字、保留Q0與同一U。source定位、程式片段、模型／temperature／thinking／output budget與tool均相同。

每個新增條件只生成一個initial，不給任何測試回饋、不續修；以同一固定Q0/U/V/E評估。新增最多16個生成請求，不增自然root N；r01先涵蓋全部四root，再r02。兩種新增條件順序按root交替。所有失敗／無差結果保留。

這是不同需求資訊的作用，不是equal-information排序比較；不能將其結果歸因M／J或宣稱自動發現未知使用者意圖。完整政策仍由作者策展，old-side定位已供給，這些條件在稿件中明示。

Cash authority仍FREE_ONLY，paid fallback=false。若主實驗已回答問題且額外條件無可辨識價值，依已得證據停止擴張；不刪除已產生的不利條件。

「移除政策」只移除額外策展的政策卡，原buggy source中的docstrings與共同功能U仍保留；不能說模型完全沒有政策線索。所有新增條件只作單次initial評估，不給測試回饋。
