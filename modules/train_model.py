import pandas as pd
import xgboost as xgb
import os

# تحميل البيانات
df = pd.read_csv("datasets/training_data.csv")

# تأكد من الأعمدة المطلوبة
required_columns = ["MA10", "MA30", "Volume", "Avg_Volume", "Change", "Signal"]
if not all(col in df.columns for col in required_columns):
    raise Exception("❌ البيانات لا تحتوي على الأعمدة المطلوبة!")

# تنظيف وتحويل أنواع البيانات
for col in required_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("📊 إشارات الشراء قبل التنظيف:")
print(df["Signal"].value_counts())

df.dropna(inplace=True)

print("📊 إشارات الشراء بعد التنظيف:")
print(df["Signal"].value_counts())

# فصل الميزات والتصنيف
X = df[["MA10", "MA30", "Volume", "Avg_Volume", "Change"]]
y = df["Signal"].astype(int)

# ✅ التحقق من وجود كلا الفئتين
if y.nunique() < 2:
    print("❌ لا يمكن تدريب النموذج لأن البيانات تحتوي على فئة واحدة فقط:")
    print(y.value_counts())
    exit()

# تدريب النموذج
model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1)
model.fit(X, y)

# حفظ النموذج
os.makedirs("models", exist_ok=True)
model.save_model("models/xgb_model.json")
print("✅ تم تدريب النموذج وحفظه بنجاح في models/xgb_model.json")
