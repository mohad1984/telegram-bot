import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعدادات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# الأسهم الأمريكية الشهيرة
STOCKS = {
    "AAPL": {"name": "Apple Inc.", "emoji": "🍎"},
    "TSLA": {"name": "Tesla Inc.", "emoji": "🚗"},
    "MSFT": {"name": "Microsoft", "emoji": "💻"},
    "NVDA": {"name": "NVIDIA", "emoji": "🎮"},
    "AMZN": {"name": "Amazon", "emoji": "📦"},
    "GOOGL": {"name": "Google", "emoji": "🔍"},
    "META": {"name": "Meta (Facebook)", "emoji": "👥"},
    "SPY": {"name": "S&P 500 ETF", "emoji": "📊"}
}

# دالة البدء /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يرسل رسالة ترحيبية مع أزرار"""
    
    # إنشاء أزرار للأسهم (صفين في كل صف سهمين)
    keyboard = []
    stocks_list = list(STOCKS.items())
    
    for i in range(0, len(stocks_list), 2):
        row = []
        for j in range(2):
            if i + j < len(stocks_list):
                symbol, info = stocks_list[i + j]
                row.append(InlineKeyboardButton(
                    f"{info['emoji']} {symbol}",
                    callback_data=f"stock_{symbol}"
                ))
        keyboard.append(row)
    
    # أزرار إضافية
    keyboard.append([
        InlineKeyboardButton("📋 جميع الأسهم", callback_data="all_stocks"),
        InlineKeyboardButton("❓ المساعدة", callback_data="help")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 **مرحباً {user.first_name}!**\n\n"
        "أنا بوت التحليل المالي للسوق الأمريكي 📈\n\n"
        "**اختر سهم من القائمة:**\n"
        "أو اكتب رمز السهم مباشرة\nمثال: `/analyze AAPL`\n\n"
        "سأعطيك:\n"
        "✅ معلومات السهم الأساسية\n"
        "✅ مستويات الدعم والمقاومة\n"
        "✅ توصية مبدئية",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# دالة التحليل البسيطة
def analyze_stock(symbol):
    """تقوم بعملية تحليل بسيطة للأسهم"""
    
    # بيانات وهمية للبداية (بعدين نحولها لحقيقية)
    import random
    
    prices = {
        "AAPL": {"current": 185.25, "high": 190.50, "low": 182.75},
        "TSLA": {"current": 245.80, "high": 250.25, "low": 240.50},
        "MSFT": {"current": 375.40, "high": 380.75, "low": 370.25},
        "NVDA": {"current": 495.60, "high": 505.25, "low": 488.75},
        "AMZN": {"current": 152.30, "high": 155.75, "low": 150.25},
        "GOOGL": {"current": 142.80, "high": 145.25, "low": 140.50},
        "META": {"current": 352.90, "high": 358.75, "low": 348.25},
        "SPY": {"current": 478.50, "high": 482.25, "low": 475.75}
    }
    
    if symbol in prices:
        price_data = prices[symbol]
        
        # حساب مستويات الدعم والمقاومة (بسيطة)
        support = round(price_data["low"] * 0.99, 2)
        resistance = round(price_data["high"] * 1.01, 2)
        
        # توصية مبسطة
        current = price_data["current"]
        avg = (price_data["high"] + price_data["low"]) / 2
        
        if current < avg * 0.98:
            recommendation = "🟢 **شراء قوي** (سعر منخفض عن المتوسط)"
        elif current < avg:
            recommendation = "🟡 **شراء محتمل** (سعر معقول)"
        elif current > avg * 1.02:
            recommendation = "🔴 **انتظار** (سعر مرتفع)"
        else:
            recommendation = "⚪ **محايد** (راقب السوق)"
        
        return {
            "success": True,
            "name": STOCKS[symbol]["name"],
            "symbol": symbol,
            "current": f"${price_data['current']}",
            "high": f"${price_data['high']}",
            "low": f"${price_data['low']}",
            "support": f"${support}",
            "resistance": f"${resistance}",
            "recommendation": recommendation,
            "change": f"+{random.uniform(0.5, 3.2):.2f}%" if random.random() > 0.4 else f"-{random.uniform(0.3, 2.1):.2f}%"
        }
    
    return {"success": False}

# عرض تحليل السهم
async def show_stock_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol=None):
    """يعرض تحليل السهم"""
    
    query = update.callback_query
    
    if query:
        await query.answer()
        user_message = query.edit_message_text
        symbol = symbol or query.data.replace("stock_", "")
    else:
        user_message = update.message.reply_text
        symbol = symbol or (context.args[0] if context.args else None)
    
    if not symbol:
        await user_message("⚠️ **يرجى إدخال رمز السهم**\nمثال: `/analyze AAPL`")
        return
    
    symbol = symbol.upper()
    
    # إظهار رسالة الانتظار
    if query:
        await query.edit_message_text(f"⏳ **جاري تحليل {symbol}...**")
    else:
        await update.message.reply_text(f"⏳ **جاري تحليل {symbol}...**")
    
    # الحصول على التحليل
    analysis = analyze_stock(symbol)
    
    if not analysis["success"]:
        keyboard = [[InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await (query.edit_message_text if query else update.message.reply_text)(
            f"❌ **لم أجد بيانات لـ {symbol}**\n\n"
            f"**الرموز المتاحة:**\n" + 
            "\n".join([f"• {s} - {STOCKS[s]['name']}" for s in STOCKS]),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # بناء رسالة التحليل
    message = f"📊 **{analysis['name']} ({symbol})**\n\n"
    message += f"💰 **السعر الحالي:** {analysis['current']}\n"
    message += f"📈 **التغير:** {analysis['change']}\n"
    message += f"🔺 **أعلى سعر:** {analysis['high']}\n"
    message += f"🔻 **أدنى سعر:** {analysis['low']}\n"
    message += f"🛡️ **الدعم القوي:** {analysis['support']}\n"
    message += f"🎯 **المقاومة القوية:** {analysis['resistance']}\n\n"
    message += f"💡 **التوصية:** {analysis['recommendation']}\n\n"
    message += "---\n"
    message += "📌 *ملاحظة: هذه بيانات أولية للاختبار*\n"
    message += "*البيانات الحقيقية قريباً إن شاء الله*"
    
    # أزرار التحكم
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث البيانات", callback_data=f"stock_{symbol}")],
        [InlineKeyboardButton("📋 سهم آخر", callback_data="all_stocks")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# عرض جميع الأسهم
async def show_all_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض قائمة بجميع الأسهم"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for symbol, info in STOCKS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{info['emoji']} {symbol} - {info['name']}",
                callback_data=f"stock_{symbol}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 **جميع الأسهم المتاحة:**\n\n"
        "اختر سهم للتحليل:",
        reply_markup=reply_markup
    )

# دالة المساعدة
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض رسالة المساعدة"""
    
    query = update.callback_query if update.callback_query else None
    
    help_text = (
        "❓ **كيفية استخدام البوت:**\n\n"
        "1. **ابدأ بالأمر** `/start`\n"
        "2. **اختر سهم** من القائمة\n"
        "3. **احصل على** التحليل الفوري\n\n"
        "🔍 **الأوامر المتاحة:**\n"
        "• `/start` - بدء البوت\n"
        "• `/analyze [رمز]` - تحليل سهم\n"
        "• `/help` - هذه الرسالة\n\n"
        "💡 **مثال:**\n"
        "`/analyze AAPL` لتحليل Apple\n\n"
        "📞 **الدعم:**\n"
        "لأي استفسار، راسل المطور"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع ضغطات الأزرار"""
    query = update.callback_query
    data = query.data
    
    if data == "main_menu":
        await start_command(update, context)
    elif data == "all_stocks":
        await show_all_stocks(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data.startswith("stock_"):
        await show_stock_analysis(update, context)
    else:
        await query.answer("⚠️ زر غير معروف")

# أمر تحليل مباشر
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع أمر /analyze"""
    await show_stock_analysis(update, context)

# دالة لمعالجة الرسائل النصية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع الرسائل النصية"""
    text = update.message.text.upper().strip()
    
    # إذا كان النص يشبه رمز سهم
    if text in STOCKS or (len(text) <= 5 and text.isalpha()):
        await show_stock_analysis(update, context, text)
    else:
        await update.message.reply_text(
            "🤔 **لم أفهم طلبك**\n\n"
            "جرب أحد الخيارات:\n"
            "• استخدم `/start` للقائمة\n"
            "• أو اكتب رمز سهم (مثل: AAPL)\n"
            "• أو استخدم `/help` للمساعدة",
            parse_mode='Markdown'
        )

# معالجة الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "⚠️ **حدث خطأ غير متوقع**\n"
            "يرجى المحاولة مرة أخرى لاحقاً."
        )

# الدالة الرئيسية
def main():
    """بدء تشغيل البوت"""
    
    # الحصول على التوكن من متغير البيئة
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ **BOT_TOKEN غير موجود!**")
        print("=" * 50)
        print("⚠️  خطأ: يجب إضافة متغير البيئة BOT_TOKEN")
        print("=" * 50)
        print("\n📋 **خطوات الحل:**")
        print("1. احصل على توكن من @BotFather")
        print("2. على Render: Environment → Add Environment Variable")
        print("3. Key: BOT_TOKEN")
        print("4. Value: التوكن الخاص بك")
        print("=" * 50)
        return
    
    try:
        # إنشاء التطبيق
        app = Application.builder().token(TOKEN).build()
        
        # إضافة handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("analyze", analyze_command))
        app.add_handler(CommandHandler("help", help_command))
        
        # معالجة الأزرار
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # معالجة الرسائل النصية
        from telegram.ext import MessageHandler, filters
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # معالجة الأخطاء
        app.add_error_handler(error_handler)
        
        logger.info("🚀 **بدء تشغيل البوت...**")
        print("=" * 50)
        print("✅ **البوت يعمل بنجاح!**")
        print("=" * 50)
        print("\n📱 **كيفية الاستخدام:**")
        print("1. ابحث عن البوت في تلجرام")
        print("2. أرسل /start")
        print("3. اختر سهم للتحليل")
        print("=" * 50)
        
        # بدء الاستماع للرسائل
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ **فشل تشغيل البوت:** {e}")
        print(f"\n❌ **الخطأ:** {e}")

# تشغيل البوت
if __name__ == '__main__':
    main()
