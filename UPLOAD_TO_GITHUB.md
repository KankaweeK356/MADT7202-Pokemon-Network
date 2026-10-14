# วิธีอัป Repository ขึ้น GitHub สำหรับมือใหม่

ไฟล์ ZIP นี้เตรียมโครงสร้าง repo ไว้แล้ว ไม่ต้องเขียน code เพิ่มก่อนอัปโหลด

## วิธีง่ายที่สุดผ่านเว็บไซต์ GitHub

1. เข้า https://github.com และ Sign in
2. กด **New repository**
3. Repository name: `MADT7202-Pokemon-Network`
4. เลือก **Public** เพื่อให้อาจารย์เปิดได้โดยไม่ต้องขอสิทธิ์
5. **อย่า** ติ๊ก Add README / .gitignore / license เพราะในโฟลเดอร์มีให้แล้ว
6. กด **Create repository**
7. ในหน้า repo ใหม่ กด **uploading an existing file**
8. แตก ZIP `MADT7202-Pokemon-Network-GitHub-Ready.zip` ในเครื่องก่อน
9. เปิดโฟลเดอร์ `MADT7202-Pokemon-Network`
10. ลากไฟล์และโฟลเดอร์ทั้งหมดขึ้นหน้า GitHub
11. Commit message: `Initial MADT7202 midterm submission`
12. กด **Commit changes**

## ตรวจหลังอัปโหลด

หน้าแรกของ repo ควรเห็น README อัตโนมัติ และควรมี:
- `data/`
- `notebooks/`
- `src/`
- `outputs/`
- `report/`

เปิด `data/raw/decklists_snapshot.csv` แล้วต้องเห็น anonymous deck IDs เช่น `D0001` และไม่ควรมี player name

## ลิงก์ที่ใส่ใน A4

ใส่ URL ของหน้า repo เช่น:

`https://github.com/YOUR_USERNAME/MADT7202-Pokemon-Network`

Repository link นี้เพียงลิงก์เดียวพอ เพราะ README ชี้ไปยัง dataset, notebook, code และ output ครบแล้ว

## ถ้าต้องการใช้ Colab ภายหลัง

หลัง repo อยู่บน GitHub แล้ว:
1. เปิด `notebooks/pokemon_network_analysis.ipynb`
2. คัดลอก URL ของ notebook
3. ไปที่ https://colab.research.google.com/
4. เลือกแท็บ **GitHub**
5. วาง GitHub URL หรือค้นหา repository
6. เปิด notebook

หมายเหตุ: Notebook ใช้ relative path ไปยัง frozen CSV ใน repo ดังนั้นวิธีที่แน่นอนที่สุดคือ clone/download repo ทั้งชุดก่อนรัน
หรือรัน `python src/analyze_snapshot.py` จาก repository root
