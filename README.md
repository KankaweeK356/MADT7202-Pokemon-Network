# Pokémon TCG Stock Network Analysis

**MADT7202 · Web and Social Network Analytics Management · Mid-Term Applied Case**

โครงการนี้ใช้ Network Analysis เพื่อช่วยเจ้าของร้าน Pokémon TCG ตัดสินใจว่า  
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
- **Privacy:** public snapshot ใน repo ไม่เก็บ player name; ใช้ anonymous deck IDs เท่านั้น
- **Access:** source audit ใน `data/raw/source_audit.csv` แสดงว่า events เป็น public และ `decklists=True`
- **Sampling bias:** ข้อมูลสะท้อนเฉพาะเด็คแข่งขัน Pumpkaweekly 3 รายการ จึงไม่แทนความต้องการของนักสะสม ผู้เล่นทั่วไป หรือยอดขายจริงหน้าร้าน

### Source documentation

- Limitless developer documentation: https://docs.limitlesstcg.com/developer
- Tournament/API URLs ที่ใช้จริงอยู่ใน `data/raw/source_audit.csv`

## 4. Graph construction

### Node / Edge
- **Node:** การ์ด 1 ใบ
- **Technical exclusion:** ตัด Basic Energy
- **Edge:** การ์ด 2 ใบปรากฏร่วมกันใน decklist เดียวกัน

### Weighting
- **Jaccard similarity:** วัดสัดส่วนการใช้ร่วมกัน
- **Lift:** ตรวจว่าการพบร่วมกันสูงกว่าที่คาดจากความนิยมพื้นฐานของแต่ละใบหรือไม่

เลือก Jaccard + Lift แทน raw co-occurrence count เพราะ raw count สามารถดัน staple cards ขึ้นสูงเพียงเพราะมีความนิยมกว้าง เช่น **Boss's Orders–Night Stretcher พบร่วมกัน 434 decklists แต่ Lift = 0.991**

### Business-aware pruning

| Criterion | Threshold | Rationale |
|---|---:|---|
| Card prevalence | ≥ 10% (≥59 decks) | Core stock ควรมี competitive footprint กว้าง |
| Shared decks | ≥ 30 | ต้องมี material support ประมาณ 5% ของ corpus |
| Jaccard | ≥ 0.30 | ความสัมพันธ์ต้องมี overlap ชัด |
| Lift | ≥ 1.20 | co-occurrence สูงกว่า independence expectation ≥20% |
| Shared archetypes | ≥ 3 | relation ต้องไม่จำกัดอยู่ใน deck strategy เดียว |
| Mechanical/evolution pairs | declared exclusion list | ตัด tautological deck-building links ก่อน ranking |

**Graph reduction:**  
Raw Graph **501 nodes / 18,049 edges** → Analysis Graph **43 nodes / 115 edges** → Display Graph **12 nodes / 15 edges**

> Centrality คำนวณจาก **Analysis Graph 43/115**; Display Graph ใช้เพื่อความอ่านง่ายเท่านั้น

## 5. Findings

1. **Core Watchlist — Budew**  
   พบใน **209/584 decklists (35.8%)**, Weighted Degree = **7.614**, Betweenness = **0.302**  
   จึงมีทั้งการใช้งานกว้างและบทบาทเชื่อมหลาย relation ที่ ranking ทีละใบมองไม่เห็น

2. **Actionable pair — Dragapult ex × Rosa's Encouragement**  
   พบพร้อมกัน **94 decklists**, Jaccard = **0.712**, Lift = **4.366**, breadth = **3 archetypes**  
   จึงเป็น candidate สำหรับตรวจสต็อกพร้อมกันก่อนออก PO

3. **Robustness**  
   คู่ดังกล่าวยังผ่านเมื่อ sweep Jaccard cutoff:
   - 0.25 → 49 nodes / 184 edges
   - 0.30 → 43 nodes / 115 edges
   - 0.35 → 32 nodes / 77 edges

## 6. Recommended action

- **ทุกวันจันทร์:** ตรวจ Core Watchlist — Budew, Munkidori, Crispin และ Unfair Stamp
- **ก่อนออก PO:** ถ้า Dragapult ex หรือ Rosa's Encouragement ถึง reorder point ให้ตรวจยอดของอีกใบพร้อมกัน
- **หลัง major event / rotation:** rerun analysis; ถ้าคู่ไม่ผ่าน Shared ≥30, Jaccard ≥0.30, Lift ≥1.20 หรือ breadth ≥3 ติดต่อกัน 2 รอบ ให้ยกเลิก pair-check

## 7. What would change my mind

ความนิยมในเด็คแข่งไม่ได้แปลว่าลูกค้าจะซื้อคู่กัน ต้องตรวจเทียบยอดขายหน้าร้าน **4 สัปดาห์** ก่อนจับคู่โปรโมชัน หากยอดขายจริงไม่รองรับ ให้ยกเลิกการตรวจคู่ และกลับไปสั่งเติมสต็อกแยกตามยอดขายจริงของแต่ละใบ

---

## Repository structure

```text
MADT7202-Pokemon-Network/
├── README.md
├── requirements.txt
├── .gitignore
├── UPLOAD_TO_GITHUB.md
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
│   └── pokemon_network_analysis.ipynb
├── src/
│   ├── fetch_limitless_api.py
│   └── analyze_snapshot.py
├── outputs/
│   └── actionable_network.png
└── report/
    └── midterm_report.docx
```

## How to reproduce

### Recommended: reproduce the submitted results from the frozen snapshot

```bash
pip install -r requirements.txt
python src/analyze_snapshot.py
```

หรือเปิด `notebooks/pokemon_network_analysis.ipynb` แล้ว Run All

### Optional: re-collect from the live API

```bash
python src/fetch_limitless_api.py
```

การ fetch ใหม่อาจได้ข้อมูลต่างจาก frozen snapshot หาก source เปลี่ยนภายหลัง ดังนั้น **ผลในรายงานอ้างอิง frozen snapshot ที่อยู่ใน repo**

---

## Key files for the grader

- `README.md` — project context, methodology, findings and actions
- `data/raw/decklists_snapshot.csv` — frozen, sanitized dataset used for the report
- `src/fetch_limitless_api.py` — real data collection code
- `notebooks/pokemon_network_analysis.ipynb` — analysis workflow
- `data/processed/` — exact tables behind metrics
- `outputs/actionable_network.png` — report-ready graph
- `report/midterm_report.docx` — one-page report source
