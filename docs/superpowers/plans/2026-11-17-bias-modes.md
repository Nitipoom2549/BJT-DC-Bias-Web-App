# แผน: เพิ่มโหมด Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว)

วันที่: 2026-11-17 · สถานะ: **รออนุมัติแผน** (ยังไม่เขียนโค้ด)

> รูปแบบอ้างอิง: `docs/superpowers/plans/2026-11-10-bjt-dc-bias.md`
> (session นี้ไม่มี skill `superpowers` ติดตั้ง จึงใช้โครงเอกสารเดิมของ repo)

## 0. สถานะปัจจุบัน

- Branch `lab02-dc-bias`, HEAD `c9cf734`, 43 tests ผ่าน
- ยังไม่ commit: `app.py`, `dc_bias.py`, `tests/test_dc_bias.py`, `tests/test_web.py`
  จากงานหน้า `/lab03` ที่เขียนค้างไว้ (7 tests แดง เพราะยังไม่มี `templates/lab03.html`)
- ต้องตัดสินก่อนเริ่ม: **A) revert งานค้าง** (แนะนำ) หรือ **B) ทำหน้า `/lab03` ให้จบเพิ่มอีกงานหนึ่ง**

## 1. เป้าหมาย

เพิ่มโหมดคำนวณ 2 แบบในแอปเดิม โดย **ผลของ Divider ต้องเหมือน Lab 2 ทุกประการ**:

| โหมด | พารามิเตอร์ที่ใช้ | UI |
|---|---|---|
| `divider` (เดิม) | VCC, R1, R2, RC, RE, β, VBE | ค่าเริ่มต้นของหน้า `/` เหมือนเดิม |
| `fixed` (ใหม่) | VCC, RB, RC, β, VBE | เลือกโหมดแล้วฟอร์มเปลี่ยนช่อง |
| `emitter` (ใหม่) | VCC, RB, RC, RE, β, VBE | เลือกโหมดแล้วฟอร์มเปลี่ยนช่อง |

Whole app ยังเป็น DC Bias เท่านั้น (ไม่แตะ AC/SPICE ตาม `AGENTS.md`)

## 2. โครงสร้างที่อ่านจาก Lab 2 (สรุป)

- `dc_bias.py` = แกนวิศวกรรมล้วน: ค่าคงที่, `BiasInputError`, `to_ohms`, `parse_inputs`, `BiasResult` (+ property แปลงหน่วย), `_solve_saturation`, `solve_voltage_divider_bias`
- `app.py` = บาง: `create_app`, filter `num3`, route `GET /` + `POST /` / `POST /calculate`, `render_page`
- `templates/index.html` = หน้าเดียว: ฟอร์ม → schematic SVG → การ์ดผลลัพธ์ → สมการ
- `static/style.css` = CSS ล้วน
- `tests/` = `test_dc_bias.py` (วิศวกรรม) + `test_web.py` (HTTP) รวม 43 tests

## 3. สถาปัตยกรรมที่เสนอ

```
raw form ──> parse_inputs(raw, mode)  ──┐  (แปลงหน่วย Ω/kΩ → Ω ที่จุดเดียว)
                                        ├─> solve_bias(mode, values) ──> dict
mode selector ──────────────────────────┘                                   │
                                                                            v
                                                     templates/index.html (loop จาก dict)
```

หลักการ:

1. **สมการอยู่ใน Python ทั้งหมด** ไม่มีสมการใน Jinja
2. ทุกโหมดคืน **dict แบบเดียวกัน** ใช้ชื่อคีย์ชุดเดียวกัน + `QUANTITY_UNITS` บอกหน่วย
3. `solve_voltage_divider_bias` **ไม่แก้แม้แต่บรรทัดเดียว** → ผล Lab 2 คงเดิม
4. โหมดเป็นตัวเลือก ไม่ใช่หน้าใหม่ → URL `/` และ POST เดิมยังทำงานเหมือนเดิม

## 4. ไฟล์ที่จะเปลี่ยน

| ไฟล์ | สิ่งที่ทำ |
|---|---|
| `dc_bias.py` | เพิ่ม `BIAS_MODES`, `MODE_FIELDS`, `MODE_DEFAULTS`, `QUANTITY_UNITS`, `solve_fixed_bias()`, `solve_emitter_bias()`, `solve_bias()`; ขยาย `parse_inputs(raw, mode="divider")` ให้ตรวจเฉพาะฟิลด์ของโหมด |
| `app.py` | filter เพิ่ม (`num0`, `unit_label` ถ้าจำเป็น), route เดิมรับ `mode` จากฟอร์ม (ไม่ส่ง = `divider`), เรียก `solve_bias` แล้วส่ง dict เข้า template |
| `templates/index.html` | เพิ่ม select "โหมดไบอัส" + กลุ่มฟิลด์ตามโหมด (RB / R1,R2 / RE) แสดง/ซ่อนด้วย `hidden` attribute ที่เรนเดอร์จากเซิร์ฟเวอร์; การ์ดผลลัพธ์ render จาก dict |
| `static/style.css` | `.mode-group` + `[hidden]` เล็กน้อย (ไม่แตะสไตล์เดิม) |
| `README.md`, `docs/design-note.md` | เพิ่มตารางโหมด + สมการ + ข้อจำกัด |
| `docs/superpowers/plans/2026-11-17-bias-modes.md` | ไฟล์แผนนี้ |
| `tests/` | **ไม่แก้ ไม่เพิ่ม** ตามคำสั่ง (43 tests เดิมต้องผ่านครบ) |

ไม่แตะ: `requirements.txt`, `.gitignore`, `AGENTS.md`, `docs/validation.md`

## 5. สูตรต่อฟังก์ชัน (ตามใบงาน — ขอยืนยันก่อนเขียนโค้ด)

### 5.1 `solve_voltage_divider_bias(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult` (ของเดิม)

```
VTH = VCC·R2/(R1+R2)      RTH = R1·R2/(R1+R2)
IB  = (VTH−VBE)/(RTH+(β+1)RE)
IC  = β·IB                IE = (β+1)·IB
VE  = IE·RE               VB = VE+VBE
VC  = VCC−IC·RC           VCE = VC−VE
```

### 5.2 `solve_fixed_bias(vcc, rb, rc, beta, vbe) -> dict`

```
IB  = (VCC − VBE) / RB
IC  = β·IB                IE = (β+1)·IB
VE  = 0                   VB = VBE
VC  = VCC − IC·RC         VCE = VC
```

### 5.3 `solve_emitter_bias(vcc, rb, rc, re, beta, vbe) -> dict`

```
IB  = (VCC − VBE) / (RB + (β+1)·RE)
IC  = β·IB                IE = (β+1)·IB
VE  = IE·RE               VB = VE+VBE
VC  = VCC − IC·RC         VCE = VC−VE
```

### 5.4 กฎ region (ใช้ร่วมทุกโหมด)

- **Cutoff**: กระแสฐานจากสูตร ≤ 0 (`VCC ≤ VBE` สำหรับ fixed/emitter, `VTH ≤ VBE` สำหรับ divider) → IB=IC=IE=0, VE=0, VC=VCE=VCC
- **Saturation**: VCE ที่คำนวณได้ ≤ 0.30 V → ตรึง `VCE = 0.30 V` แล้วแก้ด้วย `_solve_saturation(vcc, rc, re, vth, rth, vbe)` ตัวเดิม
  - fixed: เรียกด้วย `re=0`, `vth=VCC`, `rth=RB` → `IC = (VCC−0.30)/RC`
  - emitter: เรียกด้วย `vth=VCC`, `rth=RB` → เหมือน divider แต่แทน R1‖R2 ด้วย RB
- **Forward-Active**: กรณีอื่น

## 6. การแปลงหน่วย (จุดเดียว)

| ขั้น | ที่ทำ | รายละเอียด |
|---|---|---|
| รับเข้า | `parse_inputs()` | ทุกตัวต้านทานของโหมดนั้น × 1000 เมื่อ `r_unit="kohm"`, ผ่าน `to_ohms()`; VCC/β/VBE คงเดิม |
| คำนวณ | ในฟังก์ชัน `solve_*` | รับ **SI ล้วน** (V, Ω, A, –) ไม่มีการแปลงหน่วย |
| แสดงผล | template + filter | `ic*1000 → mA`, `ib*1e6 → µA`, `rth/1000 → kΩ` ผ่าน property/filter เดิม |

## 7. รูปแบบ dict ผลลัพธ์ (คีย์และหน่วยตรงกันทุกโหมด)

`solve_bias(mode, values)` คืน dict:

```python
{
  "mode": "divider" | "fixed" | "emitter",
  "region": "active" | "cutoff" | "saturation",
  "values": { "<key>": float, ... },   # SI ล้วน
  "warnings": [str, ...],
  "assumptions": [str, ...],
}
```

`QUANTITY_UNITS = {"vcc": "V", "rb": "Ω", "r1": "Ω", "r2": "Ω", "rc": "Ω",
"re": "Ω", "beta": "–", "vbe": "V", "vth": "V", "rth": "Ω", "ib": "A",
"ic": "A", "ie": "A", "vb": "V", "ve": "V", "vc": "V", "vce": "V",
"power_q": "W"}`

คีย์ที่มีในแต่ละโหมด:

| key | unit | divider | fixed | emitter |
|---|---|---|---|---|
| `vcc` `rc` `beta` `vbe` | V, Ω, –, V | ✓ | ✓ | ✓ |
| `rb` | Ω | – | ✓ | ✓ |
| `r1` `r2` | Ω | ✓ | – | – |
| `re` | Ω | ✓ | – | ✓ |
| `vth` `rth` | V, Ω | ✓ | – | – |
| `ib` `ic` `ie` | A | ✓ | ✓ | ✓ |
| `vb` `ve` `vc` `vce` | V | ✓ | ✓ | ✓ |
| `power_q` | W | ✓ | ✓ | ✓ |

## 8. เลือกโหมด + ตรวจอินพุตตามโหมด

```python
BIAS_MODES = ("divider", "fixed", "emitter")

MODE_FIELDS = {
    "divider": ("r1", "r2", "rc", "re"),
    "fixed":   ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}
# ฟิลด์ร่วม: ("vcc", "beta", "vbe") + "r_unit" สำหรับตัวต้านทาน
```

- `parse_inputs(raw, mode="divider")` — ไม่ส่ง `mode` = พฤติกรรมเดิมทุกอย่าง (43 tests เดิมผ่าน)
- `mode` ไม่รู้จัก → `BiasInputError({"mode": "โหมดไม่ถูกต้อง"})` → HTTP 400
- ฟิลด์ที่ไม่ใช้ในโหมดนั้น **ไม่ถูกอ่าน** (ไม่ error ถ้าส่งมาเกิน)
- กติกาตัวเลข/ช่วงค่าเดิมใช้ซ้ำทั้งหมด (VCC>0, R>0, β>0, 0≤VBE<VCC, ASCII decimal)
- `MODE_DEFAULTS` แยกค่าเริ่มต้นต่อโหมด เพื่อให้หน้าแรกของแต่ละโหมดได้ผล Forward-Active

## 9. หลักประกันว่า Divider ไม่เปลี่ยน

1. `solve_voltage_divider_bias()` และ `BiasResult` ไม่ถูกแก้
2. `parse_inputs(raw)` signature เดิม (มี default `mode="divider"`)
3. `GET /` ไม่ส่ง `mode` → `divider` → ฟอร์ม/ผลลัพธ์เหมือน Lab 2
4. 43 tests เดิมต้องผ่านครบ ก่อนรายงานผล
5. ค่าอ้างอิงที่ต้องเห็นเหมือนเดิม: IC `1.230 mA`, VCE `8.052 V`, VB `1.942 V`, VC `9.294 V`

## 10. การตรวจรับ (Browser + ตารางของคุณ)

1. `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` → 43 tests OK
2. เปิด `http://127.0.0.1:5000/` ในเบราว์เซอร์ของ OpenCode
3. Divider: กด Calculate → เทียบค่าอ้างอิงเดิม
4. Fixed: ใส่ค่าจากตารางของคุณ → ตรวจ IC, VCE
5. Emitter: ใส่ค่าจากตารางของคุณ → ตรวจ IC, VCE
6. ส่ง screenshot + ตารางผลเทียบ (คำนวณ / ตารางคุณ / ผลต่าง) ให้ตรวจ

## 11. สิ่งที่ไม่ทำในงานนี้

- ไม่มี unittest ใหม่ (ตามคำสั่ง) — ใช้ browser + ตารางของคุณเป็นหลักฐาน
- ไม่แตะ AC/transient/SPICE/FET
- ไม่ commit / ไม่ push (เจ้าของทำใน GitHub Desktop)

## 12. คำถามที่ต้องตอบก่อนลงมือ

1. **งานค้าง `/lab03`**: revert หรือทำต่อ?
2. **ชื่อพารามิเตอร์ในใบงาน**: ใช้ `RB` ตัวเดียวใช่ไหม (ไม่ใช่ `R1`)?
3. **Emitter Bias**: มีทั้ง `RC` และ `RE` ตามสูตร 5.3 ใช่ไหม (บางใบงาน Emitter Bias ไม่มี RC)?
4. **Fixed Bias**: ต่อฐานผ่าน `RB` ตัวเดียวถึง VCC และอิมิตเตอร์ลงกราวด์ตรง ๆ ใช่ไหม?
5. **Saturation**: ใช้เกณฑ์ `VCE ≤ 0.30 V` เหมือน Lab 2 หรือใบงานกำหนดค่าอื่น?
6. **ป้ายชื่อโหมดบนหน้าจอ**: ภาษาไทย เช่น "ไฟลบแบบคงที่ (Fixed Bias)" / "ไฟลบแบบมีตัวต้านทานอิมิตเตอร์ (Emitter Bias)" หรือใช้ชื่ออังกฤษล้วน?
