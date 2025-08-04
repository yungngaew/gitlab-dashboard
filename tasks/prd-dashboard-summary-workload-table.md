# Product Requirements Document (PRD): Dashboard Summary Workload Table & Tab Navigation

## 1. Introduction/Overview

ปรับปรุงหน้า Executive Dashboard ให้ใช้งานง่ายขึ้น โดยเปลี่ยนจากการ scroll ยาวเป็นการเลือกดูแต่ละส่วนผ่านแท็บด้านบน (Summary, Group Analysis, Issues Analysis, Project Portfolio, Team Performance, Issues Management) และเพิ่มตาราง Workload ในแท็บ Summary เพื่อแสดงภาพรวมปริมาณงานของแต่ละสมาชิกในทีม (อ้างอิงจาก author_name ใน issue_cache) โดยตารางนี้ต้อง responsive และ scroll ได้

## 2. Goals

- ให้ผู้ใช้สามารถสลับดูแต่ละส่วนของ Dashboard ได้สะดวกผ่านแท็บ
- แสดงตาราง Workload ในแท็บ Summary เพื่อให้เห็นปริมาณงานของแต่ละสมาชิก
- ตาราง Workload ต้อง responsive และ scroll ได้

## 3. User Stories

- ในฐานะผู้บริหาร/หัวหน้าทีม ฉันต้องการดูปริมาณงานของแต่ละสมาชิกในทีมได้อย่างรวดเร็วจาก Dashboard
- ในฐานะผู้ใช้ ฉันต้องการสลับดูแต่ละส่วนของ Dashboard ได้ง่าย ไม่ต้อง scroll ยาว

## 4. Functional Requirements

1. Dashboard ต้องแสดง navigation tab ด้านบน (Summary, Group Analysis, Issues Analysis, Project Portfolio, Team Performance, Issues Management)
2. เมื่อเลือกแต่ละแท็บ จะแสดงเฉพาะเนื้อหาของแท็บนั้น (ไม่ต้อง scroll ยาว)
3. ในแท็บ Summary:
    1. แบ่ง layout เป็น 2 ส่วน: ซ้าย 65% (เนื้อหาเดิม), ขวา 35% (Workload Table)
    2. แสดงตาราง Workload ด้านขวา โดยมี column: Name (author_name), Open, In Progress, Total
    3. ข้อมูลดึงจาก issue_cache:
        - Name: author_name
        - Open: จำนวน issue ที่ state = opened
        - In Progress: จำนวน issue ที่ state = opened และ label = in progress
        - Total: Open + In Progress
        - แสดงเฉพาะ author_name ที่มี issue อย่างน้อย 1 รายการ
    4. ถ้าไม่มีข้อมูลในช่องใด ให้แสดง “-”
    5. ตาราง Workload ต้อง scroll ได้ (ถ้าข้อมูลเยอะ)
    6. ตาราง Workload ต้อง responsive รองรับมือถือ/แท็บเล็ต
4. ตาราง Workload แสดงเฉพาะในแท็บ Summary (แท็บอื่นไม่ต้องแสดง)

## 5. Non-Goals (Out of Scope)

- ไม่ปรับเปลี่ยน logic การดึงข้อมูลอื่น ๆ ของ Dashboard
- ไม่เพิ่ม/ลบข้อมูลใน issue_cache
- ไม่แสดงตาราง Workload ในแท็บอื่น

## 6. Design Considerations (Optional)

- Layout: ซ้าย 65% (เนื้อหาเดิม), ขวา 35% (Workload Table)
- Responsive: ตาราง Workload ต้องแสดงผลดีทั้ง desktop และ mobile
- Scroll: ถ้าข้อมูลเกินพื้นที่ ให้ scroll เฉพาะตาราง

## 7. Technical Considerations (Optional)

- ดึงข้อมูล author_name, state, label จาก issue_cache (backend หรือ frontend แล้วแต่โครงสร้างเดิม)
- ถ้าไม่มีข้อมูลในช่องใด (เช่น ไม่มี in progress) ให้แสดง “-”
- ใช้ component/tab pattern เดิมของ frontend (Next.js/React)

## 8. Success Metrics

- ผู้ใช้สามารถสลับดูแต่ละแท็บได้โดยไม่ต้อง scroll ยาว
- ตาราง Workload แสดงข้อมูลถูกต้อง, scroll ได้, responsive
- ถ้าไม่มีข้อมูล แสดง “-”

## 9. Open Questions

- ต้องการ sorting/filter เพิ่มเติมในตาราง Workload หรือไม่? (ถ้าใช่ ระบุรายละเอียด)
- ต้องการ export ข้อมูล Workload หรือไม่? 