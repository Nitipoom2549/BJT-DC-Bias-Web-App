# Validation Report — BJT Voltage-Divider DC Bias

วันที่: 2026-11-10

เอกสารนี้อธิบายการคำนวณอิสระด้วยมือสำหรับวงจรอ้างอิง และจับคู่ค่าที่ได้กับ
เทสต์ที่ยืนยันค่าเหล่านั้น ค่าอ้างอิงทั้งหมดคำนวณจากสมการ ไม่ได้ดึงจากโค้ดแอป

## วงจรอ้างอิง

| พารามิเตอร์ | ค่า |
|---|---|
| VCC | 12 V |
| R1 | 100 kΩ = 100,000 Ω |
| R2 | 22 kΩ = 22,000 Ω |
| RC | 2.2 kΩ = 2,200 Ω |
| RE | 1 kΩ = 1,000 Ω |
| β | 100 |
| VBE | 0.70 V |

## ขั้นที่ 1 — Thevenin equivalent ที่ Base

```text
VTH = VCC × R2 / (R1 + R2)
    = 12 × 22,000 / (100,000 + 22,000)
    = 264,000 / 122,000
    = 2.163934426 V

RTH = R1 × R2 / (R1 + R2)
    = 100,000 × 22,000 / 122,000
    = 2,200,000,000 / 122,000
    = 18,032.786885 Ω
```

## ขั้นที่ 2 — กระแสฐาน

```text
IB = (VTH − VBE) / (RTH + (β + 1) × RE)
   = (2.163934426 − 0.70) / (18,032.786885 + 101 × 1,000)
   = 1.463934426 / 119,032.786885
   = 0.000012298581 A
   = 12.298581 µA
```

## ขั้นที่ 3 — กระแส Collector และ Emitter

```text
IC = β × IB = 100 × 12.298581 µA = 1.229858 mA
IE = (β + 1) × IB = 101 × 12.298581 µA = 1.242157 mA
```

## ขั้นที่ 4 — แรงดันที่ขา

```text
VE = IE × RE = 1.242157 mA × 1,000 Ω = 1.242157 V
VB = VE + VBE = 1.242157 + 0.70 = 1.942157 V
VC = VCC − IC × RC = 12 − (1.229858 mA × 2,200 Ω) = 9.294312 V
VCE = VC − VE = 9.294312 − 1.242157 = 8.052155 V
```

## ผลรวม

| ปริมาณ | ค่าที่คำนวณมือ | เทสต์ที่ยืนยัน |
|---|---|---|
| VTH | 2.163934 V | `ReferenceCaseTests.test_intermediate_values_match_hand_calculation` |
| RTH | 18,032.787 Ω | `ReferenceCaseTests.test_intermediate_values_match_hand_calculation` |
| IB | 12.298581 µA | `ReferenceCaseTests.test_currents_match_hand_calculation` |
| IC | 1.229858 mA | `ReferenceCaseTests.test_currents_match_hand_calculation` |
| IE | 1.242157 mA | `ReferenceCaseTests.test_currents_match_hand_calculation` |
| VE | 1.242157 V | `ReferenceCaseTests.test_voltages_match_hand_calculation` |
| VB | 1.942157 V | `ReferenceCaseTests.test_voltages_match_hand_calculation` |
| VC | 9.294312 V | `ReferenceCaseTests.test_voltages_match_hand_calculation` |
| VCE | 8.052155 V | `ReferenceCaseTests.test_voltages_match_hand_calculation` |

## เอกลักษณ์ที่ตรวจเพิ่ม

ใน active/saturation:

```text
IE = IC + IB
VB = VE + VBE
VC = VCC − IC × RC
VCE = VC − VE
```

ใน cutoff ไม่ตรวจ `VB = VE + VBE` เพราะเป็นความไม่ต่อเนื่องของแบบจำลอง
(`IB = IC = IE = 0`, `VE = 0`, `VB = VTH`) — ตรวจด้วย
`RegionTests.test_cutoff_does_not_assert_base_emitter_identity`

## หลักฐานการรัน

```text
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Ran 34 tests
OK
```

## ข้อจำกัด

- ค่า β และ VBE ถือว่าคงที่
- ไม่คิด Early effect, กระแสรั่ว, อุณหภูมิ, หรือ tolerance
- ค่าใน saturation ยังเป็นค่าจาก Forward-Active เพื่อให้ตรวจได้
  แต่แอปแสดงคำเตือนว่าแบบจำลองใช้ไม่ได้
