import joblib
import pandas as pd
import numpy as np

def load_trained_model(model_path = "./Models/power_predictor.joblib"):
    try:
        model = joblib.load(model_path)
        print("ML model loaded successfully!")
        return model
    except FileNotFoundError:
        print(f"Error: Couldn't find '{model_path}'. Run training script at fisrt.")
        return None

def predict_design_power(model, input_data):
    df_new = pd.DataFrame([input_data])

    df_new['vdd_squared'] = df_new['vdd'] ** 2
    df_new['freq_x_toggle'] = df_new['clock_frequency_mhz'] * df_new['toggle_rate']

    df_new['process_SS'] = 1 if input_data['process'] == "SS" else 0
    df_new['process_TT'] = 1 if input_data['process'] == "TT" else 0
    # if process is "FF" both would be 0

    features = [
        'clock_frequency_mhz', 'toggle_rate', 'static_probability', 
        'cell_count', 'seq_cell_count', 'total_area', 'logic_depth', 
        'vdd', 'temperature', 'vdd_squared', 'freq_x_toggle',
        'process_SS', 'process_TT'
    ]

    x_new = df_new[features]
    predicted_power = model.predict(x_new)[0]
    return predicted_power

if __name__ == "__main__":
    ml_model = load_trained_model()

    if ml_model:
        new_circuit = {
            'clock_frequency_mhz': 900.0,
            'toggle_rate': 0.1,
            'static_probability': 0.5,
            'cell_count': 23,
            'seq_cell_count': 3,
            'total_area': 0.580608,
            'logic_depth': 1,
            'vdd': 0.6,
            'temperature': 25.0,
            'process': 'TT'
        }

        result = predict_design_power(ml_model, new_circuit)
        print(f"\n--- PREDICTION RESULT ---")
        print(f"Predicted Power is: {result:.4f} uW")
