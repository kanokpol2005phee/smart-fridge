
from flask import Flask, request, redirect, url_for, render_template_string, flash
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "smart-fridge-local-dev")

# Google Apps Script Web App URL
APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbw8m_ezn_CoUMGADjLLusWg7Mbd-NABqnnwIDC2FlKSICb4TgTE_Q3yI32NEblaImB_/exec"
)

PAGE = """
<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Fridge</title>
<style>
* { box-sizing: border-box; }
body {
  font-family: system-ui, sans-serif;
  background: #f3f6f3;
  color: #25352a;
  max-width: 760px;
  margin: auto;
  padding: 20px;
}
h1 { color: #276749; }
.card {
  background: white;
  padding: 20px;
  margin: 16px 0;
  border-radius: 16px;
  box-shadow: 0 3px 12px #0000000c;
}
label { display: block; margin-top: 12px; }
input, select, button {
  width: 100%;
  padding: 12px;
  margin-top: 6px;
  border: 1px solid #ccd5cd;
  border-radius: 8px;
  font: inherit;
}
button {
  background: #278451;
  color: white;
  border: 0;
  margin-top: 16px;
  cursor: pointer;
}
.notice { padding: 12px; background: #e5f5e9; border-radius: 8px; }
.error { padding: 12px; background: #fde8e8; border-radius: 8px; }
small { color: #637166; }
</style>
</head>
<body>
<h1>🥬 Smart Fridge</h1>
<p>ระบบจัดการอาหารและวันหมดอายุ</p>

{% for message in messages %}
<div class="{{ 'error' if 'ไม่สำเร็จ' in message else 'notice' }}">
  {{ message }}
</div>
{% endfor %}

<div class="card">
<h2>👤 สมัครสมาชิก</h2>
<form method="post" action="/register">
<label>รหัสสมาชิก</label>
<input name="member_id" placeholder="เช่น M-000001" required>
<label>ชื่อสมาชิก</label>
<input name="name" placeholder="ชื่อของคุณ" required>
<label>อีเมล (ถ้ามี)</label>
<input name="email" type="email" placeholder="name@example.com">
<button type="submit">บันทึกสมาชิก</button>
</form>
</div>

<div class="card">
<h2>🥗 เพิ่มอาหารในตู้เย็น</h2>
<form method="post" action="/add-food">
<label>รหัสสมาชิก</label>
<input name="member_id" placeholder="รหัสสมาชิกที่สมัครไว้" required>
<label>ชื่ออาหาร</label>
<input name="food_name" placeholder="เช่น นมสด" required>
<label>จำนวน</label>
<input name="quantity" placeholder="เช่น 2 กล่อง">
<label>วันที่ซื้อ</label>
<input name="purchase_date" type="date">
<label>วันหมดอายุ</label>
<input name="expiry_date" type="date" required>
<label>หมายเหตุ</label>
<input name="note" placeholder="เช่น เปิดแล้ว">
<button type="submit">บันทึกอาหาร</button>
</form>
</div>

<div class="card">
<h2>🔔 การแจ้งเตือน LINE OA</h2>
<p>Token จะถูกเก็บใน Google Apps Script ไม่ต้องใส่ใน Python</p>
<p><small>หลังตั้งค่า LINE OA ใน Apps Script แล้ว ให้ทดสอบ Token และระบบแจ้งเตือนที่นั่น</small></p>
</div>
</body>
</html>
"""


def send_to_apps_script(payload):
    """ส่งข้อมูลไป Google Apps Script โดยไม่เปิดเผย Token"""
    if not APPS_SCRIPT_URL or "/exec" not in APPS_SCRIPT_URL:
        raise RuntimeError("กรุณาตั้งค่า APPS_SCRIPT_URL ให้ถูกต้อง")

    response = requests.post(
        APPS_SCRIPT_URL,
        json=payload,
        timeout=30
    )
    response.raise_for_status()

    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            "Google Apps Script ไม่ได้ส่ง JSON กลับมา "
            "โปรดตรวจสอบ Web App URL และการ Deploy"
        )

    if result.get("ok") is False:
        raise RuntimeError(result.get("message", "Apps Script แจ้งข้อผิดพลาด"))

    return result


@app.get("/")
def home():
    messages = request.args.getlist("message")
    return render_template_string(PAGE, messages=messages)


@app.post("/register")
def register():
    payload = {
        "action": "register",
        "member_id": request.form.get("member_id", "").strip(),
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip()
    }

    if not payload["member_id"] or not payload["name"]:
        return redirect(url_for("home", message="ข้อมูลสมาชิกไม่ครบ"))

    try:
        send_to_apps_script(payload)
        return redirect(url_for("home", message="บันทึกสมาชิกสำเร็จ"))
    except Exception as exc:
        app.logger.exception("Register failed")
        return redirect(
            url_for("home", message=f"บันทึกสมาชิกไม่สำเร็จ: {exc}")
        )


@app.post("/add-food")
def add_food():
    payload = {
        "action": "add_food",
        "member_id": request.form.get("member_id", "").strip(),
        "food_name": request.form.get("food_name", "").strip(),
        "quantity": request.form.get("quantity", "").strip(),
        "purchase_date": request.form.get("purchase_date", "").strip(),
        "expiry_date": request.form.get("expiry_date", "").strip(),
        "note": request.form.get("note", "").strip()
    }

    if not payload["member_id"] or not payload["food_name"]:
        return redirect(url_for("home", message="กรุณากรอกสมาชิกและชื่ออาหาร"))

    if not payload["expiry_date"]:
        return redirect(url_for("home", message="กรุณาระบุวันหมดอายุ"))

    try:
        send_to_apps_script(payload)
        return redirect(url_for("home", message="บันทึกอาหารสำเร็จ"))
    except Exception as exc:
        app.logger.exception("Add food failed")
        return redirect(
            url_for("home", message=f"บันทึกอาหารไม่สำเร็จ: {exc}")
        )
s

if __name__ == "__main__":
    print("Smart Fridge กำลังเริ่มทำงาน")
    print("เปิดเว็บที่ http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
