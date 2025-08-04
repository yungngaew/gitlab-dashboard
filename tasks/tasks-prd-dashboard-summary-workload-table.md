## Relevant Files

- `frontend/src/app/dashboard/page.tsx` - หน้า Dashboard หลักที่จะแก้ไข layout และเพิ่ม tab navigation
- `frontend/src/components/dashboard/FilterBar.tsx` - อาจต้องปรับปรุงหากมี filter ที่เกี่ยวข้องกับ tab
- `frontend/src/components/dashboard/WorkloadTable.tsx` - (ใหม่) component สำหรับตาราง Workload
- `frontend/src/services/dashboardApi.ts` - ดึงข้อมูล issue_cache สำหรับ workload
- `frontend/src/app/globals.css` - ปรับปรุง style สำหรับ responsive/scroll
- `tests/unit/services/test_dashboardApi.ts` - ทดสอบ logic การดึงข้อมูล workload
- `tests/unit/components/test_WorkloadTable.tsx` - ทดสอบ component ตาราง Workload

### Notes

- Unit tests ควรอยู่ในโฟลเดอร์เดียวกับไฟล์ที่ทดสอบ
- ใช้ `npx jest` สำหรับรันทดสอบ

## Tasks

- [ ] 1.0 Implement tab navigation for Dashboard sections
- [ ] 2.0 Refactor Summary tab layout to 65/35 split and add Workload Table area
- [ ] 3.0 Implement Workload Table component (responsive, scrollable)
- [ ] 4.0 Integrate Workload Table with issue_cache data source
- [ ] 5.0 Write unit tests for Workload Table and data logic

---

I have generated the high-level tasks based on the PRD. Ready to generate the sub-tasks? Respond with 'Go' to proceed. 