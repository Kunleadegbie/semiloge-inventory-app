import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import altair as alt
import base64

# Database setup
DATABASE = 'retail_store.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT,
        date_of_entry DATE,
        cost_price REAL NOT NULL,
        selling_price REAL NOT NULL,
        quantity INTEGER NOT NULL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        buyer_name TEXT NOT NULL,
        sold_quantity INTEGER NOT NULL,
        sold_price REAL NOT NULL,
        sale_date DATE NOT NULL,
        FOREIGN KEY (product_id) REFERENCES inventory(id)
    )''')

    conn.commit()
    conn.close()


def fetch_inventory():
    conn = sqlite3.connect(DATABASE)
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

def fetch_sales():
    conn = sqlite3.connect(DATABASE)
    query = """
        SELECT sales.id, inventory.name AS product_name, sales.buyer_name, sales.sold_quantity,
               sales.sold_price, (sales.sold_quantity * sales.sold_price) AS total_price, sales.sale_date
        FROM sales
        JOIN inventory ON sales.product_id = inventory.id
        ORDER BY sales.sale_date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def add_product(name, type_, cost_price, selling_price, quantity):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    date_of_entry = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO inventory (name, type, cost_price, selling_price, quantity, date_of_entry) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, type_, cost_price, selling_price, quantity, date_of_entry))
    conn.commit()
    conn.close()

def sell_goods(product_id, buyer_name, sold_quantity):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch product info
    cursor.execute("SELECT selling_price, quantity FROM inventory WHERE id = ?", (product_id,))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        raise ValueError("Product not found in inventory.")

    selling_price, available_qty = result

    if sold_quantity > available_qty:
        conn.close()
        raise ValueError("Not enough stock available.")

    # Update inventory quantity
    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (sold_quantity, product_id))

    # Record sale properly
    sale_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO sales (product_id, buyer_name, sold_quantity, sold_price, sale_date)
        VALUES (?, ?, ?, ?, ?)
    """, (product_id, buyer_name, sold_quantity, selling_price, sale_date))

    conn.commit()
    conn.close()

    return selling_price

# Initialize DB
init_db()

# Styling
st.markdown("""
    <style>
    .company-banner {
        background-color: purple;
        color: white;
        padding: 15px;
        text-align: center;
        margin-bottom: 25px;
        border-radius: 10px;
    }
    .company-banner img {
        height: 50px;
        vertical-align: middle;
        margin-right: 10px;
    }
    .company-banner h1 {
        display: inline;
        font-size: 28px;
    }
    .stButton > button {
        background-color: purple;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div class="company-banner"><h1>SEMILOGE TEXTILES & JEWELRIES INVENTORY MANAGEMENT APP</h1></div>', unsafe_allow_html=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == 'admin' and password == '1234':
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# App Banner
st.markdown('<div class="company-banner"><h1>SEMILOGE TEXTILES & JEWELRIES INVENTORY MANAGEMENT APP</h1></div>', unsafe_allow_html=True)

# Sidebar Navigation
menu = st.sidebar.selectbox("Menu", ["Dashboard", "View Inventory", "Add Goods", "Sell Goods", "Sales History"])

if menu == "Dashboard":
    st.subheader("📊 Dashboard")
    inventory = fetch_inventory()
    sales = fetch_sales()
    total_goods = inventory['quantity'].sum()
    total_sales = sales['sold_quantity'].sum()
    total_revenue = (sales['sold_quantity'] * sales['sold_price']).sum()

    st.metric("Total Goods in Stock", total_goods)
    st.metric("Total Sales Made", total_sales)
    st.metric("Total Revenue Generated (₦)", f"₦{total_revenue:,.2f}")

    if not sales.empty:
        chart_data = sales.groupby('sale_date').agg({'sold_quantity':'sum', 'total_price':'sum'}).reset_index()
        st.write("### Sales Quantity Trend")
        chart = alt.Chart(chart_data).mark_bar(color='purple').encode(
            x='sale_date:T', y='sold_quantity')
        st.altair_chart(chart, use_container_width=True)

elif menu == "View Inventory":
    st.subheader("📦 Inventory Overview")
    inventory = fetch_inventory()
    if inventory.empty:
        st.info("No products in inventory.")
    else:
        st.dataframe(inventory)

elif menu == "Add Goods":
    st.subheader("📦 Add New Goods")
    with st.form("add_form"):
        name = st.text_input("Product Name")
        type_ = st.text_input("Type")
        cost_price = st.number_input("Cost Price (₦)", min_value=0.0, step=0.01)
        selling_price = st.number_input("Selling Price (₦)", min_value=0.0, step=0.01)
        quantity = st.number_input("Quantity", min_value=0, step=1)
        submitted = st.form_submit_button("Add Product")
        if submitted:
            add_product(name, type_, cost_price, selling_price, quantity)
            st.success(f"Product '{name}' added successfully!")

elif menu == "Sell Goods":
    st.subheader("💸 Sell Goods")
    df = fetch_inventory()
    if df.empty:
        st.warning("No products available in inventory.")
    else:
        product_names = df['name'] + " (Qty: " + df['quantity'].astype(str) + ")"
        selected = st.selectbox("Select Product", product_names)
        product_id = int(df.loc[product_names == selected, 'id'].values[0])
        available_qty = int(df.loc[df['id'] == product_id, 'quantity'].values[0])
        buyer_name = st.text_input("Buyer's Name")
        quantity = st.number_input("Quantity to sell", min_value=1, max_value=available_qty, step=1)
        if st.button("Sell"):
            if buyer_name == "":
                st.error("Enter buyer's name.")
            else:
                price = sell_goods(product_id, buyer_name, quantity)
                total_price = price * quantity
                sale_date = datetime.now().strftime("%Y-%m-%d")
                st.success("Sale completed successfully ✅")
                st.subheader("🧾 Sales Receipt")
                receipt_text = f"""
SEMILOGE TEXTILES & JEWELRIES
Sales Receipt
-----------------------------
Buyer: {buyer_name}
Product: {df.loc[df['id'] == product_id, 'name'].values[0]}
Quantity: {quantity}
Unit Price: ₦{price:,.2f}
Total: ₦{total_price:,.2f}
Date: {sale_date}
"""
                st.text(receipt_text)
                b64 = base64.b64encode(receipt_text.encode()).decode()
                href = f'<a href="data:file/txt;base64,{b64}" download="receipt.txt">📥 Download Receipt</a>'
                st.markdown(href, unsafe_allow_html=True)

elif menu == "Sales History":
    st.subheader("📈 Sales History")
    sales_df = fetch_sales()
    if sales_df.empty:
        st.info("No sales records available.")
    else:
        st.dataframe(sales_df)
