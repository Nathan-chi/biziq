"""
BizIQ - Stage 4: AI Predictions & Machine Learning Engine
Uses scikit-learn for price forecasting and business intelligence
"""

import sqlite3
import json
import math
from datetime import datetime, timedelta
from typing import Optional

# ─────────────────────────────────────────────────────────
# LIGHTWEIGHT ML — No heavy dependencies needed!
# Uses pure Python + math for predictions (Linear Regression,
# Moving Averages, Exponential Smoothing)
# ─────────────────────────────────────────────────────────


def get_db():
    conn = sqlite3.connect("biziq.db")
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────
# CORE ML ALGORITHMS (pure Python, no libraries needed)
# ─────────────────────────────────────────────────────────

def linear_regression(x_vals: list, y_vals: list):
    """
    Simple linear regression — finds the trend line through data points.
    Returns (slope, intercept) so we can predict future values.
    """
    n = len(x_vals)
    if n < 2:
        return 0, y_vals[0] if y_vals else 0

    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x ** 2 for x in x_vals)

    denominator = (n * sum_x2 - sum_x ** 2)
    if denominator == 0:
        return 0, sum_y / n

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def exponential_smoothing(values: list, alpha: float = 0.3):
    """
    Exponential smoothing — gives more weight to recent data.
    alpha = 0.3 means recent data matters more than old data.
    Good for smoothing out noisy business data.
    """
    if not values:
        return []
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
    return smoothed


def moving_average(values: list, window: int = 7):
    """Simple moving average over a sliding window"""
    if len(values) < window:
        return values
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        result.append(sum(values[start:i+1]) / (i - start + 1))
    return result


def forecast_next_n(values: list, n_days: int = 30):
    """
    Forecast the next N days using linear regression on recent trend.
    Returns list of predicted values.
    """
    if len(values) < 3:
        last = values[-1] if values else 0
        return [last] * n_days

    x = list(range(len(values)))
    slope, intercept = linear_regression(x, values)

    predictions = []
    for i in range(n_days):
        future_x = len(values) + i
        predicted = slope * future_x + intercept
        predictions.append(round(max(0, predicted), 2))

    return predictions


def calculate_confidence(values: list, prediction: float) -> int:
    """
    Calculate prediction confidence (0-100%) based on data variance.
    Lower variance = higher confidence.
    """
    if len(values) < 3:
        return 40
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = math.sqrt(variance)
    cv = (std_dev / mean * 100) if mean else 100  # coefficient of variation
    confidence = max(20, min(95, int(100 - cv)))
    return confidence


def detect_anomalies(values: list, threshold: float = 2.0) -> list:
    """
    Detect unusual spikes or drops in data.
    Returns indices of anomalous points.
    """
    if len(values) < 4:
        return []
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = math.sqrt(variance) if variance > 0 else 0
    if std_dev == 0:
        return []
    return [i for i, v in enumerate(values) if abs(v - mean) > threshold * std_dev]


# ─────────────────────────────────────────────────────────
# BUSINESS REVENUE PREDICTIONS
# ─────────────────────────────────────────────────────────

def get_revenue_data(days: int = 90, user_id: int = None) -> list:
    """Pull revenue data from the database"""
    conn = get_db()
    if user_id is not None:
        rows = conn.execute("""
            SELECT date, SUM(amount) as total
            FROM transactions_v2
            WHERE type = 'sales' AND user_id = ?
            GROUP BY date
            ORDER BY date ASC
            LIMIT ?
        """, (user_id, days)).fetchall()
    else:
        rows = conn.execute("""
            SELECT date, SUM(amount) as total
            FROM transactions_v2
            WHERE type = 'sales'
            GROUP BY date
            ORDER BY date ASC
            LIMIT ?
        """, (days,)).fetchall()
    conn.close()
    return [{"date": r["date"], "revenue": r["total"]} for r in rows]


def get_expense_data(days: int = 90, user_id: int = None) -> list:
    """Pull expense data from the database"""
    conn = get_db()
    if user_id is not None:
        rows = conn.execute("""
            SELECT date, SUM(amount) as total
            FROM transactions_v2
            WHERE type = 'expense' AND user_id = ?
            GROUP BY date
            ORDER BY date ASC
            LIMIT ?
        """, (user_id, days)).fetchall()
    else:
        rows = conn.execute("""
            SELECT date, SUM(amount) as total
            FROM transactions_v2
            WHERE type = 'expense'
            GROUP BY date
            ORDER BY date ASC
            LIMIT ?
        """, (days,)).fetchall()
    conn.close()
    return [{"date": r["date"], "expense": r["total"]} for r in rows]


def predict_revenue(forecast_days: int = 30, user_id: int = None) -> dict:
    """
    Predict future revenue using linear regression on historical data.
    """
    data = get_revenue_data(user_id=user_id)

    if len(data) < 3:
        # Not enough data — return honest message
        return {
            "status": "insufficient_data",
            "message": "Need at least 3 days of sales data to make predictions.",
            "forecast": [],
            "confidence": 0,
        }

    values = [d["revenue"] for d in data]
    smoothed = exponential_smoothing(values, alpha=0.4)
    predictions = forecast_next_n(smoothed, forecast_days)
    confidence = calculate_confidence(values, predictions[0])
    anomalies = detect_anomalies(values)

    # Generate forecast dates
    last_date = datetime.strptime(data[-1]["date"], "%Y-%m-%d")
    forecast_dates = [
        (last_date + timedelta(days=i+1)).strftime("%Y-%m-%d")
        for i in range(forecast_days)
    ]

    # Key stats
    avg_daily = sum(values) / len(values)
    predicted_monthly = sum(predictions[:30])
    current_monthly = sum(values[-30:]) if len(values) >= 30 else sum(values)
    growth_pct = ((predicted_monthly - current_monthly) / current_monthly * 100) if current_monthly else 0

    return {
        "status": "success",
        "confidence": confidence,
        "avg_daily_revenue": round(avg_daily),
        "predicted_next_30_days": round(predicted_monthly),
        "current_30_days": round(current_monthly),
        "growth_forecast_pct": round(growth_pct, 1),
        "anomaly_days": len(anomalies),
        "forecast": [
            {"date": d, "predicted_revenue": p}
            for d, p in zip(forecast_dates, predictions)
        ],
        "trend": "up" if growth_pct > 0 else "down",
    }


def predict_expenses(forecast_days: int = 30, user_id: int = None) -> dict:
    """Predict future expenses"""
    data = get_expense_data(user_id=user_id)

    if len(data) < 3:
        return {"status": "insufficient_data", "forecast": [], "confidence": 0}

    values = [d["expense"] for d in data]
    smoothed = exponential_smoothing(values, alpha=0.3)
    predictions = forecast_next_n(smoothed, forecast_days)
    confidence = calculate_confidence(values, predictions[0])

    last_date = datetime.strptime(data[-1]["date"], "%Y-%m-%d")
    forecast_dates = [(last_date + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(forecast_days)]

    predicted_monthly = sum(predictions[:30])
    current_monthly = sum(values[-30:]) if len(values) >= 30 else sum(values)
    change_pct = ((predicted_monthly - current_monthly) / current_monthly * 100) if current_monthly else 0

    return {
        "status": "success",
        "confidence": confidence,
        "predicted_next_30_days": round(predicted_monthly),
        "current_30_days": round(current_monthly),
        "change_forecast_pct": round(change_pct, 1),
        "forecast": [
            {"date": d, "predicted_expense": p}
            for d, p in zip(forecast_dates, predictions)
        ],
    }


# ─────────────────────────────────────────────────────────
# MARKET PRICE PREDICTIONS
# ─────────────────────────────────────────────────────────

def predict_commodity_price(symbol: str, forecast_days: int = 30) -> dict:
    """
    Predict future commodity price using historical market data
    stored in our market_history table.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT date, AVG(price) as price FROM market_history
        WHERE symbol = ?
        GROUP BY date ORDER BY date ASC
    """, (symbol,)).fetchall()
    conn.close()

    if len(rows) < 3:
        return {
            "status": "insufficient_data",
            "message": "Need more historical data. Prices are cached daily — check back in a few days.",
            "forecast": []
        }

    values = [r["price"] for r in rows]
    predictions = forecast_next_n(values, forecast_days)
    confidence = calculate_confidence(values, predictions[0])

    last_date = datetime.strptime(rows[-1]["date"], "%Y-%m-%d")
    forecast_dates = [(last_date + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(forecast_days)]

    current_price = values[-1]
    predicted_price = predictions[-1]
    change_pct = ((predicted_price - current_price) / current_price * 100) if current_price else 0

    return {
        "status": "success",
        "symbol": symbol,
        "current_price": round(current_price, 4),
        "predicted_price_30d": round(predicted_price, 4),
        "change_forecast_pct": round(change_pct, 2),
        "confidence": confidence,
        "direction": "up" if change_pct > 0 else "down",
        "forecast": [
            {"date": d, "predicted_price": p}
            for d, p in zip(forecast_dates, predictions)
        ]
    }


# ─────────────────────────────────────────────────────────
# SMART BUSINESS RECOMMENDATIONS
# ─────────────────────────────────────────────────────────

def generate_smart_recommendations(user_id: int = None) -> list:
    """
    Generate AI-powered business recommendations by combining:
    - Revenue predictions
    - Expense predictions
    - Market commodity trends
    - Anomaly detection
    """
    recommendations = []

    rev = predict_revenue(30, user_id=user_id)
    exp = predict_expenses(30, user_id=user_id)

    # Revenue trend advice
    if rev["status"] == "success":
        if rev["growth_forecast_pct"] > 10:
            recommendations.append({
                "priority": "high",
                "icon": "🚀",
                "category": "Revenue Forecast",
                "title": f"Revenue expected to grow {rev['growth_forecast_pct']}%",
                "detail": f"Your predicted revenue for the next 30 days is ₦{rev['predicted_next_30_days']:,}. Consider increasing inventory to meet demand.",
                "action": "Increase stock orders by 15-20%",
                "color": "#00d4aa",
                "confidence": rev["confidence"],
            })
        elif rev["growth_forecast_pct"] < -10:
            recommendations.append({
                "priority": "urgent",
                "icon": "📉",
                "category": "Revenue Warning",
                "title": f"Revenue may drop {abs(rev['growth_forecast_pct'])}% next month",
                "detail": "Based on your recent sales trend, revenue appears to be declining. Consider promotions or diversifying products.",
                "action": "Run a promotion this week",
                "color": "#ff4444",
                "confidence": rev["confidence"],
            })

        if rev["anomaly_days"] > 0:
            recommendations.append({
                "priority": "medium",
                "icon": "🔍",
                "category": "Anomaly Detected",
                "title": f"{rev['anomaly_days']} unusual sales day(s) detected",
                "detail": "Some days had unusually high or low sales. Understanding why can help you replicate successes or avoid problems.",
                "action": "Review those specific dates in your records",
                "color": "#f5a623",
                "confidence": 90,
            })

    # Expense vs revenue risk
    if rev["status"] == "success" and exp["status"] == "success":
        predicted_profit = rev["predicted_next_30_days"] - exp["predicted_next_30_days"]
        predicted_margin = (predicted_profit / rev["predicted_next_30_days"] * 100) if rev["predicted_next_30_days"] > 0 else 0

        if predicted_margin < 10:
            recommendations.append({
                "priority": "urgent",
                "icon": "⚠️",
                "category": "Margin Risk",
                "title": f"Predicted profit margin next month: {predicted_margin:.1f}%",
                "detail": f"With predicted revenue of ₦{rev['predicted_next_30_days']:,} and expenses of ₦{exp['predicted_next_30_days']:,}, your margin will be thin.",
                "action": "Cut discretionary expenses now",
                "color": "#ff4444",
                "confidence": min(rev["confidence"], exp["confidence"]),
            })
        elif predicted_margin > 25:
            recommendations.append({
                "priority": "low",
                "icon": "💰",
                "category": "Strong Outlook",
                "title": f"Healthy margin of {predicted_margin:.1f}% predicted",
                "detail": "Your business looks financially healthy next month. Good time to reinvest in growth.",
                "action": "Consider investing in marketing or equipment",
                "color": "#4a9eff",
                "confidence": min(rev["confidence"], exp["confidence"]),
            })

    # Commodity price predictions
    commodities_to_check = ["WHEAT", "SUGAR", "CMO/PALM_OIL_USD"]
    for symbol in commodities_to_check:
        pred = predict_commodity_price(symbol, 30)
        if pred["status"] == "success":
            if pred["change_forecast_pct"] > 8:
                name = {"WHEAT": "Flour/Wheat", "SUGAR": "Sugar", "CMO/PALM_OIL_USD": "Palm Oil"}.get(symbol, symbol)
                recommendations.append({
                    "priority": "high",
                    "icon": "📦",
                    "category": "Stock Up Alert",
                    "title": f"{name} price may rise {pred['change_forecast_pct']:.1f}% in 30 days",
                    "detail": f"Current price: ₦{pred['current_price']:,}. Predicted: ₦{pred['predicted_price_30d']:,}. Buy in bulk now to lock in lower prices.",
                    "action": f"Bulk purchase {name} this week",
                    "color": "#f5a623",
                    "confidence": pred["confidence"],
                })
            elif pred["change_forecast_pct"] < -5:
                name = {"WHEAT": "Flour/Wheat", "SUGAR": "Sugar", "CMO/PALM_OIL_USD": "Palm Oil"}.get(symbol, symbol)
                recommendations.append({
                    "priority": "low",
                    "icon": "⏳",
                    "category": "Wait to Buy",
                    "title": f"{name} price may drop {abs(pred['change_forecast_pct']):.1f}% in 30 days",
                    "detail": f"Prices are trending down. Consider delaying your next large order to save money.",
                    "action": f"Delay {name} restock by 1-2 weeks",
                    "color": "#00d4aa",
                    "confidence": pred["confidence"],
                })

    # Sort by priority
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))

    if not recommendations:
        recommendations.append({
            "priority": "low",
            "icon": "✅",
            "category": "All Clear",
            "title": "No urgent actions needed",
            "detail": "Add more transaction data daily to unlock better AI predictions and insights.",
            "action": "Keep entering daily sales data",
            "color": "#00d4aa",
            "confidence": 70,
        })

    return recommendations


# ─────────────────────────────────────────────────────────
# BUSINESS HEALTH SCORE
# ─────────────────────────────────────────────────────────

def calculate_health_score(user_id: int = None) -> dict:
    """
    Give the business an overall health score out of 100.
    Combines profitability, revenue trend, expense control, and data completeness.
    """
    conn = get_db()
    this_month = datetime.now().strftime("%Y-%m")

    if user_id is not None:
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions_v2 WHERE user_id=? AND type='sales' AND date LIKE ?",
            (user_id, f"{this_month}%")
        ).fetchone()[0]
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions_v2 WHERE user_id=? AND type='expense' AND date LIKE ?",
            (user_id, f"{this_month}%")
        ).fetchone()[0]
        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM transactions_v2 WHERE user_id=?", (user_id,)
        ).fetchone()[0]
    else:
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions_v2 WHERE type='sales' AND date LIKE ?",
            (f"{this_month}%",)
        ).fetchone()[0]
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions_v2 WHERE type='expense' AND date LIKE ?",
            (f"{this_month}%",)
        ).fetchone()[0]
        transaction_count = conn.execute("SELECT COUNT(*) FROM transactions_v2").fetchone()[0]
    conn.close()

    scores = {}

    # Profitability score (0-40 points)
    margin = ((revenue - expenses) / revenue * 100) if revenue > 0 else 0
    scores["profitability"] = min(40, max(0, int(margin * 2)))

    # Revenue consistency score (0-30 points)
    rev_data = get_revenue_data(30, user_id=user_id)
    if len(rev_data) >= 7:
        values = [d["revenue"] for d in rev_data]
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean)**2 for v in values) / len(values))
        cv = (std / mean) if mean > 0 else 1
        scores["consistency"] = min(30, max(0, int(30 - cv * 30)))
    else:
        scores["consistency"] = 10  # partial score for new businesses

    # Data completeness score (0-30 points)
    scores["data_quality"] = min(30, transaction_count * 2)

    total_score = sum(scores.values())

    if total_score >= 80:
        grade, label, color = "A", "Excellent", "#00d4aa"
    elif total_score >= 65:
        grade, label, color = "B", "Good", "#4a9eff"
    elif total_score >= 50:
        grade, label, color = "C", "Fair", "#f5a623"
    else:
        grade, label, color = "D", "Needs Work", "#ff4444"

    return {
        "total_score": total_score,
        "grade": grade,
        "label": label,
        "color": color,
        "breakdown": [
            {"label": "Profitability", "score": scores["profitability"], "max": 40},
            {"label": "Revenue Consistency", "score": scores["consistency"], "max": 30},
            {"label": "Data Completeness", "score": scores["data_quality"], "max": 30},
        ],
        "tip": "Enter daily sales data to improve your score and unlock better predictions."
            if scores["data_quality"] < 20 else
            "Keep maintaining consistent records for the most accurate forecasts."
    }
