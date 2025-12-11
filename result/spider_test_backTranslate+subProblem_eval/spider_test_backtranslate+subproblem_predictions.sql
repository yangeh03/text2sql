SELECT COUNT(*) FROM club;
SELECT COUNT(*) FROM club;
SELECT Name FROM club ORDER BY Name ASC;
SELECT Name FROM club ORDER BY Name;
SELECT Manager, Captain FROM club WHERE Name IN ('Arsenal', 'Aston Villa', 'Blackburn Rovers', 'Bolton Wanderers', 'Chelsea')
SELECT Manager, Captain FROM club;
SELECT Name FROM club WHERE Manufacturer != 'Nike'
SELECT Name FROM club WHERE Manufacturer != 'Nike'
SELECT Name FROM player ORDER BY Wins_count ASC;
SELECT Name FROM player ORDER BY Wins_count ASC;
SELECT Name FROM player ORDER BY Earnings DESC LIMIT 1;
SELECT Name FROM player ORDER BY Earnings DESC LIMIT 1
SELECT DISTINCT Country FROM player WHERE Earnings > 1200000;
SELECT Country FROM player WHERE Earnings > 1200000;
SELECT Country FROM player WHERE Wins_count > 2 ORDER BY Earnings DESC LIMIT 1;
SELECT Country FROM player WHERE Wins_count > 2 ORDER BY Earnings DESC LIMIT 1;
SELECT player.Name, club.Name FROM player JOIN club ON player.Club_ID = club.Club_ID WHERE club.Name IN ('Arsenal', 'Aston Villa', 'Blackburn Rovers', 'Bolton Wanderers', 'Chelsea') OR player.Name IN ('Nick Price', 'Paul Azinger', 'Greg Norman', 'Jim Gallagher', 'Jr.', 'David Frost');
SELECT player.Name, club.Name FROM player JOIN club ON player.Club_ID = club.Club_ID WHERE club.Name IN ('Arsenal', 'Aston Villa', 'Blackburn Rovers', 'Bolton Wanderers', 'Chelsea') OR player.Name IN ('Nick Price', 'Paul Azinger', 'Greg Norman');
SELECT DISTINCT club.Name FROM club JOIN player ON club.Club_ID = player.Club_ID WHERE player.Wins_count > 2;
SELECT DISTINCT club.Name FROM club JOIN player ON club.Club_ID = player.Club_ID WHERE player.Wins_count > 2;
SELECT player.Name FROM player INNER JOIN club ON player.Club_ID = club.Club_ID WHERE club.Manager = 'Sam Allardyce';
SELECT player.Name FROM player JOIN club ON player.Club_ID = club.Club_ID WHERE club.Manager = 'Sam Allardyce';
SELECT T1.Name FROM club AS T1 JOIN player AS T2 ON T1.Club_ID = T2.Club_ID GROUP BY T1.Club_ID ORDER BY avg(T2.Earnings) DESC;
SELECT T1.Name FROM club AS T1 JOIN player AS T2 ON T1.Club_ID = T2.Club_ID GROUP BY T1.Club_ID ORDER BY avg(T2.Earnings) DESC;
SELECT Manufacturer, COUNT(Club_ID) AS clubs FROM club GROUP BY Manufacturer;
SELECT Manufacturer, COUNT(*) FROM club GROUP BY Manufacturer;
SELECT Manufacturer, COUNT(*) AS count FROM club GROUP BY Manufacturer ORDER BY count DESC LIMIT 1;
SELECT Manufacturer FROM club GROUP BY Manufacturer ORDER BY COUNT(*) DESC LIMIT 1;
SELECT Manufacturer FROM club GROUP BY Manufacturer HAVING COUNT(*) > 1;
SELECT Manufacturer FROM club GROUP BY Manufacturer HAVING COUNT(DISTINCT Club_ID) > 1;
SELECT Country FROM player GROUP BY Country HAVING COUNT(Player_ID) > 1;
SELECT Country FROM player GROUP BY Country HAVING COUNT(*) > 1;
SELECT Name FROM club WHERE Club_ID NOT IN (SELECT DISTINCT Club_ID FROM player);
SELECT Name FROM club WHERE Club_ID NOT IN (SELECT DISTINCT Club_ID FROM player);
SELECT Country FROM player WHERE Earnings > 1400000 INTERSECT SELECT Country FROM player WHERE Earnings < 1100000;
SELECT Country FROM player WHERE Earnings > 1400000 INTERSECT SELECT Country FROM player WHERE Earnings < 1100000;
SELECT COUNT(DISTINCT Country) FROM player;
SELECT COUNT(DISTINCT Country) FROM player;
SELECT Earnings FROM player WHERE Country = "Australia" OR Country = "Zimbabwe"
SELECT Earnings FROM player WHERE Country = "Australia" OR Country = "Zimbabwe"
SELECT T1.customer_id, T1.customer_first_name, T1.customer_last_name FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id GROUP BY T1.customer_id HAVING count(*) >= 2;
SELECT Customers.customer_id, Customers.customer_first_name, Customers.customer_last_name FROM Customers JOIN Orders ON Customers.customer_id = Orders.customer_id JOIN Order_Items ON Orders.order_id = Order_Items.order_id GROUP BY Customers.customer_id HAVING COUNT(Orders.order_id) > 2 AND SUM(CASE WHEN Order_Items.order_item_status_code = 'Delivered' THEN 1 ELSE 0 END) >= 3;
SELECT T1.order_id, T1.order_status_code, count(*) FROM Orders AS T1 JOIN Order_items AS T2 ON T1.order_id = T2.order_id GROUP BY T1.order_id;
SELECT T1.order_id, T1.order_status_code, count(*) FROM Orders AS T1 JOIN Order_items AS T2 ON T1.order_id = T2.order_id GROUP BY T1.order_id;
SELECT DISTINCT date_order_placed FROM Orders WHERE date_order_placed = (SELECT MIN(date_order_placed) FROM Orders) OR order_id IN (SELECT order_id FROM Order_Items GROUP BY order_id HAVING COUNT(*) > 1);
SELECT MIN(date_order_placed) AS earliest_order_date FROM Orders WHERE order_status_code IN ('Cancelled', 'Part Completed', 'Delivered', 'Out of Stock') GROUP BY order_id HAVING COUNT(*) > 1 UNION SELECT date_order_placed FROM Orders WHERE order_id IN (SELECT order_id FROM Order_Items GROUP BY order_id HAVING COUNT(*) > 1) AND order_status_code IN ('Cancelled', 'Part Completed', 'Delivered', 'Out of Stock') ORDER BY date_order_placed;
SELECT customer_first_name, customer_middle_initial, customer_last_name FROM Customers EXCEPT SELECT T1.customer_first_name, T1.customer_middle_initial, T1.customer_last_name FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id;
SELECT customer_first_name, customer_middle_initial, customer_last_name FROM Customers EXCEPT SELECT T1.customer_first_name, T1.customer_middle_initial, T1.customer_last_name FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id;
SELECT product_id, product_name, product_price, product_color FROM Products WHERE product_id NOT IN (SELECT product_id FROM Order_Items WHERE order_item_status_code = 'Cancelled' OR order_item_status_code = 'Part Completed' OR order_item_status_code = 'Delivered' GROUP BY product_id HAVING COUNT(*) >= 2) ORDER BY product_id;
SELECT product_id, product_name, product_price, product_color FROM Products WHERE product_id NOT IN (SELECT DISTINCT product_id FROM Order_Items WHERE order_id IN (SELECT order_id FROM Orders WHERE order_status_code = 'Cancelled' OR order_status_code = 'Part Completed' OR order_status_code = 'Delivered')) AND product_id IN (SELECT product_id FROM Order_Items);
SELECT T1.order_id, T1.date_order_placed FROM Orders AS T1 JOIN Order_items AS T2 ON T1.order_id = T2.order_id GROUP BY T1.order_id HAVING count(*) >= 2;
SELECT T1.order_id, T1.date_order_placed FROM Orders AS T1 JOIN Order_items AS T2 ON T1.order_id = T2.order_id GROUP BY T1.order_id HAVING count(*) >= 2;
SELECT T2.product_id, T2.product_name, T2.product_price FROM Order_items AS T1 JOIN Products AS T2 ON T1.product_id = T2.product_id GROUP BY T2.product_id ORDER BY count(*) DESC LIMIT 1;
SELECT T2.product_id, T2.product_name, T2.product_price FROM Order_items AS T1 JOIN Products AS T2 ON T1.product_id = T2.product_id GROUP BY T2.product_id ORDER BY count(*) DESC LIMIT 1;
SELECT T1.order_id, sum(T2.product_price) FROM Order_items AS T1 JOIN Products AS T2 ON T1.product_id = T2.product_id GROUP BY T1.order_id ORDER BY sum(T2.product_price) ASC LIMIT 1;
SELECT T1.order_id, sum(T2.product_price) FROM Order_items AS T1 JOIN Products AS T2 ON T1.product_id = T2.product_id GROUP BY T1.order_id ORDER BY sum(T2.product_price) ASC LIMIT 1;
SELECT payment_method_code FROM Customer_Payment_Methods GROUP BY payment_method_code ORDER BY COUNT(*) DESC LIMIT 1;
SELECT payment_method_code FROM Customer_Payment_Methods GROUP BY payment_method_code ORDER BY COUNT(*) DESC LIMIT 1;
SELECT T1.gender_code, count(*) FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id JOIN Order_items AS T3 ON T2.order_id = T3.order_id GROUP BY T1.gender_code;
SELECT T1.gender_code, count(*) FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id JOIN Order_items AS T3 ON T2.order_id = T3.order_id GROUP BY T1.gender_code;
SELECT T1.gender_code, count(*) FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id GROUP BY T1.gender_code;
SELECT T1.gender_code, count(*) FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id GROUP BY T1.gender_code;
SELECT Customers.customer_first_name, Customers.customer_middle_initial, Customers.customer_last_name, Customer_Payment_Methods.payment_method_code FROM Customers JOIN Customer_Payment_Methods ON Customers.customer_id = Customer_Payment_Methods.customer_id;
SELECT Customers.customer_first_name, Customers.customer_middle_initial, Customers.customer_last_name, Customer_Payment_Methods.payment_method_code FROM Customers LEFT JOIN Customer_Payment_Methods ON Customers.customer_id = Customer_Payment_Methods.customer_id;
SELECT T1.invoice_status_code, T1.invoice_date, T2.shipment_date FROM Invoices AS T1 JOIN Shipments AS T2 ON T1.invoice_number = T2.invoice_number;
SELECT T1.invoice_status_code, T1.invoice_date, T2.shipment_date FROM Invoices AS T1 JOIN Shipments AS T2 ON T1.invoice_number = T2.invoice_number;
SELECT Products.product_name, Shipments.shipment_date FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id JOIN Shipments ON Order_Items.order_id = Shipments.order_id;
SELECT DISTINCT Products.product_name, Shipments.shipment_date FROM Products JOIN Shipments ON Products.product_id = Shipments.order_id WHERE Products.product_name IN ('Dell monitor', 'Dell keyboard', 'iPhone6s', 'iWatch', 'Lenovo keyboard');
SELECT Order_Items.order_item_status_code, Shipments.shipment_tracking_number FROM Order_Items JOIN Shipments ON Order_Items.order_id = Shipments.order_id WHERE Order_Items.order_item_status_code IN ('Delivered', 'Out of Stock') AND Shipments.shipment_tracking_number IN ('6900', '3499', '5617', '6074', '3848');
SELECT Orders.order_status_code, Shipments.shipment_tracking_number FROM Orders JOIN Order_Items ON Orders.order_id = Order_Items.order_id JOIN Shipments ON Orders.order_id = Shipments.order_id WHERE Orders.order_status_code IN ('Cancelled', 'Part Completed', 'Delivered', 'Out of Stock') AND Order_Items.order_item_status_code IN ('Cancelled', 'Part Completed', 'Delivered', 'Out of Stock');
SELECT Products.product_name, Products.product_color FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id JOIN Orders ON Order_Items.order_id = Orders.order_id JOIN Shipments ON Orders.order_id = Shipments.order_id WHERE Products.product_name IN ('Dell monitor', 'Dell keyboard', 'iPhone6s', 'iWatch', 'Lenovo keyboard') AND Orders.order_status_code = 'Cancelled' AND Shipments.shipment_date IS NOT NULL;
SELECT Products.product_name, Products.product_color FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id JOIN Orders ON Order_Items.order_id = Orders.order_id WHERE Orders.order_status_code = 'shipped' AND Order_Items.order_item_status_code = 'shipped'
SELECT DISTINCT T1.product_name, T1.product_price, T1.product_description FROM Products AS T1 JOIN Order_items AS T2 ON T1.product_id = T2.product_id JOIN Orders AS T3 ON T2.order_id = T3.order_id JOIN Customers AS T4 ON T3.customer_id = T4.customer_id WHERE T4.gender_code = 'Female';
SELECT DISTINCT T1.product_name, T1.product_price, T1.product_description FROM Products AS T1 JOIN Order_items AS T2 ON T1.product_id = T2.product_id JOIN Orders AS T3 ON T2.order_id = T3.order_id JOIN Customers AS T4 ON T3.customer_id = T4.customer_id WHERE T4.gender_code = 'Female';
SELECT invoice_status_code FROM Invoices WHERE invoice_number IN (SELECT invoice_number FROM Shipments WHERE order_id NOT IN (SELECT order_id FROM Orders WHERE order_status_code = 'Shipped'))
SELECT invoice_status_code FROM Invoices WHERE invoice_number IN (SELECT invoice_number FROM Shipments WHERE order_id NOT IN (SELECT order_id FROM Orders WHERE order_status_code = 'Shipped'))
SELECT T1.order_id, T1.date_order_placed, sum(T3.product_price) FROM Orders AS T1 JOIN Order_items AS T2 ON T1.order_id = T2.order_id JOIN Products AS T3 ON T2.product_id = T3.product_id GROUP BY T1.order_id;
SELECT Orders.order_id, Orders.date_order_placed, Invoices.invoice_number, Invoices.invoice_date, Invoices.invoice_status_code FROM Orders JOIN Invoices ON Orders.order_id = Invoices.invoice_number;
SELECT count(DISTINCT customer_id) FROM Orders;
SELECT count(DISTINCT customer_id) FROM Orders;
SELECT COUNT(DISTINCT order_item_status_code) FROM Order_items;
SELECT COUNT(DISTINCT order_item_status_code) FROM Order_items;
SELECT COUNT(DISTINCT payment_method_code) FROM Customer_Payment_Methods;
SELECT COUNT(DISTINCT payment_method_code) FROM Customer_Payment_Methods;
SELECT login_name, login_password FROM Customers WHERE phone_number LIKE '+12%';
SELECT login_name, login_password FROM Customers WHERE phone_number LIKE '+12%'
SELECT product_size FROM Products WHERE product_name LIKE '%Dell%';
SELECT product_size FROM Products WHERE product_name LIKE '%Dell%';
SELECT product_price, product_size FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products)
SELECT product_price, product_size FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products)
SELECT count(*) FROM Products WHERE product_id NOT IN (SELECT product_id FROM Order_items);
SELECT COUNT(*) FROM Products WHERE product_id NOT IN (SELECT product_id FROM Order_Items)
SELECT COUNT(*) FROM Customers WHERE customer_id NOT IN (SELECT customer_id FROM Customer_Payment_Methods);
SELECT count(*) FROM Customers WHERE customer_id NOT IN (SELECT customer_id FROM Customer_Payment_Methods);
SELECT order_status_code, date_order_placed FROM Orders;
SELECT order_status_code, date_order_placed FROM Orders;
SELECT address_line_1, town_city, county FROM Customers WHERE country = 'USA';
SELECT address_line_1, town_city, county FROM Customers WHERE country = 'United States';
SELECT T1.customer_first_name, T4.product_name FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id JOIN Order_items AS T3 ON T2.order_id = T3.order_id JOIN Products AS T4 ON T3.product_id = T4.product_id;
SELECT T1.customer_first_name, T4.product_name FROM Customers AS T1 JOIN Orders AS T2 ON T1.customer_id = T2.customer_id JOIN Order_items AS T3 ON T2.order_id = T3.order_id JOIN Products AS T4 ON T3.product_id = T4.product_id;
SELECT COUNT(DISTINCT order_item_id) FROM Shipment_Items;
SELECT COUNT(DISTINCT order_id) FROM Shipments;
SELECT AVG(product_price) FROM Products;
SELECT AVG(product_price) FROM Products;
SELECT AVG(product_price) FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id WHERE product_name IN ('Dell monitor', 'Dell keyboard', 'iPhone6s', 'iWatch', 'Lenovo keyboard');
SELECT AVG(product_price) FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id WHERE product_name IN ('Dell monitor', 'Dell keyboard', 'iPhone6s', 'iWatch', 'Lenovo keyboard') AND order_item_status_code = 'Delivered';
SELECT email_address, town_city, county FROM Customers WHERE gender_code = (SELECT gender_code FROM Customers GROUP BY gender_code ORDER BY COUNT(*) ASC LIMIT 1)
SELECT email_address, town_city, county FROM Customers WHERE gender_code IN (SELECT gender_code FROM Customers GROUP BY gender_code HAVING COUNT(*) < (SELECT COUNT(*) FROM Orders WHERE Orders.customer_id = Customers.customer_id));
SELECT date_order_placed FROM Orders WHERE customer_id IN (SELECT customer_id FROM Customer_Payment_Methods GROUP BY customer_id HAVING COUNT(DISTINCT payment_method_code) >= 2)
SELECT DISTINCT date_order_placed FROM Orders WHERE customer_id IN (SELECT customer_id FROM Customer_Payment_Methods GROUP BY customer_id HAVING COUNT(DISTINCT payment_method_code) >= 2);
SELECT order_status_code FROM Orders GROUP BY order_status_code ORDER BY COUNT(*) ASC LIMIT 1;
SELECT order_status_code FROM Orders GROUP BY order_status_code ORDER BY COUNT(*) ASC LIMIT 1;
SELECT Products.product_id, Products.product_description FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id GROUP BY Products.product_id HAVING COUNT(*) > 3;
SELECT Products.product_id, Products.product_description FROM Products JOIN Order_Items ON Products.product_id = Order_Items.product_id GROUP BY Products.product_id HAVING COUNT(*) > 3;
SELECT T1.invoice_date, T1.invoice_number FROM Invoices AS T1 JOIN Shipments AS T2 ON T1.invoice_number = T2.invoice_number GROUP BY T1.invoice_number HAVING count(*) >= 2;
SELECT invoice_number, invoice_date FROM Invoices WHERE invoice_number IN (SELECT invoice_number FROM Shipments GROUP BY invoice_number HAVING COUNT(*) >= 2) ORDER BY invoice_date;
SELECT shipment_tracking_number, shipment_date FROM Shipments;
SELECT shipment_tracking_number, shipment_date FROM Shipments;
SELECT product_color, product_description, product_size FROM Products WHERE product_price < (SELECT MAX(product_price) FROM Products);
SELECT product_color, product_description, product_size FROM Products WHERE product_price < (SELECT MAX(product_price) FROM Products)
SELECT Name FROM director WHERE Age > (SELECT AVG(Age) FROM director)
SELECT name FROM director ORDER BY age DESC LIMIT 1;
SELECT COUNT(*) FROM channel WHERE Internet LIKE '%bbc%'
SELECT COUNT(DISTINCT Digital_terrestrial_channel) FROM channel;
SELECT Title FROM program ORDER BY Start_Year DESC;
SELECT T2.name FROM program AS T1 JOIN director AS T2 ON T1.director_id = T2.director_id GROUP BY T1.director_id ORDER BY count(*) DESC LIMIT 1;
SELECT T2.name, T2.age FROM program AS T1 JOIN director AS T2 ON T1.director_id = T2.director_id GROUP BY T1.director_id ORDER BY count(*) DESC LIMIT 1;
SELECT Title FROM program ORDER BY Start_Year DESC LIMIT 1;
SELECT Name, Internet FROM channel WHERE Channel_ID IN (SELECT Channel_ID FROM program GROUP BY Channel_ID HAVING COUNT(Program_ID) > 1)
SELECT T1.name, count(*) FROM channel AS T1 JOIN program AS T2 ON T1.channel_id = T2.channel_id GROUP BY T1.channel_id;
SELECT COUNT(*) FROM channel WHERE Channel_ID NOT IN (SELECT DISTINCT Channel_ID FROM program);
SELECT T2.name FROM program AS T1 JOIN director AS T2 ON T1.director_id = T2.director_id WHERE T1.title = 'Dracula';
SELECT c.Name, c.Internet FROM channel c JOIN director_admin da ON c.Channel_ID = da.Channel_ID GROUP BY c.Channel_ID ORDER BY COUNT(DISTINCT da.Director_ID) DESC LIMIT 1;
SELECT Name FROM director WHERE Age BETWEEN 30 AND 60;
SELECT 1;  -- ERROR: Request timed out.
SELECT Channel_ID, Name FROM channel WHERE Channel_ID NOT IN (SELECT Channel_ID FROM director_admin WHERE Director_ID = (SELECT Director_ID FROM director WHERE Name = 'Hank Baskett'));
SELECT COUNT(*) FROM radio
SELECT Transmitter FROM radio ORDER BY ERP_kW ASC;
SELECT tv_show_name, Original_Airdate FROM tv_show;
SELECT Station_name FROM city_channel WHERE Affiliation != 'ABC' AND City IN ('Phoenix', 'Bakersfield', 'San Diego', 'Colorado Springs', 'Denver') AND ID IN (SELECT City_channel_ID FROM city_channel_radio UNION SELECT City_channel_ID FROM city_channel_tv_show);
SELECT Transmitter FROM radio WHERE ERP_kW > '150' OR ERP_kW < '30';
SELECT Transmitter FROM radio ORDER BY CAST(ERP_kW AS NUMBER) DESC LIMIT 1;
SELECT AVG(ERP_kW) FROM radio;
SELECT Affiliation, COUNT(ID) FROM city_channel GROUP BY Affiliation;
SELECT Affiliation FROM city_channel GROUP BY Affiliation ORDER BY COUNT(*) DESC LIMIT 1;
SELECT Affiliation FROM city_channel GROUP BY Affiliation HAVING COUNT(*) > 3;
SELECT City, Station_name FROM city_channel ORDER BY Station_name ASC;
SELECT city_channel.City, radio.Transmitter FROM city_channel JOIN city_channel_radio ON city_channel.ID = city_channel_radio.City_channel_ID JOIN radio ON city_channel_radio.Radio_ID = radio.Radio_ID WHERE city_channel.City IN ('Phoenix', 'Bakersfield', 'California', 'San Diego', 'Colorado Springs', 'Colorado', 'Denver', 'Cairn Hill');
SELECT radio.Transmitter, city_channel.Station_name FROM radio JOIN city_channel_radio ON radio.Radio_ID = city_channel_radio.Radio_ID JOIN city_channel ON city_channel_radio.City_channel_ID = city_channel.ID ORDER BY radio.ERP_kW DESC;
SELECT radio.Transmitter, COUNT(city_channel_radio.City_channel_ID) AS city_channels_count FROM radio JOIN city_channel_radio ON radio.Radio_ID = city_channel_radio.Radio_ID GROUP BY radio.Transmitter;
SELECT DISTINCT Transmitter FROM radio WHERE Radio_ID NOT IN (SELECT Radio_ID FROM city_channel_radio);
SELECT Model FROM vehicle WHERE Power > 6000 ORDER BY Top_Speed DESC LIMIT 1;
SELECT Model FROM vehicle WHERE Power > 6000 ORDER BY Top_Speed DESC LIMIT 1;
SELECT Name FROM driver WHERE Citizenship = 'United States';
SELECT Name FROM driver WHERE Citizenship = 'United States'
SELECT COUNT(Vehicle_ID) AS max_vehicles, Driver_ID FROM vehicle_driver GROUP BY Driver_ID ORDER BY max_vehicles DESC LIMIT 1;
SELECT Driver_ID, COUNT(*) AS Vehicle_Count FROM vehicle_driver GROUP BY Driver_ID ORDER BY Vehicle_Count DESC LIMIT 1;
SELECT MAX(Power), AVG(Power) FROM vehicle WHERE Builder = 'Zhuzhou';
SELECT MAX(Power) AS Max_Power, AVG(Power) AS Avg_Power FROM vehicle WHERE Builder = 'Zhuzhou';
SELECT v.Vehicle_ID FROM vehicle_driver vd JOIN vehicle v ON vd.Vehicle_ID = v.Vehicle_ID GROUP BY v.Vehicle_ID ORDER BY COUNT(*) ASC LIMIT 1;
SELECT Vehicle_ID FROM vehicle_driver GROUP BY Vehicle_ID ORDER BY COUNT(Driver_ID) ASC LIMIT 1;
SELECT top_speed, power FROM vehicle WHERE build_year = 1996;
SELECT top_speed, power FROM vehicle WHERE build_year = 1996
SELECT Build_Year, Model, Builder FROM vehicle;
SELECT Build_Year, Model, Builder FROM vehicle;
SELECT COUNT(DISTINCT vehicle_driver.Driver_ID) FROM vehicle_driver JOIN vehicle ON vehicle_driver.Vehicle_ID = vehicle.Vehicle_ID WHERE vehicle.Build_Year = '2012';
SELECT COUNT(DISTINCT vd.Driver_ID) FROM vehicle_driver vd JOIN vehicle v ON vd.Vehicle_ID = v.Vehicle_ID WHERE v.Build_Year = '2012'
SELECT COUNT(Driver_ID) FROM driver WHERE Racing_Series = 'NASCAR'
SELECT COUNT(*) FROM driver WHERE Racing_Series = 'NASCAR'
SELECT AVG(Top_Speed) FROM vehicle;
SELECT AVG(Top_Speed) FROM vehicle;
SELECT DISTINCT driver.Name FROM driver JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID JOIN vehicle ON vehicle_driver.Vehicle_ID = vehicle.Vehicle_ID WHERE vehicle.Power > 5000
SELECT driver.Name FROM driver JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID JOIN vehicle ON vehicle_driver.Vehicle_ID = vehicle.Vehicle_ID WHERE vehicle.Power > 5000;
SELECT Model FROM vehicle WHERE Total_Production > '100' OR Top_Speed > 150;
SELECT Model FROM vehicle WHERE Total_Production > '100' OR Top_Speed > 150;
SELECT Model, Build_Year FROM vehicle WHERE Model LIKE '%DJ%'
SELECT Model, Build_Year FROM vehicle WHERE Model LIKE '%DJ%';
SELECT Model FROM vehicle LEFT JOIN vehicle_driver ON vehicle.Vehicle_ID = vehicle_driver.Vehicle_ID WHERE vehicle_driver.Vehicle_ID IS NULL;
SELECT Model FROM vehicle WHERE Vehicle_ID NOT IN (SELECT Vehicle_ID FROM vehicle_driver);
SELECT Vehicle_ID, Model FROM vehicle WHERE Builder = 'Ziyang' OR Vehicle_ID IN (SELECT Vehicle_ID FROM vehicle_driver GROUP BY Vehicle_ID HAVING COUNT(Driver_ID) >= 2);
SELECT Vehicle_ID, Model FROM vehicle WHERE Builder = 'Ziyang' OR Vehicle_ID IN (SELECT Vehicle_ID FROM vehicle_driver GROUP BY Vehicle_ID HAVING COUNT(Driver_ID) = 2);
SELECT Vehicle_ID, Model FROM vehicle WHERE Vehicle_ID IN (SELECT Vehicle_ID FROM vehicle_driver GROUP BY Vehicle_ID HAVING COUNT(Driver_ID) > 2) OR Vehicle_ID IN (SELECT Vehicle_ID FROM vehicle_driver WHERE Driver_ID = (SELECT Driver_ID FROM driver WHERE Name = 'Jeff Gordon'));
SELECT DISTINCT v.Vehicle_ID, v.Model FROM vehicle v JOIN vehicle_driver vd ON v.Vehicle_ID = vd.Vehicle_ID WHERE vd.Driver_ID IN (SELECT Driver_ID FROM driver WHERE Name = 'Jeff Gordon') OR (SELECT COUNT(*) FROM vehicle_driver WHERE Vehicle_ID = v.Vehicle_ID) > 2;
SELECT COUNT(*) FROM vehicle WHERE Top_Speed = (SELECT MAX(Top_Speed) FROM vehicle)
SELECT COUNT(*) FROM vehicle WHERE Top_Speed = (SELECT MAX(Top_Speed) FROM vehicle)
SELECT Name FROM driver ORDER BY Name;
SELECT Name FROM driver ORDER BY Name ASC;
SELECT COUNT(DISTINCT vehicle_driver.Driver_ID) FROM vehicle_driver JOIN driver ON vehicle_driver.Driver_ID = driver.Driver_ID GROUP BY driver.Racing_Series;
SELECT Racing_Series, COUNT(DISTINCT driver.Driver_ID) FROM driver JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID GROUP BY Racing_Series;
SELECT driver.Name, driver.Citizenship FROM driver INNER JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID INNER JOIN vehicle ON vehicle_driver.Vehicle_ID = vehicle.Vehicle_ID WHERE vehicle.Model = 'DJ1'
SELECT driver.Name, driver.Citizenship FROM driver JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID JOIN vehicle ON vehicle_driver.Vehicle_ID = vehicle.Vehicle_ID WHERE vehicle.Model = 'DJ1'
SELECT COUNT(*) FROM driver WHERE Driver_ID NOT IN (SELECT Driver_ID FROM vehicle_driver);
SELECT COUNT(*) FROM driver LEFT JOIN vehicle_driver ON driver.Driver_ID = vehicle_driver.Driver_ID WHERE vehicle_driver.Vehicle_ID IS NULL
SELECT COUNT(*) FROM Exams;
SELECT COUNT(*) FROM Exams
SELECT DISTINCT Subject_Code FROM Exams ORDER BY Subject_Code ASC;
SELECT DISTINCT Subject_Code FROM Exams ORDER BY Subject_Code;
SELECT Exam_Date, Exam_Name FROM Exams WHERE Subject_Code != 'Database';
SELECT Exam_Date, Exam_Name FROM Exams WHERE Subject_Code != 'Database'
SELECT Exam_Date FROM Exams WHERE Subject_Code LIKE '%data%' ORDER BY Exam_Date DESC;
SELECT Exam_Date FROM Exams WHERE Subject_Code LIKE '%data%' ORDER BY Exam_Date DESC;
SELECT Q1.Type_of_Question_Code, COUNT(Q2.Question_ID) AS Count FROM Questions Q1 JOIN Questions_in_Exams Q2 ON Q1.Question_ID = Q2.Question_ID GROUP BY Q1.Type_of_Question_Code;
SELECT Type_of_Question_Code, COUNT(*) AS occurrence_count FROM Questions GROUP BY Type_of_Question_Code;
SELECT DISTINCT Student_Answer_Text FROM Student_Answers WHERE Comments = 'Normal';
SELECT DISTINCT Student_Answers.Student_Answer_Text FROM Student_Answers JOIN Student_Assessments ON Student_Answers.Student_Answer_ID = Student_Assessments.Student_Answer_ID WHERE Student_Assessments.Assessment = 'Normal' AND Student_Answers.Student_Answer_ID IN ('ABC', 'C', 'Absent')
SELECT COUNT(DISTINCT Comments) FROM Student_Answers;
SELECT COUNT(DISTINCT Comments) FROM Student_Answers;
SELECT Student_Answer_Text, COUNT(*) AS count FROM Student_Answers GROUP BY Student_Answer_Text ORDER BY count DESC;
SELECT Student_Answer_Text, COUNT(*) AS Frequency FROM Student_Answers GROUP BY Student_Answer_Text ORDER BY Frequency DESC;
SELECT Students.First_Name, Student_Answers.Date_of_Answer FROM Students JOIN Student_Answers ON Students.Student_ID = Student_Answers.Student_ID WHERE Students.First_Name IN ('Wilbert', 'Abdul', 'Ari', 'Cassidy', 'Alfreda', 'Normal', 'Absent')
SELECT Students.First_Name, Student_Answers.Date_of_Answer FROM Students JOIN Student_Answers ON Students.Student_ID = Student_Answers.Student_ID WHERE Students.First_Name = 'Wilbert' OR Students.First_Name = 'Abdul' OR Students.First_Name = 'Ari' OR Students.First_Name = 'Cassidy' OR Students.First_Name = 'Alfreda' OR Students.First_Name = 'Normal' OR Students.First_Name = 'Absent';
SELECT Students.Email_Adress, Student_Answers.Date_of_Answer FROM Students JOIN Student_Answers ON Students.Student_ID = Student_Answers.Student_ID ORDER BY Student_Answers.Date_of_Answer DESC;
SELECT Students.Email_Adress, Student_Answers.Date_of_Answer FROM Students JOIN Student_Answers ON Students.Student_ID = Student_Answers.Student_ID ORDER BY Student_Answers.Date_of_Answer DESC;
SELECT Assessment FROM Student_Assessments GROUP BY Assessment ORDER BY COUNT(*) ASC LIMIT 1;
SELECT Assessment FROM Student_Assessments GROUP BY Assessment ORDER BY COUNT(*) ASC LIMIT 1;
SELECT First_Name FROM Students WHERE Student_ID IN (SELECT Student_ID FROM Student_Answers GROUP BY Student_ID HAVING COUNT(*) >= 2)
SELECT s.First_Name FROM Students s JOIN Student_Answers sa ON s.Student_ID = sa.Student_ID GROUP BY s.Student_ID HAVING COUNT(sa.Student_Answer_ID) >= 2;
SELECT Valid_Answer_Text FROM Valid_Answers GROUP BY Valid_Answer_Text ORDER BY COUNT(*) DESC LIMIT 1;
SELECT Valid_Answer_Text FROM Valid_Answers GROUP BY Valid_Answer_Text ORDER BY COUNT(*) DESC LIMIT 1;
SELECT Last_Name FROM Students WHERE Gender_MFU != 'M'
SELECT Last_Name FROM Students WHERE Gender_MFU != 'M';
SELECT Gender_MFU, COUNT(*) AS Number_of_Students FROM Students GROUP BY Gender_MFU;
SELECT Gender_MFU, COUNT(*) AS student_count FROM Students GROUP BY Gender_MFU;
SELECT Last_Name FROM Students WHERE Gender_MFU IN ('F','M')
SELECT Last_Name FROM Students WHERE Gender_MFU IN ('F', 'M')
SELECT First_Name FROM Students WHERE Student_ID NOT IN (SELECT Student_ID FROM Student_Answers)
SELECT First_Name FROM Students LEFT JOIN Student_Answers ON Students.Student_ID = Student_Answers.Student_ID WHERE Student_Answers.Student_ID IS NULL;
SELECT Student_Answer_Text FROM Student_Answers WHERE Comments  =  "Normal" INTERSECT SELECT Student_Answer_Text FROM Student_Answers WHERE Comments  =  "Absent"	
SELECT Student_Answer_Text FROM Student_Answers WHERE Comments  =  "Normal" INTERSECT SELECT Student_Answer_Text FROM Student_Answers WHERE Comments  =  "Absent"	
SELECT Type_of_Question_Code FROM Questions GROUP BY Type_of_Question_Code HAVING COUNT(*) >= 3;
SELECT Type_of_Question_Code FROM Questions GROUP BY Type_of_Question_Code HAVING COUNT(*) >= 3;
SELECT * FROM Students;
SELECT Student_ID, First_Name, Middle_Name, Last_Name, Gender_MFU, Student_Address, Email_Adress, Cell_Mobile_Phone, Home_Phone FROM Students;
SELECT COUNT(*) FROM Addresses;
SELECT COUNT(*) FROM Addresses;
SELECT address_id, address_details FROM Addresses;
SELECT address_id, address_details FROM Addresses;
SELECT COUNT(*) FROM Products
SELECT COUNT(*) FROM Products;
SELECT product_id, product_type_code, product_name FROM Products;
SELECT product_id, product_type_code, product_name FROM Products;
SELECT product_price FROM Products WHERE product_name = 'Monitor';
SELECT product_price FROM Products WHERE product_name = 'Monitor';
SELECT MIN(product_price), AVG(product_price), MAX(product_price) FROM Products;
SELECT MIN(product_price), AVG(product_price), MAX(product_price) FROM Products;
SELECT AVG(product_price) FROM Products WHERE product_type_code = 'Clothes';
SELECT AVG(product_price) FROM Products WHERE product_type_code = 'Clothes';
SELECT COUNT(DISTINCT product_type_code) FROM Products WHERE product_type_code IN ('hardware', 'Hardware', 'Clothes');
SELECT COUNT(*) FROM Products WHERE product_type_code = 'Hardware'
SELECT product_name FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products);
SELECT product_name FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products)
SELECT product_name FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products WHERE product_type_code = 'Hardware') AND product_type_code = 'Hardware'
SELECT product_name FROM Products WHERE product_price > (SELECT AVG(product_price) FROM Products WHERE product_type_code = 'Hardware') AND product_type_code = 'Hardware';
SELECT product_name FROM Products WHERE product_type_code = 'Clothes' ORDER BY product_price DESC LIMIT 1;
SELECT product_name FROM Products WHERE product_type_code = 'Clothes' ORDER BY product_price DESC LIMIT 1;
SELECT product_id, product_name FROM Products WHERE product_type_code = 'Hardware' ORDER BY product_price ASC LIMIT 1;
SELECT product_id, product_name FROM Products WHERE product_type_code = 'Hardware' ORDER BY product_price ASC LIMIT 1;
SELECT product_name FROM Products ORDER BY product_price DESC
SELECT product_name FROM Products ORDER BY product_price DESC
SELECT * FROM Products WHERE product_type_code = 'hardware' ORDER BY product_price ASC;
SELECT product_name FROM Products WHERE product_type_code = 'Hardware' ORDER BY product_price ASC;
SELECT product_type_code, COUNT(*) FROM Products GROUP BY product_type_code;
SELECT product_type_code, COUNT(product_id) FROM Products GROUP BY product_type_code;
SELECT product_type_code, AVG(product_price) FROM Products GROUP BY product_type_code;
SELECT product_type_code, AVG(product_price) AS average_price FROM Products GROUP BY product_type_code;
SELECT product_type_code FROM Products GROUP BY product_type_code HAVING COUNT(*) >= 2;
SELECT product_type_code FROM Products GROUP BY product_type_code HAVING COUNT(*) >= 2;
SELECT product_type_code, COUNT(*) AS product_count FROM Products GROUP BY product_type_code ORDER BY product_count DESC LIMIT 1;
SELECT product_type_code FROM Products GROUP BY product_type_code ORDER BY COUNT(*) DESC LIMIT 1;
SELECT COUNT(customer_id) FROM Customers;
SELECT COUNT(*) FROM Customers;
SELECT customer_id, customer_name FROM Customers;
SELECT customer_id, customer_name FROM Customers;
SELECT customer_address, customer_phone, customer_email FROM Customers WHERE customer_name = 'Jeromy'
SELECT customer_address, customer_phone, customer_email FROM Customers WHERE customer_name = 'Jeromy';
SELECT payment_method_code, COUNT(*) AS number_of_customers FROM Customers GROUP BY payment_method_code;
SELECT payment_method_code, COUNT(*) AS count FROM Customers GROUP BY payment_method_code;
SELECT payment_method_code, COUNT(*) AS count FROM Customers GROUP BY payment_method_code ORDER BY count DESC LIMIT 1;
SELECT payment_method_code FROM Customers GROUP BY payment_method_code ORDER BY COUNT(*) DESC LIMIT 1;
SELECT customer_name FROM Customers WHERE payment_method_code IN (SELECT payment_method_code FROM Customers GROUP BY payment_method_code HAVING COUNT(*) = (SELECT MIN(cnt) FROM (SELECT COUNT(*) AS cnt FROM Customers GROUP BY payment_method_code) AS sub))
SELECT customer_name FROM Customers WHERE payment_method_code = 'Credit Card' OR payment_method_code = 'Direct Debit' ORDER BY payment_method_code ASC LIMIT 1;
SELECT payment_method_code, customer_number FROM Customers WHERE customer_name = 'Jeromy';
SELECT payment_method_code, customer_number FROM Customers WHERE customer_name = 'Jeromy'
SELECT DISTINCT payment_method_code FROM Customers WHERE payment_method_code IN ('Credit Card', 'Direct Debit')
SELECT DISTINCT payment_method_code FROM Customers;
SELECT product_id, product_type_code FROM Products ORDER BY product_name;
SELECT product_id, product_type_code FROM Products ORDER BY product_name ASC;
SELECT product_type_code FROM Products GROUP BY product_type_code ORDER BY COUNT(*) ASC LIMIT 1;
SELECT product_type_code FROM Products GROUP BY product_type_code ORDER BY COUNT(*) ASC LIMIT 1;
SELECT COUNT(*) FROM Customer_Orders WHERE order_status_code IN ('Part', 'Completed')
SELECT COUNT(*) FROM Customer_Orders;
SELECT order_id, order_date, order_status_code FROM Customer_Orders WHERE customer_id = (SELECT customer_id FROM Customers WHERE customer_name = 'Jeromy')
SELECT Customer_Orders.order_id, Customer_Orders.order_date, Customer_Orders.order_status_code FROM Customer_Orders JOIN Customers ON Customer_Orders.customer_id = Customers.customer_id WHERE Customers.customer_name = 'Jeromy'
SELECT Customers.customer_name, Customers.customer_id, COUNT(Customer_Orders.order_id) AS order_count FROM Customers LEFT JOIN Customer_Orders ON Customers.customer_id = Customer_Orders.customer_id GROUP BY Customers.customer_id;
SELECT Customers.customer_name, Customers.customer_id, COUNT(Customer_Orders.order_id) AS number_of_orders FROM Customers LEFT JOIN Customer_Orders ON Customers.customer_id = Customer_Orders.customer_id GROUP BY Customers.customer_id;
SELECT customer_id, customer_name, customer_phone, customer_email FROM Customers WHERE customer_id = (SELECT customer_id FROM Customer_Orders GROUP BY customer_id ORDER BY COUNT(*) DESC LIMIT 1);
SELECT Customers.customer_id, Customers.customer_name, Customers.customer_phone, Customers.customer_email FROM Customers JOIN Customer_Orders ON Customers.customer_id = Customer_Orders.customer_id GROUP BY Customers.customer_id ORDER BY COUNT(Customer_Orders.order_id) DESC LIMIT 1;
SELECT order_status_code, COUNT(*) AS order_count FROM Customer_Orders GROUP BY order_status_code;
SELECT order_status_code, COUNT(*) AS count FROM Customer_Orders GROUP BY order_status_code;
SELECT order_status_code, COUNT(*) as count FROM Customer_Orders GROUP BY order_status_code ORDER BY count DESC LIMIT 1;
