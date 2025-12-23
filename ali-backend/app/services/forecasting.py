import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

def generate_forecast(history_data: list, days=7) -> list:
    """
    Predicts next 7 days of CPC/Spend using Linear Regression.
    """
    if not history_data or len(history_data) < 3:
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