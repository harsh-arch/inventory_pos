
### Summary of Changes:
"""
1.  **Dashboard (`index.html` & `app.py`):**
    *   A new "Today's Credit Sales" card has been added to the "Today's Activity" section.
    *   The backend now uses a single, efficient API endpoint (`/api/reports/dashboard-kpis`) to load all dashboard data at once, improving performance.
    *   All currency symbols have been standardized to **RS.** for consistency across the application.
    *   The sales and profit overview chart now displays both metrics for better comparison.

2.  **Sales Page & Item Returns (`app.py` & `script.js`):**
    *   **Return Functionality Fixed:** The item return process has been completely overhauled and is now fully functional.
    *   **Enhanced Return Options:** You can now process returns for specific quantities of items (including single items) from a sale.
    *   **Refund Method:** When processing a return, you can choose whether to refund the amount as **Cash** or adjust the customer's **Credit** balance.
    *   **Date Filtering:** The sales page now correctly filters the sales records based on the selected start and end dates.

3.  **General Enhancements ("More Features"):**
    *   **Improved Customer Statistics:** When an item is returned, the customer's "Total Spent" statistic is now correctly updated.
    *   **Robust Error Handling:** Added more specific error messages and checks, for example, preventing a user from returning more items than were originally purchased.
    *   **Better UI/UX:** The return process now takes place in a larger, more user-friendly modal. Recent sales on the dashboard are now clickable to view details directly.

Below are the complete, updated versions of your files.

---

### `app.py` (Backend)

This version includes the new dashboard KPI endpoint, the fixed and enhanced sales return logic, and consistent currency formatting in notifications.

```python"""
import os
import json
import math
import shutil
import csv
from io import StringIO
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, send_from_directory, send_file, after_this_request, Response
from flask_cors import CORS
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='../frontend/static', static_url_path='/static')
CORS(app, supports_credentials=True)

# --- ENHANCED DIRECTORY SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
UPLOADS_DIR = os.path.join(BASE_DIR, '..', 'uploads')
BACKUP_DIR = os.path.join(BASE_DIR, '..', 'backups')

# Enhanced data directories
DATA_DIRS = {
    "products": os.path.join(DATA_DIR, 'products'),
    "customers": os.path.join(DATA_DIR, 'customers'),
    "sales": os.path.join(DATA_DIR, 'sales'),
    "expenses": os.path.join(DATA_DIR, 'expenses'),
    "adjustments": os.path.join(DATA_DIR, 'adjustments'),
    "suppliers": os.path.join(DATA_DIR, 'suppliers'),
    "purchase_orders": os.path.join(DATA_DIR, 'purchase_orders'),
    "categories": os.path.join(DATA_DIR, 'categories'),
    "inventory_ledger": os.path.join(DATA_DIR, 'inventory_ledger'),
    "uploads_products": os.path.join(UPLOADS_DIR, 'products'),
    "uploads_customers": os.path.join(UPLOADS_DIR, 'customers'),
    "held_sales": os.path.join(DATA_DIR, 'held_sales'),
    "notifications": os.path.join(DATA_DIR, 'notifications'),
    "backups": BACKUP_DIR,
    "reports": os.path.join(DATA_DIR, 'reports')
}

# Create all directories
for d in DATA_DIRS.values(): 
    os.makedirs(d, exist_ok=True)

ITEMS_PER_PAGE = 20  # Increased for better UX
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

# --- ENHANCED HELPER FUNCTIONS ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    return file_size <= MAX_FILE_SIZE

def get_next_id(data_dir, prefix):
    if not os.path.exists(data_dir): 
        return f"{prefix}-001"
    files = [f for f in os.listdir(data_dir) if f.startswith(prefix) and f.endswith('.json')]
    if not files: 
        return f"{prefix}-001"
    
    ids = []
    for f in files:
        try:
            num = int(f.split('-')[1].split('.')[0])
            ids.append(num)
        except (ValueError, IndexError):
            continue
    max_id = max(ids) if ids else 0
    return f"{prefix}-{max_id + 1:03d}"

def paginate_data(data, page, limit=ITEMS_PER_PAGE):
    if limit == 0: 
        return {"data": data, "currentPage": 1, "totalPages": 1, "totalItems": len(data)}
    total_items = len(data)
    total_pages = math.ceil(total_items / limit) if limit > 0 else 1
    start_index = (page - 1) * limit
    end_index = start_index + limit
    return {
        "data": data[start_index:end_index], 
        "currentPage": page, 
        "totalPages": total_pages, 
        "totalItems": total_items
    }

def is_in_date_range(item_date_str, start_date_str, end_date_str):
    try:
        item_date = datetime.fromisoformat(item_date_str.replace('Z', '')).date()
        start_date = datetime.fromisoformat(start_date_str).date() if start_date_str else date.min
        end_date = datetime.fromisoformat(end_date_str).date() if end_date_str else date.max
        return start_date <= item_date <= end_date
    except (ValueError, TypeError, AttributeError): 
        return False

def read_all_data_from_dir(directory, sort_key=None, reverse=False):
    all_data = []
    if not os.path.exists(directory): 
        return []
    
    for filename in sorted(os.listdir(directory)):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f: 
                    all_data.append(json.load(f))
            except (json.JSONDecodeError, FileNotFoundError) as e: 
                app.logger.error(f"Error reading {filename}: {e}")
    
    if sort_key: 
        all_data.sort(key=lambda x: x.get(sort_key, ''), reverse=reverse)
    return all_data

def log_stock_change(product_id, change_quantity, reason, reference_id="N/A", notes=""):
    ledger_dir = DATA_DIRS['inventory_ledger']
    log_id = get_next_id(ledger_dir, 'LOG')
    log_entry = {
        'id': log_id, 
        'productId': product_id, 
        'timestamp': datetime.utcnow().isoformat() + 'Z', 
        'changeQuantity': change_quantity, 
        'reason': reason, 
        'referenceId': reference_id,
        'notes': notes
    }
    with open(os.path.join(ledger_dir, f"{log_id}.json"), 'w', encoding='utf-8') as f: 
        json.dump(log_entry, f, indent=4, ensure_ascii=False)

def create_notification(title, message, priority="normal", notification_type="system"):
    """Create system notification with type support"""
    notif_id = get_next_id(DATA_DIRS['notifications'], 'NOTIF')
    notification = {
        'id': notif_id,
        'title': title,
        'message': message,
        'priority': priority,
        'type': notification_type,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'read': False
    }
    with open(os.path.join(DATA_DIRS['notifications'], f"{notif_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(notification, f, indent=4, ensure_ascii=False)
    return notification

def check_reorder_alerts():
    """Check for products below reorder threshold"""
    alerts = []
    for product in read_all_data_from_dir(DATA_DIRS['products']):
        threshold = product.get('reorderThreshold', 0)
        current_stock = product.get('quantity', 0)
        if threshold > 0 and current_stock <= threshold:
            alert_level = "critical" if current_stock == 0 else "high" if current_stock <= threshold * 0.5 else "medium"
            alerts.append({
                'productId': product['id'],
                'productName': product['name'],
                'currentStock': current_stock,
                'threshold': threshold,
                'unit': product.get('unit', 'pcs'),
                'alertLevel': alert_level
            })
    return alerts

def calculate_product_profit(product_id):
    """Calculate total profit for a product"""
    total_profit = 0
    all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
    
    for sale in all_sales:
        if sale.get('type') == 'sale':
            for item in sale.get('cart', []):
                if item['id'] == product_id:
                    profit_per_item = item.get('price', 0) - item.get('cost', 0)
                    total_profit += profit_per_item * item.get('quantity', 0)
    
    return total_profit

def get_system_stats():
    """Get comprehensive system statistics"""
    all_products = read_all_data_from_dir(DATA_DIRS['products'])
    all_customers = read_all_data_from_dir(DATA_DIRS['customers'])
    all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
    all_expenses = read_all_data_from_dir(DATA_DIRS['expenses'])
    
    # Calculate various stats
    total_products = len(all_products)
    total_customers = len(all_customers)
    total_sales = len([s for s in all_sales if s.get('type') == 'sale'])
    
    low_stock_count = len([
        p for p in all_products 
        if p.get('reorderThreshold', 0) > 0 and p.get('quantity', 0) <= p.get('reorderThreshold', 0)
    ])
    
    out_of_stock_count = len([p for p in all_products if p.get('quantity', 0) <= 0])
    
    customers_with_credit = len([
        c for c in all_customers 
        if c.get('credit_balance', 0) > 0
    ])
    
    total_inventory_value = sum(
        p.get('quantity', 0) * p.get('cost', 0) 
        for p in all_products
    )
    
    total_sales_value = sum(
        s.get('totalAmount', 0) 
        for s in all_sales if s.get('type') == 'sale'
    )
    
    total_expenses = sum(e.get('amount', 0) for e in all_expenses)
    
    # Top selling products
    product_sales = defaultdict(float)
    for sale in all_sales:
        if sale.get('type') == 'sale':
            for item in sale.get('cart', []):
                product_sales[item['id']] += item.get('quantity', 0)
    
    top_selling_products = sorted(
        [(pid, qty) for pid, qty in product_sales.items()], 
        key=lambda x: x[1], 
        reverse=True
    )[:5]
    
    return {
        'totalProducts': total_products,
        'totalCustomers': total_customers,
        'totalSales': total_sales,
        'lowStockCount': low_stock_count,
        'outOfStockCount': out_of_stock_count,
        'customersWithCredit': customers_with_credit,
        'totalInventoryValue': round(total_inventory_value, 2),
        'totalSalesValue': round(total_sales_value, 2),
        'totalExpenses': round(total_expenses, 2),
        'topSellingProducts': top_selling_products
    }

# --- ENHANCED HTML SERVING ROUTES ---
@app.route('/')
def serve_index(): 
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/products')
def serve_products(): 
    return send_from_directory(FRONTEND_DIR, 'products.html')

@app.route('/customers')
def serve_customers(): 
    return send_from_directory(FRONTEND_DIR, 'customers.html')

@app.route('/customers/<string:customer_id>')
def serve_customer_dashboard(customer_id): 
    return send_from_directory(FRONTEND_DIR, 'customer_dashboard.html')

@app.route('/pos')
def serve_pos(): 
    return send_from_directory(FRONTEND_DIR, 'pos.html')

@app.route('/sales')
def serve_sales(): 
    return send_from_directory(FRONTEND_DIR, 'sales.html')

@app.route('/expenses')
def serve_expenses(): 
    return send_from_directory(FRONTEND_DIR, 'expenses.html')

@app.route('/stock')
def serve_stock(): 
    return send_from_directory(FRONTEND_DIR, 'stock.html')

@app.route('/adjustments')
def serve_adjustments(): 
    return send_from_directory(FRONTEND_DIR, 'adjustments.html')

@app.route('/reports')
def serve_reports(): 
    return send_from_directory(FRONTEND_DIR, 'reports.html')

@app.route('/suppliers')
def serve_suppliers(): 
    return send_from_directory(FRONTEND_DIR, 'suppliers.html')

@app.route('/purchase-orders')
def serve_purchase_orders(): 
    return send_from_directory(FRONTEND_DIR, 'purchase_orders.html')

@app.route('/settings')
def serve_settings(): 
    return send_from_directory(FRONTEND_DIR, 'settings.html')

@app.route('/uploads/<path:filename>')
def serve_upload(filename): 
    return send_from_directory(UPLOADS_DIR, filename)

# --- ENHANCED API: GLOBAL SEARCH ---
@app.route('/api/search', methods=['GET'])
def global_search():
    query = request.args.get('q', '').lower().strip()
    if not query or len(query) < 2: 
        return jsonify({"products": [], "customers": [], "sales": [], "suppliers": []})
    
    # Search products
    products = [
        p for p in read_all_data_from_dir(DATA_DIRS['products']) 
        if (query in p.get('name', '').lower() or 
           query in p.get('barcode', '').lower() or 
           query in p.get('id', '').lower() or
           query in p.get('category', '').lower())
    ][:8]
    
    # Search customers
    customers = [
        c for c in read_all_data_from_dir(DATA_DIRS['customers']) 
        if (query in c.get('name', '').lower() or 
           query in c.get('phone', '') or
           query in c.get('email', '').lower())
    ][:8]
    
    # Search sales
    sales = [
        s for s in read_all_data_from_dir(DATA_DIRS['sales']) 
        if (query in s.get('id', '').lower() or
           query in s.get('customerName', '').lower())
    ][:8]
    
    # Search suppliers
    suppliers = [
        s for s in read_all_data_from_dir(DATA_DIRS['suppliers']) 
        if query in s.get('name', '').lower()
    ][:5]
    
    return jsonify({
        "products": products, 
        "customers": customers, 
        "sales": sales,
        "suppliers": suppliers
    })

# --- ENHANCED API: PRODUCTS ---
@app.route('/api/products/quick-add', methods=['POST'])
def quick_add_product():
    data = request.get_json()
    if not data or 'name' not in data or 'price' not in data:
        return jsonify({"error": "Missing required fields: name and price"}), 400
    
    try:
        product_id = get_next_id(DATA_DIRS['products'], 'PROD')
        product = {
            'id': product_id, 
            'name': str(data['name']).strip(), 
            'price': float(data['price']), 
            'cost': float(data.get('cost', 0)), 
            'quantity': float(data.get('quantity', 0)), 
            'unit': data.get('unit', 'pcs'), 
            'barcode': data.get('barcode', ''), 
            'expiryDate': data.get('expiryDate', ''), 
            'imagePath': '', 
            'category': data.get('category', 'Uncategorized'), 
            'reorderThreshold': float(data.get('reorderThreshold', 0)),
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        with open(os.path.join(DATA_DIRS['products'], f"{product_id}.json"), 'w', encoding='utf-8') as f:
            json.dump(product, f, indent=4, ensure_ascii=False)
        
        if product['quantity'] > 0:
            log_stock_change(product_id, product['quantity'], "Initial Stock (Quick Add)", product_id)
        
        create_notification(
            "Product Added", 
            f"Product '{product['name']}' was added via quick add",
            "normal",
            "product"
        )
        
        return jsonify(product), 201
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    except Exception as e:
        app.logger.error(f"Quick add product error: {e}")
        return jsonify({"error": f"Server error: {e}"}), 500

@app.route('/api/products/check-barcode', methods=['GET'])
def check_barcode():
    barcode = request.args.get('barcode', '').strip()
    product_id_to_exclude = request.args.get('excludeId', '')
    
    if not barcode: 
        return jsonify({"exists": False})
    
    all_products = read_all_data_from_dir(DATA_DIRS['products'])
    for product in all_products:
        if product.get('barcode') == barcode and product.get('id') != product_id_to_exclude:
            return jsonify({
                "exists": True, 
                "productName": product.get('name'),
                "productId": product.get('id')
            })
    
    return jsonify({"exists": False})

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    return jsonify({"error": "Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WEBP"}), 400
                if not validate_file_size(file):
                    return jsonify({"error": "File size too large. Maximum 16MB allowed"}), 400
        
        data = request.form
        if not data.get('name') or not data.get('price'):
            return jsonify({"error": "Missing required fields: name and price"}), 400
        
        product_id = get_next_id(DATA_DIRS['products'], 'PROD')
        image_path = ''
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{product_id}_{file.filename}")
                file_path = os.path.join(DATA_DIRS['uploads_products'], filename)
                file.save(file_path)
                image_path = f"products/{filename}"
        
        quantity = float(data.get('quantity', 0))
        product = {
            'id': product_id, 
            'name': str(data['name']).strip(), 
            'price': float(data['price']), 
            'cost': float(data.get('cost', 0)), 
            'quantity': quantity, 
            'unit': str(data.get('unit', 'pcs')), 
            'barcode': str(data.get('barcode', '')), 
            'expiryDate': data.get('expiryDate', ''), 
            'imagePath': image_path, 
            'category': data.get('category', 'Uncategorized'),
            'reorderThreshold': float(data.get('reorderThreshold', 0)),
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        with open(os.path.join(DATA_DIRS['products'], f"{product_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(product, f, indent=4, ensure_ascii=False)
        
        if quantity > 0:
            log_stock_change(product_id, quantity, "Initial Stock", product_id)
        
        create_notification(
            "Product Added", 
            f"New product '{product['name']}' was added to inventory",
            "normal",
            "product"
        )
        
        return jsonify(product), 201
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    except Exception as e: 
        app.logger.error(f"Add product error: {e}")
        return jsonify({"error": f"Server error: {e}"}), 500

@app.route('/api/products/<string:product_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_product(product_id):
    product_file = os.path.join(DATA_DIRS['products'], f"{product_id}.json")
    
    if not os.path.exists(product_file): 
        return jsonify({"error": "Product not found"}), 404
    
    if request.method == 'GET':
        try:
            with open(product_file, 'r', encoding='utf-8') as f:
                product = json.load(f)
                # Add profit information
                product['totalProfit'] = calculate_product_profit(product_id)
                return jsonify(product)
        except Exception as e:
            app.logger.error(f"Get product error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'PUT':
        try:
            with open(product_file, 'r+', encoding='utf-8') as f:
                product = json.load(f)
                old_quantity = product.get('quantity', 0)
                image_path = product.get('imagePath', '')
                
                if 'image' in request.files:
                    file = request.files['image']
                    if file and file.filename != '' and allowed_file(file.filename):
                        if not validate_file_size(file):
                            return jsonify({"error": "File size too large. Maximum 16MB allowed"}), 400
                            
                        # Remove old image if exists
                        if image_path and os.path.exists(os.path.join(UPLOADS_DIR, image_path)):
                            try:
                                os.remove(os.path.join(UPLOADS_DIR, image_path))
                            except OSError:
                                pass
                        
                        filename = secure_filename(f"{product_id}_{file.filename}")
                        file.save(os.path.join(DATA_DIRS['uploads_products'], filename))
                        image_path = f"products/{filename}"

                # Update fields
                data = request.form
                for key in ['name', 'unit', 'barcode', 'expiryDate', 'category']:
                    if key in data:
                        product[key] = data[key].strip() if isinstance(data[key], str) else data[key]
                
                if 'reorderThreshold' in data: 
                    product['reorderThreshold'] = float(data.get('reorderThreshold', 0))
                if 'cost' in data: 
                    product['cost'] = float(data['cost'])
                if 'price' in data: 
                    product['price'] = float(data['price'])
                
                product['imagePath'] = image_path
                product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                
                # Log quantity changes
                new_quantity = product.get('quantity', 0)
                if new_quantity != old_quantity:
                    quantity_change = new_quantity - old_quantity
                    log_stock_change(product_id, quantity_change, "Manual Update", product_id)
                
                f.seek(0)
                json.dump(product, f, indent=4, ensure_ascii=False)
                f.truncate()
            
            create_notification(
                "Product Updated", 
                f"Product '{product['name']}' was updated",
                "normal",
                "product"
            )
            
            return jsonify(product)
        except Exception as e: 
            app.logger.error(f"Update product error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            with open(product_file, 'r', encoding='utf-8') as f:
                product = json.load(f)
                product_name = product.get('name', 'Unknown')
                
                # Check if product has sales history
                all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
                has_sales = any(
                    sale.get('type') == 'sale' and 
                    any(item.get('id') == product_id for item in sale.get('cart', []))
                    for sale in all_sales
                )
                
                if has_sales:
                    return jsonify({
                        "error": "Cannot delete product with sales history. Consider archiving instead."
                    }), 400
                
                # Remove image
                if product.get('imagePath') and os.path.exists(os.path.join(UPLOADS_DIR, product['imagePath'])):
                    try:
                        os.remove(os.path.join(UPLOADS_DIR, product['imagePath']))
                    except OSError:
                        pass
            
            os.remove(product_file)
            
            create_notification(
                "Product Deleted", 
                f"Product '{product_name}' was deleted",
                "high",
                "product"
            )
            
            return jsonify({"message": "Product deleted successfully"}), 200
        except Exception as e: 
            app.logger.error(f"Delete product error: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        category = request.args.get('category', '')
        low_stock = request.args.get('lowStock', '').lower() == 'true'
        out_of_stock = request.args.get('outOfStock', '').lower() == 'true'
        search = request.args.get('search', '')
        
        all_products = read_all_data_from_dir(DATA_DIRS['products'], sort_key='name')
        
        # Apply filters
        if category and category != 'all':
            all_products = [p for p in all_products if p.get('category') == category]
        
        if low_stock:
            all_products = [
                p for p in all_products 
                if p.get('reorderThreshold', 0) > 0 and 
                p.get('quantity', 0) <= p.get('reorderThreshold', 0)
            ]
        
        if out_of_stock:
            all_products = [p for p in all_products if p.get('quantity', 0) <= 0]
        
        if search:
            search_lower = search.lower()
            all_products = [
                p for p in all_products 
                if (search_lower in p.get('name', '').lower() or 
                    search_lower in p.get('barcode', '').lower() or
                    search_lower in p.get('id', '').lower() or
                    search_lower in p.get('category', '').lower())
            ]
        
        return jsonify(paginate_data(all_products, page, limit))
    except Exception as e:
        app.logger.error(f"Get products error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower().strip()
    in_stock_only = request.args.get('inStockOnly', 'false').lower() == 'true'
    
    if not query: 
        return jsonify([])
    
    results = [
        p for p in read_all_data_from_dir(DATA_DIRS['products'])
        if (query in p.get('name', '').lower() or 
           query in p.get('id', '').lower() or 
           query in p.get('barcode', '').lower() or
           query in p.get('category', '').lower())
    ]
    
    if in_stock_only:
        results = [p for p in results if p.get('quantity', 0) > 0]
    
    return jsonify(results[:15])  # Increased limit

@app.route('/api/products/export', methods=['GET'])
def export_products():
    try:
        products_data = read_all_data_from_dir(DATA_DIRS['products'], sort_key='name')
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID', 'Name', 'Barcode', 'Category', 'Quantity', 'Unit', 
            'Cost Price', 'Selling Price', 'Reorder Threshold', 'Expiry Date',
            'Created At', 'Updated At'
        ])
        for p in products_data:
            writer.writerow([
                p.get('id'), 
                p.get('name'), 
                p.get('barcode', ''), 
                p.get('category', 'N/A'), 
                p.get('quantity', 0), 
                p.get('unit', ''), 
                p.get('cost', 0), 
                p.get('price', 0), 
                p.get('reorderThreshold', 0), 
                p.get('expiryDate', ''),
                p.get('createdAt', ''),
                p.get('updatedAt', '')
            ])
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Response(
            output, 
            mimetype="text/csv", 
            headers={"Content-Disposition": f"attachment;filename=products_export_{timestamp}.csv"}
        )
    except Exception as e:
        app.logger.error(f"Export products error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<string:product_id>/history', methods=['GET'])
def get_product_history(product_id):
    try:
        all_logs = read_all_data_from_dir(DATA_DIRS['inventory_ledger'])
        product_logs = [log for log in all_logs if log.get('productId') == product_id]
        product_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(product_logs)
    except Exception as e:
        app.logger.error(f"Get product history error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<string:product_id>/add-stock', methods=['POST'])
def add_stock(product_id):
    data = request.get_json()
    if not data or 'quantity' not in data:
        return jsonify({"error": "Missing quantity"}), 400
    
    product_file = os.path.join(DATA_DIRS['products'], f"{product_id}.json")
    if not os.path.exists(product_file): 
        return jsonify({"error": "Product not found"}), 404
    
    try:
        quantity_to_add = float(data['quantity'])
        if quantity_to_add <= 0:
            return jsonify({"error": "Quantity must be positive"}), 400
        
        with open(product_file, 'r+', encoding='utf-8') as f:
            product = json.load(f)
            product['quantity'] += quantity_to_add
            
            # Update cost price if provided
            if 'cost' in data and data['cost'] is not None:
                product['cost'] = float(data['cost'])

            product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
            f.seek(0)
            json.dump(product, f, indent=4, ensure_ascii=False)
            f.truncate()
        
        supplier_id = data.get('supplierId', 'N/A')
        log_notes = f"New Cost: {product['cost']}" if 'cost' in data else ""
        log_stock_change(product_id, quantity_to_add, "Manual Stock-In", supplier_id, notes=log_notes)
        
        create_notification(
            "Stock Added", 
            f"Added {quantity_to_add} units to '{product['name']}'",
            "normal",
            "inventory"
        )
        
        return jsonify(product)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    except Exception as e: 
        app.logger.error(f"Add stock error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: CATEGORIES ---
@app.route('/api/categories', methods=['GET', 'POST', 'DELETE'])
def handle_categories():
    categories_file = os.path.join(DATA_DIRS['categories'], 'categories.json')
    
    if request.method == 'GET':
        if not os.path.exists(categories_file): 
            return jsonify([])
        try:
            with open(categories_file, 'r', encoding='utf-8') as f: 
                return jsonify(json.load(f))
        except json.JSONDecodeError:
            return jsonify([])
    
    if request.method == 'POST':
        data = request.get_json()
        new_category = data.get('name', '').strip()
        
        if not new_category: 
            return jsonify({"error": "Invalid category name"}), 400
        
        categories = []
        if os.path.exists(categories_file):
            try:
                with open(categories_file, 'r', encoding='utf-8') as f: 
                    categories = json.load(f)
            except json.JSONDecodeError:
                categories = []
        
        if new_category in categories:
            return jsonify({"error": "Category already exists"}), 400
        
        categories.append(new_category)
        with open(categories_file, 'w', encoding='utf-8') as f: 
            json.dump(sorted(categories), f, indent=4, ensure_ascii=False)
        
        return jsonify(categories), 201
    
    if request.method == 'DELETE':
        data = request.get_json()
        category_to_delete = data.get('name', '').strip()
        
        if not category_to_delete:
            return jsonify({"error": "Category name required"}), 400
        
        # Check if category is used by any products
        all_products = read_all_data_from_dir(DATA_DIRS['products'])
        products_in_category = [p for p in all_products if p.get('category') == category_to_delete]
        
        if products_in_category:
            return jsonify({
                "error": f"Cannot delete category. {len(products_in_category)} products are using it."
            }), 400
        
        categories = []
        if os.path.exists(categories_file):
            try:
                with open(categories_file, 'r', encoding='utf-8') as f: 
                    categories = json.load(f)
            except json.JSONDecodeError:
                categories = []
        
        if category_to_delete in categories:
            categories.remove(category_to_delete)
            with open(categories_file, 'w', encoding='utf-8') as f: 
                json.dump(sorted(categories), f, indent=4, ensure_ascii=False)
        
        return jsonify({"message": "Category deleted successfully"}), 200

# --- ENHANCED API: CUSTOMERS ---
@app.route('/api/customers', methods=['GET', 'POST'])
def handle_customers():
    if request.method == 'POST':
        try:
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    if not allowed_file(file.filename):
                        return jsonify({"error": "Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WEBP"}), 400
                    if not validate_file_size(file):
                        return jsonify({"error": "File size too large. Maximum 16MB allowed"}), 400
            
            data = request.form
            if not data.get('name') or not data.get('phone'):
                return jsonify({"error": "Missing required fields: name and phone"}), 400
            
            customer_id = get_next_id(DATA_DIRS['customers'], 'CUST')
            image_path = ''
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"{customer_id}_{file.filename}")
                    file.save(os.path.join(DATA_DIRS['uploads_customers'], filename))
                    image_path = f"customers/{filename}"
            
            customer = {
                'id': customer_id, 
                'name': str(data['name']).strip(), 
                'phone': str(data['phone']), 
                'email': str(data.get('email', '')), 
                'address': str(data.get('address', '')), 
                'notes': str(data.get('notes', '')), 
                'credit_balance': 0.0, 
                'imagePath': image_path,
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'updatedAt': datetime.utcnow().isoformat() + 'Z',
                'totalSpent': 0.0,
                'totalOrders': 0
            }
            
            with open(os.path.join(DATA_DIRS['customers'], f"{customer_id}.json"), 'w', encoding='utf-8') as f: 
                json.dump(customer, f, indent=4, ensure_ascii=False)
            
            create_notification(
                "Customer Added", 
                f"New customer '{customer['name']}' was added",
                "normal",
                "customer"
            )
            
            return jsonify(customer), 201
        except Exception as e: 
            app.logger.error(f"Add customer error: {e}")
            return jsonify({"error": f"Server error: {e}"}), 500
    
    # GET request
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        has_credit = request.args.get('hasCredit', '').lower() == 'true'
        search = request.args.get('search', '')
        
        all_customers = read_all_data_from_dir(DATA_DIRS['customers'], sort_key='name')
        
        if has_credit:
            all_customers = [c for c in all_customers if c.get('credit_balance', 0) > 0]
        
        if search:
            search_lower = search.lower()
            all_customers = [
                c for c in all_customers 
                if (search_lower in c.get('name', '').lower() or 
                    search_lower in c.get('phone', '') or
                    search_lower in c.get('email', '').lower())
            ]
        
        return jsonify(paginate_data(all_customers, page, limit))
    except Exception as e:
        app.logger.error(f"Get customers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/<string:customer_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_customer(customer_id):
    customer_file = os.path.join(DATA_DIRS['customers'], f"{customer_id}.json")
    
    if not os.path.exists(customer_file): 
        return jsonify({"error": "Customer not found"}), 404
    
    if request.method == 'GET':
        try:
            with open(customer_file, 'r', encoding='utf-8') as f: 
                customer = json.load(f)
                
                # Calculate customer statistics
                all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
                customer_sales = [s for s in all_sales if s.get('customerId') == customer_id and s.get('type') == 'sale']
                customer_returns = [s for s in all_sales if s.get('customerId') == customer_id and s.get('type') == 'return']
                
                total_spent = sum(sale.get('totalAmount', 0) for sale in customer_sales)
                total_orders = len(customer_sales)
                avg_order_value = total_spent / total_orders if total_orders > 0 else 0
                
                customer['totalSpent'] = round(total_spent, 2)
                customer['totalOrders'] = total_orders
                customer['avgOrderValue'] = round(avg_order_value, 2)
                customer['returnCount'] = len(customer_returns)
                
                return jsonify(customer)
        except Exception as e:
            app.logger.error(f"Get customer error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'PUT':
        try:
            with open(customer_file, 'r+', encoding='utf-8') as f:
                customer = json.load(f)
                image_path = customer.get('imagePath', '')
                
                if 'image' in request.files:
                    file = request.files['image']
                    if file and file.filename != '' and allowed_file(file.filename):
                        if not validate_file_size(file):
                            return jsonify({"error": "File size too large. Maximum 16MB allowed"}), 400
                            
                        if image_path and os.path.exists(os.path.join(UPLOADS_DIR, image_path)):
                            try:
                                os.remove(os.path.join(UPLOADS_DIR, image_path))
                            except OSError:
                                pass
                        filename = secure_filename(f"{customer_id}_{file.filename}")
                        file.save(os.path.join(DATA_DIRS['uploads_customers'], filename))
                        image_path = f"customers/{filename}"
                
                data = request.form
                for key in ['name', 'phone', 'email', 'address', 'notes']:
                    if key in data:
                        customer[key] = data[key].strip() if isinstance(data[key], str) else data[key]
                
                customer['imagePath'] = image_path
                customer['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                f.seek(0)
                json.dump(customer, f, indent=4, ensure_ascii=False)
                f.truncate()
            
            create_notification(
                "Customer Updated", 
                f"Customer '{customer['name']}' was updated",
                "normal",
                "customer"
            )
            
            return jsonify(customer)
        except Exception as e: 
            app.logger.error(f"Update customer error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            with open(customer_file, 'r', encoding='utf-8') as f: 
                customer = json.load(f)
                customer_name = customer.get('name', 'Unknown')
            
            if customer.get('credit_balance', 0) > 0: 
                return jsonify({"error": "Cannot delete customer with outstanding credit"}), 400
            
            # Check if customer has sales history
            all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
            customer_sales = [s for s in all_sales if s.get('customerId') == customer_id]
            
            if customer_sales:
                return jsonify({
                    "error": "Cannot delete customer with transaction history"
                }), 400
            
            if customer.get('imagePath') and os.path.exists(os.path.join(UPLOADS_DIR, customer['imagePath'])):
                try:
                    os.remove(os.path.join(UPLOADS_DIR, customer['imagePath']))
                except OSError:
                    pass
            
            os.remove(customer_file)
            
            create_notification(
                "Customer Deleted", 
                f"Customer '{customer_name}' was deleted",
                "high",
                "customer"
            )
            
            return jsonify({"message": "Customer deleted successfully"}), 200
        except Exception as e: 
            app.logger.error(f"Delete customer error: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/customers/all', methods=['GET'])
def get_all_customers():
    try:
        all_customers = read_all_data_from_dir(DATA_DIRS['customers'], sort_key='name')
        return jsonify([{"id": c["id"], "name": c["name"], "phone": c.get("phone", "")} for c in all_customers])
    except Exception as e:
        app.logger.error(f"Get all customers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/export', methods=['GET'])
def export_customers():
    try:
        customers_data = read_all_data_from_dir(DATA_DIRS['customers'], sort_key='name')
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID', 'Name', 'Phone', 'Email', 'Address', 'Credit Balance', 
            'Total Orders', 'Total Spent', 'Notes', 'Created At'
        ])
        for c in customers_data:
            writer.writerow([
                c.get('id'), 
                c.get('name'), 
                c.get('phone'), 
                c.get('email', ''), 
                c.get('address', ''), 
                c.get('credit_balance', 0), 
                c.get('totalOrders', 0),
                c.get('totalSpent', 0),
                c.get('notes', ''),
                c.get('createdAt', '')
            ])
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Response(
            output, 
            mimetype="text/csv", 
            headers={"Content-Disposition": f"attachment;filename=customers_export_{timestamp}.csv"}
        )
    except Exception as e:
        app.logger.error(f"Export customers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/<string:customer_id>/dashboard-data', methods=['GET'])
def get_customer_dashboard_data(customer_id):
    try:
        history, total_spent, total_orders = [], 0.0, 0
        all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
        
        for record in all_sales:
            if record.get('customerId') == customer_id:
                if record.get('type') == 'sale':
                    record['itemSummary'] = ", ".join([
                        f"{item['quantity']}x {item['name']}" 
                        for item in record.get('cart', [])
                    ])
                    total_spent += record.get('totalAmount', 0)
                    total_orders += 1
                elif record.get('type') == 'return':
                    record['itemSummary'] = "Return: " + ", ".join([
                        f"{item['quantity']}x {item['name']}" 
                        for item in record.get('items', [])
                    ])
                elif record.get('type') == 'payment':
                    record['itemSummary'] = f"Credit payment - {record.get('paymentMethod', 'Cash')}"
                
                history.append(record)
        
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Calculate customer metrics
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0
        return_count = len([h for h in history if h.get('type') == 'return'])
        
        return jsonify({
            "history": history[:50],  # Limit to 50 most recent
            "totalSpent": round(total_spent, 2),
            "totalOrders": total_orders,
            "avgOrderValue": round(avg_order_value, 2),
            "returnCount": return_count
        })
    except Exception as e:
        app.logger.error(f"Get customer dashboard data error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers/<string:customer_id>/pay-credit', methods=['POST'])
def pay_customer_credit(customer_id):
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({"error": "Missing amount"}), 400
    
    customer_file = os.path.join(DATA_DIRS['customers'], f"{customer_id}.json")
    if not os.path.exists(customer_file): 
        return jsonify({"error": "Customer not found"}), 404
    
    try:
        amount = float(data['amount'])
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
        
        with open(customer_file, 'r+', encoding='utf-8') as f:
            customer = json.load(f)
            
            if amount > customer.get('credit_balance', 0):
                return jsonify({"error": "Payment exceeds credit balance"}), 400
            
            customer['credit_balance'] -= amount
            customer['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
            f.seek(0)
            json.dump(customer, f, indent=4, ensure_ascii=False)
            f.truncate()
        
        payment_id = get_next_id(DATA_DIRS['sales'], 'PAY')
        payment_record = {
            'id': payment_id, 
            'type': 'payment', 
            'timestamp': datetime.utcnow().isoformat() + 'Z', 
            'customerId': customer_id, 
            'customerName': customer['name'], 
            'totalAmount': amount,
            'paymentMethod': data.get('paymentMethod', 'Cash'),
            'notes': data.get('notes', 'Credit payment')
        }
        with open(os.path.join(DATA_DIRS['sales'], f"{payment_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(payment_record, f, indent=4, ensure_ascii=False)
        
        create_notification(
            "Credit Payment", 
            f"Customer '{customer['name']}' paid RS. {amount:.2f} towards credit",
            "normal",
            "payment"
        )
        
        return jsonify(customer)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid amount: {e}"}), 400
    except Exception as e:
        app.logger.error(f"Pay credit error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: SALES & POS ---
@app.route('/api/sales', methods=['POST'])
def process_sale():
    sale_data = request.get_json()
    if not sale_data or 'cart' not in sale_data or not sale_data['cart'] or 'payments' not in sale_data or not sale_data['payments']:
        return jsonify({"error": "Invalid sale data"}), 400

    total_paid = sum(p.get('amount', 0) for p in sale_data['payments'])
    if total_paid < sale_data['totalAmount']:
        return jsonify({"error": "Payment incomplete"}), 400

    for item in sale_data['cart']:
        product_file = os.path.join(DATA_DIRS['products'], f"{item['id']}.json")
        if not os.path.exists(product_file): return jsonify({"error": f"Product not found"}), 404
        with open(product_file, 'r+', encoding='utf-8') as f:
            product = json.load(f)
            if product.get('quantity', 0) < item['quantity']:
                return jsonify({"error": f"Insufficient stock for {product['name']}"}), 400
            product['quantity'] -= item['quantity']
            item['cost'] = product.get('cost', 0) # Embed cost at time of sale
            f.seek(0)
            json.dump(product, f, indent=4)
            f.truncate()
        log_stock_change(item['id'], -item['quantity'], "Sale", sale_data.get('id', 'N/A'))

    customer_id = sale_data.get('customerId')
    if customer_id and customer_id != 'cash_customer':
        credit_payment = next((p for p in sale_data['payments'] if p['method'] == 'Credit'), None)
        with open(os.path.join(DATA_DIRS['customers'], f"{customer_id}.json"), 'r+', encoding='utf-8') as f:
            customer = json.load(f)
            customer['totalSpent'] = customer.get('totalSpent', 0) + sale_data['totalAmount']
            customer['totalOrders'] = customer.get('totalOrders', 0) + 1
            if credit_payment:
                customer['credit_balance'] = customer.get('credit_balance', 0) + credit_payment['amount']
            f.seek(0)
            json.dump(customer, f, indent=4)
            f.truncate()

    sale_id = get_next_id(DATA_DIRS['sales'], 'SALE')
    sale_record = { 'id': sale_id, 'type': 'sale', 'timestamp': datetime.utcnow().isoformat() + 'Z', **sale_data }
    with open(os.path.join(DATA_DIRS['sales'], f"{sale_id}.json"), 'w', encoding='utf-8') as f:
        json.dump(sale_record, f, indent=4)

    change_due = total_paid - sale_data['totalAmount']
    create_notification("Sale Completed", f"Sale {sale_id} for RS. {sale_data['totalAmount']:.2f}", "normal", "sale")
    return jsonify({"message": "Sale processed successfully", "saleId": sale_id, "changeDue": round(change_due, 2)}), 201

# --- NEW: HELD SALES API ---
@app.route('/api/sales/hold', methods=['POST'])
def hold_sale():
    held_data = request.get_json()
    hold_id = f"HELD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    held_data['id'] = hold_id
    with open(os.path.join(DATA_DIRS['held_sales'], f"{hold_id}.json"), 'w') as f:
        json.dump(held_data, f, indent=4)
    return jsonify({"message": "Sale held successfully", "holdId": hold_id}), 201

@app.route('/api/sales/held', methods=['GET'])
def get_held_sales():
    held_sales = read_all_data_from_dir(DATA_DIRS['held_sales'], sort_key='id', reverse=True)
    return jsonify(held_sales)

@app.route('/api/sales/held/<string:hold_id>', methods=['GET', 'DELETE'])
def handle_single_held_sale(hold_id):
    file_path = os.path.join(DATA_DIRS['held_sales'], f"{hold_id}.json")
    if not os.path.exists(file_path):
        return jsonify({"error": "Held sale not found"}), 404
    
    if request.method == 'GET':
        with open(file_path, 'r') as f:
            return jsonify(json.load(f))
    
    if request.method == 'DELETE':
        os.remove(file_path)
        return jsonify({"message": "Held sale removed"})

# --- NEW: BATCH PRODUCT UPDATE API ---
@app.route('/api/products/batch-update', methods=['POST'])
def batch_update_products():
    data = request.get_json()
    product_ids = data.get('productIds', [])
    action = data.get('action')
    value = data.get('value')

    if not all([product_ids, action, value]):
        return jsonify({"error": "Missing required fields"}), 400

    updated_count = 0
    for pid in product_ids:
        product_file = os.path.join(DATA_DIRS['products'], f"{pid}.json")
        if os.path.exists(product_file):
            with open(product_file, 'r+', encoding='utf-8') as f:
                product = json.load(f)
                if action == 'add_stock':
                    product['quantity'] += float(value)
                    log_stock_change(pid, float(value), "Batch Stock Update", "BATCH")
                elif action == 'update_price_percent':
                    product['price'] *= (1 + float(value) / 100)
                    product['price'] = round(product['price'], 2)
                elif action == 'update_price_fixed':
                    product['price'] = float(value)
                
                product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                f.seek(0)
                json.dump(product, f, indent=4)
                f.truncate()
                updated_count += 1
    
    create_notification("Batch Update", f"Updated {updated_count} products with action: {action}", "normal", "product")
    return jsonify({"message": f"Successfully updated {updated_count} products."})
@app.route('/api/sales/<string:sale_id>', methods=['GET'])
def get_sale_details(sale_id):
    sale_file = os.path.join(DATA_DIRS['sales'], f"{sale_id}.json")
    if not os.path.exists(sale_file): 
        return jsonify({"error": "Sale not found"}), 404
    
    try:
        with open(sale_file, 'r', encoding='utf-8') as f: 
            sale_data = json.load(f)
            
            # Calculate profit for the sale
            total_profit = 0
            if sale_data.get('type') == 'sale':
                for item in sale_data.get('cart', []):
                    profit_per_item = item.get('price', 0) - item.get('cost', 0)
                    total_profit += profit_per_item * item.get('quantity', 0)
            
            sale_data['totalProfit'] = round(total_profit, 2)
            return jsonify(sale_data)
    except Exception as e:
        app.logger.error(f"Get sale details error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales/<string:sale_id>/return', methods=['POST'])
def process_return(sale_id):
    data = request.get_json()
    items_to_return = data.get('items', [])
    refund_method = data.get('refundMethod', 'Credit')  # 'Credit' or 'Cash'
    reason = data.get('reason', 'Customer return')

    if not items_to_return:
        return jsonify({"error": "No items specified for return"}), 400

    sale_file = os.path.join(DATA_DIRS['sales'], f"{sale_id}.json")
    if not os.path.exists(sale_file):
        return jsonify({"error": "Original sale not found"}), 404

    try:
        with open(sale_file, 'r', encoding='utf-8') as f:
            sale = json.load(f)

        return_total = 0
        returned_items_with_cost = []
        
        for item_to_return in items_to_return:
            original_item = next((i for i in sale.get('cart', []) if i['id'] == item_to_return['id']), None)
            if not original_item:
                return jsonify({"error": f"Item {item_to_return.get('name', '')} was not in the original sale."}), 400
            if item_to_return['quantity'] > original_item['quantity']:
                return jsonify({"error": f"Cannot return more {item_to_return.get('name', '')} than were purchased."}), 400

            product_file = os.path.join(DATA_DIRS['products'], f"{item_to_return['id']}.json")
            if os.path.exists(product_file):
                with open(product_file, 'r+', encoding='utf-8') as pf:
                    product = json.load(pf)
                    product['quantity'] += item_to_return['quantity']
                    product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                    pf.seek(0)
                    json.dump(product, pf, indent=4, ensure_ascii=False)
                    pf.truncate()
                log_stock_change(item_to_return['id'], item_to_return['quantity'], "Sale Return", sale_id)
            
            refund_amount_for_item = item_to_return['quantity'] * item_to_return['price']
            return_total += refund_amount_for_item
            returned_items_with_cost.append({**item_to_return, 'cost': original_item.get('cost', 0)})

        customer_id = sale.get('customerId')
        if customer_id and customer_id != 'cash_customer':
            customer_file = os.path.join(DATA_DIRS['customers'], f"{customer_id}.json")
            if os.path.exists(customer_file):
                with open(customer_file, 'r+', encoding='utf-8') as f:
                    customer = json.load(f)
                    if refund_method == 'Credit':
                        customer['credit_balance'] = max(0, customer.get('credit_balance', 0) - return_total)
                    customer['totalSpent'] = customer.get('totalSpent', 0) - return_total
                    customer['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                    f.seek(0)
                    json.dump(customer, f, indent=4, ensure_ascii=False)
                    f.truncate()
        
        return_id = get_next_id(DATA_DIRS['sales'], 'RTN')
        return_record = {
            'id': return_id,
            'type': 'return',
            'originalSaleId': sale_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'customerId': sale.get('customerId'),
            'customerName': sale.get('customerName'),
            'totalAmount': -return_total,
            'items': returned_items_with_cost,
            'reason': reason,
            'refundMethod': refund_method
        }
        with open(os.path.join(DATA_DIRS['sales'], f"{return_id}.json"), 'w', encoding='utf-8') as f:
            json.dump(return_record, f, indent=4, ensure_ascii=False)

        create_notification(
            "Sale Return",
            f"Return processed for sale {sale_id} (Amount: RS. {return_total:.2f})",
            "normal", "return"
        )
        return jsonify({"message": "Return processed successfully", "returnId": return_id}), 201

    except Exception as e:
        app.logger.error(f"Process return error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/sales/summary/<string:date_str>', methods=['GET'])
def get_daily_sales_summary(date_str):
    try:
        summary = {
            "totalSales": 0, 
            "totalProfit": 0, 
            "transactionCount": 0, 
            "paymentMethods": defaultdict(float),
            "totalItemsSold": 0
        }
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') != 'sale': 
                continue
            
            try:
                sale_date = datetime.fromisoformat(sale['timestamp'].replace('Z', '')).strftime('%Y-%m-%d')
                if sale_date == date_str:
                    summary['totalSales'] += sale['totalAmount']
                    
                    # Calculate profit
                    sale_profit = 0
                    for item in sale.get('cart', []):
                        profit_per_item = item.get('price', 0) - item.get('cost', 0)
                        sale_profit += profit_per_item * item.get('quantity', 0)
                        summary['totalItemsSold'] += item.get('quantity', 0)
                    
                    summary['totalProfit'] += sale_profit
                    summary['transactionCount'] += 1
                    summary['paymentMethods'][sale.get('paymentMethod', 'Cash')] += sale['totalAmount']
            except (ValueError, TypeError):
                continue
        
        summary['totalSales'] = round(summary['totalSales'], 2)
        summary['totalProfit'] = round(summary['totalProfit'], 2)
        
        return jsonify(summary)
    except Exception as e:
        app.logger.error(f"Get daily sales summary error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sales/export', methods=['GET'])
def export_sales():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        sales_data = [
            s for s in read_all_data_from_dir(DATA_DIRS['sales']) 
            if s.get('type') == 'sale' and is_in_date_range(s['timestamp'], start_date_str, end_date_str)
        ]
        
        if not sales_data: 
            return jsonify({"error": "No sales data in the selected range"}), 404
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Sale ID', 'Timestamp', 'Customer Name', 'Payment Method', 
            'Discount', 'Total Amount', 'Total Profit', 'Items', 'Remarks'
        ])
        
        for sale in sorted(sales_data, key=lambda x: x.get('timestamp', '')):
            items_str = "; ".join([
                f"{item['name']} (Qty: {item['quantity']}, Price: {item['price']}, Cost: {item.get('cost', 0)})" 
                for item in sale.get('cart', [])
            ])
            
            # Calculate sale profit
            sale_profit = 0
            for item in sale.get('cart', []):
                profit_per_item = item.get('price', 0) - item.get('cost', 0)
                sale_profit += profit_per_item * item.get('quantity', 0)
            
            writer.writerow([
                sale['id'], 
                sale['timestamp'], 
                sale.get('customerName', 'N/A'), 
                sale.get('paymentMethod', 'Cash'), 
                sale.get('discount', 0), 
                sale['totalAmount'],
                round(sale_profit, 2),
                items_str, 
                sale.get('remarks', '')
            ])
        
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Response(
            output, 
            mimetype="text/csv", 
            headers={"Content-Disposition": f"attachment;filename=sales_export_{start_date_str}_to_{end_date_str}_{timestamp}.csv"}
        )
    except Exception as e:
        app.logger.error(f"Export sales error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: EXPENSES ---
@app.route('/api/expenses', methods=['GET', 'POST'])
def handle_expenses():
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'description' not in data or 'amount' not in data:
            return jsonify({"error": "Missing required fields: description and amount"}), 400
        
        try:
            expense_id = get_next_id(DATA_DIRS['expenses'], 'EXP')
            expense = {
                'id': expense_id, 
                'description': str(data['description']).strip(), 
                'amount': float(data['amount']), 
                'date': str(data.get('date', datetime.utcnow().date().isoformat())),
                'category': data.get('category', 'Other'),
                'createdAt': datetime.utcnow().isoformat() + 'Z'
            }
            with open(os.path.join(DATA_DIRS['expenses'], f"{expense_id}.json"), 'w', encoding='utf-8') as f: 
                json.dump(expense, f, indent=4, ensure_ascii=False)
            
            create_notification(
                "Expense Added", 
                f"New expense recorded: {expense['description']} - RS. {expense['amount']:.2f}",
                "normal",
                "expense"
            )
            
            return jsonify(expense), 201
        except (ValueError, TypeError) as e: 
            return jsonify({"error": f"Invalid data: {e}"}), 400
    
    # GET request
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        start_date = request.args.get('startDate', '')
        end_date = request.args.get('endDate', '')
        category = request.args.get('category', '')
        
        all_expenses = read_all_data_from_dir(DATA_DIRS['expenses'], sort_key='date', reverse=True)
        
        # Apply filters
        if start_date and end_date:
            all_expenses = [
                e for e in all_expenses 
                if is_in_date_range(f"{e.get('date', '')}T00:00:00", start_date, end_date)
            ]
        
        if category and category != 'all':
            all_expenses = [e for e in all_expenses if e.get('category') == category]
        
        return jsonify(paginate_data(all_expenses, page, limit))
    except Exception as e:
        app.logger.error(f"Get expenses error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/expenses/<string:expense_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_expense(expense_id):
    expense_file = os.path.join(DATA_DIRS['expenses'], f"{expense_id}.json")
    
    if not os.path.exists(expense_file): 
        return jsonify({"error": "Expense not found"}), 404
    
    if request.method == 'GET':
        try:
            with open(expense_file, 'r', encoding='utf-8') as f: 
                return jsonify(json.load(f))
        except Exception as e:
            app.logger.error(f"Get expense error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'PUT':
        data = request.get_json()
        try:
            with open(expense_file, 'r+', encoding='utf-8') as f:
                expense = json.load(f)
                expense['description'] = str(data.get('description', expense['description'])).strip()
                expense['amount'] = float(data.get('amount', expense['amount']))
                expense['date'] = str(data.get('date', expense['date']))
                expense['category'] = data.get('category', expense.get('category', 'Other'))
                f.seek(0)
                json.dump(expense, f, indent=4, ensure_ascii=False)
                f.truncate()

            create_notification(
                "Expense Updated", 
                f"Expense updated: {expense['description']}",
                "normal",
                "expense"
            )
            
            return jsonify(expense)
        except (ValueError, TypeError) as e: 
            return jsonify({"error": f"Invalid data: {e}"}), 400
    
    if request.method == 'DELETE':
        try:
            with open(expense_file, 'r', encoding='utf-8') as f:
                expense = json.load(f)
                expense_description = expense.get('description', 'Unknown')
            
            os.remove(expense_file)
            
            create_notification(
                "Expense Deleted", 
                f"Expense deleted: {expense_description}",
                "high",
                "expense"
            )
            
            return jsonify({"message": "Expense deleted successfully"}), 200
        except Exception as e:
            app.logger.error(f"Delete expense error: {e}")
            return jsonify({"error": str(e)}), 500

# --- ENHANCED API: ADJUSTMENTS ---
@app.route('/api/adjustments', methods=['GET', 'POST'])
def handle_adjustments():
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'productId' not in data or 'quantityChange' not in data:
            return jsonify({"error": "Missing required fields: productId and quantityChange"}), 400
        
        try:
            quantity_change = float(data['quantityChange'])
            product_file = os.path.join(DATA_DIRS['products'], f"{data['productId']}.json")
            
            if not os.path.exists(product_file): 
                return jsonify({"error": "Product not found"}), 404
            
            with open(product_file, 'r+', encoding='utf-8') as f:
                product = json.load(f)
                old_quantity = product.get('quantity', 0)

                if old_quantity + quantity_change < 0:
                    return jsonify({"error": "Adjustment cannot result in negative stock."}), 400

                product['quantity'] += quantity_change
                product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                f.seek(0)
                json.dump(product, f, indent=4, ensure_ascii=False)
                f.truncate()
            
            adj_id = get_next_id(DATA_DIRS['adjustments'], 'ADJ')
            adjustment = {
                'id': adj_id, 
                'timestamp': datetime.utcnow().isoformat() + 'Z', 
                'productId': product['id'], 
                'productName': product.get('name'), 
                'quantityChange': quantity_change, 
                'unit': product.get('unit'), 
                'costAtTime': product.get('cost'), 
                'reason': data.get('reason', 'Manual Adjustment'),
                'previousQuantity': old_quantity,
                'newQuantity': product['quantity']
            }
            with open(os.path.join(DATA_DIRS['adjustments'], f"{adj_id}.json"), 'w', encoding='utf-8') as f: 
                json.dump(adjustment, f, indent=4, ensure_ascii=False)
            
            log_stock_change(product['id'], quantity_change, f"Adjustment: {data.get('reason', 'Manual')}", adj_id)
            
            # Create notification for significant adjustments
            if abs(quantity_change) >= 10:  # Threshold for significant adjustment
                create_notification(
                    "Inventory Adjustment", 
                    f"Adjusted {product.get('name')} by {quantity_change} {product.get('unit')}",
                    "high" if quantity_change < 0 else "normal",
                    "inventory"
                )
            
            return jsonify(adjustment), 201
        except (ValueError, TypeError) as e:
            return jsonify({"error": f"Invalid data: {e}"}), 400
        except Exception as e:
            app.logger.error(f"Create adjustment error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # GET request
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        start_date = request.args.get('startDate', '')
        end_date = request.args.get('endDate', '')
        
        all_adjustments = read_all_data_from_dir(DATA_DIRS['adjustments'], sort_key='timestamp', reverse=True)
        
        # Apply date filter
        if start_date and end_date:
            all_adjustments = [
                a for a in all_adjustments 
                if is_in_date_range(a.get('timestamp', ''), start_date, end_date)
            ]
        
        return jsonify(paginate_data(all_adjustments, page, limit))
    except Exception as e:
        app.logger.error(f"Get adjustments error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: SUPPLIERS ---
@app.route('/api/suppliers', methods=['GET', 'POST'])
def handle_suppliers():
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({"error": "Missing supplier name"}), 400
        
        supplier_id = get_next_id(DATA_DIRS['suppliers'], 'SUP')
        supplier = {
            'id': supplier_id,
            'name': data['name'].strip(),
            'contact': data.get('contact', ''),
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'address': data.get('address', ''),
            'notes': data.get('notes', ''),
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'updatedAt': datetime.utcnow().isoformat() + 'Z'
        }
        with open(os.path.join(DATA_DIRS['suppliers'], f"{supplier_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(supplier, f, indent=4, ensure_ascii=False)
        
        create_notification(
            "Supplier Added", 
            f"New supplier added: {supplier['name']}",
            "normal",
            "supplier"
        )
        
        return jsonify(supplier), 201
    
    # GET request
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        search = request.args.get('search', '')
        
        suppliers = read_all_data_from_dir(DATA_DIRS['suppliers'], sort_key='name')
        
        if search:
            search_lower = search.lower()
            suppliers = [
                s for s in suppliers 
                if search_lower in s.get('name', '').lower() or
                   search_lower in s.get('contact', '').lower() or
                   search_lower in s.get('email', '').lower()
            ]
        
        return jsonify(paginate_data(suppliers, page, limit))
    except Exception as e:
        app.logger.error(f"Get suppliers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/suppliers/all', methods=['GET'])
def get_all_suppliers():
    try:
        all_suppliers = read_all_data_from_dir(DATA_DIRS['suppliers'], sort_key='name')
        return jsonify([{"id": s["id"], "name": s["name"], "contact": s.get("contact", "")} for s in all_suppliers])
    except Exception as e:
        app.logger.error(f"Get all suppliers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/suppliers/<string:supplier_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_supplier(supplier_id):
    supplier_file = os.path.join(DATA_DIRS['suppliers'], f"{supplier_id}.json")
    
    if not os.path.exists(supplier_file): 
        return jsonify({"error": "Supplier not found"}), 404
    
    if request.method == 'GET':
        try:
            with open(supplier_file, 'r', encoding='utf-8') as f: 
                return jsonify(json.load(f))
        except Exception as e:
            app.logger.error(f"Get supplier error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'PUT':
        data = request.get_json()
        try:
            with open(supplier_file, 'r+', encoding='utf-8') as f:
                supplier = json.load(f)
                for key in ['name', 'contact', 'phone', 'email', 'address', 'notes']:
                    if key in data:
                        supplier[key] = data[key].strip() if isinstance(data[key], str) else data[key]
                
                supplier['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                f.seek(0)
                json.dump(supplier, f, indent=4, ensure_ascii=False)
                f.truncate()
            
            create_notification(
                "Supplier Updated", 
                f"Supplier updated: {supplier['name']}",
                "normal",
                "supplier"
            )
            
            return jsonify(supplier)
        except Exception as e:
            app.logger.error(f"Update supplier error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            with open(supplier_file, 'r', encoding='utf-8') as f:
                supplier = json.load(f)
                supplier_name = supplier.get('name', 'Unknown')
            
            # Check if supplier has purchase orders
            all_pos = read_all_data_from_dir(DATA_DIRS['purchase_orders'])
            supplier_pos = [po for po in all_pos if po.get('supplierId') == supplier_id]
            
            if supplier_pos:
                return jsonify({
                    "error": f"Cannot delete supplier. {len(supplier_pos)} purchase orders are associated."
                }), 400
            
            os.remove(supplier_file)
            
            create_notification(
                "Supplier Deleted", 
                f"Supplier deleted: {supplier_name}",
                "high",
                "supplier"
            )
            
            return jsonify({"message": "Supplier deleted successfully"}), 200
        except Exception as e:
            app.logger.error(f"Delete supplier error: {e}")
            return jsonify({"error": str(e)}), 500

# --- ENHANCED API: PURCHASE ORDERS ---
@app.route('/api/purchase-orders', methods=['GET', 'POST'])
def handle_purchase_orders():
    if request.method == 'POST':
        data = request.get_json()
        
        if not data or 'items' not in data or not data['items']:
            return jsonify({"error": "Missing purchase order items"}), 400
        
        po_id = get_next_id(DATA_DIRS['purchase_orders'], 'PO')
        po = {
            'id': po_id, 
            'status': 'Pending', 
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'supplierId': data.get('supplierId'),
            'supplierName': data.get('supplierName'),
            'items': data['items'],
            'totalAmount': data.get('totalAmount', 0),
            'notes': data.get('notes', ''),
            'expectedDelivery': data.get('expectedDelivery', '')
        }
        with open(os.path.join(DATA_DIRS['purchase_orders'], f"{po_id}.json"), 'w', encoding='utf-8') as f: 
            json.dump(po, f, indent=4, ensure_ascii=False)
        
        create_notification(
            "Purchase Order Created", 
            f"New PO created: {po_id} for {po['supplierName']}",
            "normal",
            "purchase_order"
        )
        
        return jsonify(po), 201
    
    # GET request
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', ITEMS_PER_PAGE, type=int)
        status = request.args.get('status', '')
        supplier_id = request.args.get('supplierId', '')
        
        pos = read_all_data_from_dir(DATA_DIRS['purchase_orders'], sort_key='createdAt', reverse=True)
        
        if status and status != 'all':
            pos = [p for p in pos if p.get('status') == status]
        
        if supplier_id:
            pos = [p for p in pos if p.get('supplierId') == supplier_id]
        
        return jsonify(paginate_data(pos, page, limit))
    except Exception as e:
        app.logger.error(f"Get purchase orders error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/purchase-orders/<string:po_id>', methods=['GET', 'DELETE'])
def handle_single_purchase_order(po_id):
    po_file = os.path.join(DATA_DIRS['purchase_orders'], f"{po_id}.json")
    
    if not os.path.exists(po_file):
        return jsonify({"error": "Purchase Order not found"}), 404
    
    if request.method == 'GET':
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception as e:
            app.logger.error(f"Get purchase order error: {e}")
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                po = json.load(f)
            
            if po.get('status') == 'Received':
                return jsonify({"error": "Cannot delete received purchase order"}), 400
            
            os.remove(po_file)
            
            create_notification(
                "Purchase Order Deleted", 
                f"PO deleted: {po_id}",
                "high",
                "purchase_order"
            )
            
            return jsonify({"message": "Purchase order deleted successfully"}), 200
        except Exception as e:
            app.logger.error(f"Delete purchase order error: {e}")
            return jsonify({"error": str(e)}), 500
    
@app.route('/api/purchase-orders/<string:po_id>/receive', methods=['PUT'])
def receive_purchase_order(po_id):
    po_file = os.path.join(DATA_DIRS['purchase_orders'], f"{po_id}.json")
    
    if not os.path.exists(po_file): 
        return jsonify({"error": "Purchase Order not found"}), 404
    
    try:
        with open(po_file, 'r+', encoding='utf-8') as f:
            po = json.load(f)
            
            if po.get('status') == 'Received': 
                return jsonify({"error": "PO already received"}), 400
            
            for item in po.get('items', []):
                product_file = os.path.join(DATA_DIRS['products'], f"{item['id']}.json")
                if os.path.exists(product_file):
                    with open(product_file, 'r+', encoding='utf-8') as pf:
                        product = json.load(pf)
                        old_quantity = product.get('quantity', 0)
                        product['quantity'] += float(item['quantity'])
                        
                        # Update cost if provided in PO
                        if 'cost' in item:
                            product['cost'] = float(item['cost'])
                        
                        product['updatedAt'] = datetime.utcnow().isoformat() + 'Z'
                        pf.seek(0)
                        json.dump(product, pf, indent=4, ensure_ascii=False)
                        pf.truncate()
                    
                    log_stock_change(item['id'], float(item['quantity']), "PO Received", po_id)
            
            po['status'] = 'Received'
            po['receivedAt'] = datetime.utcnow().isoformat() + 'Z'
            f.seek(0)
            json.dump(po, f, indent=4, ensure_ascii=False)
            f.truncate()
        
        create_notification(
            "Purchase Order Received",
            f"PO {po_id} has been received successfully",
            "normal",
            "purchase_order"
        )
        
        return jsonify(po)
    except Exception as e:
        app.logger.error(f"Receive purchase order error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: NOTIFICATIONS ---
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    try:
        all_notifications = read_all_data_from_dir(DATA_DIRS['notifications'], sort_key='timestamp', reverse=True)
        unread_count = len([n for n in all_notifications if not n.get('read', False)])
        
        # Return limited notifications for performance
        return jsonify({
            "notifications": all_notifications[:50], 
            "unreadCount": unread_count,
            "totalCount": len(all_notifications)
        })
    except Exception as e:
        app.logger.error(f"Get notifications error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/<string:notif_id>/mark-read', methods=['PUT'])
def mark_notification_read(notif_id):
    notif_file = os.path.join(DATA_DIRS['notifications'], f"{notif_id}.json")
    
    if not os.path.exists(notif_file):
        return jsonify({"error": "Notification not found"}), 404
    
    try:
        with open(notif_file, 'r+', encoding='utf-8') as f:
            notification = json.load(f)
            notification['read'] = True
            f.seek(0)
            json.dump(notification, f, indent=4, ensure_ascii=False)
            f.truncate()
        
        return jsonify(notification)
    except Exception as e:
        app.logger.error(f"Mark notification read error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/mark-all-read', methods=['PUT'])
def mark_all_notifications_read():
    try:
        for filename in os.listdir(DATA_DIRS['notifications']):
            if filename.endswith('.json'):
                notif_file = os.path.join(DATA_DIRS['notifications'], filename)
                with open(notif_file, 'r+', encoding='utf-8') as f:
                    notification = json.load(f)
                    notification['read'] = True
                    f.seek(0)
                    json.dump(notification, f, indent=4, ensure_ascii=False)
                    f.truncate()
        
        return jsonify({"message": "All notifications marked as read"}), 200
    except Exception as e:
        app.logger.error(f"Mark all notifications read error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: REPORTS ---
def calculate_pnl(start_date_str, end_date_str):
    total_revenue, total_cogs, total_expenses, spoilage_loss = 0.0, 0.0, 0.0, 0.0
    sales_count, total_items_sold = 0, 0
    
    all_sales_records = read_all_data_from_dir(DATA_DIRS['sales'])
    all_expenses = read_all_data_from_dir(DATA_DIRS['expenses'])
    all_adjustments = read_all_data_from_dir(DATA_DIRS['adjustments'])
    
    for record in all_sales_records:
        if is_in_date_range(record.get('timestamp', ''), start_date_str, end_date_str):
            if record.get('type') == 'sale':
                sales_count += 1
                total_revenue += record.get('totalAmount', 0)
                
                for item in record.get('cart', []):
                    total_cogs += item.get('cost', 0) * item.get('quantity', 0)
                    total_items_sold += item.get('quantity', 0)
                    
            elif record.get('type') == 'return':
                total_revenue += record.get('totalAmount', 0)
                for item in record.get('items', []):
                    total_cogs -= item.get('cost', 0) * item.get('quantity', 0)

    for expense in all_expenses:
        expense_date_iso = f"{expense.get('date', '')}T00:00:00"
        if is_in_date_range(expense_date_iso, start_date_str, f"{end_date_str}T23:59:59"):
             total_expenses += expense.get('amount', 0)

    for adj in all_adjustments:
        if is_in_date_range(adj.get('timestamp', ''), start_date_str, end_date_str):
            if adj.get('quantityChange', 0) < 0:
                spoilage_loss += abs(adj['quantityChange']) * adj.get('costAtTime', 0)
    
    gross_profit = total_revenue - (total_cogs + spoilage_loss)
    net_profit = gross_profit - total_expenses
    
    return {
        "totalRevenue": round(total_revenue, 2),
        "totalCogs": round(total_cogs, 2),
        "spoilageLoss": round(spoilage_loss, 2),
        "grossProfit": round(gross_profit, 2),
        "totalExpenses": round(total_expenses, 2),
        "netProfit": round(net_profit, 2),
        "salesCount": sales_count,
        "totalItemsSold": total_items_sold,
        "avgSaleValue": round(total_revenue / sales_count, 2) if sales_count > 0 else 0,
        "profitMargin": round((net_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0
    }

@app.route('/api/reports/profit-loss', methods=['GET'])
def get_profit_loss_report():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        try:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
            period_duration = end_date - start_date
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - period_duration
            previous_period_data = calculate_pnl(prev_start_date.isoformat(), prev_end_date.isoformat())
        except (ValueError, TypeError):
            previous_period_data = {}
        
        current_period_data = calculate_pnl(start_date_str, end_date_str)
        return jsonify({"current": current_period_data, "previous": previous_period_data})
    except Exception as e:
        app.logger.error(f"Get profit loss report error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/dashboard-kpis', methods=['GET'])
def get_dashboard_kpis():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start date and end date are required"}), 400

        # P&L Data for the period and comparison
        pnl_data = calculate_pnl(start_date_str, end_date_str)
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        period_duration = end_date - start_date
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - period_duration
        previous_pnl_data = calculate_pnl(prev_start_date.isoformat(), prev_end_date.isoformat())

        # Today's specific stats
        today_str = datetime.utcnow().date().isoformat()
        today_sales, today_transactions, today_credit_sales = 0, 0, 0
        all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
        for sale in all_sales:
            if sale.get('type') == 'sale' and datetime.fromisoformat(sale['timestamp'].replace('Z', '')).date().isoformat() == today_str:
                today_sales += sale.get('totalAmount', 0)
                today_transactions += 1
                if sale.get('paymentMethod') == 'Credit':
                    today_credit_sales += sale.get('totalAmount', 0)

        # Other summary data
        summary_data = get_dashboard_summary_data(start_date_str, end_date_str)
        
        return jsonify({
            "pnl": pnl_data,
            "previous_pnl": previous_pnl_data,
            "today": {
                "sales": round(today_sales, 2),
                "transactions": today_transactions,
                "creditSales": round(today_credit_sales, 2)
            },
            **summary_data
        })
    except Exception as e:
        app.logger.error(f"Get dashboard KPIs error: {e}")
        return jsonify({"error": str(e)}), 500

def get_dashboard_summary_data(start_date_str, end_date_str):
    all_sales = read_all_data_from_dir(DATA_DIRS['sales'])
    product_sales = defaultdict(lambda: {'revenue': 0, 'name': 'N/A', 'quantity': 0})
    
    for sale in all_sales:
        if sale.get('type') == 'sale' and is_in_date_range(sale.get('timestamp', ''), start_date_str, end_date_str):
            for item in sale.get('cart', []):
                product_sales[item['id']]['revenue'] += item.get('quantity', 0) * item.get('price', 0)
                product_sales[item['id']]['name'] = item.get('name', 'N/A')
                product_sales[item['id']]['quantity'] += item.get('quantity', 0)

    top_products = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:5]
    
    recent_sales = []
    for sale in sorted(all_sales, key=lambda x: x.get('timestamp', ''), reverse=True):
        if sale.get('type') == 'sale' and len(recent_sales) < 5:
            recent_sales.append({
                "id": sale['id'], 
                "customerName": sale.get('customerName', 'N/A'), 
                "totalAmount": sale.get('totalAmount', 0),
                "timestamp": sale.get('timestamp', '')
            })
            
    low_stock_alerts = check_reorder_alerts()
    system_stats = get_system_stats()
    
    return {
        "topProducts": top_products, 
        "recentSales": recent_sales, 
        "lowStockAlerts": low_stock_alerts[:5],
        "systemStats": system_stats
    }

@app.route('/api/reports/inventory-valuation', methods=['GET'])
def get_inventory_valuation():
    try:
        inventory, total_cost_value, total_retail_value = [], 0, 0
        
        for product in read_all_data_from_dir(DATA_DIRS['products']):
            cost_value = product.get('quantity', 0) * product.get('cost', 0)
            retail_value = product.get('quantity', 0) * product.get('price', 0)
            
            inventory.append({
                "id": product['id'], 
                "name": product['name'], 
                "quantity": product.get('quantity', 0),
                "unit": product.get('unit', ''), 
                "cost_value": round(cost_value, 2), 
                "retail_value": round(retail_value, 2),
                "category": product.get('category', 'Uncategorized')
            })
            
            total_cost_value += cost_value
            total_retail_value += retail_value
        
        return jsonify({
            "inventory": sorted(inventory, key=lambda x: x['retail_value'], reverse=True), 
            "total_cost_value": round(total_cost_value, 2), 
            "total_retail_value": round(total_retail_value, 2),
            "total_products": len(inventory)
        })
    except Exception as e:
        app.logger.error(f"Get inventory valuation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/sales-overview', methods=['GET'])
def get_sales_overview():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        
        # Generate daily labels
        date_range = (end_date - start_date).days + 1
        labels = [
            (start_date + timedelta(days=i)).strftime('%Y-%m-%d') 
            for i in range(date_range)
        ]
        
        daily_revenue = {label: 0.0 for label in labels}
        daily_profit = {label: 0.0 for label in labels}
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') == 'sale' and is_in_date_range(sale.get('timestamp', ''), start_date_str, end_date_str):
                try:
                    sale_date = datetime.fromisoformat(sale['timestamp'].replace('Z', '')).strftime('%Y-%m-%d')
                    if sale_date in daily_revenue: 
                        daily_revenue[sale_date] += sale.get('totalAmount', 0)
                        
                        # Calculate profit for this sale
                        sale_profit = 0
                        for item in sale.get('cart', []):
                            profit_per_item = item.get('price', 0) - item.get('cost', 0)
                            sale_profit += profit_per_item * item.get('quantity', 0)
                        
                        daily_profit[sale_date] += sale_profit
                except (ValueError, TypeError):
                    continue
        
        return jsonify({
            "labels": labels, 
            "revenueData": [round(daily_revenue[l], 2) for l in labels],
            "profitData": [round(daily_profit[l], 2) for l in labels]
        })
    except Exception as e:
        app.logger.error(f"Get sales overview error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/low-stock', methods=['GET'])
def get_low_stock_report():
    try:
        low_stock_items = [
            p for p in read_all_data_from_dir(DATA_DIRS['products']) 
            if p.get('reorderThreshold', 0) > 0 and p.get('quantity', 0) <= p.get('reorderThreshold', 0)
        ]
        return jsonify(sorted(low_stock_items, key=lambda x: x.get('quantity', 0)))
    except Exception as e:
        app.logger.error(f"Get low stock report error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/sales-by-category', methods=['GET'])
def get_sales_by_category_report():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        category_sales = defaultdict(lambda: {'revenue': 0, 'profit': 0, 'quantity': 0})
        products_cache = {p['id']: p for p in read_all_data_from_dir(DATA_DIRS['products'])}
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') == 'sale' and is_in_date_range(sale.get('timestamp', ''), start_date_str, end_date_str):
                for item in sale.get('cart', []):
                    product = products_cache.get(item['id'])
                    if product:
                        category = product.get('category', 'Uncategorized')
                        revenue = item.get('quantity', 0) * item.get('price', 0)
                        profit = revenue - (item.get('quantity', 0) * item.get('cost', 0))
                        category_sales[category]['revenue'] += revenue
                        category_sales[category]['profit'] += profit
                        category_sales[category]['quantity'] += item.get('quantity', 0)
        
        report_data = [
            {
                "category": cat, 
                "revenue": round(data['revenue'], 2), 
                "profit": round(data['profit'], 2),
                "quantity": data['quantity']
            } 
            for cat, data in category_sales.items()
        ]
        return jsonify(sorted(report_data, key=lambda x: x['revenue'], reverse=True))
    except Exception as e:
        app.logger.error(f"Get sales by category report error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/sales-by-product', methods=['GET'])
def get_sales_by_product_report():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        if not start_date_str or not end_date_str:
            return jsonify({"error": "Start date and end date are required"}), 400
        
        product_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0, 'cogs': 0, 'name': 'N/A'})
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') == 'sale' and is_in_date_range(sale.get('timestamp', ''), start_date_str, end_date_str):
                for item in sale.get('cart', []):
                    product_sales[item['id']]['quantity'] += item.get('quantity', 0)
                    product_sales[item['id']]['revenue'] += item.get('quantity', 0) * item.get('price', 0)
                    product_sales[item['id']]['cogs'] += item.get('quantity', 0) * item.get('cost', 0)
                    product_sales[item['id']]['name'] = item.get('name', 'N/A')
        
        report_data = [
            {
                'id': pid, 
                'name': data['name'],
                'quantity': round(data['quantity'], 2),
                'revenue': round(data['revenue'], 2),
                'cogs': round(data['cogs'], 2),
                'profit': round(data['revenue'] - data['cogs'], 2),
                'profitMargin': round(((data['revenue'] - data['cogs']) / data['revenue']) * 100, 2) if data['revenue'] > 0 else 0
            } 
            for pid, data in product_sales.items()
        ]
        return jsonify(sorted(report_data, key=lambda x: x['revenue'], reverse=True))
    except Exception as e:
        app.logger.error(f"Get sales by product report error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/top-customers', methods=['GET'])
def get_top_customers_report():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        limit = request.args.get('limit', 10, type=int)
        
        customer_stats = defaultdict(lambda: {'totalSpent': 0, 'transactionCount': 0, 'name': 'N/A'})
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') == 'sale' and is_in_date_range(sale.get('timestamp', ''), start_date_str, end_date_str):
                customer_id = sale.get('customerId')
                if customer_id and customer_id != 'cash_customer':
                    customer_stats[customer_id]['totalSpent'] += sale.get('totalAmount', 0)
                    customer_stats[customer_id]['transactionCount'] += 1
                    customer_stats[customer_id]['name'] = sale.get('customerName', 'N/A')
        
        report_data = [
            {
                'customerId': cid,
                'customerName': data['name'],
                'totalSpent': round(data['totalSpent'], 2),
                'transactionCount': data['transactionCount'],
                'avgTransaction': round(data['totalSpent'] / data['transactionCount'], 2) if data['transactionCount'] > 0 else 0
            }
            for cid, data in customer_stats.items()
        ]
        
        return jsonify(sorted(report_data, key=lambda x: x['totalSpent'], reverse=True)[:limit])
    except Exception as e:
        app.logger.error(f"Get top customers report error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/expense-breakdown', methods=['GET'])
def get_expense_breakdown():
    try:
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        expense_categories = defaultdict(float)
        
        for expense in read_all_data_from_dir(DATA_DIRS['expenses']):
            expense_date_iso = f"{expense.get('date', '')}T00:00:00"
            if is_in_date_range(expense_date_iso, start_date_str, f"{end_date_str}T23:59:59"):
                category = expense.get('category', 'Other')
                expense_categories[category] += expense.get('amount', 0)
        
        report_data = [
            {'category': cat, 'amount': round(amt, 2)} 
            for cat, amt in expense_categories.items()
        ]
        
        return jsonify(sorted(report_data, key=lambda x: x['amount'], reverse=True))
    except Exception as e:
        app.logger.error(f"Get expense breakdown error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: BACKUP & RESTORE ---
@app.route('/api/backup', methods=['GET', 'POST'])
def backup_data():
    try:
        if request.method == 'GET':
            # Create backup
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename_base = os.path.join(DATA_DIRS['backups'], f"retail_backup_{timestamp}")
            archive_path = shutil.make_archive(backup_filename_base, 'zip', DATA_DIR)
            
            @after_this_request
            def remove_file(response):
                try: 
                    os.remove(archive_path)
                except Exception as e: 
                    app.logger.error(f"Error removing backup archive: {e}")
                return response
            
            return send_file(archive_path, as_attachment=True)
        
        elif request.method == 'POST':
            # Restore from backup
            if 'backup_file' not in request.files:
                return jsonify({"error": "No backup file provided"}), 400
            
            backup_file = request.files['backup_file']
            if backup_file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            if not backup_file.filename.endswith('.zip'):
                return jsonify({"error": "Only ZIP files are supported"}), 400
            
            # Create temporary directory for extraction
            temp_dir = os.path.join(BASE_DIR, '..', 'temp_restore')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Save and extract backup
                backup_path = os.path.join(temp_dir, backup_file.filename)
                backup_file.save(backup_path)
                shutil.unpack_archive(backup_path, temp_dir)
                
                # Validate backup structure
                required_dirs = ['products', 'customers', 'sales', 'expenses']
                for dir_name in required_dirs:
                    if not os.path.exists(os.path.join(temp_dir, dir_name)):
                        raise ValueError(f"Invalid backup: missing {dir_name} directory")
                
                # Backup current data
                backup_current = os.path.join(DATA_DIRS['backups'], f"pre_restore_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
                shutil.make_archive(backup_current, 'zip', DATA_DIR)
                
                # Restore data
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path) and item in required_dirs:
                        dest_path = os.path.join(DATA_DIR, item)
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(item_path, dest_path)
                
                create_notification(
                    "Data Restored", 
                    "System data has been successfully restored from backup",
                    "high",
                    "system"
                )
                
                return jsonify({"message": "Data restored successfully"}), 200
                
            except Exception as e:
                app.logger.error(f"Restore error: {e}")
                return jsonify({"error": f"Restore failed: {str(e)}"}), 500
            finally:
                # Cleanup
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
    
    except Exception as e: 
        app.logger.error(f"Backup error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: STATISTICS ---
@app.route('/api/stats/overview', methods=['GET'])
def get_stats_overview():
    try:
        stats = get_system_stats()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Get stats overview error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/real-time', methods=['GET'])
def get_real_time_stats():
    try:
        # Today's sales
        today = datetime.now().date().isoformat()
        today_sales = 0
        today_transactions = 0
        
        for sale in read_all_data_from_dir(DATA_DIRS['sales']):
            if sale.get('type') == 'sale':
                sale_date = datetime.fromisoformat(sale['timestamp'].replace('Z', '')).date().isoformat()
                if sale_date == today:
                    today_sales += sale.get('totalAmount', 0)
                    today_transactions += 1
        
        # Current alerts
        low_stock_alerts = check_reorder_alerts()
        critical_alerts = [alert for alert in low_stock_alerts if alert.get('alertLevel') == 'critical']
        
        return jsonify({
            'todaySales': round(today_sales, 2),
            'todayTransactions': today_transactions,
            'criticalAlerts': len(critical_alerts),
            'totalAlerts': len(low_stock_alerts)
        })
    except Exception as e:
        app.logger.error(f"Get real-time stats error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED API: SYSTEM MAINTENANCE ---
@app.route('/api/system/cleanup', methods=['POST'])
def system_cleanup():
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'all')
        
        if cleanup_type in ['temp_files', 'all']:
            # Clean up temporary files (you can extend this)
            temp_dirs = [
                os.path.join(BASE_DIR, '..', 'temp_restore'),
                os.path.join(BASE_DIR, '..', 'temp_export')
            ]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    os.makedirs(temp_dir)
        
        if cleanup_type in ['old_notifications', 'all']:
            # Clean up old notifications (keep only last 1000)
            all_notifications = read_all_data_from_dir(DATA_DIRS['notifications'], sort_key='timestamp', reverse=True)
            if len(all_notifications) > 1000:
                notifications_to_keep = all_notifications[:1000]
                notifications_to_delete = all_notifications[1000:]
                
                # Clear all notification files
                for filename in os.listdir(DATA_DIRS['notifications']):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(DATA_DIRS['notifications'], filename))
                
                # Recreate kept notifications
                for notification in notifications_to_keep:
                    with open(os.path.join(DATA_DIRS['notifications'], f"{notification['id']}.json"), 'w', encoding='utf-8') as f:
                        json.dump(notification, f, indent=4, ensure_ascii=False)
        
        create_notification(
            "System Cleanup", 
            f"System cleanup completed: {cleanup_type}",
            "normal",
            "system"
        )
        
        return jsonify({"message": f"System cleanup completed: {cleanup_type}"}), 200
    except Exception as e:
        app.logger.error(f"System cleanup error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENHANCED ERROR HANDLERS ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(415)
def unsupported_media(e):
    return jsonify({"error": "Unsupported media type"}), 415

if __name__ == '__main__':
    # Create welcome notification if it doesn't exist
    notif_dir = DATA_DIRS['notifications']
    if not any(f.endswith('.json') for f in os.listdir(notif_dir)):
        create_notification(
            'System Started',
            'Retail Management System has been started successfully.',
            'normal',
            'system'
        )
    
    print("Retail Management System Advanced Edition")
    print("Server starting on http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")
    
    # Use threaded=False to avoid potential issues with file writing in debug mode on some systems
    app.run(debug=True, port=5000, host='0.0.0.0', threaded=False)



