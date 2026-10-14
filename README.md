# Pokémon TCG Stock Network Analysis

**MADT7202 · Web and Social Network Analytics Management · Mid-Term Applied Case**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/KankaweeK356/MADT7202-Pokemon-Network/blob/main/notebooks/pokemon_network_analysis.ipynb)

โครงการนี้ใช้ **Network Analysis** เพื่อช่วยเจ้าของร้าน Pokémon TCG ตัดสินใจว่า  
**การ์ดใบใดควรอยู่ในรายการตรวจสต็อกประจำสัปดาห์ และคู่การ์ดใดควรตรวจยอดคงเหลือพร้อมกันก่อนออกคำสั่งซื้อ**

---

## 1. The decision

**Decision:** เจ้าของร้านต้องตัดสินใจว่าการ์ดใบใดควรอยู่ในรายการตรวจสต็อกประจำสัปดาห์ และคู่การ์ดใดควรตรวจยอดคงเหลือพร้อมกันก่อนออกคำสั่งซื้อ

**Business Value:** ช่วยให้ร้านวางสต็อกได้ตรงกับรูปแบบความต้องการ ลดความเสี่ยงจาก Stockout, สต็อกไม่สมดุล และ Dead Stock พร้อมช่วยจัดสรรเงินลงทุนในสต็อกได้ดีขึ้น; คู่การ์ดที่พบเป็น candidate สำหรับ Cross-sell/Bundle และต้องยืนยันด้วย POS ก่อนใช้จริง

## 2. Why a network

จัดอันดับจำนวนการ์ดที่พบในเด็คได้ แต่ไม่สามารถบอกได้ว่า **คู่ใดปรากฏร่วมกันซ้ำ ๆ ใน decklists จริง** หรือ **การ์ดใดเป็นตัวเชื่อมระหว่างกลุ่ม**; จึงต้องใช้ Network เพื่อเห็นความสัมพันธ์ที่การจัดอันดับทีละใบมองไม่เห็น

## 3. Data

- **Source:** public decklists จาก **Limitless TCG Official Tournament API**
- **Events:** Pumpkaweekly วันที่ **14, 21 และ 28 ก.ย. 2026**
- **Format:** STANDARD
- **Volume:** **584 valid 60-card decklists**
- **Card-line records:** **14,744**
- **Frozen snapshot:** `data/raw/decklists_snapshot.csv`
- **Privacy / data minimization:** snapshot ที่เผยแพร่ใน repo ไม่เก็บ player name และใช้ anonymous deck IDs แทน
- **Source audit:** `data/raw/source_audit.csv` เก็บ tournament/API reference และค่าที่ตรวจพบจาก source เช่น `is_public=True` และ `decklists=True`
- **Sampling bias:** ข้อมูลสะท้อนเฉพาะเด็คแข่งขัน Pumpkaweekly 3 รายการ จึงไม่แทนความต้องการของนักสะสม ผู้เล่นทั่วไป หรือยอดขายจริงหน้าร้าน

### Data collection

โครงการแยก **การเก็บข้อมูล** ออกจาก **การวิเคราะห์** เพื่อให้ผลในรายงาน reproduce ได้ตรงกันทุกครั้ง

```text
Limitless Tournament API
        ↓
src/fetch_limitless_api.py
        ↓
Frozen sanitized snapshot
data/raw/decklists_snapshot.csv
        ↓
notebooks/pokemon_network_analysis.ipynb
        ↓
Network → Metrics → Robustness → Actionable Graph
```

- `src/fetch_limitless_api.py` = code ดึงข้อมูลจริงจาก API
- Notebook หลัก = วิเคราะห์จาก frozen snapshot ไม่ยิง API ใหม่โดยอัตโนมัติ
- การ fetch ใหม่อาจได้ผลต่างจากรายงานหาก source เปลี่ยนภายหลัง

Limitless developer documentation: <https://docs.limitlesstcg.com/developer>

## 4. Graph construction

### Node / Edge

- **Node:** การ์ด 1 ใบ
- **Technical exclusion:** ตัด Basic Energy
- **Edge:** การ์ด 2 ใบปรากฏร่วมกันใน decklist เดียวกัน

### Weighting

- **Jaccard similarity:** วัดสัดส่วน overlap ของ decklists ที่มีการ์ด A หรือ B
- **Lift:** ตรวจว่าการพบร่วมกันสูงกว่าที่คาดจากความนิยมพื้นฐานของแต่ละใบหรือไม่

เลือก Jaccard + Lift แทนการใช้ raw co-occurrence count เพียงอย่างเดียว เพราะ raw count สามารถดัน staple cards ขึ้นสูงจากความนิยมทั่วไป เช่น **Boss's Orders–Night Stretcher พบร่วมกัน 434 decklists แต่ Lift = 0.991**

### Business-aware pruning

| Criterion | Threshold | Rationale |
|---|---:|---|
| Card prevalence | ≥ 10% (≥59 decks) | Core stock ควรมี competitive footprint กว้าง |
| Shared decks | ≥ 30 | คู่ต้องมี material support เพียงพอ |
| Jaccard | ≥ 0.30 | ความสัมพันธ์ต้องมี overlap ชัด |
| Lift | ≥ 1.20 | co-occurrence สูงกว่า independence expectation อย่างน้อย 20% |
| Shared archetypes | ≥ 3 | relation ต้องไม่จำกัดอยู่ใน deck strategy เดียว |
| Mechanical/evolution pairs | declared exclusion list | ตัด tautological deck-building links ก่อน ranking |

**Graph reduction:**  
Raw Graph **501 nodes / 18,049 edges** → Analysis Graph **43 nodes / 115 edges** → Display Graph **12 nodes / 15 edges**

> Centrality คำนวณจาก **Analysis Graph 43/115**; Display Graph ใช้เพื่อความอ่านง่ายเท่านั้น

## 5. The graph

กราฟด้านล่างเป็น **Display Graph** ที่ใช้สื่อสารผลเชิงธุรกิจในรายงาน ส่วนการคำนวณ centrality ใช้ Analysis Graph เต็ม

![Actionable Stock Network](outputs/actionable_network.png)

- **Core Watchlist highlight:** Budew
- **Pair-check highlight:** Dragapult ex — Rosa's Encouragement
- Display Graph: **12 nodes / 15 edges**

## 6. Findings

1. **Core Watchlist — Budew**  
   พบใน **209/584 decklists (35.8%)**, Weighted Degree = **7.614**, Betweenness = **0.302**  
   จึงมีทั้งการใช้งานกว้างและบทบาทเชื่อมหลาย relation ที่ ranking ทีละใบมองไม่เห็น

2. **Actionable pair — Dragapult ex × Rosa's Encouragement**  
   พบพร้อมกัน **94 decklists**, Jaccard = **0.712**, Lift = **4.366**, breadth = **3 archetypes**  
   จึงเป็น candidate สำหรับตรวจสต็อกพร้อมกันก่อนออก PO

3. **Robustness**  
   คู่ดังกล่าวยังผ่านเมื่อ sweep Jaccard cutoff:
   - **0.25 → 49 nodes / 184 edges**
   - **0.30 → 43 nodes / 115 edges**
   - **0.35 → 32 nodes / 77 edges**

## 7. Recommended action

- **ทุกวันจันทร์:** เจ้าของร้านตรวจ Core Watchlist — Budew, Munkidori, Crispin และ Unfair Stamp
- **ก่อนออก PO:** ถ้า Dragapult ex หรือ Rosa's Encouragement ถึง reorder point ให้ตรวจยอดของอีกใบพร้อมกัน
- **หลัง major event / rotation:** rerun analysis; ถ้าคู่ไม่ผ่าน Shared ≥30, Jaccard ≥0.30, Lift ≥1.20 หรือ breadth ≥3 ติดต่อกัน 2 รอบ ให้ยกเลิก pair-check

## 8. What would change my mind

ความนิยมในเด็คแข่งไม่ได้แปลว่าลูกค้าจะซื้อคู่กัน ต้องตรวจเทียบยอดขายหน้าร้าน **4 สัปดาห์** ก่อนจับคู่โปรโมชัน หากยอดขายจริงไม่รองรับ ให้ยกเลิกการตรวจคู่ และกลับไปสั่งเติมสต็อกแยกตามยอดขายจริงของแต่ละใบ

---

## Repository structure

```text
MADT7202-Pokemon-Network/
├── README.md
├── requirements.txt
├── data/
│   ├── README.md
│   ├── raw/
│   │   ├── decklists_snapshot.csv
│   │   ├── decklists_summary.csv
│   │   ├── tournaments.csv
│   │   └── source_audit.csv
│   └── processed/
│       ├── raw_graph_edges.csv
│       ├── analysis_edges.csv
│       ├── node_metrics.csv
│       ├── display_edges.csv
│       ├── robustness.csv
│       └── a4_findings.csv
├── notebooks/
│   ├── pokemon_network_analysis.ipynb
│   └── api_pipeline_original_v3.ipynb
├── src/
│   ├── fetch_limitless_api.py
│   └── analyze_snapshot.py
├── outputs/
│   └── actionable_network.png
└── report/
    └── midterm_report.docx
```

## How to reproduce

### Option A — Google Colab (recommended for grading)

กดปุ่ม **Open in Colab** ด้านบน README แล้วเลือก **Runtime → Run all**

Notebook จะ:
1. ตรวจว่ามี repository/data อยู่แล้วหรือไม่
2. ถ้าเปิดจาก GitHub บน Colab จะ clone public repository ให้อัตโนมัติ
3. อ่าน frozen snapshot
4. ตรวจ 60-card decklists
5. สร้าง Raw Graph
6. ใช้ business-aware pruning
7. คำนวณ Analysis Graph และ centrality
8. ทำ robustness check
9. สร้าง Display Graph
10. แสดง A4-ready findings

### Option B — Local / repository root

```bash
pip install -r requirements.txt
python src/analyze_snapshot.py
```

### Optional — re-collect live data

```bash
python src/fetch_limitless_api.py
```

> **Important:** ผลในรายงานอ้างอิง frozen snapshot ที่ commit ไว้ใน repository ไม่ใช่ live API response ในอนาคต

## Key files for the grader

- `README.md` — business context, methodology, findings, actions และวิธี reproduce
- `data/raw/decklists_snapshot.csv` — frozen sanitized dataset ที่ใช้ในรายงาน
- `data/raw/source_audit.csv` — source audit ของ 3 tournaments
- `src/fetch_limitless_api.py` — real data collection code
- `notebooks/pokemon_network_analysis.ipynb` — Colab-ready reproducible analysis
- `notebooks/api_pipeline_original_v3.ipynb` — original API pipeline evidence
- `data/processed/` — exact tables behind metrics
- `outputs/actionable_network.png` — report-ready graph
- `report/midterm_report.docx` — one-page report source
