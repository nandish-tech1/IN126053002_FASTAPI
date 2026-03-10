from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

app = FastAPI()

# ══ MODELS ════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    customer_name:    str = Field(..., min_length=2, max_length=100)
    product_id:       int = Field(..., gt=0)
    quantity:         int = Field(..., gt=0, le=100)
    delivery_address: str = Field(..., min_length=10)

class CustomerFeedback(BaseModel):
    customer_name: str           = Field(..., min_length=2, max_length=100)
    product_id:    int           = Field(..., gt=0)
    rating:        int           = Field(..., ge=1, le=5)
    comment:       Optional[str] = Field(None, max_length=300)

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity:   int = Field(..., gt=0, le=50)

class BulkOrder(BaseModel):
    company_name:  str            = Field(..., min_length=2)
    contact_email: EmailStr       # Used EmailStr for better validation
    items:         List[OrderItem] = Field(..., min_items=1)

# ══ DATA ══════════════════════════════════════════════════════════

products = [
    {'id': 1, 'name': 'Wireless Mouse', 'price': 499, 'category': 'Electronics', 'in_stock': True},
    {'id': 2, 'name': 'Notebook',       'price':  99, 'category': 'Stationery',  'in_stock': True},
    {'id': 3, 'name': 'USB Hub',        'price': 799, 'category': 'Electronics', 'in_stock': False},
    {'id': 4, 'name': 'Pen Set',        'price':  49, 'category': 'Stationery',  'in_stock': True},
]

orders = []
feedback = []
order_counter = 1

# ══ HELPERS ═══════════════════════════════════════════════════════

def find_product(product_id: int):
    return next((p for p in products if p['id'] == product_id), None)

# ══ PRODUCT ENDPOINTS ═════════════════════════════════════════════

@app.get('/')
def home():
    return {'message': 'Welcome to our E-commerce API'}

@app.get('/products')
def get_all_products():
    return {'products': products, 'total': len(products)}

@app.get('/products/summary')
def product_summary():
    in_stock = [p for p in products if p["in_stock"]]
    out_stock = [p for p in products if not p["in_stock"]]
    expensive = max(products, key=lambda p: p["price"])
    cheapest = min(products, key=lambda p: p["price"])
    categories = list(set(p["category"] for p in products))
    
    return {
        "total_products": len(products),
        "in_stock_count": len(in_stock),
        "out_of_stock_count": len(out_stock),
        "most_expensive": {"name": expensive["name"], "price": expensive["price"]},
        "cheapest": {"name": cheapest["name"], "price": cheapest["price"]},
        "categories": categories,
    }

@app.get('/products/filter')
def filter_products(
    category:  str  = Query(None),
    min_price: int  = Query(None),
    max_price: int  = Query(None),
    in_stock:  bool = Query(None),
):
    result = products
    if category:  result = [p for p in result if p['category'] == category]
    if min_price: result = [p for p in result if p['price'] >= min_price]
    if max_price: result = [p for p in result if p['price'] <= max_price]
    if in_stock is not None: result = [p for p in result if p['in_stock'] == in_stock]
    
    return {'filtered_products': result, 'count': len(result)}

@app.get('/products/compare')
def compare_products(product_id_1: int = Query(...), product_id_2: int = Query(...)):
    p1, p2 = find_product(product_id_1), find_product(product_id_2)
    if not p1 or not p2:
        return {'error': 'One or both products not found'}
    
    cheaper = p1 if p1['price'] < p2['price'] else p2
    return {
        'product_1': p1, 'product_2': p2,
        'better_value': cheaper['name'],
        'price_diff': abs(p1['price'] - p2['price'])
    }

@app.get('/products/{product_id}')
def get_product(product_id: int):
    product = find_product(product_id)
    if not product:
        return {'error': 'Product not found'}
    return {'product': product}

@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    product = find_product(product_id)
    if product:
        return {"name": product["name"], "price": product["price"]}
    return {"error": "Product not found"}

# ══ ORDER & FEEDBACK ENDPOINTS ════════════════════════════════════

@app.post('/orders')
def place_order(order_data: OrderRequest):
    global order_counter
    product = find_product(order_data.product_id)
    
    if not product: return {'error': 'Product not found'}
    if not product['in_stock']: return {'error': f"{product['name']} is out of stock"}

    order = {
        'order_id': order_counter,
        'customer_name': order_data.customer_name,
        'product': product['name'],
        'quantity': order_data.quantity,
        'total_price': product['price'] * order_data.quantity,
        'status': 'confirmed'
    }
    orders.append(order)
    order_counter += 1
    return {'message': 'Order placed successfully', 'order': order}

@app.post("/orders/bulk")
def place_bulk_order(order: BulkOrder):
    confirmed, failed, grand_total = [], [], 0
    for item in order.items:
        product = find_product(item.product_id)
        if not product:
            failed.append({"product_id": item.product_id, "reason": "Not found"})
        elif not product["in_stock"]:
            failed.append({"product_id": item.product_id, "reason": "Out of stock"})
        else:
            subtotal = product["price"] * item.quantity
            grand_total += subtotal
            confirmed.append({"product": product["name"], "qty": item.quantity, "subtotal": subtotal})
            
    return {"company": order.company_name, "confirmed": confirmed, "failed": failed, "grand_total": grand_total}

@app.get('/orders')
def get_all_orders():
    return {'orders': orders, 'total_orders': len(orders)}

@app.post("/feedback")
def submit_feedback(data: CustomerFeedback):
    feedback.append(data.dict())
    return {"message": "Feedback submitted successfully", "total_feedback": len(feedback)}