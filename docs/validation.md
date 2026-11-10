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

## ตัวอย่าง Saturation ที่คำนวณมือ

Saturation ไม่ใช้ `IC = β × IB` เพราะทรานซิสเตอร์ไม่ทำหน้าที่เป็นแหล่งกระแส
แบบจำลองกำหนด `VCE = 0.30 V` แล้วแก้สมการวงจรเดียวกัน

วงจร: `VCC = 12 V`, `R1 = R2 = RC = 10 kΩ`, `RE = 1 kΩ`, `β = 100`,
`VBE = 0.70 V` → `VTH = 6 V`, `RTH = 5 kΩ`

```text
VTH = IB × RTH + VBE + IE × RE
VCC = IC × RC + VCE(sat) + IE × RE
IE  = IC + IB
```

แทน `IC = (11.7 − IE × 1,000) / 10,000` และ
`IB = (5.3 − IE × 1,000) / 5,000` ลงใน `IE = IC + IB`:

```text
10,000 × IE = (11.7 − 1,000 × IE) + 2 × (5.3 − 1,000 × IE)
13,000 × IE = 22.3
IE = 1.715384615 mA
IC = (11.7 − 1.715384615) / 10,000 = 0.998461538 mA
IB = (5.3 − 1.715384615) / 5,000  = 0.716923077 mA
```

```text
VE  = IE × RE = 1.715384615 V
VB  = VE + VBE = 2.415384615 V
VC  = VE + VCE(sat) = 2.015384615 V
VCE = 0.300 V
P   = VCE × IC = 0.299538 mW
βforced = IC / IB ≈ 1.39  (ไม่เท่ากับ β = 100)
```

ตรวจ KVL ฝั่ง collector: `VC = 12 − 0.998461538 mA × 10 kΩ = 2.015384615 V` ✓

| ปริมาณ | ค่าที่คำนวณมือ | เทสต์ที่ยืนยัน |
|---|---|---|
| IC | 0.998462 mA | `SaturationSolutionTests.test_saturation_currents_match_hand_calculation` |
| IB | 0.716923 mA | `SaturationSolutionTests.test_saturation_currents_match_hand_calculation` |
| IE | 1.715385 mA | `SaturationSolutionTests.test_saturation_currents_match_hand_calculation` |
| VE | 1.715385 V | `SaturationSolutionTests.test_saturation_voltages_match_hand_calculation` |
| VB | 2.415385 V | `SaturationSolutionTests.test_saturation_voltages_match_hand_calculation` |
| VC | 2.015385 V | `SaturationSolutionTests.test_saturation_voltages_match_hand_calculation` |
| VCE | 0.300 V | `SaturationSolutionTests.test_saturation_voltages_match_hand_calculation` |

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
Ran 43 tests
OK
```

## ข้อจำกัด

- ค่า β และ VBE ถือว่าคงที่
- ไม่คิด Early effect, กระแสรั่ว, อุณหภูมิ, หรือ tolerance
- Saturation กำหนด `VCE = 0.30 V` คงที่ (ไม่ได้แยก `VBE(sat)`) และ
  `IC` มาจาก `RC`/`RE` ไม่ได้มาจาก `β`
