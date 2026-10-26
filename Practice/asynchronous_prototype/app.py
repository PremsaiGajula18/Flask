"""
Tea Shop Simulator - Synchronous vs Asynchronous Prototype
A beginner-friendly educational Flask application demonstrating:
- Synchronous (blocking) execution vs Asynchronous (non-blocking) execution.
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# In-memory storage for orders
# Each order: { id, customer_name, duration, mode ('sync' | 'async'), status ('Preparing' | 'Ready'), created_at, completed_at }
orders = []
order_counter = 1


@app.route('/')
def index():
    """Render the main Tea Shop simulator page."""
    return render_template('index.html')


@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Return list of all orders."""
    return jsonify({
        "success": True,
        "orders": orders
    })


@app.route('/api/orders', methods=['POST'])
def save_or_update_order():
    """
    Create a new order or update an existing order status.
    Payload:
    - Creating: { "customer_name": str, "duration": int, "mode": "sync" | "async", "status": "Preparing" }
    - Updating: { "id": int, "status": "Ready" }
    """
    global order_counter
    data = request.get_json() or {}

    order_id = data.get('id')

    if order_id:
        # Update existing order
        for order in orders:
            if order['id'] == order_id:
                if 'status' in data:
                    order['status'] = data['status']
                if data['status'] == 'Ready' and not order.get('completed_at'):
                    order['completed_at'] = datetime.now().strftime('%H:%M:%S')
                return jsonify({"success": True, "order": order})
        return jsonify({"success": False, "error": "Order not found"}), 404

    # Create new order
    customer_name = data.get('customer_name', '').strip() or f"Guest #{order_counter}"
    duration = int(data.get('duration', 2))
    mode = data.get('mode', 'async')  # 'sync' or 'async'
    status = data.get('status', 'Preparing')

    new_order = {
        "id": order_counter,
        "customer_name": customer_name,
        "duration": duration,
        "mode": mode,
        "status": status,
        "created_at": datetime.now().strftime('%H:%M:%S'),
        "completed_at": datetime.now().strftime('%H:%M:%S') if status == 'Ready' else None
    }
    order_counter += 1
    orders.append(new_order)

    return jsonify({"success": True, "order": new_order}), 201


@app.route('/api/orders/clear', methods=['POST'])
def clear_orders():
    """Clear all orders for a fresh demonstration."""
    global orders, order_counter
    orders = []
    order_counter = 1
    return jsonify({"success": True, "message": "All orders cleared"})


if __name__ == '__main__':
    # Run development server
    app.run(debug=True, port=5000)
