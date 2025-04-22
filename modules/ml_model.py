import xgboost as xgb
import pandas as pd
import os

MODEL_PATH = "models/xgb_model_full.json"  # ✅ مسار النموذج الكامل
TRAINING_DATA = "training_data_nasdaq_full.csv"  # ✅ ملف التدريب الكامل
FEATURES = ["MA10", "MA30", "Volume", "Avg_Volume", "Change"]

# 🎯 تحميل النموذج الذكي
def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"❌ النموذج غير موجود في: {MODEL_PATH}")

    booster = xgb.Booster()
    booster.load_model(MODEL_PATH)
    print("✅ تم تحميل النموذج بنجاح.")
    return booster

# 🔍 التنبؤ بنسبة نجاح السهم
def predict_buy_signal(model, data):
    try:
        input_data = pd.DataFrame([{
            "MA10": float(data["ma10"]),
            "MA30": float(data["ma30"]),
            "Volume": float(data["vol"]),
            "Avg_Volume": float(data["avg_vol"]),
            "Change": float(data["change"])
        }], columns=FEATURES)

        dmatrix = xgb.DMatrix(input_data)
        prob = model.predict(dmatrix)[0]
        score = round(prob * 100, 2)
        return score

    except Exception as e:
        print(f"❌ خطأ أثناء التنبؤ بالسهم {data.get('symbol', '')}: {e}")
        return 0

# 🧠 تدريب النموذج يومياً
def train_model_daily():
    try:
        if not os.path.exists(TRAINING_DATA):
            raise FileNotFoundError(f"❌ ملف التدريب غير موجود: {TRAINING_DATA}")

        df = pd.read_csv(TRAINING_DATA)
        required = FEATURES + ["Signal"]
        if not all(col in df.columns for col in required):
            raise ValueError(f"❌ ملف التدريب ناقص الأعمدة: {required}")

        df = df.dropna()
        X = df[FEATURES].astype(float)
        y = df["Signal"].astype(int)

        if y.nunique() < 2:
            raise ValueError("❌ لا يمكن تدريب النموذج لأن البيانات تحتوي على فئة واحدة فقط.")

        model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
        model.fit(X, y)

        booster = model.get_booster()
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        booster.save_model(MODEL_PATH)

        print("✅ تم تدريب النموذج الكامل وحفظه بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء تدريب النموذج اليومي: {e}")
