import os
import streamlit as st
import requests
from dotenv import load_dotenv
from utils.prompt_helper import build_prompt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="AI Diet Plan Generator", layout="wide")

# --- Styling Improvements ---
st.markdown(
    """
    <style>
    .st-title {
        color: #4CAF50; /* A nice green color */
    }
    .st-form {
        background-color: #f0f8f4; /* Light background for the form */
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #d4edda;
    }
    .st-form-submit-button {
        background-color: #4CAF50 !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        padding: 10px 20px !important;
        cursor: pointer !important;
    }
    .st-selectbox > div > div > div > div {
        background-color: white;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px;
    }
    .st-number-input > div > div > input {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px;
    }
    .st-text-input > div > div > input {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px;
    }
    .st-text-area > div > div > textarea {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥗 AI-Powered Personalized Diet Plan Generator")

with st.form("user_input_form"):
    st.subheader("Tell us about yourself:")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name", "Varun Kumar")
        age = st.number_input("Age (in years)", 12, 100, 24)
        height = st.number_input("Height (in cm)", 100, 220, 170)
        weight = st.number_input("Weight (in kg)", 30, 150, 65)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        diet_type = st.selectbox("Diet Type", ["Veg", "Non-Veg", "Vegan"])
        allergies = st.text_input("Any Allergies?", placeholder="e.g., Peanuts, Dairy")
    with col2:
        cuisine = st.selectbox("Preferred Cuisine", ["Indian", "Chinese", "American", "Italian", "Mexican", "Mediterranean"])
        activity_level = st.selectbox("Your Activity Level", ["Low", "Moderate", "High"])
        goal = st.selectbox("Your Goal", ["Weight Loss", "Muscle Gain", "Maintenance"])
        budget = st.selectbox("Your Budget", ["Low", "Medium", "High"])
        custom_foods_expander = st.expander("Optional: Add Specific Foods You Like")
        with custom_foods_expander:
            custom_foods = st.text_area("Enter foods separated by commas", placeholder="e.g., Avocado, Salmon, Quinoa")
    submitted = st.form_submit_button("Generate Your Personalized Diet Plan")

def generate_pdf(user_info, diet_plan, custom_foods=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Personalized Diet Plan for {user_info['name']}</b>", styles['h1']))
    story.append(Paragraph(f"<b>Age:</b> {user_info['age']}, <b>Gender:</b> {user_info['gender']}", styles['normal']))
    story.append(Paragraph(f"<b>Height:</b> {user_info['height']} cm, <b>Weight:</b> {user_info['weight']} kg", styles['normal']))
    story.append(Paragraph(f"<b>Goal:</b> {user_info['goal']}, <b>Diet Type:</b> {user_info['diet_type']}", styles['normal']))
    if user_info['allergies']:
        story.append(Paragraph(f"<b>Allergies:</b> {user_info['allergies']}", styles['normal']))
    story.append(Paragraph("<br/>", styles['normal']))  # Add some space
    story.append(Paragraph("<b>Your Personalized Diet Plan:</b>", styles['h2']))
    story.append(Paragraph(diet_plan, styles['normal']))

    if custom_foods:
        story.append(Paragraph("<br/>", styles['normal']))
        story.append(Paragraph("<b>Additional Information for Your Custom Foods:</b>", styles['h2']))
        for item in custom_foods.split(","):
            food = item.strip()
            if food:
                story.append(Paragraph(f"- {food}", styles['normal']))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

if submitted:
    st.markdown(f"### Hi **{name}**! Generating a diet plan tailored for your goal: **{goal}**")
    input_data = {
        "name": name,
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

    with st.spinner("Contacting AI and crafting your personalized diet plan..."):
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            plan_text = response.json()["choices"][0]["message"]["content"]
            st.subheader("Your Personalized Diet Plan:")
            st.markdown(plan_text)

            # Generate and offer PDF download
            pdf_bytes = generate_pdf(input_data, plan_text, custom_foods)
            st.download_button(
                label="Download Diet Plan as PDF",
                data=pdf_bytes,
                file_name="diet_plan.pdf",
                mime="application/pdf"
            )

            if custom_foods:
                st.subheader("🍎 Additional Information for Your Custom Foods:")
                st.write("Here's a list of the custom foods you mentioned:")
                for item in custom_foods.split(","):
                    food = item.strip()
                    if food:
                        st.markdown(f"- **{food}**")
        else:
            st.error(f"Failed to get diet plan from Groq API. Status code: {response.status_code}")
            try:
                error_message = response.json().get("error", {}).get("message", "No detailed error provided.")
                st.error(f"Error details: {error_message}")
            except:
                st.error("Could not parse error details from the API response.")