# Product Requirements Document (PRD): Dashboard Activity Trend Filters (User & Project)

## 1. Introduction/Overview
เพิ่มฟีเจอร์ Filter สำหรับกราฟ "30-Day Activity Trend" ในหน้า Dashboard เพื่อให้ผู้ใช้สามารถเลือกดูข้อมูลตาม user และ project ได้พร้อมกัน ช่วยให้การวิเคราะห์ข้อมูล activity มีความละเอียดและตรงกับความต้องการมากขึ้น

## 2. Goals
- ให้ผู้ใช้สามารถเลือก filter ข้อมูลกราฟตาม user และ project ได้พร้อมกัน
- รองรับ multi-select และมี search box สำหรับค้นหา user/project
- กราฟรีเฟรชอัตโนมัติเมื่อเปลี่ยน filter
- มีปุ่ม clear filter เพื่อรีเซ็ตการเลือก

## 3. User Stories
- ในฐานะผู้ใช้ ฉันต้องการเลือก user และ project ที่ต้องการ เพื่อดู activity trend เฉพาะกลุ่มที่สนใจ
- ในฐานะผู้ใช้ ฉันต้องการค้นหาชื่อ user/project ใน filter dropdown ได้อย่างรวดเร็ว
- ในฐานะผู้ใช้ ฉันต้องการรีเซ็ต filter ได้ง่าย ๆ เพื่อกลับไปดูข้อมูลรวม

## 4. Functional Requirements
1. ระบบต้องมี filter สำหรับเลือก user และ project อยู่ข้าง ๆ dropdown ประเภท chart
2. filter ทั้งสองต้องรองรับ multi-select (เลือกได้หลายค่า)
3. filter dropdown ต้องมี search box สำหรับค้นหา user/project
4. เมื่อเลือก filter ใด ๆ กราฟต้องรีเฟรชข้อมูลอัตโนมัติทันที
5. ต้องมีปุ่ม clear filter สำหรับรีเซ็ตการเลือกทั้งหมด
6. ถ้าเลือก filter แล้วไม่มีข้อมูล ต้องแสดงข้อความ "No data"
7. ถ้าไม่ได้เลือก filter ใดเลย ให้แสดงข้อมูลรวมทั้งหมด

## 5. Non-Goals (Out of Scope)
- ไม่รวมการแก้ไขหรือเพิ่มประเภทกราฟใหม่
- ไม่รวมการเปลี่ยนแปลงโครงสร้างข้อมูล backend จริง (ใช้ mockup data ได้ในช่วงแรก)
- ไม่รวมการ export ข้อมูลจากกราฟ

## 6. Design Considerations
- UI ของ filter ให้ทำคล้ายกับ dropdown ประเภท chart ที่มีอยู่แล้ว เพื่อความสอดคล้อง
- ตำแหน่ง filter: อยู่ข้าง ๆ dropdown ประเภท chart
- ใช้ component ที่รองรับ multi-select และ search box (เช่น MUI Autocomplete, React Select ฯลฯ)

## 7. Technical Considerations
- ข้อมูล user/project สามารถใช้ mockup data ได้ในช่วงแรก
- ต้องออกแบบให้สามารถเปลี่ยนไปใช้ข้อมูลจริงได้ในอนาคต
- กราฟต้องรองรับการอัปเดตข้อมูลแบบ dynamic ตาม filter

## 8. Success Metrics
- ผู้ใช้สามารถเลือก filter ได้ทั้ง user และ project พร้อมกัน และกราฟแสดงผลถูกต้อง
- มี search box และปุ่ม clear filter ใช้งานได้จริง
- กราฟแสดง "No data" เมื่อไม่มีข้อมูลตาม filter
- ไม่มี bug หรือ error ในการใช้งาน filter

## 9. Open Questions
- ต้องการจำกัดจำนวน user/project ที่เลือกสูงสุดหรือไม่?
- ต้องการบันทึกสถานะ filter (เช่น ใน URL หรือ local storage) หรือไม่? 