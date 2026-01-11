import os
import logging
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import yfinance as yf
import pandas as pd
import numpy as np
import talib

# إعدادات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# الأسهم المتاحة
STOCKS = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "TSLA": {"name": "Tesla Inc.", "sector": "Automotive"},
    "MSFT": {"name": "Microsoft", "sector": "Technology"},
    "NVDA": {"name": "NVIDIA", "sector": "Semiconductors"},
    "AMZN": {"name": "Amazon", "sector": "E-commerce"},
    "GOOGL": {"name": "Google", "sector": "Technology"},
    "META": {"name": "Meta", "sector": "Technology"},
    "SPY": {"name": "S&P 500 ETF", "sector": "ETF"},
    "QQQ": {"name": "NASDAQ ETF", "sector": "ETF"}
}

# فريمات التحليل
TIMEFRAMES = {
    "15m": {"name": "15 دقيقة", "period": "5d", "interval": "15m"},
    "30m": {"name": "30 دقيقة", "period": "10d", "interval": "30m"},
    "1h": {"name": "1 ساعة", "period": "30d", "interval": "1h"},
    "4h": {"name": "4 ساعات", "period": "60d", "interval": "4h"},
    "1d": {"name": "يومي", "period": "6mo", "interval": "1d"}
}

# دالة البدء
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🍎 AAPL", callback_data="stock_AAPL"),
            InlineKeyboardButton("🚗 TSLA", callback_data="stock_TSLA"),
            InlineKeyboardButton("💻 MSFT", callback_data="stock_MSFT")
        ],
        [
            InlineKeyboardButton("🎮 NVDA", callback_data="stock_NVDA"),
            InlineKeyboardButton("📦 AMZN", callback_data="stock_AMZN"),
            InlineKeyboardButton("🔍 GOOGL", callback_data="stock_GOOGL")
        ],
        [
            InlineKeyboardButton("📊 كل الأسهم", callback_data="all_stocks"),
            InlineKeyboardButton("🎯 تحليل متقدم", callback_data="advanced_menu")
        ],
        [
            InlineKeyboardButton("📚 المدارس الفنية", callback_data="schools_menu"),
            InlineKeyboardButton("❓ المساعدة", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **بوت التحليل الفني المتقدم**\n\n"
        f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"⏰ الوقت: {datetime.now().strftime('%H:%M')}\n\n"
        "**اختر سهم للتحليل:**\n"
        "أو استخدم /analyze لتحليل متقدم",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ==================== الجزء 1: جلب البيانات ====================
def get_stock_data(symbol, timeframe="1d"):
    """جلب بيانات السهم لفريم معين"""
    try:
        timeframe_info = TIMEFRAMES.get(timeframe, TIMEFRAMES["1d"])
        
        stock = yf.Ticker(symbol)
        df = stock.history(
            period=timeframe_info["period"],
            interval=timeframe_info["interval"]
        )
        
        if df.empty:
            return None
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "data": df,
            "current_price": df['Close'].iloc[-1],
            "high": df['High'].max(),
            "low": df['Low'].min(),
            "volume": df['Volume'].sum()
        }
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات {symbol}: {e}")
        return {"success": False, "error": str(e)}

# ==================== الجزء 2: موجات إليوت ====================
def analyze_elliott_waves(df):
    """تحليل موجات إليوت"""
    closes = df['Close'].values
    
    # خوارزمية مبسطة للكشف عن الموجات
    waves = []
    
    # البحث عن القمم والقيعان
    from scipy.signal import argrelextrema
    
    if len(closes) > 20:
        maxima = argrelextrema(closes, np.greater, order=5)[0]
        minima = argrelextrema(closes, np.less, order=5)[0]
        
        # تحديد الموجات
        wave_count = min(5, len(maxima) + len(minima))
        
        for i in range(wave_count):
            if i % 2 == 0:  # موجات دافعة (1, 3, 5)
                if i//2 < len(maxima):
                    waves.append({
                        "type": "دفع",
                        "number": i + 1,
                        "price": closes[maxima[i//2]],
                        "position": maxima[i//2]
                    })
            else:  # موجات تصحيحية (2, 4)
                if i//2 < len(minima):
                    waves.append({
                        "type": "تصحيح",
                        "number": i + 1,
                        "price": closes[minima[i//2]],
                        "position": minima[i//2]
                    })
    
    # حساب أهداف الموجات
    targets = {}
    if len(waves) >= 3:
        # هدف الموجة 3 (عادة 1.618 من الموجة 1)
        if len(waves) >= 1:
            wave1_length = abs(waves[0]["price"] - closes[0])
            targets["wave3"] = waves[0]["price"] + wave1_length * 1.618
        
        # هدف الموجة 5 (عادة مساوية للموجة 1 أو 0.618 من الموجة 1-3)
        if len(waves) >= 3:
            wave13_length = abs(waves[2]["price"] - waves[0]["price"])
            targets["wave5"] = waves[2]["price"] + wave13_length * 0.618
    
    return {
        "waves": waves[:5],  # أول 5 موجات فقط
        "targets": targets,
        "current_wave": len(waves) if waves else 0,
        "pattern": "دفع" if len(waves) % 2 == 1 else "تصحيح"
    }

# ==================== الجزء 3: التحليل الكلاسيكي ====================
def analyze_classical(df):
    """تحليل كلاسيكي (دعم/مقاومة، نماذج سعرية)"""
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    # مستويات الدعم والمقاومة
    pivot = (df['High'].iloc[-1] + df['Low'].iloc[-1] + df['Close'].iloc[-1]) / 3
    
    resistance_levels = [
        {"level": 2 * pivot - df['Low'].iloc[-1], "strength": "قوي"},
        {"level": pivot + (df['High'].iloc[-1] - df['Low'].iloc[-1]), "strength": "متوسط"},
        {"level": df['High'].max(), "strength": "تاريخي"}
    ]
    
    support_levels = [
        {"level": 2 * pivot - df['High'].iloc[-1], "strength": "قوي"},
        {"level": pivot - (df['High'].iloc[-1] - df['Low'].iloc[-1]), "strength": "متوسط"},
        {"level": df['Low'].min(), "strength": "تاريخي"}
    ]
    
    # الكشف عن النماذج السعرية
    patterns = []
    
    # رأس وأكتاف
    if len(closes) > 100:
        # كشف مبسط للنماذج
        middle = len(closes) // 2
        left_shoulder = closes[middle-30:middle-10].max()
        head = closes[middle-10:middle+10].max()
        right_shoulder = closes[middle+10:middle+30].max()
        
        if head > left_shoulder and head > right_shoulder:
            patterns.append("رأس وأكتاف")
    
    # أعلام ومثلثات
    if len(closes) > 20:
        recent_high = closes[-20:].max()
        recent_low = closes[-20:].min()
        range_ratio = (recent_high - recent_low) / recent_low
        
        if range_ratio < 0.05:  # نطاق ضيق
            patterns.append("مثلث متماثل")
        elif closes[-1] > closes[-20]:  # اتجاه صعودي
            patterns.append("علم صعودي")
    
    return {
        "pivot": pivot,
        "resistance_levels": resistance_levels,
        "support_levels": support_levels,
        "patterns": patterns,
        "trend": "صعودي" if closes[-1] > closes[-20] else "هبوطي"
    }

# ==================== الجزء 4: مدرسة ICT ====================
def analyze_ict(df):
    """تحليل مدرسة ICT (السيولة، FVG، Order Blocks)"""
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    
    # Fair Value Gaps (FVG)
    fvg_levels = []
    for i in range(2, len(df)):
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:  # صعودي
            fvg_levels.append({
                "type": "FVG صعودي",
                "zone": [df['High'].iloc[i-2], df['Low'].iloc[i]],
                "strength": "متوسط"
            })
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:  # هبوطي
            fvg_levels.append({
                "type": "FVG هبوطي",
                "zone": [df['High'].iloc[i], df['Low'].iloc[i-2]],
                "strength": "متوسط"
            })
    
    # Order Blocks
    order_blocks = []
    for i in range(1, len(df)-1):
        # كتل شرائية (سعر أغلق عند أعلى النطاق)
        if df['Close'].iloc[i] > df['Close'].iloc[i-1] and df['Close'].iloc[i] > df['Open'].iloc[i]:
            order_blocks.append({
                "type": "Order Block شرائي",
                "price": df['Close'].iloc[i],
                "strength": "قوي" if df['Volume'].iloc[i] > df['Volume'].iloc[i-1:i+2].mean() else "ضعيف"
            })
        # كتل بيعية (سعر أغلق عند أدنى النطاق)
        elif df['Close'].iloc[i] < df['Close'].iloc[i-1] and df['Close'].iloc[i] < df['Open'].iloc[i]:
            order_blocks.append({
                "type": "Order Block بيعي",
                "price": df['Close'].iloc[i],
                "strength": "قوي" if df['Volume'].iloc[i] > df['Volume'].iloc[i-1:i+2].mean() else "ضعيف"
            })
    
    # مستويات السيولة
    liquidity_levels = []
    recent_lows = lows[-20:]
    recent_highs = highs[-20:]
    
    # Stop Hunts المحتملة
    if len(recent_lows) > 0:
        liquidity_levels.append({
            "type": "Liquidity Pool بيعي",
            "level": min(recent_lows),
            "description": "مستوى وقف الخسارة للمشترين"
        })
    
    if len(recent_highs) > 0:
        liquidity_levels.append({
            "type": "Liquidity Pool شرائي",
            "level": max(recent_highs),
            "description": "مستوى وقف الخسارة للبائعين"
        })
    
    return {
        "fvg_levels": fvg_levels[-3:],  # آخر 3 FVG
        "order_blocks": order_blocks[-5:],  # آخر 5 Order Blocks
        "liquidity_levels": liquidity_levels,
        "market_structure": "صعودي" if closes[-1] > closes[-50] else "هبوطي" if closes[-1] < closes[-50] else "جانبي"
    }

# ==================== الجزء 5: التحليل التوافقي ====================
def analyze_harmonic(df):
    """تحليل النماذج التوافقية"""
    closes = df['Close'].values
    
    patterns = []
    
    # نسب فيبوناتشي للأنماط التوافقية
    fib_ratios = {
        "باترفلاي": [0.786, 0.886, 1.27, 1.618],
        "غارتلي": [0.618, 0.786, 1.27, 1.618],
        "بات": [0.382, 0.886, 1.13, 1.618],
        "كراب": [0.382, 0.618, 1.27, 1.618],
        "شارك": [0.886, 1.13, 1.27, 1.618]
    }
    
    # كشف مبسط للأنماط
    if len(closes) > 100:
        # تقسيم البيانات لموجات
        segments = []
        for i in range(0, len(closes)-20, 20):
            segment = closes[i:i+20]
            segments.append({
                "start": i,
                "end": i+20,
                "high": max(segment),
                "low": min(segment),
                "direction": "up" if segment[-1] > segment[0] else "down"
            })
        
        # البحث عن أنماط
        for i in range(len(segments)-3):
            X = segments[i]
            A = segments[i+1]
            B = segments[i+2]
            C = segments[i+3]
            
            # حساب نسب الموجات
            XA = abs(A["high"] - X["low"]) if A["direction"] == "up" else abs(A["low"] - X["high"])
            AB = abs(B["high"] - A["low"]) if B["direction"] == "down" else abs(B["low"] - A["high"])
            BC = abs(C["high"] - B["low"]) if C["direction"] == "up" else abs(C["low"] - B["high"])
            
            if XA > 0 and AB > 0 and BC > 0:
                AB_XA = AB / XA
                BC_AB = BC / AB
                
                # باترفلاي
                if 0.78 <= AB_XA <= 0.79 and 1.27 <= BC_AB <= 1.28:
                    patterns.append({
                        "name": "باترفلاي",
                        "completion": C["end"],
                        "target": C["high"] * 1.27 if C["direction"] == "up" else C["low"] * 0.786,
                        "direction": "بيع" if C["direction"] == "up" else "شراء"
                    })
                
                # غارتلي
                if 0.61 <= AB_XA <= 0.62 and 1.27 <= BC_AB <= 1.28:
                    patterns.append({
                        "name": "غارتلي",
                        "completion": C["end"],
                        "target": C["high"] * 1.13 if C["direction"] == "up" else C["low"] * 0.886,
                        "direction": "بيع" if C["direction"] == "up" else "شراء"
                    })
    
    return {
        "patterns": patterns,
        "active_patterns": [p for p in patterns if len(closes) - p["completion"] < 20]
    }

# ==================== الجزء 6: التحليل الشامل ====================
async def comprehensive_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol, timeframe="1d"):
    """تحليل شامل لكل المدارس"""
    await update.callback_query.edit_message_text(
        f"📊 جاري التحليل الشامل لـ {symbol} ({TIMEFRAMES[timeframe]['name']})..."
    )
    
    # جلب البيانات
    stock_data = get_stock_data(symbol, timeframe)
    
    if not stock_data or not stock_data["success"]:
        await update.callback_query.edit_message_text(
            f"❌ تعذر تحليل {symbol}\nقد يكون السوق مغلقاً",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
            ])
        )
        return
    
    df = stock_data["data"]
    
    # إجراء جميع التحليلات
    elliott = analyze_elliott_waves(df)
    classical = analyze_classical(df)
    ict = analyze_ict(df)
    harmonic = analyze_harmonic(df)
    
    # بناء الرسالة
    message = f"📈 **التحليل الشامل لـ {STOCKS[symbol]['name']} ({symbol})**\n"
    message += f"⏰ **الفريم**: {TIMEFRAMES[timeframe]['name']}\n"
    message += f"💰 **السعر الحالي**: ${stock_data['current_price']:.2f}\n"
    message += f"📅 **البيانات من**: {df.index[0].strftime('%Y-%m-%d')} إلى {df.index[-1].strftime('%Y-%m-%d')}\n\n"
    
    # === موجات إليوت ===
    message += "🌊 **موجات إليوت:**\n"
    if elliott["waves"]:
        for wave in elliott["waves"]:
            message += f"• الموجة {wave['number']} ({wave['type']}): ${wave['price']:.2f}\n"
        
        if elliott["targets"].get("wave5"):
            message += f"🎯 **هدف الموجة 5**: ${elliott['targets']['wave5']:.2f}\n"
    else:
        message += "• لم يتم اكتشاف موجات واضحة\n"
    
    # === التحليل الكلاسيكي ===
    message += "\n🏛️ **التحليل الكلاسيكي:**\n"
    message += f"• **الاتجاه**: {classical['trend']}\n"
    message += f"• **المحور**: ${classical['pivot']:.2f}\n"
    
    if classical["patterns"]:
        message += f"• **النماذج**: {', '.join(classical['patterns'])}\n"
    
    message += f"• **المقاومة القوية**: ${classical['resistance_levels'][0]['level']:.2f}\n"
    message += f"• **الدعم القوي**: ${classical['support_levels'][0]['level']:.2f}\n"
    
    # === مدرسة ICT ===
    message += "\n🎯 **مدرسة ICT:**\n"
    message += f"• **هيكل السوق**: {ict['market_structure']}\n"
    
    if ict["liquidity_levels"]:
        for liq in ict["liquidity_levels"]:
            message += f"• {liq['type']}: ${liq['level']:.2f}\n"
    
    if ict["order_blocks"]:
        latest_ob = ict["order_blocks"][-1]
        message += f"• أحدث Order Block: {latest_ob['type']} عند ${latest_ob['price']:.2f}\n"
    
    # === التحليل التوافقي ===
    message += "\n🎵 **التحليل التوافقي:**\n"
    if harmonic["active_patterns"]:
        for pattern in harmonic["active_patterns"][:2]:  # عرض أول نموذجين فقط
            message += f"• **{pattern['name']}** ({pattern['direction']})\n"
            message += f"  الهدف: ${pattern['target']:.2f}\n"
    else:
        message += "• لا توجد أنماط توافقية نشطة\n"
    
    # === التوصية الشاملة ===
    message += "\n🎯 **التوصية الشاملة:**\n"
    
    # نظام تسجيل النقاط
    score = 0
    max_score = 10
    
    # موجات إليوت (3 نقاط)
    if elliott["waves"]:
        if elliott["pattern"] == "دفع":
            score += 2
        else:
            score += 1
    
    # التحليل الكلاسيكي (3 نقاط)
    if classical["trend"] == "صعودي":
        score += 2
    else:
        score += 1
    
    # ICT (2 نقطة)
    if ict["market_structure"] == "صعودي":
        score += 1
    
    if ict["order_blocks"] and ict["order_blocks"][-1]["type"] == "Order Block شرائي":
        score += 1
    
    # التوافقي (2 نقطة)
    if harmonic["active_patterns"]:
        for pattern in harmonic["active_patterns"]:
            if pattern["direction"] == "شراء":
                score += 1
                break
    
    # قرار التوصية
    percentage = (score / max_score) * 100
    
    if percentage >= 70:
        recommendation = "🟢 **شراء قوي**"
        action = "الدخول عند الدعم مع وقف تحت الدعم القوي"
    elif percentage >= 50:
        recommendation = "🟡 **شراء معتدل**"
        action = "الدخول على دفعات مع إدارة مخاطر محكمة"
    elif percentage >= 30:
        recommendation = "🟠 **انتظار**"
        action = "انتظار تأكيدات إضافية أو اختراق مستوى حاسم"
    else:
        recommendation = "🔴 **تجنب/بيع**"
        action = "الخروج من الصفقات أو البحث عن فرص بيعية"
    
    message += f"{recommendation}\n"
    message += f"📊 **درجة الثقة**: {percentage:.0f}%\n"
    message += f"📌 **الإجراء**: {action}\n\n"
    
    message += f"⏰ **وقت التحليل**: {datetime.now().strftime('%H:%M:%S')}\n"
    message += "⚠️ *هذا تحليل آلي، ليس نصيحة استثمارية*"
    message += "🔍 *استشر مختصاً قبل أي قرار استثماري*"
    
    # بناء لوحة الأزرار للفريمات
    timeframe_buttons = []
    for tf_key, tf_info in TIMEFRAMES.items():
        timeframe_buttons.append(
            InlineKeyboardButton(
                tf_info["name"],
                callback_data=f"comprehensive_{symbol}_{tf_key}"
            )
        )
    
    keyboard = [
        timeframe_buttons[:3],  # أول 3 فريمات
        timeframe_buttons[3:],  # باقي الفريمات
        [
            InlineKeyboardButton("📈 موجات إليوت", callback_data=f"elliott_{symbol}_{timeframe}"),
            InlineKeyboardButton("🏛️ كلاسيكي", callback_data=f"classical_{symbol}_{timeframe}")
        ],
        [
            InlineKeyboardButton("🎯 ICT", callback_data=f"ict_{symbol}_{timeframe}"),
            InlineKeyboardButton("🎵 توافقي", callback_data=f"harmonic_{symbol}_{timeframe}")
        ],
        [
            InlineKeyboardButton("📋 سهم آخر", callback_data="all_stocks"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        ]
    ]
    
    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== الجزء 7: معالجة الأوامر ====================
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر التحليل المباشر"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ **استخدم:** `/analyze رمز_السهم`\nمثال: `/analyze AAPL 1h`\n\n"
            "الفريمات المتاحة: 15m, 30m, 1h, 4h, 1d",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else "1d"
    
    if timeframe not in TIMEFRAMES:
        timeframe = "1d"
    
    # محاكاة ضغط زر
    class FakeQuery:
        def __init__(self, message, data):
            self.data = data
            self.message = message
        
        async def edit_message_text(self, text, **kwargs):
            await self.message.reply_text(text, **kwargs)
        
        async def answer(self):
            pass
    
    fake_query = FakeQuery(update.message, f"comprehensive_{symbol}_{timeframe}")
    update.callback_query = fake_query
    
    await comprehensive_analysis(update, context, symbol, timeframe)

async def schools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة المدارس الفنية"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🌊 موجات إليوت", callback_data="school_elliott"),
            InlineKeyboardButton("🏛️ كلاسيكي", callback_data="school_classical")
        ],
        [
            InlineKeyboardButton("🎯 مدرسة ICT", callback_data="school_ict"),
            InlineKeyboardButton("🎵 توافقي", callback_data="school_harmonic")
        ],
        [
            InlineKeyboardButton("📊 مقارنة المدارس", callback_data="school_compare"),
            InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        ]
    ]
    
    await query.edit_message_text(
        "📚 **المدارس الفنية المتاحة:**\n\n"
        "1️⃣ **🌊 موجات إليوت:** تحليل دورات السوق والموجات\n"
        "2️⃣ **🏛️ الكلاسيكي:** الدعم/المقاومة والنماذج السعرية\n"
        "3️⃣ **🎯 مدرسة ICT:** السيولة وFair Value Gaps\n"
        "4️⃣ **🎵 التوافقي:** النماذج الهندسية ونسب فيبوناتشي\n\n"
        "اختر مدرسة للتعرف عليها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def advanced_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة التحليل المتقدم"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("15m", callback_data="tf_15m"),
            InlineKeyboardButton("30m", callback_data="tf_30m"),
            InlineKeyboardButton("1h", callback_data="tf_1h")
        ],
        [
            InlineKeyboardButton("4h", callback_data="tf_4h"),
            InlineKeyboardButton("1d", callback_data="tf_1d")
        ],
        [
            InlineKeyboardButton("📊 تحليل متعدد الفريمات", callback_data="multi_timeframe"),
            InlineKeyboardButton("📈 المؤشرات الفنية", callback_data="technical_indicators")
        ],
        [
            InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        ]
    ]
    
    await query.edit_message_text(
        "🎯 **التحليل المتقدم:**\n\n"
        "**الفريمات الزمنية:**\n"
        "• 15m - للتداول اليومي\n"
        "• 30m - للمدى المتوسط\n"
        "• 1h - للاتجاه الرئيسي\n"
        "• 4h - للاستثمار المتوسط\n"
        "• 1d - للاستثمار طويل الأجل\n\n"
        "اختر فريم للتحليل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        await start_command(update, context)
    elif data == "all_stocks":
        await show_all_stocks(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "schools_menu":
        await schools_menu(update, context)
    elif data == "advanced_menu":
        await advanced_menu(update, context)
    elif data.startswith("stock_"):
        symbol = data.replace("stock_", "")
        # تحليل شامل بالفريم اليومي
        await comprehensive_analysis(update, context, symbol, "1d")
    elif data.startswith("comprehensive_"):
        # comprehensive_AAPL_1h
        parts = data.split("_")
        if len(parts) >= 3:
            symbol = parts[1]
            timeframe = parts[2]
            await comprehensive_analysis(update, context, symbol, timeframe)
    elif data.startswith("elliott_") or data.startswith("classical_") or \
         data.startswith("ict_") or data.startswith("harmonic_"):
        # elliott_AAPL_1h
        parts = data.split("_")
        if len(parts) >= 3:
            analysis_type = parts[0]
            symbol = parts[1]
            timeframe = parts[2]
            await show_specific_analysis(update, context, analysis_type, symbol, timeframe)
    elif data.startswith("tf_"):
        timeframe = data.replace("tf_", "")
        await query.edit_message_text(
            f"⏰ **اختر سهم للتحليل على فريم {TIMEFRAMES[timeframe]['name']}:**",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("AAPL", callback_data=f"comprehensive_AAPL_{timeframe}"),
                    InlineKeyboardButton("TSLA", callback_data=f"comprehensive_TSLA_{timeframe}")
                ],
                [
                    InlineKeyboardButton("MSFT", callback_data=f"comprehensive_MSFT_{timeframe}"),
                    InlineKeyboardButton("NVDA", callback_data=f"comprehensive_NVDA_{timeframe}")
                ],
                [
                    InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
                ]
            ])
        )

async def show_all_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض كل الأسهم"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    row = []
    for i, (symbol, info) in enumerate(STOCKS.items()):
        row.append(InlineKeyboardButton(symbol, callback_data=f"stock_{symbol}"))
        if len(row) == 3 or i == len(STOCKS) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")])
    
    await query.edit_message_text(
        "📋 **جميع الأسهم المتاحة:**\n\n"
        "اختر سهم للتحليل الشامل:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة المساعدة"""
    await update.callback_query.edit_message_text(
        "📚 **دليل استخدام البوت:**\n\n"
        "🔹 **الأوامر الرئيسية:**\n"
        "• /start - القائمة الرئيسية\n"
        "• /analyze [رمز] [فريم] - تحليل سريع\n"
        "• /help - هذه الرسالة\n\n"
        "🔹 **الفريمات الزمنية:**\n"
        "• 15m - 15 دقيقة (تداول سريع)\n"
        "• 30m - 30 دقيقة (تداول يومي)\n"
        "• 1h - ساعة (اتجاه متوسط)\n"
        "• 4h - 4 ساعات (استثمار)\n"
        "• 1d - يومي (استثمار طويل)\n\n"
        "🔹 **المدارس الفنية:**\n"
        "1. 🌊 موجات إليوت - دورات السوق\n"
        "2. 🏛️ التحليل الكلاسيكي - الدعم والمقاومة\n"
        "3. 🎯 مدرسة ICT - السيولة وFVG\n"
        "4. 🎵 التوافقي - النماذج الهندسية\n\n"
        "⚠️ **تنويه:**\n"
        "• البيانات تتأخر 15-20 دقيقة\n"
        "• التحليل للتعليم والتدريب\n"
        "• استشر مختصاً قبل الاستثمار\n\n"
        "🔄 **لأحدث البيانات:**\n"
        "اضغط 'تحديث' بعد دقائق",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
        ])
    )

async def show_specific_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 analysis_type, symbol, timeframe):
    """عرض تحليل محدد"""
    await query.edit_message_text(f"⏳ جاري تحليل {analysis_type} لـ {symbol}...")
    
    # جلب البيانات
    stock_data = get_stock_data(symbol, timeframe)
    
    if not stock_data or not stock_data["success"]:
        await query.edit_message_text(f"❌ تعذر تحليل {symbol}")
        return
    
    df = stock_data["data"]
    
    # اختيار نوع التحليل
    if analysis_type == "elliott":
        result = analyze_elliott_waves(df)
        title = "🌊 موجات إليوت"
    elif analysis_type == "classical":
        result = analyze_classical(df)
        title = "🏛️ التحليل الكلاسيكي"
    elif analysis_type == "ict":
        result = analyze_ict(df)
        title = "🎯 مدرسة ICT"
    elif analysis_type == "harmonic":
        result = analyze_harmonic(df)
        title = "🎵 التحليل التوافقي"
    else:
        return
    
    # بناء الرسالة (بسيطة)
    message = f"{title} - {symbol} ({TIMEFRAMES[timeframe]['name']})\n\n"
    
    for key, value in result.items():
        if isinstance(value, list):
            message += f"**{key}**:\n"
            for item in value[:3]:  # أول 3 عناصر فقط
                message += f"• {item}\n"
        else:
            message += f"**{key}**: {value}\n"
    
    await query.edit_message_text(
        message[:4000],  # تقليل النص إذا كان طويلاً
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 تحليل شامل", callback_data=f"comprehensive_{symbol}_{timeframe}")],
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
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # معالجة الأزرار
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 بدء تشغيل البوت المتقدم...")
    print("=" * 60)
    print("✅ بوت التحليل الفني المتقدم يعمل!")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 {len(STOCKS)} سهم متاح")
    print(f"⏰ {len(TIMEFRAMES)} فريم زمني")
    print("💡 الأوامر: /start, /analyze AAPL 1h, /help")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
