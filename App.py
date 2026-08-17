#!/usr/bin/env python3
import re, asyncio, datetime, json, os
from flask import Flask, render_template_string, request, jsonify
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ImportChatInviteRequest

app = Flask(__name__)

API_ID = int(os.environ.get('API_ID', 38689786))
API_HASH = os.environ.get('API_HASH', 'be493ae51cd5a5906946a5d3d50c04f2')
PHONE = os.environ.get('PHONE', '+21695046279')
CARD_GROUP = int(os.environ.get('CARD_GROUP', -4949353398))
AI_REPORT_INVITE = os.environ.get('AI_REPORT_INVITE', 'https://t.me/+Fk8mvRZh6WExMzM8')
BILL_CODE = os.environ.get('BILL_CODE', 'RF61907738000300017385863')
BILL_AMOUNT = float(os.environ.get('BILL_AMOUNT', 300))

bot_client = None
bot_running = False
known_cards = set()
active_bill = {"code": BILL_CODE, "amount": BILL_AMOUNT}
payment_history = []
ai_chat_entity = None
loop = asyncio.new_event_loop()

def detect_card(text):
    patterns = [
        r'\b(4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b',
        r'\b(5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b',
        r'\b(3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5})\b'
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).replace(" ", "").replace("-", "")
    return None

async def run_bot():
    global bot_client, bot_running, ai_chat_entity
    if bot_client and bot_client.is_connected():
        return
    bot_client = TelegramClient("session", API_ID, API_HASH)
    await bot_client.connect()
    if not await bot_client.is_user_authorized():
        sent = await bot_client.send_code_request(PHONE)
        print("📲 Code sent! Check your Telegram.")
        code = input("Enter code: ")
        await bot_client.sign_in(PHONE, code, phone_code_hash=sent.phone_code_hash)
    try:
        await bot_client.join_channel(CARD_GROUP)
        print(f"✅ Joined card group: {CARD_GROUP}")
    except: pass
    try:
        hash_ = AI_REPORT_INVITE.split('+')[-1]
        updates = await bot_client(ImportChatInviteRequest(hash_))
        if updates.chats:
            ai_chat_entity = updates.chats[0]
            print(f"✅ Joined AI Report: {ai_chat_entity.title}")
    except: pass
    @bot_client.on(events.NewMessage)
    async def handler(event):
        if not event.message or not event.message.text:
            return
        text = event.message.text
        chat = await event.get_chat()
        if ai_chat_entity and chat.id == ai_chat_entity.id:
            if text.startswith('/'):
                await handle_command(event)
            else:
                await event.reply("🤖 Hi! Use /help for commands.")
            return
        if chat.id == CARD_GROUP:
            card = detect_card(text)
            if card and card not in known_cards:
                known_cards.add(card)
                await event.reply(f"💳 Card detected: {card[:4]}****{card[-4:]}")
                tid = "TXN-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                payment_history.append({"bill": active_bill["code"], "amount": active_bill["amount"], "card": card[:4]+"****", "status": "success", "time": datetime.datetime.now().isoformat()})
                await event.reply(f"✅ Payment successful!\nBill: {active_bill['code']}\nAmount: {active_bill['amount']}€\nTransaction: {tid}")
    bot_running = True
    print("🧠 Bot is running!")
    await bot_client.run_until_disconnected()

async def handle_command(event):
    text = event.text
    if text.startswith('/status'):
        await event.reply(f"📇 Bill: {active_bill['code']} - {active_bill['amount']}€\n💳 Cards: {len(known_cards)}\n📋 Payments: {len(payment_history)}")
    elif text.startswith('/setbill'):
        parts = text[9:].strip().split()
        if len(parts) >= 2:
            active_bill["code"] = parts[0]
            active_bill["amount"] = float(parts[1])
            await event.reply(f"✅ Bill set: {parts[0]} - {parts[1]}€")
    elif text.startswith('/cards'):
        if known_cards:
            await event.reply("\n".join([f"• {c[:4]}****{c[-4:]}" for c in list(known_cards)[-10:]]))
        else:
            await event.reply("📭 No cards yet.")
    elif text.startswith('/history'):
        if payment_history:
            await event.reply("\n".join([f"• {p['bill']} - {p['amount']}€ - {p['status']}" for p in payment_history[-5:]]))
        else:
            await event.reply("📭 No payments yet.")
    elif text.startswith('/help'):
        await event.reply("/status, /setbill <code> <amount>, /cards, /history, /help")

HTML = """
<!DOCTYPE html>
<html>
<head><title>Legendary AI Dashboard</title>
<style>
body{font-family:sans-serif;background:#0a0e17;color:#e0e0e0;padding:20px}
.container{max-width:800px;margin:auto}
.card{background:#121a2e;border:1px solid #1e2844;border-radius:12px;padding:20px;margin-bottom:20px}
.status{display:flex;align-items:center;gap:10px}
.dot{width:14px;height:14px;border-radius:50%;display:inline-block}
.online{background:#00ff88}.offline{background:#ff4444}
.btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:bold}
.btn-success{background:#00cc66;color:#000}
.btn-danger{background:#ff4444;color:#fff}
.btn-warning{background:#ffdd00;color:#000}
input{background:#0a0e17;border:1px solid #1e2844;color:#fff;padding:10px;border-radius:8px;width:100%}
</style>
</head>
<body>
<div class="container">
<h1>🧠 Legendary AI</h1>
<div class="card">
    <div class="status">
        <span class="dot {{ 'online' if running else 'offline' }}"></span>
        <span>{{ '🟢 Running' if running else '🔴 Stopped' }}</span>
    </div>
    <p><b>Bill:</b> {{ bill.code }} - {{ bill.amount }}€</p>
    <p><b>Cards:</b> {{ cards }}</p>
    <p><b>Payments:</b> {{ payments }}</p>
</div>
<div class="card">
    <h3>Control</h3>
    <button onclick="control('start')" class="btn btn-success">▶️ Start</button>
    <button onclick="control('stop')" class="btn btn-danger">⏹ Stop</button>
    <button onclick="control('restart')" class="btn btn-warning">🔄 Restart</button>
</div>
<div class="card">
    <h3>Settings</h3>
    <form action="/update" method="post">
        <label>Group ID:</label>
        <input name="group_id" value="{{ group_id }}">
        <label>Bill Code:</label>
        <input name="bill_code" value="{{ bill.code }}">
        <label>Amount:</label>
        <input name="bill_amount" value="{{ bill.amount }}">
        <button type="submit" class="btn btn-success">Save</button>
    </form>
</div>
<script>
function control(action) {
    fetch('/control', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:action})})
    .then(r=>r.json()).then(d=>location.reload());
}
</script>
</div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML, running=bot_running, bill=active_bill, cards=len(known_cards), payments=len(payment_history), group_id=CARD_GROUP)

@app.route('/control', methods=['POST'])
def control():
    action = request.json.get('action')
    if action == 'start':
        asyncio.run_coroutine_threadsafe(run_bot(), loop)
    elif action == 'stop':
        if bot_client:
            asyncio.run_coroutine_threadsafe(bot_client.disconnect(), loop)
    elif action == 'restart':
        if bot_client:
            asyncio.run_coroutine_threadsafe(bot_client.disconnect(), loop)
        asyncio.run_coroutine_threadsafe(run_bot(), loop)
    return jsonify({"status": "ok"})

@app.route('/update', methods=['POST'])
def update():
    # تحديث الإعدادات (مبسط)
    return "Updated", 200

def start_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())
    from threading import Thread
    Thread(target=start_flask).start()
    loop.run_forever()        if chat.id == CARD_GROUP:
            card = detect_card(text)
            if card and card not in known_cards:
                known_cards.add(card)
                await event.reply(f"💳 Card: {card[:4]}****{card[-4:]}")
                tid = "TXN-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                payment_history.append({"bill": active_bill["code"], "amount": active_bill["amount"], "card": card[:4]+"****", "status": "success", "time": datetime.datetime.now().isoformat()})
                await event.reply(f"✅ Payment OK!\nBill: {active_bill['code']}\nAmount: {active_bill['amount']}€")
    bot_running = True
    await bot_client.run_until_disconnected()

async def handle_command(event):
    text = event.text
    if text.startswith('/status'):
        await event.reply(f"Bill: {active_bill['code']} - {active_bill['amount']}€\nCards: {len(known_cards)}\nPayments: {len(payment_history)}")
    elif text.startswith('/setbill'):
        parts = text[9:].strip().split()
        if len(parts) >= 2:
            active_bill["code"] = parts[0]
            active_bill["amount"] = float(parts[1])
            await event.reply(f"✅ Bill set: {parts[0]} - {parts[1]}€")
    elif text.startswith('/help'):
        await event.reply("/status, /setbill <code> <amount>, /cards, /history, /help")

HTML = """
<!DOCTYPE html>
<html><head><title>Legendary AI</title>
<style>body{font-family:sans-serif;background:#0a0e17;color:#e0e0e0;padding:20px}.container{max-width:800px;margin:auto}.card{background:#121a2e;border:1px solid #1e2844;border-radius:12px;padding:20px;margin-bottom:20px}.status{display:flex;align-items:center;gap:10px}.dot{width:14px;height:14px;border-radius:50%;display:inline-block}.online{background:#00ff88}.offline{background:#ff4444}.btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:bold}.btn-success{background:#00cc66;color:#000}.btn-danger{background:#ff4444;color:#fff}.btn-warning{background:#ffdd00;color:#000}input{background:#0a0e17;border:1px solid #1e2844;color:#fff;padding:10px;border-radius:8px;width:100%}</style></head>
<body><div class="container"><h1>🧠 Legendary AI</h1><div class="card"><div class="status"><span class="dot online"></span> <span>🟢 Running</span></div><p><b>Bill:</b> {{ bill.code }} - {{ bill.amount }}€</p><p><b>Cards:</b> {{ cards }}</p><p><b>Payments:</b> {{ payments }}</p></div>
<div class="card"><h3>Control</h3><button onclick="control('start')" class="btn btn-success">▶️ Start</button><button onclick="control('stop')" class="btn btn-danger">⏹ Stop</button><button onclick="control('restart')" class="btn btn-warning">🔄 Restart</button></div>
<div class="card"><h3>Settings</h3><form action="/update" method="post"><label>Group ID:</label><input name="group_id" value="{{ group_id }}"><label>Bill Code:</label><input name="bill_code" value="{{ bill.code }}"><label>Amount:</label><input name="bill_amount" value="{{ bill.amount }}"><button type="submit" class="btn btn-success">Save</button></form></div>
<script>function control(a){fetch('/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a})}).then(r=>r.json()).then(d=>location.reload());}</script></div></body></html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML, running=bot_running, bill=active_bill, cards=len(known_cards), payments=len(payment_history), group_id=CARD_GROUP)

@app.route('/control', methods=['POST'])
def control():
    action = request.json.get('action')
    if action == 'start':
        asyncio.run_coroutine_threadsafe(run_bot(), loop)
    elif action == 'stop':
        if bot_client:
            asyncio.run_coroutine_threadsafe(bot_client.disconnect(), loop)
    elif action == 'restart':
        if bot_client:
            asyncio.run_coroutine_threadsafe(bot_client.disconnect(), loop)
        asyncio.run_coroutine_threadsafe(run_bot(), loop)
    return jsonify({"status": "ok"})

@app.route('/update', methods=['POST'])
def update():
    # for simplicity, just return
    return "Updated", 200

def start_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == '__main__':
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())
    from threading import Thread
    Thread(target=start_flask).start()
    loop.run_forever()
