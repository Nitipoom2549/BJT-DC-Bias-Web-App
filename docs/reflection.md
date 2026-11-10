# Reflection — คำถามรายบุคคล

วันที่: 2026-11-10
ผู้เขียน: นักศึกษาเจ้าของงาน (ร่างโดย OpenCode และตรวจทานโดยเจ้าของงาน)

## 1. เหตุใดการเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับการรัน Flask?

เพราะ `templates/index.html` เป็น **Jinja template** ไม่ใช่ HTML ที่สมบูรณ์
ในไฟล์มี placeholder เช่น `{{ form.get('vcc', '') }}`,
`{{ result.vb|num3 }}` และ `{{ url_for('calculate') }}` ซึ่ง Jinja จะแทนค่า
ก็ต่อเมื่อ Flask เรียก `render_template()` เท่านั้น

ถ้าเปิดไฟล์ตรง ๆ ผ่าน `file://`:

- เบราว์เซอร์จะเห็นข้อความ `{{ ... }}` ดิบ ๆ หรือแสดงหน้าไม่สมบูรณ์
- ไม่มี Python backend ทำงาน จึงไม่มี `parse_inputs()` หรือ
  `solve_voltage_divider_bias()` ถูกเรียก
- ฟอร์ม POST ไปที่ `action="/calculate"` ไม่ได้ เพราะไม่มี HTTP server
- ไม่มี HTTP status 200/400 และไม่มี validation ฝั่ง server

การรัน Flask (`python -m flask --app app run`) ทำให้มี HTTP server,
มี route `GET /` และ `POST /calculate`, และมี Jinja แทนค่าเป็น HTML จริง
นี่คือเหตุผลที่ handout กำหนดให้เปิดผ่าน `http://127.0.0.1:5000/` ไม่ใช่
ดับเบิลคลิกไฟล์

อ้างอิง: `app.py` (`render_page`, `calculate`) และ `templates/index.html`

## 2. ฟอร์มส่งข้อมูลไป Python อย่างไร?

ลำดับการทำงาน:

1. `templates/index.html` มี
   `<form method="post" action="{{ url_for('calculate') }}">`
   และ input ชื่อ `vcc`, `r1`, `r2`, `rc`, `re`, `beta`, `vbe`, `r_unit`
2. เมื่อกด **Calculate DC Bias** เบราว์เซอร์สร้าง HTTP POST ไปที่
   `/calculate` พร้อม body แบบ `application/x-www-form-urlencoded`
3. Flask route `calculate()` ใน `app.py` อ่านค่าจาก `request.form`
4. `dc_bias.parse_inputs()` แปลงข้อความเป็น `float`, ตรวจช่วงค่า และแปลง
   kΩ → Ω
5. `dc_bias.solve_voltage_divider_bias()` คำนวณ `VTH`, `RTH`, `IB`, `IC`,
   `IE`, `VE`, `VB`, `VC`, `VCE` และตัดสิน region
6. `render_template("index.html", result=result, form=submitted)` ส่ง
   `BiasResult` กลับไปให้ Jinja แสดงผลเป็น HTML

ถ้าค่าไม่ถูกต้อง `parse_inputs()` โยน `BiasInputError` ที่มี
`errors` รายฟิลด์; route จะ render ฟอร์มเดิมพร้อมข้อความภาษาไทยและคืน
HTTP 400 โดยไม่ทำให้หน้าเว็บล้ม

อ้างอิง: `app.py`, `dc_bias.py`, `tests/test_web.py`

## 3. แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML หรือไม่?

**ไม่จำเป็น** ตราบใดที่ชื่อ field ของ `BiasResult` และความหมายของค่ายังเหมือนเดิม
เพราะ HTML แสดงค่าผ่านชื่อ field เช่น `result.vb`, `result.ic_ma`,
`result.region_label` ไม่ได้ฝังสมการไว้

ตัวอย่าง: ถ้าปรับวิธีคำนวณ `IB` แต่ยังคืนค่า `ib`, `ic`, `vb`, `vce` เหมือนเดิม
เทมเพลตไม่ต้องแก้ไข และเทสต์วิศวกรรมจะเป็นตัวบอกว่าผลเปลี่ยนไปหรือไม่

ต้องแก้ HTML เมื่อ:

- เพิ่มหรือเปลี่ยนชื่อ field ที่จะแสดง
- เปลี่ยนหน่วยที่แสดง เช่น จาก mA เป็น A
- เปลี่ยนข้อความคำเตือนหรือสมการที่แสดงเป็นเอกสารประกอบ

การแยกแบบนี้คือเหตุผลที่ `dc_bias.py` ห้าม import Flask/HTML:
ทำให้แก้ฟิสิกส์ได้โดยไม่แตะ presentation และเขียนเทสต์ได้โดยไม่ต้องเปิดเบราว์เซอร์

อ้างอิง: `dc_bias.py` (`BiasResult`), `templates/index.html`,
`tests/test_dc_bias.py`

## 4. ทำไมผลใน Region ที่แบบจำลองใช้ไม่ได้จึงต้องมี Warning?

เพราะสมการ Forward-Active ตั้งอยู่บนสมมติฐานว่าไบแอสฐาน-อิมิตเตอร์นำกระแส
และ `VCE` ยังสูงพอที่จะอยู่ในช่วง Active เมื่อเงื่อนไขเปลี่ยน:

- **Cutoff** (`VTH ≤ VBE`): ทรานซิสเตอร์ไม่นำกระแส สมการที่ให้ `IB > 0`
  ใช้ไม่ได้ ค่าที่คำนวณต่อจะไม่มีความหมาย
- **Saturation** (`VCE ≤ 0.30 V`): รอยต่อ Collector-Base เริ่มนำกระแส
  ค่า `IC = β × IB` อาจสูงเกินจริง

ถ้าแอปแสดงตัวเลขโดยไม่มีคำเตือน ผู้ใช้ (โดยเฉพาะนักศึกษา) อาจเข้าใจว่า
นั่นคือค่าจริงของวงจร ซึ่งเป็นอันตรายต่อการวิเคราะห์และการออกแบบ
Warning จึงทำหน้าที่:

1. บอกขอบเขตความถูกต้องของแบบจำลอง
2. แยก “ผลจากการคำนวณ” ออกจาก “ผลที่เชื่อถือได้”
3. สนับสนุนให้ผู้ใช้ตรวจสอบไบแอสและเลือกแบบจำลองที่เหมาะสม

แอปจึงแสดง region badge และคำเตือนร่วมกับค่าเสมอ โดยไม่ซ่อนค่าที่คำนวณได้
แต่ก็ไม่กล่าวอ้างว่าแบบจำลองยังใช้ได้

อ้างอิง: `dc_bias.py` (`CUTOFF_WARNING`, `SATURATION_WARNING`,
`VBE_RANGE_WARNING`), `templates/index.html`
