import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import configparser
from datetime import date
from database import *

# تحميل الإعدادات
config = configparser.ConfigParser()
config.read('config.ini')

BOT_TOKEN = config['BOT']['TOKEN']
CHANNEL_USERNAME = config['SETTINGS']['CHANNEL_USERNAME'].lstrip('@')
AFFILIATE_LINK = config['SETTINGS']['AFFILIATE_LINK']
PROMO_CODE = config['SETTINGS']['PROMO_CODE']
CASH_NUMBER = config['SETTINGS']['CASH_NUMBER']
ADMIN_ID = int(config['SETTINGS']['ADMIN_ID'])
MIN_WITHDRAW_POINTS = int(config['SETTINGS']['MIN_WITHDRAW_POINTS'])
DAILY_REWARD = int(config['SETTINGS']['DAILY_REWARD'])

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# التحقق من الاشتراك في القناة
def is_user_joined_channel(user_id):
    try:
        status = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# القائمة الرئيسية
def get_main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💰 أرباحي", callback_data="mypoints"),
        InlineKeyboardButton("⏰ المكافأة اليومية", callback_data="daily"),
        InlineKeyboardButton("🏷 استخدام كود البريمو", callback_data="promo"),
        InlineKeyboardButton("📤 رابط الدعوة", callback_data="invite"),
        InlineKeyboardButton("💳 السحب", callback_data="withdraw"),
        InlineKeyboardButton("❓ ما هذا البوت؟", callback_data="about")
    )
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👨‍💻 لوحة الأدمن", callback_data="admin"))
    return markup

@bot.message_handler(commands=["start"])
def handle_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not is_user_joined_channel(user_id):
        join_markup = InlineKeyboardMarkup()
        join_markup.add(InlineKeyboardButton("📢 اضغط للاشتراك", url=f"https://t.me/{CHANNEL_USERNAME}"))
        return bot.send_message(user_id, "🚫 يجب الاشتراك في القناة أولاً للمتابعة!", reply_markup=join_markup)

    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    new_user = register_user(user_id, username, referrer_id)
    if new_user and referrer_id and is_user_joined_channel(user_id):
        add_points(referrer_id, 150)
        bot.send_message(referrer_id, "🎉 لقد حصلت على 150 نقطة لإحالة صديقك!")

    points = get_points(user_id)
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, f'''
👋 <b>أهلاً بك في بوت BA7R الرسمي للربح من 1xBet</b>

🎁 <b>كود البريمو:</b> <code>{PROMO_CODE}</code>
🌐 <b>رابط التسجيل:</b> <a href="{AFFILIATE_LINK}">اضغط هنا</a>

🧾 للتواصل مع الوكيل: @MR_xvip1

💵 <b>رصيدك الحالي:</b> {points} نقطة
🔗 <b>رابط الدعوة:</b> {invite_link}
''', reply_markup=get_main_menu(user_id))

# التعامل مع الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: CallbackQuery):
    user_id = call.from_user.id

    if call.data == "mypoints":
        points = get_points(user_id)
        bot.answer_callback_query(call.id, text=f"💰 نقاطك: {points}")

    elif call.data == "daily":
        today = str(date.today())
        if not has_checked_in_today(user_id, today):
            update_daily_checkin(user_id, today)
            add_points(user_id, DAILY_REWARD)
            bot.answer_callback_query(call.id, f"✅ حصلت على {DAILY_REWARD} نقطة اليوم!")
        else:
            bot.answer_callback_query(call.id, "⛔ لقد حصلت على مكافأتك اليوم بالفعل.")

    elif call.data == "invite":
        invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
        bot.send_message(call.message.chat.id, f"""
🎯 للتسجيل استخدم هذا الرابط:
🔗 <a href="{AFFILIATE_LINK}">اضغط هنا</a>

🎁 كود البريمو: <code>{PROMO_CODE}</code>

📨 هذا هو رابط الدعوة الخاص بك:
🔗 {invite_link}
""", parse_mode="HTML", reply_markup=markup)

    elif call.data == "promo":
        if has_done_promo(user_id):
            return bot.answer_callback_query(call.id, "✅ لقد قمت بالفعل بهذه المهمة.")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
        bot.send_message(call.message.chat.id, f"""
🎯 للتسجيل استخدم هذا الرابط:
🔗 <a href="{AFFILIATE_LINK}">اضغط هنا</a>

🎁 كود البريمو: <code>{PROMO_CODE}</code>

📸 بعد التسجيل أرسل ID المستخدم + سكرين من الحساب.
""", parse_mode="HTML", reply_markup=markup)
        set_temp_state(user_id, 'awaiting_id')


    elif call.data == "withdraw":

        points = get_points(user_id)

        if points < MIN_WITHDRAW_POINTS:

            bot.send_message(call.message.chat.id, f"❌ الحد الأدنى للسحب هو {MIN_WITHDRAW_POINTS} نقطة.")

        else:

            bot.send_message(call.message.chat.id, "📩 أرسل الآن رقم فودافون كاش لاستلام الأرباح:")

            set_temp_state(user_id, "awaiting_withdraw_number")


    elif call.data == "about":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu"))
        bot.send_message(call.message.chat.id, "🤖 هذا البوت يتيح لك الربح من خلال تنفيذ المهام ودعوة الأصدقاء.", reply_markup=markup)

    elif call.data == "back_to_menu":
        bot.edit_message_text("✅ عدت للقائمة الرئيسية:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_menu(user_id))



    elif call.data == "admin" and user_id == ADMIN_ID:

        markup = InlineKeyboardMarkup(row_width=2)

        markup.add(

            InlineKeyboardButton("📥 مراجعة مهام البريمو", callback_data="review_promo"),

            InlineKeyboardButton("📤 طلبات السحب", callback_data="review_withdrawals"),

            InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user"),

            InlineKeyboardButton("🧹 تصفير نقاط", callback_data="reset_points"),

            InlineKeyboardButton("📣 رسالة جماعية", callback_data="broadcast")

        )

        bot.send_message(user_id, "👨‍💻 لوحة تحكم الأدمن:", reply_markup=markup)


    elif call.data == "search_user" and user_id == ADMIN_ID:

        bot.send_message(user_id, "🔍 أرسل ID المستخدم الآن:")

        set_temp_state(user_id, "searching_user")


    elif call.data == "review_promo" and user_id == ADMIN_ID:

        submissions = get_pending_promos()

        if not submissions:
            return bot.send_message(user_id, "✅ لا يوجد مهام معلقة حالياً.")

        for uid, id_txt, screenshot_id in submissions:
            markup = InlineKeyboardMarkup()

            markup.add(

                InlineKeyboardButton("✅ قبول", callback_data=f"approve_{uid}"),

                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}")

            )

            bot.send_photo(user_id, screenshot_id, caption=f"ID: {id_txt}\nمن: {uid}", reply_markup=markup)


    elif call.data.startswith("approve_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[1])

        approve_promo(uid)

        add_points(uid, 400)

        bot.send_message(uid, "✅ تم قبول مهمة كود البريمو وإضافة 300 نقطة.")

        bot.answer_callback_query(call.id, "✅ تم القبول.")


    elif call.data.startswith("reject_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[1])

        reject_promo(uid)

        bot.send_message(uid, "❌ تم رفض مهمة كود البريمو.")

        bot.answer_callback_query(call.id, "❌ تم الرفض.")


    elif call.data == "review_withdrawals" and user_id == ADMIN_ID:

        withdrawals = get_pending_withdrawals()

        if not withdrawals:
            return bot.send_message(user_id, "✅ لا توجد طلبات سحب معلقة.")

        for uid, number, amount in withdrawals:
            markup = InlineKeyboardMarkup()

            markup.add(

                InlineKeyboardButton("✅ تأكيد السحب", callback_data=f"confirm_withdraw_{uid}"),

                InlineKeyboardButton("❌ رفض", callback_data=f"cancel_withdraw_{uid}")

            )

            bot.send_message(user_id, f"طلب سحب من {uid}\n📲 رقم: {number}\n💰 المبلغ: {amount} نقطة",

                             reply_markup=markup)


    elif call.data.startswith("confirm_withdraw_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[2])

        confirm_withdraw(uid)

        bot.send_message(uid, "✅ تم تأكيد طلب السحب وسيتم التحويل قريباً.")

        bot.answer_callback_query(call.id, "✅ تم التأكيد.")


    elif call.data.startswith("cancel_withdraw_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[2])

        cancel_withdraw(uid)

        bot.send_message(uid, "❌ تم رفض طلب السحب.")

        bot.answer_callback_query(call.id, "❌ تم الرفض.")


    elif call.data.startswith("givepoints_") and user_id == ADMIN_ID:

        target_id = int(call.data.split("_")[1])

        bot.send_message(user_id, f"📝 أرسل عدد النقاط لإضافتها للمستخدم {target_id}")

        set_temp_state(user_id, f"add_points_to_{target_id}")


    elif call.data == "reset_points" and user_id == ADMIN_ID:

        bot.send_message(user_id, "🧹 أرسل الآن ID المستخدم لتصفير نقاطه.")

        set_temp_state(user_id, "resetting_points")


    elif call.data == "broadcast" and user_id == ADMIN_ID:

        bot.send_message(user_id, "✉️ أرسل الرسالة الآن ليتم إرسالها لجميع المستخدمين.")

        set_temp_state(user_id, "broadcasting")


    elif call.data.startswith("confirm_withdraw_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[2])

        confirm_withdraw(uid)

        bot.send_message(uid, "✅ تم تأكيد طلب السحب وسيتم التحويل قريباً.")

        bot.answer_callback_query(call.id, "✅ تم التأكيد.")


    elif call.data.startswith("cancel_withdraw_") and user_id == ADMIN_ID:

        uid = int(call.data.split("_")[2])

        cancel_withdraw(uid)

        bot.send_message(uid, "❌ تم رفض طلب السحب.")

        bot.answer_callback_query(call.id, "❌ تم الرفض.")


    elif call.data == "reset_points" and user_id == ADMIN_ID:

        bot.send_message(user_id, "🧹 أرسل الآن ID المستخدم لتصفير نقاطه.")

        set_temp_state(user_id, "resetting_points")


    elif call.data == "broadcast" and user_id == ADMIN_ID:

        bot.send_message(user_id, "✉️ أرسل الرسالة الآن ليتم إرسالها لجميع المستخدمين.")

        set_temp_state(user_id, "broadcasting")



# معالجة الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message: Message):
    temp_state = get_temp_state(message.from_user.id)
    if temp_state and temp_state.startswith("task_"):
        data = get_temp_data(message.from_user.id) or {}
        data['screenshot_id'] = message.photo[-1].file_id
        set_temp_data(message.from_user.id, data)
        bot.send_message(message.chat.id, "✅ أرسل الآن ID المستخدم.")

@bot.message_handler(func=lambda m: True)
def handle_text(message: Message):
    user_id = message.from_user.id
    temp_state = get_temp_state(user_id)

    if temp_state and temp_state.startswith("task_"):
        data = get_temp_data(user_id)
        if not data or 'screenshot_id' not in data:
            return bot.send_message(user_id, "❗ أرسل صورة للمهمة أولاً.")

        id_value = message.text.strip()
        screenshot_id = data['screenshot_id']
        task_title = data['task_title']
        points = data['points']

        save_task_submission(user_id, id_value, screenshot_id, task_title)
        clear_temp_state(user_id)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ قبول", callback_data=f"task_approve_{user_id}_{points}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"task_reject_{user_id}")
        )

        bot.send_photo(ADMIN_ID, screenshot_id,
                       caption=f"📥 مهمة جديدة\n📝 {task_title}\nID: {id_value}\nمن: {user_id}",
                       reply_markup=markup)

        bot.send_message(user_id, "✅ تم استلام المهمة، جارٍ مراجعتها من قبل الأدمن.")
    elif temp_state == "awaiting_withdraw_number":
        number = message.text.strip()
        amount = get_points(user_id)

        # حفظ طلب السحب في قاعدة البيانات
        cursor.execute("INSERT INTO withdrawals (user_id, number, amount, status) VALUES (?, ?, ?, ?)",
                       (user_id, number, amount, 'pending'))
        conn.commit()

        reset_user_points(user_id)
        clear_temp_state(user_id)

        bot.send_message(user_id, "✅ تم إرسال طلب السحب، سيتم مراجعته قريبًا من الأدمن.")

    elif temp_state == "resetting_points":
        try:
            target_id = int(message.text.strip())
            reset_user_points(target_id)
            clear_temp_state(user_id)
            bot.send_message(user_id, f"✅ تم تصفير نقاط المستخدم {target_id}.")
        except:
            bot.send_message(user_id, "❌ تأكد من كتابة ID صحيح.")
    elif temp_state == "searching_user":
            try:
                target_id = int(message.text.strip())
                points = get_points(target_id)
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (target_id,))
                row = cursor.fetchone()
                if not row:
                    return bot.send_message(user_id, "❌ المستخدم غير موجود.")
                username = row[0] or "بدون اسم"
                caption = f"<b>🔍 بيانات المستخدم:</b>\n\n🆔 ID: <code>{target_id}</code>\n👤 Username: @{username}\n💰 نقاط: {points}"
                cursor.execute("SELECT screenshot_id FROM task_submissions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                               (target_id,))
                img_row = cursor.fetchone()
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("➕ إضافة نقاط", callback_data=f"givepoints_{target_id}"))
                if img_row:
                    bot.send_photo(user_id, img_row[0], caption=caption, parse_mode="HTML", reply_markup=markup)
                else:
                    bot.send_message(user_id, caption, parse_mode="HTML", reply_markup=markup)
                clear_temp_state(user_id)
            except:
                bot.send_message(user_id, "❌ تأكد من أن ID المستخدم رقم صحيح.")

    elif temp_state and temp_state.startswith("add_points_to_"):
        try:
            target_id = int(temp_state.split("_")[-1])
            pts = int(message.text.strip())
            add_points(target_id, pts)
            clear_temp_state(user_id)
            bot.send_message(user_id, f"✅ تم إضافة {pts} نقطة للمستخدم {target_id}.")
            bot.send_message(target_id, f"💰 تم إضافة {pts} نقطة إلى حسابك من الأدمن.")
        except:
            bot.send_message(user_id, "❌ تأكد من أن الرقم صحيح.")

        clear_temp_state(user_id)

    elif temp_state == "broadcasting":
        users = get_all_users()
        for uid in users:
            try:
                bot.send_message(uid, message.text)
            except:
                continue
        clear_temp_state(user_id)
        bot.send_message(user_id, "✅ تم إرسال الرسالة الجماعية.")

    elif temp_state == "adding_task":
        try:
            title, pts = message.text.split(" - ")
            title = title.strip()
            pts = int(pts.strip())

            add_task_to_db(title, pts)
            clear_temp_state(user_id)
            bot.send_message(user_id, "✅ تم إضافة المهمة وسيتم إرسالها للمستخدمين.")

            users = get_all_users()
            for uid in users:
                try:
                    bot.send_message(
                        uid,
                        f"📢 مهمة جديدة!\n\n📝 <b>{title}</b>\n💰 النقاط: {pts}\n\n📸 بعد تنفيذ المهمة، أرسل ID الخاص بك وسكرين شوت كإثبات.",
                        parse_mode="HTML"
                    )
                    set_temp_state(uid, f"task_{title}")
                    set_temp_data(uid, {"task_title": title, "points": pts})
                except:
                    continue
        except:
            bot.send_message(user_id, "❌ صيغة غير صحيحة. اكتب: العنوان - عدد النقاط")



@bot.callback_query_handler(func=lambda call: call.data.startswith("task_approve_"))
def approve_task(call: CallbackQuery):
    try:
        parts = call.data.split("_")
        uid = int(parts[2])
        points = int(parts[3])
        add_points(uid, points)
        mark_task_as_approved(uid, get_task_title_from_callback(call.message.caption))  # دالة هنشرحها تحت
        bot.send_message(uid, f"✅ تم قبول المهمة وتمت إضافة {points} نقطة.")
        bot.answer_callback_query(call.id, "✅ تم قبول المهمة.")
    except Exception as e:
        print("❌ خطأ في تنفيذ القبول:", e)
        bot.answer_callback_query(call.id, "❌ حصل خطأ.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_reject_"))
def reject_task(call: CallbackQuery):
    try:
        parts = call.data.split("_")
        uid = int(parts[2])

        # رفض المهمة في قاعدة البيانات
        cursor.execute('''
            UPDATE task_submissions
            SET reviewed = 1, accepted = 0
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 1
        ''', (uid,))
        conn.commit()

        bot.send_message(uid, "❌ تم رفض المهمة. يمكنك المحاولة مرة أخرى إذا كان هناك خطأ.")
        bot.answer_callback_query(call.id, "❌ تم رفض المهمة.")
    except Exception as e:
        print("❌ خطأ في تنفيذ الرفض:", e)
        bot.answer_callback_query(call.id, "❌ حصل خطأ.")

# تشغيل البوت
if __name__ == "__main__":
    print("✅ Bot is running...")
    bot.infinity_polling()
