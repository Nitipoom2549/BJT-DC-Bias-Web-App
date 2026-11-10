# Design Note — BJT Voltage-Divider DC Bias

วันที่: 2026-11-10
สถานะ: อนุมัติแล้ว
เอกสารฉบับเต็ม: [`superpowers/specs/2026-11-10-bjt-dc-bias-design.md`](superpowers/specs/2026-11-10-bjt-dc-bias-design.md)

## เป้าหมาย

สร้าง Flask Web Application หลายไฟล์ที่คำนวณจุดทำงาน DC ของ NPN
Common-Emitter แบบ Voltage-Divider Bias โดยให้ Python Backend เป็นผู้คำนวณ
และแสดงผลพร้อมหน่วย มี validation และคำเตือนเมื่ออยู่นอก Forward-Active

## สถาปัตยกรรมที่เลือก

**Flask + Jinja แบบ server-rendered** แยกความรับผิดชอบเป็นสามชั้น:

| ไฟล์ | หน้าที่ | ข้อห้าม |
|---|---|---|
| `dc_bias.py` | parse, validate, แก้สมการ, ตัดสิน region | import Flask/HTML/HTTP |
| `app.py` | route, อ่านฟอร์ม, เรียก solver, render | ใส่สมการฟิสิกส์ |
| `templates/index.html` | แสดงฟอร์ม/ผล/คำเตือน/สมการ | คำนวณหรือ hardcode คำตอบ |

เหตุผล: มีภาษาเดียวฝั่ง server, test ผ่าน Flask test client ได้ตรงไปตรงมา,
และตรงกับสถาปัตยกรรมที่ handout กำหนด

## ทางเลือกที่ตัดออก

- **Flask JSON API + JavaScript** — เพิ่ม path การคำนวณที่สองและ state ฝั่ง client
  เสี่ยงทำให้ฟิสิกส์ซ้ำซ้อนและ hardcode ง่าย
- **Static HTML + JavaScript** — ไม่มี Python backend จึงผิดข้อกำหนดของ Lab
- **HTMX/Alpine.js** — เพิ่ม dependency และแนวคิดเกินขอบเขต Week 2

## สัญญาของ Region

- `VTH ≤ VBE` → **Cutoff**: `IB = IC = IE = 0`, `VE = 0`, `VB = VTH`,
  `VC = VCE = VCC`, มีคำเตือน
- `VCE ≤ 0.30 V` → **Saturation**: คงค่าจาก Forward-Active ไว้ให้ตรวจ
  แต่มีคำเตือนว่าค่า IC อาจสูงเกินจริง
- นอกนั้น → **Forward-Active**
- `VBE` นอกช่วง `0.50–0.90 V` → คำเตือนเพิ่ม แต่ยังคำนวณ

**ข้อยกเว้นสำคัญ:** สมการ `VB = VE + VBE` ใช้เฉพาะ active/saturation.
ใน cutoff เป็นความไม่ต่อเนื่องของแบบจำลอง จึงไม่ assert สมการนี้

## Validation

ทุกฟิลด์ต้องมีค่า เป็นตัวเลข ASCII และเป็นจำนวนจริงจำกัด
`VCC > 0`, `R > 0`, `β > 0`, `0 ≤ VBE < VCC`, หน่วยเป็น `Ω` หรือ `kΩ`
ข้อผิดพลาดทุกฟิลด์ถูกรวบรวมและแสดงพร้อมกัน; POST ที่ไม่ผ่านคืน HTTP 400
พร้อมฟอร์มที่คงค่าที่กรอกไว้

## การทดสอบ

- `tests/test_dc_bias.py` — ค่าอ้างอิงที่คำนวณมือ, identity, หน่วย,
  validation, cutoff/saturation, VBE warning
- `tests/test_web.py` — GET ฟอร์ม, POST ค่าอ้างอิง, HTTP 400,
  การคงค่าฟอร์ม, invalid unit, cutoff warning

รันด้วย `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

## สิ่งที่ไม่อยู่ในขอบเขต

AC, transient, SPICE, bias ชนิดอื่น, FET, interactive schematic editor,
authentication, ฐานข้อมูล, และการ deploy บน cloud
