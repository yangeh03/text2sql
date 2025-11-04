SELECT MAX("Free Meal Count (K-12)") FROM frpm WHERE "County Name" = 'Alameda County' AND "School Type" = 'K-12'
SELECT DISTINCT PERCENT_%_Eligible_Free__Ages_5_17 FROM frpm WHERE School Type = 'Continuation' AND CDSCode IN ('01100170109835', '01100170112607', '01100170118489', '01100170123968', '01100170124172') ORDER BY PERCENT_%_Eligible_Free__Ages_5_17 ASC LIMIT 3
SELECT Zip FROM schools WHERE County = 'Fresno' AND District = 'Fresno County Office of Education' AND Charter = 1
