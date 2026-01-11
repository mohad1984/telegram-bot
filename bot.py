import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعدادات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# الأسهم المتاحة
STOCKS = {
    "AAPL": {"name": "Apple Inc.", "emoji": "🍎"},
    "TSLA": {"name": "Tesla Inc.", "emoji": "🚗"},
    "MSFT": {"name": "Microsoft", "emoji": "💻"},
    "NVDA": {"name": "NVIDIA", "emoji": "🎮"},
    "AMZN": {"name": "Amazon", "emoji": "📦"},
    "GOOGL": {"name": "Google", "emoji": "🔍"},
    "META": {"name": "Meta", "emoji": "👤"},
    "SPY": {"name": "S&P 500 ETF", "emoji": "📊"},
    "QQQ": {"name": "NASDAQ ETF", "emoji": "💹"}
}

# دالة البدء
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(f"{STOCKS['AAPL']['emoji']} AAPL", callback_data="stock_AAPL"),
            InlineKeyboardButton(f"{STOCKS['TSLA']['emoji']} TSLA", callback_data="stock_TSLA")
        ],
        [
            InlineKeyboardButton(f"{STOCKS['MSFT']['emoji']} MSFT", callback_data="stock_MSFT"),
            InlineKeyboardButton(f"{STOCKS['NVDA']['emoji']} NVDA", callback_data="stock_NVDA")
        ],
        [
            InlineKeyboardButton(f"{STOCKS['AMZN']['emoji']} AMZN", callback_data="stock_AMZN"),
            InlineKeyboardButton(f"{STOCKS['GOOGL']['emoji']} GOOGL", callback_data="stock_GOOGL")
        ],
        [
            InlineKeyboardButton("📋 كل الأسهم", callback_data="all_stocks"),
            InlineKeyboardButton("❓ المساعدة", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **أهلاً! أنا بوت التحليل المالي**\n\n"
        f"⏰ الوقت: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
        "**اختر سهم للتحليل:**\n"
        "أو اكتب مباشرة: /price AAPL",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# الحصول على بيانات السهم الحقيقية
def get_real_stock_data(symbol):
    try:
        import yfinance as yf
        
        # جلب البيانات
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # إذا ما في بيانات، استخدم تاريخ اليوم
        hist = stock.history(period="1d")
        
        if hist.empty:
            # جلب بيانات اليوم من معلومات السهم
            current_price = info.get('currentPrice', 
                          info.get('regularMarketPrice', 
                          info.get('previousClose', 0)))
            
            day_high = info.get('dayHigh', current_price * 1.02)
            day_low = info.get('dayLow', current_price * 0.98)
            prev_close = info.get('previousClose', current_price)
        else:
            # استخدام البيانات التاريخية
            current_price = hist['Close'].iloc[-1]
            day_high = hist['High'].max()
            day_low = hist['Low'].min()
            prev_close = hist['Close'].iloc[0] if len(hist) > 1 else current_price
        
        # حساب التغير
        change_percent = 0
        if prev_close and prev_close > 0:
            change_percent = ((current_price - prev_close) / prev_close) * 100
        
        # حساب مستويات الدعم والمقاومة (بسيطة)
        pivot = (day_high + day_low + current_price) / 3
        resistance1 = 2 * pivot - day_low
        support1 = 2 * pivot - day_high
        
        # التوصية المبسطة
        if change_percent > 1:
            recommendation = "🟢 اتجاه صعودي"
            action = "شراء على الدعم"
        elif change_percent < -1:
            recommendation = "🔴 اتجاه هبوطي"
            action = "انتظار أو بيع"
        else:
            recommendation = "🟡 سوق جانبي"
            action = "انتظار اختراق"
        
        return {
            "success": True,
            "name": info.get('longName', STOCKS.get(symbol, {}).get('name', symbol)),
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "day_high": round(day_high, 2),
            "day_low": round(day_low, 2),
            "change_percent": round(change_percent, 2),
            "resistance": round(resistance1, 2),
            "support": round(support1, 2),
            "recommendation": recommendation,
            "action": action,
            "volume": info.get('volume', 0),
            "market_cap": info.get('marketCap', 0)
        }
        
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات {symbol}: {e}")
        return {
            "success": False,
            "error": str(e),
            "name": STOCKS.get(symbol, {}).get('name', symbol),
            "symbol": symbol,
            "current_price": 0,
            "day_high": 0,
            "day_low": 0,
            "change_percent": 0,
            "resistance": 0,
            "support": 0,
            "recommendation": "⚠️ خطأ في البيانات",
            "action": "حاول لاحقاً"
        }

# عرض تحليل السهم
async def show_stock_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(f"⏳ جاري تحليل {symbol}...")
    
    # جلب البيانات الحقيقية
    data = get_real_stock_data(symbol)
    
    if not data["success"]:
        # بيانات وهمية إذا فشل الاتصال (للطوارئ)
        emergency_data = {
            "AAPL": {"price": 259.37, "change": 0.13},
            "TSLA": {"price": 245.18, "change": -0.8},
            "MSFT": {"price": 402.65, "change": 2.1},
            "NVDA": {"price": 603.31, "change": 3.5},
            "AMZN": {"price": 156.87, "change": 0.9},
            "GOOGL": {"price": 143.25, "change": 1.2},
            "META": {"price": 368.45, "change": 1.8},
            "SPY": {"price": 478.32, "change": 0.5},
            "QQQ": {"price": 426.78, "change": 0.7}
        }
        
        if symbol in emergency_data:
            em_data = emergency_data[symbol]
            data = {
                "success": True,
                "name": STOCKS.get(symbol, {}).get('name', symbol),
                "symbol": symbol,
                "current_price": em_data["price"],
                "day_high": em_data["price"] * 1.01,
                "day_low": em_data["price"] * 0.99,
                "change_percent": em_data["change"],
                "resistance": em_data["price"] * 1.02,
                "support": em_data["price"] * 0.98,
                "recommendation": "⚠️ بيانات تجريبية",
                "action": "الاتصال بالإنترنت للبيانات الحية"
            }
    
    # بناء الرسالة
    change_emoji = "📈" if data["change_percent"] >= 0 else "📉"
    change_sign = "+" if data["change_percent"] >= 0 else ""
    
    message = f"📊 **{data['name']} ({symbol})**\n\n"
    message += f"{STOCKS.get(symbol, {}).get('emoji', '💰')} **السعر الحالي**: ${data['current_price']:,.2f}\n"
    message += f"{change_emoji} **التغير**: {change_sign}{data['change_percent']}%\n"
    message += f"📈 **أعلى اليوم**: ${data['day_high']:,.2f}\n"
    message += f"📉 **أدنى اليوم**: ${data['day_low']:,.2f}\n"
    message += f"🎯 **المقاومة (R1)**: ${data['resistance']:,.2f}\n"
    message += f"🛡️ **الدعم (S1)**: ${data['support']:,.2f}\n\n"
    
    message += f"💡 **التوصية**: {data['recommendation']}\n"
    message += f"📌 **الإجراء**: {data['action']}\n\n"
    
    # معلومات إضافية
    if data.get('volume', 0) > 0:
        vol_m = data['volume'] / 1_000_000
        message += f"📊 **الحجم**: {vol_m:.1f}M سهم\n"
    
    if data.get('market_cap', 0) > 0:
        market_cap_b = data['market_cap'] / 1_000_000_000
        message += f"🏢 **القيمة السوقية**: {market_cap_b:.1f}B\n"
    
    message += f"\n⏰ **آخر تحديث**: {datetime.now().strftime('%H:%M')}\n"
    message += "🔍 *للبيانات الحية، تأكد من اتصال الخادم بالإنترنت*"
    
    # بناء الأزرار
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث البيانات", callback_data=f"stock_{symbol}")],
        [InlineKeyboardButton("📋 سهم آخر", callback_data="all_stocks")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    
    if query:
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# عرض كل الأسهم
async def show_all_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")])
    
    await query.edit_message_text(
        "📋 **جميع الأسهم المتاحة:**\n\n"
        "اختر سهم للحصول على تحليل فوري:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await start_command(update, context)
    elif query.data == "all_stocks":
        await show_all_stocks(update, context)
    elif query.data == "help":
        await help_command(update, context)
    elif query.data.startswith("stock_"):
        symbol = query.data.replace("stock_", "")
        await show_stock_analysis(update, context, symbol)

# دالة المساعدة
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❓ **كيف تستخدم البوت:**\n\n"
            "1. **ابدأ بـ** /start\n"
            "2. **اختر سهم** من القائمة\n"
            "3. **احصل على:**\n"
            "   • السعر الحالي\n"
            "   • أعلى/أدنى اليوم\n"
            "   • مستويات الدعم والمقاومة\n"
            "   • توصية تداول\n\n"
            "💡 **أوامر مباشرة:**\n"
            "• /price AAPL - سعر AAPL\n"
            "• /start - القائمة الرئيسية\n"
            "• /help - هذه الرسالة\n\n"
            "⚠️ **ملاحظة:**\n"
            "• البيانات تتأخر 15-20 دقيقة\n"
            "• التوصيات للتعليم فقط\n"
            "• استشر مختصاً قبل الاستثمار\n\n"
            "🔄 **لأحدث البيانات:**\n"
            "اضغط 'تحديث البيانات'",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
            ])
        )
    else:
        await update.message.reply_text("استخدم /start للبدء")

# تحليل مباشر بالأمر
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ **اكتب رمز السهم**\nمثال: `/price AAPL`\n\n"
            "الرموز الشائعة:\n"
            "AAPL, TSLA, MSFT, NVDA, AMZN",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper().strip()
    
    if symbol not in STOCKS and len(symbol) <= 5:
        # إذا الرمز جديد، نضيفه مؤقتاً
        STOCKS[symbol] = {"name": symbol, "emoji": "💰"}
    
    await show_stock_analysis(update, context, symbol)

# الدالة الرئيسية
def main():
    # الحصول على التوكن من متغير البيئة
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        print("=" * 50)
        print("خطأ: يجب إضافة BOT_TOKEN في Environment Variables")
        print("على Render: Environment > Add Variable")
        print("Key: BOT_TOKEN")
        print("Value: توكن_البوت_من_@BotFather")
        print("=" * 50)
        return
    
    try:
        # إنشاء التطبيق
        app = Application.builder().token(TOKEN).build()
        
        # إضافة الأوامر
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("price", price_command))
        
        # معالجة الأزرار
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # بدء التشغيل
        logger.info("🚀 بدء تشغيل البوت...")
        print("=" * 50)
        print("✅ البوت يعمل بنجاح!")
        print(f"⏰ وقت البدء: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📊 الأسهم المتاحة: {', '.join(STOCKS.keys())}")
        print("💡 ابدأ بتلجرام: /start")
        print("=" * 50)
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ فشل تشغيل البوت: {e}")
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    main()
