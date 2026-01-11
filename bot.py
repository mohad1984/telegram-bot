import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import yfinance as yf
import pandas as pd
import numpy as np

# إعدادات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# الأسهم
STOCKS = {
    "AAPL": "Apple Inc.",
    "TSLA": "Tesla Inc.",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon"
}

# دالة البدء
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("AAPL - Apple", callback_data="stock_AAPL")],
        [InlineKeyboardButton("TSLA - Tesla", callback_data="stock_TSLA")],
        [InlineKeyboardButton("MSFT - Microsoft", callback_data="stock_MSFT")],
        [InlineKeyboardButton("NVDA - NVIDIA", callback_data="stock_NVDA")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **أهلاً! أنا بوت التحليل الفني**\n\n"
        "اختر سهم للتحليل:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# حساب RSI يدوياً
def calculate_rsi(prices, period=14):
    """حساب مؤشر RSI يدوياً"""
    if len(prices) < period + 1:
        return 50
    
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    
    if down == 0:
        return 100
    
    rs = up / down
    rsi = 100 - 100 / (1 + rs)
    
    for i in range(period+1, len(prices)):
        delta = deltas[i-1]
        
        if delta > 0:
            upval = delta
            downval = 0
        else:
            upval = 0
            downval = -delta
        
        up = (up * (period-1) + upval) / period
        down = (down * (period-1) + downval) / period
        
        if down == 0:
            rsi = np.append(rsi, 100)
        else:
            rs = up / down
            rsi = np.append(rsi, 100 - 100 / (1 + rs))
    
    return rsi[-1] if len(rsi) > 0 else 50

# تحليل سهم
async def analyze_stock(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol):
    await update.callback_query.edit_message_text(f"⏳ جاري تحليل {symbol}...")
    
    try:
        # جلب البيانات
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1mo")
        
        if hist.empty:
            await update.callback_query.edit_message_text(f"❌ لا توجد بيانات لـ {symbol}")
            return
        
        # حساب المؤشرات
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change_percent = ((current_price - prev_price) / prev_price) * 100
        
        # حساب RSI
        rsi_value = calculate_rsi(hist['Close'].values)
        
        # حساب المتوسطات
        ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else current_price
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else current_price
        
        # مستويات الدعم والمقاومة
        pivot = (hist['High'].iloc[-1] + hist['Low'].iloc[-1] + current_price) / 3
        resistance = 2 * pivot - hist['Low'].iloc[-1]
        support = 2 * pivot - hist['High'].iloc[-1]
        
        # التوصية
        if rsi_value < 30 and current_price < support:
            recommendation = "🟢 شراء قوي (تشبع بيع)"
        elif rsi_value > 70 and current_price > resistance:
            recommendation = "🔴 بيع قوي (تشبع شراء)"
        elif current_price > ma_20 and current_price > ma_50:
            recommendation = "🟢 اتجاه صعودي"
        else:
            recommendation = "🟡 انتظار"
        
        # بناء الرسالة
        message = f"📊 **{STOCKS[symbol]} ({symbol})**\n\n"
        message += f"💰 **السعر**: ${current_price:.2f}\n"
        message += f"📈 **التغير**: {change_percent:+.2f}%\n"
        message += f"📊 **RSI (14)**: {rsi_value:.1f}\n"
        message += f"📈 **المتوسط 20 يوم**: ${ma_20:.2f}\n"
        message += f"📊 **المتوسط 50 يوم**: ${ma_50:.2f}\n"
        message += f"🎯 **المقاومة**: ${resistance:.2f}\n"
        message += f"🛡️ **الدعم**: ${support:.2f}\n\n"
        message += f"💡 **التوصية**: {recommendation}\n\n"
        message += f"⏰ **آخر تحديث**: {datetime.now().strftime('%H:%M')}\n"
        message += "⚠️ *هذا تحليل آلي، استشر مختصاً*"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data=f"stock_{symbol}")],
            [InlineKeyboardButton("📋 سهم آخر", callback_data="all_stocks")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
        ]
        
        await update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"خطأ: {e}")
        await update.callback_query.edit_message_text(
            f"❌ حدث خطأ في تحليل {symbol}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
            ])
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
        await analyze_stock(update, context, symbol)

# عرض كل الأسهم
async def show_all_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for symbol, name in STOCKS.items():
        keyboard.append([InlineKeyboardButton(f"{symbol} - {name}", callback_data=f"stock_{symbol}")])
    
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")])
    
    await query.edit_message_text(
        "📋 **الأسهم المتاحة:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# المساعدة
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❓ **كيف تستخدم:**\n\n"
        "1. اختر سهم من القائمة\n"
        "2. احصل على:\n"
        "   • السعر والتغير\n"
        "   • مؤشر RSI\n"
        "   • المتوسطات المتحركة\n"
        "   • الدعم والمقاومة\n"
        "   • توصية تداول\n\n"
        "📞 للمساعدة تواصل مع المطور",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
        ])
    )

# الدالة الرئيسية
def main():
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 بدء تشغيل البوت...")
    print("✅ البوت يعمل!")
    
    app.run_polling()

if __name__ == '__main__':
    main()
