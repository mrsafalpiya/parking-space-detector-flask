import pandas as pd
from sklearn.model_selection import train_test_split
import xgboost as xgb
from datetime import datetime
from db import get_all_parking_logs


def get_free_slot_predictions():
    parking_logs = get_all_parking_logs()
    data = pd.DataFrame(parking_logs)

    data['arrival_time'] = data['arrival_time'].apply(time_to_minutes)
    data['exit_time'] = data['exit_time'].apply(time_to_minutes)

    categorical_columns = ['vehicle_number', 'day_of_week']
    for col in categorical_columns:
        data[col] = data[col].astype('category')

    X = data.drop(['exit_time'], axis=1)
    y = data['exit_time']

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train XGBoost Regressor
    xgb_regressor = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        enable_categorical=True,
        random_state=42
    )

    xgb_regressor.fit(X_train, y_train)

    current_time = datetime.now().strftime("%H:%M")
    current_time_minutes = time_to_minutes(current_time)
    current_day = datetime.now().strftime("%A")

    parked_vehicles = data[
        (data['arrival_time'] <= current_time_minutes) & (data['exit_time'] > current_time_minutes) & (
                    data['day_of_week'] == current_day)]

    predictions = {}

    parked_vehicle_numbers = parked_vehicles['vehicle_number']
    filter_condition = X['vehicle_number'].isin(parked_vehicle_numbers)
    parked_features = X[filter_condition]
    parked_predictions = xgb_regressor.predict(parked_features)

    for idx, i in enumerate(parked_vehicle_numbers.index):
        vehicle_number = parked_vehicle_numbers[i]
        predicted_minutes = round(parked_predictions[idx])
        predicted_time = minutes_to_time(predicted_minutes)
        if not vehicle_number in predictions:
            predictions[vehicle_number] = predicted_time

    return predictions


def time_to_minutes(time_str):
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def minutes_to_time(minutes):
    hours = minutes // 60
    mins = minutes % 60
    period = "AM" if hours < 12 else "PM"
    hours = hours % 12 or 12
    return f"{hours:02d}:{mins:02d} {period}"
