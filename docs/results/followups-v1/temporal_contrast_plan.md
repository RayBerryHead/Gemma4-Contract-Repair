# T5：語意對偶的探索性重播

起因：正式T5/r01的自然initial已將days=1修好，卻把hours=24也當日曆天，造成23或25小時。這是看到結果後提出的機制探查，與事前固定的主矩陣／資訊消融分開。

只在同一T5歷史lineage，使用America/New_York、Europe/Paris、Australia/Sydney的2021年春秋兩個DST轉換。每個轉換使用前一天10:45加1天／24小時，或轉換當天10:45減1天／24小時；另加各zone的1月15日正常日控制，共30個輸入。對應expected以Python標準庫zoneinfo分別計算wall/calendar與UTC elapsed；每個觀測先要求原upstream fixed通過，保留buggy與自然patch結果。

重播upstream buggy/fixed與所有已取得的T5 initial、B/M/F保留patch；不增加模型生成、不挑掉負例、不更改正式oracle、不增加自然root N。新增點只能說明該lineage的機制跨日期／地區重現，不作30個獨立bugs或跨repo通用性證據。GB10單process執行，沒有M4／GPU負載與付費資源。
