from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_DIR = PROJECT_DIR / "models"
WAIT_MODEL_PATH = MODEL_DIR / "waiting_time_model.pkl"
QUEUE_MODEL_PATH = MODEL_DIR / "queue_length_model.pkl"
YOLO_MODEL_PATH = PROJECT_DIR / "yolo11n.pt"

st.set_page_config(
    page_title="IntelliQueue | Smart Queue Prediction",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
      .stApp { background: #f4f7fb; color: #172033; }
      html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
      .block-container { max-width: 1180px; padding-top: 1.7rem; padding-bottom: 3rem; }
      .topbar { display:flex; justify-content:space-between; align-items:center; padding: 1rem 1.3rem; background:white; border:1px solid #e8edf4; border-radius:18px; margin-bottom:2rem; }
      .brand { display:flex; align-items:center; gap:12px; }
      .brand-icon { display:grid; place-items:center; width:44px; height:44px; border-radius:13px; background:#2563eb; color:white; font:800 17px Manrope,sans-serif; }
      .brand-name { font:800 19px Manrope,sans-serif; color:#172033; }
      .brand-sub { color:#8490a2; font-size:12px; margin-top:2px; }
      .top-status { color:#20845a; font-size:12px; font-weight:700; }
      .eyebrow { color:#2563eb; font-size:11px; font-weight:800; letter-spacing:2px; }
      h1 { font-family:Manrope,sans-serif !important; font-size:clamp(2rem,4vw,3.15rem) !important; line-height:1.12 !important; color:#172033 !important; margin:.55rem 0 !important; }
      .hero-copy { color:#69778c; font-size:15px; max-width:650px; line-height:1.65; margin-bottom:1.8rem; }
      .panel { background:white; border:1px solid #e7edf5; border-radius:18px; padding:1.35rem 1.45rem; box-shadow:0 8px 26px rgba(27,45,75,.045); min-height:100%; }
      .panel-title { font:800 17px Manrope,sans-serif; color:#172033; margin:0 0 3px; }
      .panel-caption { color:#7c899d; font-size:12px; margin:0 0 1rem; }
      div[data-testid="stMetric"] { background:#f5f8fc; border:1px solid #e5ecf5; padding:1rem; border-radius:14px; }
      div[data-testid="stMetricLabel"] { color:#718096; }
      .footnote { color:#8792a3; font-size:12px; text-align:center; padding-top:1.5rem; }
      .stButton > button[kind="primary"], .stFormSubmitButton > button { background:#172033; border:0; border-radius:10px; min-height:2.8rem; font-weight:700; }
      .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover { background:#263653; border:0; }
      @media (max-width: 700px) { .topbar { padding:.8rem; } .top-status { display:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)

now = datetime.now()
st.markdown(
    f"""
    <div class="topbar">
      <div class="brand">
        <div class="brand-icon">IQ</div>
        <div><div class="brand-name">IntelliQueue</div><div class="brand-sub">AI Queue Management</div></div>
      </div>
      <div class="top-status">● System ready &nbsp;·&nbsp; {now.strftime("%a, %d %b %Y · %I:%M %p")}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">AI POWERED | REAL TIME</div>', unsafe_allow_html=True)
st.title("Smart Queue Prediction System")
st.markdown(
    '<div class="hero-copy">Monitor university queues with computer vision and machine learning. Capture or upload a queue image, count people, and estimate the wait.</div>',
    unsafe_allow_html=True,
)

@st.cache_resource(show_spinner="Loading prediction models…")
def load_prediction_models():
    missing = [str(p) for p in (WAIT_MODEL_PATH, QUEUE_MODEL_PATH) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing model file(s): " + ", ".join(missing))
    return joblib.load(WAIT_MODEL_PATH), joblib.load(QUEUE_MODEL_PATH)

@st.cache_resource(show_spinner="Loading people detector…")
def load_yolo_model():
    if not YOLO_MODEL_PATH.exists():
        raise FileNotFoundError(f"YOLO weights not found: {YOLO_MODEL_PATH}")
    from ultralytics import YOLO
    return YOLO(str(YOLO_MODEL_PATH))

@st.cache_data(show_spinner="Detecting people…")
def detect_people(image_bytes: bytes):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((1280, 1280))
    model = load_yolo_model()
    result = model.predict(image, classes=[0], verbose=False, imgsz=416, device="cpu")[0]

    width, height = image.size
    x1, y1 = width * 0.15, height * 0.20
    x2, y2 = width * 0.85, height * 0.80
    count = 0
    if result.boxes is not None:
        for bx1, by1, bx2, by2 in result.boxes.xyxy.cpu().tolist():
            center_x = (bx1 + bx2) / 2
            center_y = (by1 + by2) / 2
            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                count += 1

    preview = image.copy()
    draw = ImageDraw.Draw(preview)
    draw.rectangle((x1, y1, x2, y2), outline="#00cc88", width=max(2, width // 300))
    return count, preview

def predict(wait_model, queue_model, values):
    frame = pd.DataFrame([values])
    wait = float(wait_model.predict(frame)[0])
    queue = float(queue_model.predict(frame)[0])
    return round(wait, 2), round(queue, 2)

left, right = st.columns([1.02, 0.98], gap="large")

with left:
    st.markdown('<div class="panel"><div class="panel-title">Live Queue Monitoring</div><div class="panel-caption">Capture an image or upload one for AI people detection</div>', unsafe_allow_html=True)
    camera_image = st.camera_input("Capture queue image", label_visibility="collapsed")
    uploaded_image = st.file_uploader(
        "Or upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        help="The image is processed for people inside the highlighted queue area.",
    )
    selected_image = camera_image or uploaded_image
    if selected_image is not None:
        raw_image = selected_image.getvalue()
        image_id = sha256(raw_image).hexdigest()
        if st.session_state.get("detected_image_id") != image_id:
            try:
                detected_count, preview = detect_people(raw_image)
                st.session_state["detected_image_id"] = image_id
                st.session_state["detected_count"] = detected_count
                st.session_state["queue_count"] = detected_count
                st.session_state["preview_image"] = preview
            except Exception as exc:
                st.error(f"People detection failed: {exc}")
        preview = st.session_state.get("preview_image")
        if preview is not None:
            st.image(preview, caption="Queue area shown in green", use_container_width=True)
        if "detected_count" in st.session_state:
            st.success(f"{st.session_state['detected_count']} people detected in the queue area.")
    else:
        st.info("Take a photo or upload an image to run the people detector.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel"><div class="panel-title">Queue Prediction</div><div class="panel-caption">Estimate the expected wait and queue length</div>', unsafe_allow_html=True)
    with st.form("prediction_form"):
        service = st.selectbox(
            "Service location",
            ["Cafeteria", "Admin Office", "Library Counter", "Fee Counter", "Student Service Center"],
        )
        day_of_week = st.selectbox(
            "Day of week",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=now.weekday(),
        )
        hour = st.slider("Hour of day", min_value=0, max_value=23, value=now.hour)
        queue_length = st.number_input(
            "People currently in queue",
            min_value=0,
            max_value=500,
            value=int(st.session_state.get("queue_count", 0)),
            step=1,
            key="queue_count",
        )
        number_of_counters = st.number_input("Open service counters", min_value=1, max_value=50, value=3, step=1)
        average_service_time = st.number_input(
            "Average service time (minutes)",
            min_value=0.1,
            max_value=120.0,
            value=2.5,
            step=0.5,
        )
        students_arriving = st.number_input(
            "Expected students arriving",
            min_value=0,
            max_value=1000,
            value=int(queue_length) + 10,
            step=1,
        )
        exam_period = st.checkbox("Exam period")
        holiday = st.checkbox("Holiday")
        submitted = st.form_submit_button("Predict queue", type="primary", use_container_width=True)

    if submitted:
        try:
            wait_model, queue_model = load_prediction_models()
            values = {
                "day_of_week": day_of_week,
                "hour": int(hour),
                "service_location": service,
                "number_of_counters": int(number_of_counters),
                "queue_length": int(queue_length),
                "average_service_time": float(average_service_time),
                "students_arriving": int(students_arriving),
                "exam_period": int(exam_period),
                "holiday": int(holiday),
            }
            wait, predicted_queue = predict(wait_model, queue_model, values)
            st.session_state["prediction"] = (service, wait, predicted_queue)
        except Exception as exc:
            st.error(f"Prediction failed: {exc}")

    prediction = st.session_state.get("prediction")
    if prediction:
        service_name, wait, expected_queue = prediction
        st.markdown("#### Latest estimate")
        st.caption(f"Service location: {service_name}")
        metric1, metric2 = st.columns(2)
        metric1.metric("Estimated wait", f"{wait:.2f} min")
        metric2.metric("Predicted queue", f"{expected_queue:.2f} people")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="footnote">IntelliQueue | Estimates are based on the trained project models.</div>',
    unsafe_allow_html=True,
)

