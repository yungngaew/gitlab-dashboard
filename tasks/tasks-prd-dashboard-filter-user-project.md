## Relevant Files

- `frontend/src/app/dashboard/page.tsx` - หน้า Dashboard หลักที่ต้องเพิ่มและจัดการ state ของ filter
- `frontend/src/components/dashboard/ActivityChart.tsx` - กราฟ Activity Trend ที่ต้องรับ props filter และอัปเดตข้อมูล (ใช้ native <select> + <option> สำหรับ dropdown ประเภท chart)
- `frontend/src/services/mockApi.ts` - mock API สำหรับดึงข้อมูล user (contributors) และ project
- `frontend/src/hooks/useActivityData.ts` - hook สำหรับดึงและกรอง activity data ตาม filter
- `frontend/src/components/dashboard/FilterBar.tsx` - (ใหม่) component สำหรับ multi-select filter user/project พร้อม search box และปุ่ม clear filter
- `frontend/src/components/dashboard/FilterBar.test.tsx` - unit test สำหรับ FilterBar

### Notes
- Pattern dropdown/select ที่ใช้ใน dashboard เดิม (ActivityChart):
  - ใช้ native `<select>` + `<option>`
  - มี className สำหรับ styling (`border rounded px-2 py-2 text-sm`)
  - อยู่ใน div เดียวกับ title กราฟ (flex items-center justify-between)
- แนวทาง UI/UX สำหรับ FilterBar:
  - ตำแหน่ง: ข้าง dropdown chart type, เรียงแนวนอน, ใช้ flex+gap
  - Multi-select dropdown สำหรับ user/project (เลือกได้หลายค่า)
  - มี search box ในแต่ละ dropdown
  - มีปุ่ม clear filter สำหรับรีเซ็ตการเลือกทั้งหมด
  - ใช้ className เดียวกับ dropdown เดิม, ขนาดเท่ากัน
  - กดเลือก/ลบ filter หรือ clear แล้วกราฟรีเฟรชอัตโนมัติ
  - ถ้าไม่มีข้อมูลตาม filter ให้แสดง "No data"
  - รองรับ accessibility (tab, arrow, enter/space)
  - แนะนำใช้ React Select หรือ MUI Autocomplete
- ตัวอย่าง FilterBarProps interface:

```ts
export interface FilterBarProps {
  users: { id: number; name: string }[];
  projects: { id: number; name: string }[];
  selectedUsers: number[];
  selectedProjects: number[];
  onChangeUsers: (userIds: number[]) => void;
  onChangeProjects: (projectIds: number[]) => void;
  onClear: () => void;
  isLoading?: boolean;
}
```
- Unit tests ควรอยู่ข้างไฟล์ component ที่ทดสอบ (เช่น `FilterBar.tsx` และ `FilterBar.test.tsx`)
- ใช้ mockApi สำหรับข้อมูล user/project ในช่วงแรก
- ใช้ `npx jest` สำหรับรันเทส

## Tasks

- [ ] 1.0 วิเคราะห์และออกแบบ UI/UX ของ filter (user & project) สำหรับ Dashboard Activity Trend
  - [x] 1.1 สำรวจและสรุป pattern dropdown/select ที่ใช้ใน dashboard เดิม
  - [x] 1.2 ออกแบบ UI/UX ของ filter ให้สอดคล้องกับ dropdown ประเภท chart เดิม (multi-select + search + clear)
  - [x] 1.3 กำหนด props และ interface ที่จำเป็นสำหรับ FilterBar component
- [ ] 2.0 เพิ่ม component filter (user & project) แบบ multi-select พร้อม search box และปุ่ม clear filter ในหน้า Dashboard
  - [ ] 2.1 สร้างไฟล์ `FilterBar.tsx` และพัฒนา multi-select filter (user/project)
  - [ ] 2.2 ดึง mock data user/project จาก mockApi มาแสดงใน filter
  - [ ] 2.3 เพิ่ม search box และปุ่ม clear filter ใน FilterBar
  - [ ] 2.4 เขียน unit test สำหรับ FilterBar (`FilterBar.test.tsx`)
- [ ] 3.0 เชื่อมต่อ filter กับ mockup data และอัปเดตกราฟแบบ dynamic ตาม filter ที่เลือก
  - [ ] 3.1 ปรับ DashboardPage ให้เก็บ state ของ filter และส่ง props ไปยัง ActivityChart
  - [ ] 3.2 ปรับ useActivityData ให้รองรับการกรองข้อมูลตาม user/project
  - [ ] 3.3 ปรับ ActivityChart ให้แสดงข้อมูลตาม filter ที่เลือก
- [ ] 4.0 แสดงข้อความ 'No data' เมื่อไม่มีข้อมูลตาม filter และแสดงข้อมูลรวมเมื่อไม่ได้เลือก filter ใดเลย
  - [ ] 4.1 ปรับ ActivityChart ให้แสดงข้อความ 'No data' เมื่อไม่มีข้อมูล
  - [ ] 4.2 ทดสอบ edge case: ไม่เลือก filter ใดเลยต้องแสดงข้อมูลรวม
- [ ] 5.0 ทดสอบการใช้งาน filter, search, clear filter และ edge cases ตาม acceptance criteria
  - [ ] 5.1 ทดสอบการเลือก filter หลายค่าและรีเฟรชกราฟ
  - [ ] 5.2 ทดสอบ search/filter user/project
  - [ ] 5.3 ทดสอบปุ่ม clear filter
  - [ ] 5.4 ทดสอบกรณีไม่มีข้อมูล (No data)
  - [ ] 5.5 ทดสอบการแสดงข้อมูลรวมเมื่อไม่ได้เลือก filter ใดเลย 