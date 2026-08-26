from flask import Flask, request
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import sqlite3, random, string, time, re, os

app = Flask(__name__)

TOKEN = "8842907564:AAEPRr4EekFgL0MqubQGTUGk7OERk0JbxvE"
ADMIN_ID = 8405869278
ADMIN_USERNAME = "@KiruOfficial"
KBZ_NUMBER = "09784555147"
KBZ_NAME = "Ma Ei Ei Khin"
DB_PATH = "/tmp/orders.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        stock INTEGER DEFAULT 0,
        status TEXT DEFAULT 'available'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        username TEXT,
        password TEXT,
        status TEXT DEFAULT 'available',
        sold_to INTEGER DEFAULT NULL,
        sold_date TIMESTAMP DEFAULT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        user_id INTEGER,
        product_id INTEGER,
        price INTEGER,
        status TEXT DEFAULT 'pending',
        screenshot_id TEXT DEFAULT NULL,
        account_id INTEGER DEFAULT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_products():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, price FROM products WHERE status='available'")
    products = c.fetchall()
    conn.close()
    return products

def get_accounts_by_product(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, password FROM accounts WHERE product_id=? AND status='available'", (product_id,))
    accounts = c.fetchall()
    conn.close()
    return accounts

def get_available_count(product_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM accounts WHERE product_id=? AND status='available'", (product_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def save_order(user_id, product_id, price):
    order_id = "#" + ''.join(random.choices(string.digits, k=4))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO orders (order_id, user_id, product_id, price) VALUES (?,?,?,?)", 
              (order_id, user_id, product_id, price))
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
    conn.commit()
    conn.close()

def update_order_screenshot(order_id, screenshot_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET screenshot_id=? WHERE order_id=?", (screenshot_id, order_id))
    conn.commit()
    conn.close()

def update_order_account(order_id, account_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET account_id=? WHERE order_id=?", (account_id, order_id))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, product_id, price, status, account_id FROM orders WHERE order_id=?", (order_id,))
    order = c.fetchone()
    conn.close()
    return order

def mark_account_sold(account_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE accounts SET status='sold', sold_to=?, sold_date=? WHERE id=?", 
              (user_id, time.strftime("%Y-%m-%d %H:%M:%S"), account_id))
    conn.commit()
    conn.close()

def add_product(name, price, stock):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, stock) VALUES (?,?,?)", (name, price, stock))
    conn.commit()
    conn.close()

def add_account(product_id, username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO accounts (product_id, username, password) VALUES (?,?,?)", (product_id, username, password))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT order_id, user_id, price, order_date FROM orders WHERE status='pending' ORDER BY order_date ASC")
    orders = c.fetchall()
    conn.close()
    return orders

def get_sold_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT a.username, a.password, p.name, o.user_id FROM accounts a JOIN products p ON a.product_id=p.id JOIN orders o ON a.id=o.account_id WHERE a.status='sold'")
    accounts = c.fetchall()
    conn.close()
    return accounts

def get_all_orders():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT order_id, user_id, price, status, order_date FROM orders ORDER BY order_date DESC")
    orders = c.fetchall()
    conn.close()
    return orders

def delete_sold_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE status='sold' AND sold_date < datetime('now', '-15 minutes')")
    conn.commit()
    conn.close()

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 Blox Fruit အကောက်များ", callback_data="products")],
        [InlineKeyboardButton("📦 ကျွန်တော့် Order", callback_data="myorder")],
        [InlineKeyboardButton("📞 Admin ကိုဆက်သွယ်ရန်", callback_data="contact")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")]])

async def start(update: Update, context):
    user = update.effective_user
    welcome_msg = f"Kiru Blox Sell မှ ကြိုဆိုပါတယ် {user.first_name}!\n\nကျေးဇူးပြု၍ အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။"
    keyboard = [
        [InlineKeyboardButton("🎮 Blox Fruit အကောက်များ", callback_data="products")],
        [InlineKeyboardButton("📦 ကျွန်တော့် Order", callback_data="myorder")],
        [InlineKeyboardButton("📞 Admin ကိုဆက်သွယ်ရန်", callback_data="contact")]
    ]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    await update.message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def products(update: Update, context):
    query = update.callback_query
    await query.answer()
    products = get_products()
    if not products:
        await query.edit_message_text("📦 လက်ရှိ အကောက်များ မရှိသေးပါ။", reply_markup=back_button())
        return
    text = "🎮 Blox Fruit အကောက်များ:\n\n"
    for p in products:
        count = get_available_count(p[0])
        stock_status = f"✅ ကျန် {count} ခု" if count > 0 else "❌ ကုန်ပြီ"
        text += f"📌 {p[1]}\n   💰 {p[2]:,} MMK\n   📦 {stock_status}\n\n"
    keyboard = []
    for p in products:
        count = get_available_count(p[0])
        if count > 0:
            keyboard.append([InlineKeyboardButton(f"{p[1]} - {p[2]:,} MMK", callback_data=f"product_{p[0]}")])
    keyboard.append([InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def product_detail(update: Update, context):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split("_")[1])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, price FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    if not product:
        await query.edit_message_text("အကောက် မတွေ့ပါ။", reply_markup=back_button())
        return
    count = get_available_count(product_id)
    name, price = product
    text = f"📌 {name}\n💰 {price:,} MMK\n📦 ကျန် {count} ခု\n\nဝယ်ယူရန် '🛒 ဝယ်မည်' ကိုနှိပ်ပါ။"
    keyboard = [
        [InlineKeyboardButton("🛒 ဝယ်မည်", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    product_id = int(query.data.split("_")[1])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, price FROM products WHERE id=?", (product_id,))
    product = c.fetchone()
    conn.close()
    if not product:
        await query.edit_message_text("အကောက် မတွေ့ပါ။", reply_markup=back_button())
        return
    name, price = product
    order_id = save_order(query.from_user.id, product_id, price)
    context.user_data["pending_order_id"] = order_id
    text = f"✅ Order အောင်မြင်ပါပြီ!\n\nOrder ID: {order_id}\nအကောက်: {name}\nဈေးနှုန်း: {price:,} MMK\n\n💳 KBZPay သို့လွှဲပါ:\n📱 {KBZ_NUMBER}\n👤 {KBZ_NAME}\n\n📌 ငွေလွှဲပြီးပါက Screenshot ကို သင့် Order ID ({order_id}) နှင့်အတူ ပို့ပါ။"
    await query.edit_message_text(text, reply_markup=back_button())

async def handle_photo(update: Update, context):
    user_id = update.effective_user.id
    caption = update.message.caption or ""
    match = re.search(r'#\d{4}', caption)
    if not match:
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ သင့် Order ID (ဥပမာ #1234) ကို စာတန်းထိုးရေးထည့်ပါ။", reply_markup=back_button())
        return
    order_id = match.group(0)
    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order ID မှားယွင်းနေပါသည်။", reply_markup=back_button())
        return
    if order[0] != user_id:
        await update.message.reply_text("❌ ဤ Order ID သည် သင့်အတွက် မဟုတ်ပါ။", reply_markup=back_button())
        return
    photo = update.message.photo[-1]
    update_order_screenshot(order_id, photo.file_id)
    await update.message.reply_text("✅ Screenshot လက်ခံရရှိပါပြီ။ Admin မှ အတည်ပြုပါမည်။", reply_markup=back_button())
    await context.bot.send_message(
        ADMIN_ID,
        f"📸 ငွေလွှဲပြေစာအသစ်\n👤 @{update.message.from_user.username}\n🆔 {order_id}\n💰 {order[2]:,} MMK"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{order_id}")]
    ]
    await context.bot.send_message(
        ADMIN_ID,
        f"📋 Order {order_id} ကို အတည်ပြုရန် သို့မဟုတ် ပယ်ဖျက်ရန်:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT order_id, price, status, order_date FROM orders WHERE user_id=? ORDER BY order_date DESC", (user_id,))
    orders = c.fetchall()
    conn.close()
    if not orders:
        await query.edit_message_text("📦 သင့်တွင် Order မရှိသေးပါ။", reply_markup=back_button())
        return
    msg = "📦 သင့် Order များ:\n\n"
    status_emoji = {"pending": "⏳ ဆောင်ရွက်ဆဲ", "approved": "✅ အတည်ပြုပြီး", "cancelled": "❌ ပယ်ဖျက်ပြီး"}
    for order in orders:
        emoji = status_emoji.get(order[2], "❓")
        msg += f"{emoji} ID: {order[0]}\n💰 {order[1]:,} MMK\n📅 {order[3]}\n\n"
    await query.edit_message_text(msg, reply_markup=back_button())

async def contact_admin(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"📞 Admin ကိုဆက်သွယ်ရန်: {ADMIN_USERNAME}\n\n"
        "ကျေးဇူးပြု၍ သင့် Order ID နှင့်အတူ ဆက်သွယ်ပါ။\n"
        "Admin က သင့်ကို ပြန်လည်အကြောင်းပြန်ပါလိမ့်မယ်။",
        reply_markup=back_button()
    )

async def back(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎮 Blox Fruit အကောက်များ", callback_data="products")],
        [InlineKeyboardButton("📦 ကျွန်တော့် Order အခြေအနေ", callback_data="myorder")],
        [InlineKeyboardButton("📞 Admin ကိုဆက်သွယ်ရန်", callback_data="contact")]
    ]
    if query.from_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    await query.edit_message_text(
        "Kiru Blox Sell မှ ကြိုဆိုပါတယ်!\n\nကျေးဇူးပြု၍ အောက်ပါခလုတ်များမှ ရွေးချယ်ပါ။",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_panel(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    keyboard = [
        [InlineKeyboardButton("📦 ရောင်းရသောအကောက်များ", callback_data="admin_sold")],
        [InlineKeyboardButton("💰 ငွေလွှဲစရင်း", callback_data="admin_payments")],
        [InlineKeyboardButton("➕ အကောက်ထည့်ရန်", callback_data="admin_add_product")],
        [InlineKeyboardButton("🔐 အကောက် Account ထည့်ရန်", callback_data="admin_add_account")],
        [InlineKeyboardButton("🔄 ပယ်ဖျက်ထားသော အကောက်များပြန်ထည့်", callback_data="admin_restore_products")]
    ]
    await query.edit_message_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_sold(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    sold = get_sold_accounts()
    if not sold:
        await query.edit_message_text("📦 ရောင်းရသော အကောက်များ မရှိသေးပါ။", reply_markup=back_button())
        return
    msg = "📦 ရောင်းရသောအကောက်များ:\n\n"
    for acc in sold:
        msg += f"🔑 {acc[0]}\n🔒 {acc[1]}\n👤 {acc[2]}\n🆔 ဝယ်သူ: {acc[3]}\n\n"
    await query.edit_message_text(msg, reply_markup=back_button())

async def admin_payments(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    orders = get_all_orders()
    if not orders:
        await query.edit_message_text("💰 ငွေလွှဲစရင်း မရှိသေးပါ။", reply_markup=back_button())
        return
    msg = "💰 ငွေလွှဲစရင်း:\n\n"
    status_emoji = {"pending": "⏳", "approved": "✅", "cancelled": "❌"}
    for order in orders:
        emoji = status_emoji.get(order[3], "❓")
        msg += f"{emoji} ID: {order[0]}\n👤 User: {order[1]}\n💰 {order[2]:,} MMK\n📅 {order[4]}\n\n"
    await query.edit_message_text(msg, reply_markup=back_button())

async def admin_add_product(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    context.user_data["admin_action"] = "add_product"
    await query.edit_message_text(
        "➕ အကောက်အသစ်ထည့်ရန်\n\n"
        "အောက်ပါအတိုင်း ရိုက်ထည့်ပါ:\n"
        "အကောက်နာမည်, ဈေးနှုန်း, အရေအတွက်\n\n"
        "ဥပမာ: Angel V4 Account, 6000, 5\n\n"
        "ပြန်ထွက်ရန် /cancel ကိုနှိပ်ပါ။",
        reply_markup=back_button()
    )

async def admin_add_account(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    products = get_products()
    if not products:
        await query.edit_message_text("📦 အကောက်များ မရှိသေးပါ။ အကောက်အရင်ထည့်ပါ။", reply_markup=back_button())
        return
    msg = "🔐 အကောက် Account ထည့်ရန်:\n\n"
    for p in products:
        msg += f"🆔 {p[0]}. {p[1]} (Stock: {get_available_count(p[0])})\n"
    msg += "\nထည့်လိုသော အကောက် ID ကို ရိုက်ထည့်ပါ။"
    context.user_data["admin_action"] = "add_account_select"
    await query.edit_message_text(msg, reply_markup=back_button())

async def admin_add_account_select(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text
    if text == "/cancel":
        context.user_data["admin_action"] = None
        await update.message.reply_text("✅ ပယ်ဖျက်ပြီးပါပြီ။", reply_markup=back_button())
        return
    try:
        product_id = int(text.strip())
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM products WHERE id=?", (product_id,))
        product = c.fetchone()
        conn.close()
        if not product:
            await update.message.reply_text("❌ အကောက် ID မှားနေပါသည်။", reply_markup=back_button())
            return
        context.user_data["add_account_product_id"] = product_id
        context.user_data["admin_action"] = "add_account_details"
        await update.message.reply_text(
            f"🔐 {product[0]} အတွက် Account အချက်အလက်များ ရိုက်ထည့်ပါ:\n\n"
            "Username, Password\n\nဥပမာ: player123, pass456\n\n"
            "ပြန်ထွက်ရန် /cancel ကိုနှိပ်ပါ။",
            reply_markup=back_button()
        )
    except:
        await update.message.reply_text("❌ အကောက် ID ကို နံပါတ်ဖြင့်သာ ရိုက်ထည့်ပါ။", reply_markup=back_button())

async def admin_add_account_details(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text
    if text == "/cancel":
        context.user_data["admin_action"] = None
        await update.message.reply_text("✅ ပယ်ဖျက်ပြီးပါပြီ။", reply_markup=back_button())
        return
    product_id = context.user_data.get("add_account_product_id")
    if not product_id:
        await update.message.reply_text("❌ အမှားအယွင်း ဖြစ်နေပါသည်။ /cancel နှိပ်ပြီး ပြန်စပါ။", reply_markup=back_button())
        return
    parts = text.split(",")
    if len(parts) != 2:
        await update.message.reply_text("❌ ပုံစံမှားနေပါသည်။ Username, Password ဖြင့် ရိုက်ထည့်ပါ။", reply_markup=back_button())
        return
    username = parts[0].strip()
    password = parts[1].strip()
    add_account(product_id, username, password)
    context.user_data["admin_action"] = None
    await update.message.reply_text(f"✅ Account ထည့်ပြီးပါပြီ!\n👤 {username}\n🔒 {password}", reply_markup=back_button())

async def admin_restore_products(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    delete_sold_accounts()
    await query.edit_message_text("✅ ၁၅ မိနစ်ကျော် ရောင်းပြီးသားအကောက်များကို ဖယ်ရှားပြီးပါပြီ။", reply_markup=back_button())

async def approve_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    order_id = query.data.split("_")[1]
    order = get_order(order_id)
    if not order:
        await query.edit_message_text("❌ Order မတွေ့ပါ။")
        return
    product_id = order[1]
    accounts = get_accounts_by_product(product_id)
    if not accounts:
        await query.edit_message_text(f"❌ အကောက်အတွက် Account မကျန်တော့ပါ။")
        return
    account_id, username, password = accounts[0]
    mark_account_sold(account_id, order[0])
    update_order_status(order_id, "approved")
    update_order_account(order_id, account_id)
    await context.bot.send_message(
        order[0],
        f"✅ Order {order_id} အတည်ပြုပြီးပါပြီ!\n\n"
        f"သင်၏ Account:\n👤 {username}\n🔒 {password}\n\n"
        "📌 လုံခြုံရေးအတွက် 2-Step Verification ထည့်သွင်းပါ။\n"
        "ဝယ်ယူမှုအတွက် ကျေးဇူးတင်ပါတယ်။"
    )
    await query.edit_message_text(f"✅ Order {order_id} အတည်ပြုပြီး User သို့ပို့ပြီးပါပြီ။")

async def cancel_order(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ သင့်တွင် ဤ Command ကိုသုံးခွင့်မရှိပါ။")
        return
    order_id = query.data.split("_")[1]
    order = get_order(order_id)
    if not order:
        await query.edit_message_text("❌ Order မတွေ့ပါ။")
        return
    update_order_status(order_id, "cancelled")
    await context.bot.send_message(order[0], f"❌ Order {order_id} ပယ်ဖျက်ပြီးပါပြီ။")
    await query.edit_message_text(f"❌ Order {order_id} ပယ်ဖျက်ပြီးပါပြီ။")

async def handle_admin_input(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    action = context.user_data.get("admin_action")
    if not action:
        return
    text = update.message.text
    if text == "/cancel":
        context.user_data["admin_action"] = None
        await update.message.reply_text("✅ ပယ်ဖျက်ပြီးပါပြီ။", reply_markup=back_button())
        return
    if action == "add_product":
        try:
            name, price, stock = text.split(",")
            price = int(price.strip())
            stock = int(stock.strip())
            add_product(name.strip(), price, stock)
            context.user_data["admin_action"] = None
            await update.message.reply_text(f"✅ အကောက်ထည့်ပြီးပါပြီ: {name.strip()} - {price:,} MMK (Stock: {stock})", reply_markup=back_button())
        except:
            await update.message.reply_text("❌ ပုံစံမှားနေပါသည်။ အကောက်နာမည်, ဈေးနှုန်း, အရေအတွက် ရိုက်ထည့်ပါ။", reply_markup=back_button())

def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", handle_admin_input))
    application.add_handler(CallbackQueryHandler(products, pattern="^products$"))
    application.add_handler(CallbackQueryHandler(product_detail, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(my_order, pattern="^myorder$"))
    application.add_handler(CallbackQueryHandler(contact_admin, pattern="^contact$"))
    application.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_sold, pattern="^admin_sold$"))
    application.add_handler(CallbackQueryHandler(admin_payments, pattern="^admin_payments$"))
    application.add_handler(CallbackQueryHandler(admin_add_product, pattern="^admin_add_product$"))
    application.add_handler(CallbackQueryHandler(admin_add_account, pattern="^admin_add_account$"))
    application.add_handler(CallbackQueryHandler(admin_restore_products, pattern="^admin_restore_products$"))
    application.add_handler(CallbackQueryHandler(approve_order, pattern="^approve_"))
    application.add_handler(CallbackQueryHandler(cancel_order, pattern="^cancel_"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_account_select))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_account_details))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    application.run_polling()

if __name__ == "__main__":
    main()
