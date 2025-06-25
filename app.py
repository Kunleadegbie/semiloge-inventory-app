import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ✅ Custom Page Config (optional but recommended)
st.set_page_config(page_title="SEMILOGE Inventory App", page_icon="📊", layout="wide")

# ✅ Custom CSS Styling
st.markdown("""
    <style>
        /* Page Banner */
        .company-banner {
            background-color: purple;
            padding: 18px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
        }
        .company-banner h1 {
            color: white;
            font-size: 32px;
            margin: 0;
        }

        /* Buttons Styling */
        div.stButton > button {
            background-color: purple;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 6px;
            font-size: 16px;
            margin: 5px 0;
        }
        div.stButton > button:hover {
            background-color: #5e0e99;
            color: #fff;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #f5f0fa;
        }

        /* Dataframe styling */
        .stDataFrame {
            border: 1px solid #ddd;
            border-radius: 6px;
        }

        /* General Text & Metric Styling */
        .big-metric {
            font-size: 24px !important;
            color: #4b0082;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

# 🎨 Company Banner
st.markdown("""
    <div style='background-color: purple; padding: 15px; border-radius: 8px; text-align: center'>
        <h1 style='color: white; margin: 0;'>SEMILOGE TEXTILES & JEWELRIES INVENTORY MANAGEMENT APP 📊</h1>
    </div>
    """, unsafe_allow_html=True)

DATABASE = 'retail_store.db'

# Helper functions
def fetch_inventory():
    conn = sqlite3.connect(DATABASE)
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

def generate_dashboard_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    total_goods = cursor.execute("SELECT SUM(quantity) FROM inventory").fetchone()[0] or 0
    total_sales = cursor.execute("SELECT SUM(sold_quantity) FROM sales").fetchone()[0] or 0
    total_revenue = cursor.execute("SELECT SUM(sold_quantity * sold_price) FROM sales").fetchone()[0] or 0.0
    conn.close()
    return total_goods, total_sales, total_revenue

def add_goods(name, type_, cost_price, selling_price, quantity):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inventory (name, type, date_of_entry, cost_price, selling_price, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, type_, datetime.now().date(), cost_price, selling_price, quantity))
    conn.commit()
    conn.close()

def sell_goods(product_id, sold_quantity):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch selling price
    cursor.execute("SELECT selling_price, quantity FROM inventory WHERE id = ?", (product_id,))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        raise ValueError("Product not found in inventory.")

    selling_price, available_qty = result

    if sold_quantity > available_qty:
        conn.close()
        raise ValueError("Not enough stock available.")

    # Deduct inventory quantity
    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (sold_quantity, product_id))

    # Record sale with fetched selling price
    cursor.execute("INSERT INTO sales (product_id, sold_quantity, sold_price, sale_date) VALUES (?, ?, ?, ?)",
                   (product_id, sold_quantity, selling_price, datetime.now().date()))

    conn.commit()
    conn.close()

def export_inventory_csv():
    df = fetch_inventory()
    file_path = 'inventory_export.csv'
    df.to_csv(file_path, index=False)
    return file_path

# Streamlit UI
st.title("SEMILOGE TEXTILES & JEWELRIES Inventory Management 📦")

menu = st.sidebar.selectbox("Menu", ["Dashboard", "View Inventory", "Add Goods", "Sell Goods"])

if menu == "Dashboard":
    total_goods, total_sales, total_revenue = generate_dashboard_data()
    st.subheader("📊 Dashboard Summary")
    st.metric("Total Goods in Stock", total_goods)
    st.metric("Total Sales Made", total_sales)
    st.metric("Total Revenue (₦)", f"{total_revenue:,.2f}")

elif menu == "View Inventory":
    st.subheader("📦 Current Inventory")
    df = fetch_inventory()
    st.dataframe(df)

    st.write("📄 Export Inventory to CSV")
    if st.button("Download CSV"):
        csv_file = export_inventory_csv()
        with open(csv_file, "rb") as f:
            st.download_button("Click to Download", f, file_name="inventory_export.csv")

elif menu == "Add Goods":
    st.subheader("➕ Add New Goods")
    with st.form("add_form"):
        name = st.text_input("Name")
        type_ = st.text_input("Type")
        cost_price = st.number_input("Cost Price (₦)", min_value=0.0)
        selling_price = st.number_input("Selling Price (₦)", min_value=0.0)
        quantity = st.number_input("Quantity", min_value=1, step=1)
        submit = st.form_submit_button("Add Goods")
        if submit:
            add_goods(name, type_, cost_price, selling_price, quantity)
            st.success("Goods added successfully ✅")

elif menu == "Sell Goods":
    st.subheader("💸 Sell Goods")
    df = fetch_inventory()

    if df.empty:
        st.warning("No products available in inventory.")
    else:
        product_names = df['name'] + " (Qty: " + df['quantity'].astype(str) + ")"
        selected = st.selectbox("Select Product", product_names)

        if selected:
            product_id = int(df.loc[product_names == selected, 'id'].values[0])
            selling_price = float(df.loc[df['id'] == product_id, 'selling_price'].values[0])
            available_qty = int(df.loc[df['id'] == product_id, 'quantity'].values[0])

            quantity = st.number_input("Quantity to sell", min_value=1, max_value=available_qty, step=1)

            if st.button("Sell"):
                if quantity > available_qty:
                    st.error("Not enough stock available.")
                else:
                    sell_goods(product_id, quantity)
                    total_price = selling_price * quantity
                    sale_date = datetime.now().strftime("%Y-%m-%d")

                    st.success("Sale completed successfully ✅")

                    # ✅ Sales Receipt
                    st.subheader("🧾 Sales Receipt")
                    st.write(f"**Item Name:** {df.loc[df['id'] == product_id, 'name'].values[0]}")
                    st.write(f"**Quantity Sold:** {quantity}")
                    st.write(f"**Unit Price:** ₦{selling_price:,.2f}")
                    st.write(f"**Total Price:** ₦{total_price:,.2f}")
                    st.write(f"**Date:** {sale_date}")


