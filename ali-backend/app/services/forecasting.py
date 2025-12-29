from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Any

def generate_forecast(history: List[float], days: int = 7) -> List[float]:
    """
    Generates a simple forecast based on historical data.
    Uses a linear trend + moving average approach.
    """
    if not history or len(history) < 2:
        return [0.0] * days

    try:
        # Simple Linear Regression
        x = np.arange(len(history))
        y = np.array(history)
        
        # Slope (m) and Intercept (b)
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
        
        # Project future
        future_x = np.arange(len(history), len(history) + days)
        forecast = (m * future_x + c).tolist()
        
        # Ensure no negative values for metrics like clicks/spend
        return [max(0, val) for val in forecast]
        
    except Exception as e:
        print(f"?? Forecasting Error: {e}")
        # Fallback: Return the average of the last 3 days repeated
        avg = sum(history[-3:]) / 3 if len(history) >= 3 else sum(history) / len(history)
        return [avg] * days

def legacy_generate_forecast(history_data: list, days=7) -> list:
    """
    Predicts next 7 days of CPC/Spend using Linear Regression.
    """
    if not history_data or len(history_data) < 3:
        return []

    try:
        import pandas as pd
        from sklearn.linear_model import LinearRegression
    except Exception as e:
        # If heavy deps are unavailable, gracefully skip forecasting
        return []

    df = pd.DataFrame(history_data)
    df['day_index'] = range(len(df))
    
    # Prepare Model
    X = df[['day_index']]
    
    predictions = []
    
    # Predict for each metric
    for metric in ['cpc', 'spend', 'ctr']:
        if metric not in df.columns: continue
        
        y = df[metric].fillna(0)
        model = LinearRegression()
        model.fit(X, y)
        
        # Future dates
        last_day = df['day_index'].max()
        future_X = np.array([[last_day + i + 1] for i in range(days)])
        forecast_y = model.predict(future_X)
        
        # Format
        start_date = datetime.strptime(df['date'].iloc[-1], "%Y-%m-%d")
        for i, val in enumerate(forecast_y):
            next_date = (start_date + timedelta(days=i+1)).strftime("%Y-%m-%d")
            # Ensure no negative predictions
            predictions.append({
                "date": next_date,
                "metric": metric,
                "value": max(0, round(val, 2)),
                "type": "forecast"
            })
            
    return predictions