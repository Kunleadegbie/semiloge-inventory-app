import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import base64
from supabase import create_client, Client
import os

# Supabase Credentials
SUPABASE_URL = "https://vsfchdqytkgzhxaoquzs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzZmNoZHF5dGtnemh4YW9xdXpzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEwMzM1NjEsImV4cCI6MjA2NjYwOTU2MX0.dmpQ7QMiHiBwrbIkIFV3n5NrKB2rDMsXxV_wQpmIGbc"  # Replace this with your real key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    .company-banner h1 {
        font-size: 28px;
        margin: 0;
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

# Functions
def fetch_inventory():
    res = supabase.table("inventory").select("*").execute()
    return pd.DataFrame(res.data)

def fetch_sales():
    res = supabase.table("sales").select("* , inventory(name)").execute()
    records = res.data
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df['product_name'] = df.apply(lambda x: x['inventory']['name'], axis=1)
    df.drop(columns=['inventory'], inplace=True)
    return df

def add_product(name, type_, cost_price, selling_price, quantity):
    date_of_entry = datetime.now().strftime("%Y-%m-%d")
    supabase.table("inventory").insert({
        "name": name,
        "type": type_,
        "cost_price": cost_price,
        "selling_price": selling_price,
        "quantity": quantity,
        "date_of_entry": date_of_entry
    }).execute()

def sell_goods(product_id, buyer_name, sold_quantity):
    product_res = supabase.table("inventory").select("selling_price, quantity").eq("id", product_id).single().execute()
    product = product_res.data

    if not product:
        raise ValueError("Product not found.")

    selling_price, available_qty = product['selling_price'], product['quantity']
    if sold_quantity > available_qty:
        raise ValueError("Not enough stock available.")

    # Update stock
    supabase.table("inventory").update({"quantity": available_qty - sold_quantity}).eq("id", product_id).execute()

    # Log sale
    sale_date = datetime.now().strftime("%Y-%m-%d")
    supabase.table("sales").insert({
        "product_id": product_id,
        "buyer_name": buyer_name,
        "sold_quantity": sold_quantity,
        "sold_price": selling_price,
        "sale_date": sale_date
    }).execute()

    return selling_price

# Sidebar Navigation
menu = st.sidebar.selectbox("Menu", ["Dashboard", "View Inventory", "Add Goods", "Sell Goods", "Sales History"])

if menu == "Dashboard":
    st.subheader("📊 Dashboard")
    inventory = fetch_inventory()
    sales = fetch_sales()

    total_goods = inventory['quantity'].sum() if not inventory.empty else 0
    total_sales = sales['sold_quantity'].sum() if not sales.empty else 0
    total_revenue = (sales['sold_quantity'] * sales['sold_price']).sum() if not sales.empty else 0

    st.metric("Total Goods in Stock", total_goods)
    st.metric("Total Sales Made", total_sales)
    st.metric("Total Revenue (₦)", f"₦{total_revenue:,.2f}")

    if not sales.empty:
        chart_data = sales.groupby('sale_date').agg({'sold_quantity':'sum'}).reset_index()
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
        st.warning("No products available.")
    else:
        df = df[df['quantity'] > 0]
        product_names = df['name'] + " (Qty: " + df['quantity'].astype(str) + ")"
        selected = st.selectbox("Select Product", product_names)
        selected_row = df.loc[product_names == selected]
        product_id = int(selected_row['id'].values[0])
        available_qty = int(selected_row['quantity'].values[0])
        buyer_name = st.text_input("Buyer's Name")
        quantity = st.number_input("Quantity to sell", min_value=1, max_value=available_qty, step=1)
        if st.button("Sell"):
            if buyer_name == "":
                st.error("Enter buyer's name.")
            else:
                price = sell_goods(product_id, buyer_name, quantity)
                total_price = price * quantity
                sale_date = datetime.now().strftime("%Y-%m-%d")

                st.success("Sale completed ✅")

                st.subheader("🧾 Sales Receipt")
                receipt_text = f"""
SEMILOGE TEXTILES & JEWELRIES
Sales Receipt
-----------------------------
Buyer: {buyer_name}
Product: {selected_row['name'].values[0]}
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
