# 🍵 Tea Shop Simulator: Synchronous vs. Asynchronous Execution

A minimal, beginner-friendly prototype designed to teach students the difference between **Synchronous (Blocking)** and **Asynchronous (Non-Blocking)** execution using Flask and Vanilla JavaScript.

---

## 🎯 Key Learning Objectives

1. **JavaScript is Single-Threaded:** It has only **one** Call Stack. If a synchronous task takes 5 seconds, everything else in the browser is blocked.
2. **Synchronous (Blocking) Execution:**
   - Monopolizes the main thread.
   - The browser UI freezes: you cannot type, animations stop, and buttons become unresponsive.
3. **Asynchronous (Non-Blocking) Execution:**
   - Hands off tasks (such as timers via `setTimeout` or network requests via `fetch()`) to browser Web APIs and the Event Loop.
   - The main thread remains responsive immediately: the cashier can accept more orders, and the user can type smoothly.
   - Shorter tasks (e.g., a 2-second order) can finish *before* a 5s, 20s, or 30s order placed earlier!

---

## 🚀 How to Run the App

1. Ensure Python 3 is installed.
2. Install Flask (if not already installed):
   ```bash
   pip install flask
   ```
3. Start the Flask application:
   ```bash
   python app.py
   ```
4. Open your browser and navigate to:
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Experiments to Try

### Experiment 1: The Freeze Test (Synchronous Blocking)
1. Select **5 Seconds** (or **20 Seconds** / **30 Seconds**) duration.
2. Click **🔴 Synchronous Order**.
3. Immediately try typing inside the **"Responsiveness Test"** input box.
4. **Observation:** You cannot type! The spinning tea icon freezes, clicks are ignored, and the UI is locked until the duration elapses.

### Experiment 2: Fluid Multi-Tasking (Asynchronous Non-Blocking)
1. Select **20 Seconds** or **30 Seconds** duration.
2. Click **🟢 Asynchronous Order**.
3. While it is brewing, type inside the **"Responsiveness Test"** input box.
4. **Observation:** Typing is smooth and instantaneous! The Call Stack is not blocked.

### Experiment 3: Out-of-Order Completion (Concurrency in the Event Loop)
1. Enter customer name **"Alice"**, choose **20s** (or **30s**), and click **🟢 Asynchronous Order**.
2. Immediately enter customer name **"Bob"**, choose **2s**, and click **🟢 Asynchronous Order**.
3. **Observation:** Even though Alice ordered first, Bob's 2-second tea finishes and moves to the **"Ready for Pickup"** bucket *first*, while Alice's tea continues steeping with a live countdown!

---

## 📁 File Structure

```text
asynchronous_prototype/
│
├── app.py                 # Minimal Flask REST API (GET /, GET /api/orders, POST /api/orders)
├── templates/
│   └── index.html         # Semantic HTML structure with input controls and order buckets
├── static/
│   ├── style.css          # Modern, responsive UI with animations and status indicators
│   └── app.js             # Well-commented JavaScript illustrating the Event Loop and fetch()
└── README.md              # Project documentation and learning guide
```
