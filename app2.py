import os
import streamlit as st
import requests
from dotenv import load_dotenv
from utils.prompt_helper import build_prompt
import pdfkit
import tempfile

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

st.set_page_config(page_title="AI Diet Plan Generator", layout="wide")

# --- Styling for Light Green Clean Look ---
st.markdown(
    """
    <style>
    .st-form {
        background-color: #f0f8f4;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #d4edda;
    }
    .st-form-submit-button {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 10px 20px !important;
        cursor: pointer !important;
    }
    .stMarkdown h1 {
        color: #2e7d32;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥗 AI-Powered Personalized Diet Plan Generator")

with st.form("user_input_form"):
    st.subheader("✨ Tell us about yourself:")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("👤 Your Name", "Varun Kumar")
        age = st.number_input("🎂 Age (in years)", 12, 100, 24)
        height = st.number_input("📏 Height (in cm)", 100, 220, 170)
        weight = st.number_input("⚖️ Weight (in kg)", 30, 150, 65)
        gender = st.selectbox("🚻 Gender", ["Male", "Female", "Other"])
        diet_type = st.selectbox("🥦 Diet Type", ["Veg", "Non-Veg", "Vegan"])
        allergies = st.text_input("🚫 Any Allergies?", placeholder="e.g., Peanuts, Dairy")
    with col2:
        cuisine = st.selectbox("🍛 Preferred Cuisine", ["Indian", "Chinese", "American", "Italian", "Mexican", "Mediterranean"])
        activity_level = st.selectbox("🏃‍♂️ Activity Level", ["Low", "Moderate", "High"])
        goal = st.selectbox("🎯 Your Goal", ["Weight Loss", "Muscle Gain", "Maintenance"])
        budget = st.selectbox("💸 Your Budget", ["Low", "Medium", "High"])
        custom_foods_expander = st.expander("🍽️ Optional: Add Specific Foods You Like")
        with custom_foods_expander:
            custom_foods = st.text_area("Enter foods separated by commas", placeholder="e.g., Avocado, Salmon, Quinoa")
    submitted = st.form_submit_button("✅ Generate Your Personalized Diet Plan")

# 🍽️ Spoonacular Nutrition Fetcher
def get_nutrition_from_spoonacular(food_item):
    url = f"https://api.spoonacular.com/food/ingredients/search"
    params = {
        "query": food_item,
        "number": 1,
        "apiKey": SPOONACULAR_API_KEY
    }
    res = requests.get(url, params=params)
    if res.status_code != 200 or not res.json().get("results"):
        return None

    ingredient_id = res.json()["results"][0]["id"]

    info_url = f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information"
    info_params = {"amount": 100, "unit": "g", "apiKey": SPOONACULAR_API_KEY}
    info_res = requests.get(info_url, params=info_params)
    if info_res.status_code != 200:
        return None

    data = info_res.json()
    nutrition = data.get("nutrition", {})
    return {
        "name": data.get("name", food_item),
        "calories": nutrition.get("nutrients", [{}])[0].get("amount", "N/A"),
        "protein": next((n["amount"] for n in nutrition["nutrients"] if n["name"] == "Protein"), "N/A"),
        "carbs": next((n["amount"] for n in nutrition["nutrients"] if n["name"] == "Carbohydrates"), "N/A"),
        "fat": next((n["amount"] for n in nutrition["nutrients"] if n["name"] == "Fat"), "N/A")
    }

# 📄 Generate PDF
def generate_pdf_from_text(text):
    html_content = f"<html><body><pre>{text}</pre></body></html>"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        config = pdfkit.configuration(wkhtmltopdf="C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
        pdfkit.from_string(html_content, f.name, configuration=config)
        return f.name

# 🧠 Generate Diet Plan
if submitted:
    st.markdown(f"### 👋 Hi **{name}**! Generating a diet plan tailored for your goal: **{goal}**")
    input_data = {
        "age": age,
        "height": height,
        "weight": weight,
        "gender": gender,
        "diet_type": diet_type,
        "allergies": allergies,
        "cuisine": cuisine,
        "goal": goal,
        "activity_level": activity_level,
        "budget": budget,
        "custom_foods": custom_foods
    }

    prompt = build_prompt(input_data)
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    with st.spinner("🔍 Contacting AI and crafting your personalized diet plan..."):
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            plan_text = response.json()["choices"][0]["message"]["content"]
            st.subheader("📋 Your Personalized Diet Plan:")
            st.markdown(plan_text)

            # PDF Download
            pdf_path = generate_pdf_from_text(plan_text)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download Plan as PDF",
                    data=f,
                    file_name=f"{name}_diet_plan.pdf",
                    mime="application/pdf"
                )

            # Custom food nutrition section
            if custom_foods:
                st.subheader("🍎 Nutritional Info for Your Custom Foods")
                for item in custom_foods.split(","):
                    food = item.strip()
                    if food:
                        st.markdown(f"**{food}**")
                        info = get_nutrition_from_spoonacular(food)
                        if info:
                            st.markdown(f"- 🔥 Calories: {info['calories']} kcal")
                            st.markdown(f"- 💪 Protein: {info['protein']} g")
                            st.markdown(f"- 🍞 Carbs: {info['carbs']} g")
                            st.markdown(f"- 🧈 Fat: {info['fat']} g")
                        else:
                            st.warning("❌ Could not fetch nutrition info.")
        else:
            st.error("❌ Failed to get response from Groq API.")
            try:
                error = response.json().get("error", {}).get("message", "No detailed error provided.")
                st.error(f"Error: {error}")
            except:
                st.error("Unknown error occurred while parsing response.")

