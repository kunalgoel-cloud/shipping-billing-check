import streamlit as st
import pandas as pd
import json
from pathlib import Path
from io import BytesIO
import os
import re

# Page configuration
st.set_page_config(
    page_title="Shipment Billing Validator - Mama Nourish",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File paths for persistent storage
ITEM_WEIGHTS_FILE = "item_weights_persistent.json"
RATE_CARD_FILE = "rate_card_data.json"

# Metro cities definition
METRO_CITIES = ['Delhi', 'Mumbai', 'Bangalore', 'Kolkata', 'Chennai', 
                'DELHI', 'MUMBAI', 'BANGALORE', 'KOLKATA', 'CHENNAI',
                'New Delhi', 'Navi Mumbai']

# Special zones
SPECIAL_ZONES = ['Jammu and Kashmir', 'Himachal Pradesh', 'Kerala', 
                 'Andaman', 'Lakshadweep', 'Leh', 'Ladakh',
                 'Arunachal Pradesh', 'Assam', 'Manipur', 'Meghalaya', 
                 'Mizoram', 'Nagaland', 'Tripura', 'Sikkim',
                 'J&K', 'HP', 'KL', 'AN', 'LD', 'AR', 'AS', 'MN', 'ML', 'MZ', 'NL', 'TR', 'SK']

# Hardcoded rate card (from the PDF)
RATE_CARD = {
    'Bluedart Surface': {
        'Local': {'0-500': 30.0, 'add_500': 24.0, '2kg': 96.0, 'add_1kg_2-5': 46.0, '5kg': 227.0, 'add_1kg_5-10': 45.0, '10kg': 449.0, 'add_1kg_10+': 44.0},
        'Within State': {'0-500': 36.0, 'add_500': 26.0, '2kg': 104.0, 'add_1kg_2-5': 49.0, '5kg': 250.0, 'add_1kg_5-10': 47.2, '10kg': 477.0, 'add_1kg_10+': 47.0},
        'Metro to Metro': {'0-500': 42.0, 'add_500': 33.0, '2kg': 134.0, 'add_1kg_2-5': 63.0, '5kg': 312.0, 'add_1kg_5-10': 61.0, '10kg': 617.0, 'add_1kg_10+': 61.0},
        'Rest of India': {'0-500': 47.0, 'add_500': 38.0, '2kg': 153.0, 'add_1kg_2-5': 72.0, '5kg': 355.0, 'add_1kg_5-10': 69.0, '10kg': 700.0, 'add_1kg_10+': 69.0},
        'Special Zone': {'0-500': 56.0, 'add_500': 50.0, '2kg': 202.0, 'add_1kg_2-5': 95.0, '5kg': 469.0, 'add_1kg_5-10': 92.0, '10kg': 924.0, 'add_1kg_10+': 91.0},
    },
    'Bluedart Air': {
        'Local': {'0-500': 36.0, 'add_500': 35.0},
        'Within State': {'0-500': 40.0, 'add_500': 39.0},
        'Metro to Metro': {'0-500': 46.0, 'add_500': 46.0},
        'Rest of India': {'0-500': 57.0, 'add_500': 55.0},
        'Special Zone': {'0-500': 76.0, 'add_500': 74.0},
    },
    'Delhivery Surface': {
        'Local': {'0-500': 21.0, 'add_500': 17.0, '2kg': 71.0, 'add_1kg_2-5': 27.0, '5kg': 145.0, 'add_1kg_5-10': 23.0, '10kg': 238.0, 'add_1kg_10+': 14.0},
        'Within State': {'0-500': 25.0, 'add_500': 21.0, '2kg': 83.0, 'add_1kg_2-5': 32.0, '5kg': 150.0, 'add_1kg_5-10': 24.0, '10kg': 260.0, 'add_1kg_10+': 17.0},
        'Metro to Metro': {'0-500': 31.0, 'add_500': 24.0, '2kg': 90.0, 'add_1kg_2-5': 35.0, '5kg': 178.0, 'add_1kg_5-10': 24.0, '10kg': 281.0, 'add_1kg_10+': 17.0},
        'Rest of India': {'0-500': 34.0, 'add_500': 23.0, '2kg': 97.0, 'add_1kg_2-5': 37.0, '5kg': 199.0, 'add_1kg_5-10': 25.0, '10kg': 299.0, 'add_1kg_10+': 18.0},
        'Special Zone': {'0-500': 39.0, 'add_500': 25.0, '2kg': 109.0, 'add_1kg_2-5': 39.0, '5kg': 239.0, 'add_1kg_5-10': 35.0, '10kg': 387.0, 'add_1kg_10+': 22.0},
    },
    'Delhivery Air': {
        'Local': {'0-500': 30.0, 'add_500': 28.0},
        'Within State': {'0-500': 35.0, 'add_500': 34.0},
        'Metro to Metro': {'0-500': 46.0, 'add_500': 38.0},
        'Rest of India': {'0-500': 56.0, 'add_500': 48.0},
        'Special Zone': {'0-500': 68.0, 'add_500': 62.0},
    }
}

# Load item weights from file if exists
def load_item_weights():
    if os.path.exists(ITEM_WEIGHTS_FILE):
        try:
            with open(ITEM_WEIGHTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"Error loading saved item weights: {str(e)}")
            return {}
    return {}

# Save item weights to file
def save_item_weights(weights):
    try:
        with open(ITEM_WEIGHTS_FILE, 'w') as f:
            json.dump(weights, f, indent=2)
    except Exception as e:
        st.sidebar.error(f"Error saving item weights: {str(e)}")

def determine_zone(origin_city, dest_city, dest_state):
    """Determine shipping zone based on origin and destination"""
    origin_city = str(origin_city).strip().title() if pd.notna(origin_city) else ""
    dest_city = str(dest_city).strip().title() if pd.notna(dest_city) else ""
    dest_state = str(dest_state).strip().upper() if pd.notna(dest_state) else ""
    
    # Check for special zones
    for sz in SPECIAL_ZONES:
        if sz.upper() in dest_state or sz.upper() in dest_city:
            return 'Special Zone'
    
    # Check if same city (Local)
    if origin_city and dest_city and origin_city.lower() == dest_city.lower():
        return 'Local'
    
    # Check if metro to metro
    origin_is_metro = any(metro.lower() in origin_city.lower() for metro in METRO_CITIES)
    dest_is_metro = any(metro.lower() in dest_city.lower() for metro in METRO_CITIES)
    
    if origin_is_metro and dest_is_metro:
        return 'Metro to Metro'
    
    # Within state (simplified - would need state mapping for origin)
    # For Bhiwandi (Maharashtra), check if destination is also Maharashtra
    if 'MH' in dest_state or 'MAHARASHTRA' in dest_state:
        return 'Within State'
    
    # Default to Rest of India
    return 'Rest of India'

def calculate_freight_cost(weight_kg, zone, courier):
    """Calculate freight cost based on weight, zone, and courier"""
    if courier not in RATE_CARD:
        return None, "Courier not in rate card"
    
    if zone not in RATE_CARD[courier]:
        return None, f"Zone {zone} not found for {courier}"
    
    rates = RATE_CARD[courier][zone]
    
    # Convert weight to grams for easier calculation
    weight_grams = weight_kg * 1000
    
    # For Air couriers (simpler rate structure)
    if 'Air' in courier:
        if weight_grams <= 500:
            return rates['0-500'], "Base rate (0-500g)"
        else:
            # Calculate additional 500g slabs
            additional_slabs = ((weight_grams - 500) / 500)
            if additional_slabs != int(additional_slabs):
                additional_slabs = int(additional_slabs) + 1
            else:
                additional_slabs = int(additional_slabs)
            
            cost = rates['0-500'] + (additional_slabs * rates['add_500'])
            return cost, f"Base + {additional_slabs} x 500g"
    
    # For Surface couriers (more complex structure)
    if weight_kg <= 0.5:
        return rates['0-500'], "Base rate (0-500g)"
    elif weight_kg <= 2.0:
        # Between 0.5kg and 2kg
        additional_slabs = ((weight_grams - 500) / 500)
        if additional_slabs != int(additional_slabs):
            additional_slabs = int(additional_slabs) + 1
        else:
            additional_slabs = int(additional_slabs)
        cost = rates['0-500'] + (additional_slabs * rates['add_500'])
        return cost, f"0-2kg: Base + {additional_slabs} x 500g"
    elif weight_kg <= 5.0:
        # Between 2kg and 5kg
        additional_kg = weight_kg - 2.0
        if additional_kg != int(additional_kg):
            additional_kg = int(additional_kg) + 1
        else:
            additional_kg = int(additional_kg)
        cost = rates['2kg'] + (additional_kg * rates['add_1kg_2-5'])
        return cost, f"2-5kg: 2kg base + {additional_kg} x 1kg"
    elif weight_kg <= 10.0:
        # Between 5kg and 10kg
        additional_kg = weight_kg - 5.0
        if additional_kg != int(additional_kg):
            additional_kg = int(additional_kg) + 1
        else:
            additional_kg = int(additional_kg)
        cost = rates['5kg'] + (additional_kg * rates['add_1kg_5-10'])
        return cost, f"5-10kg: 5kg base + {additional_kg} x 1kg"
    else:
        # Above 10kg
        additional_kg = weight_kg - 10.0
        if additional_kg != int(additional_kg):
            additional_kg = int(additional_kg) + 1
        else:
            additional_kg = int(additional_kg)
        cost = rates['10kg'] + (additional_kg * rates['add_1kg_10+'])
        return cost, f"10+kg: 10kg base + {additional_kg} x 1kg"

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 600 !important;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 600;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-top: 3px solid #667eea;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        color: #1e293b;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.5rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.625rem 1.5rem;
        font-weight: 500;
        transition: transform 0.2s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Dataframe text wrapping */
    .stDataFrame {
        font-size: 0.875rem;
    }
    
    .stDataFrame [data-testid="stDataFrameResizable"] div[data-testid="stDataFrameResizableCell"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        line-height: 1.5 !important;
        padding: 8px !important;
    }
    
    /* Make dataframe scrollable horizontally if needed */
    .stDataFrame {
        overflow-x: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'item_weights' not in st.session_state:
    st.session_state.item_weights = load_item_weights()
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None
if 'validation_type' not in st.session_state:
    st.session_state.validation_type = None  # 'B2C' or 'B2B'

# Header
st.markdown('<h1 class="main-title">📦 Shipment Billing Validator - Mama Nourish</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Automated billing verification with rate card validation</p>', unsafe_allow_html=True)

# Sidebar - Settings
with st.sidebar:
    st.markdown("### ⚙️ Item Weight Configuration")
    
    # Info box about persistent storage
    with st.expander("ℹ️ About Persistent Storage"):
        st.markdown("""
        **Your item configurations are saved permanently!**
        
        - All items are auto-saved to `item_weights_persistent.json`
        - Data persists across app restarts
        - No need to reconfigure items each time
        - Export/Import for backup or sharing
        
        **File Location:** Same directory as the app
        """)
    
    st.markdown("---")
    
    # Toggle between B2C and B2B configuration
    config_mode = st.radio("Configuration Mode", ["B2C (Unit Weight)", "B2B (Case Pack)"], horizontal=True)
    
    if config_mode == "B2C (Unit Weight)":
        st.markdown("#### Add B2C Item (Unit-based)")
        with st.form("add_b2c_item_form"):
            item_name = st.text_input("Item Name (e.g., SKU ID or Title)")
            col1, col2 = st.columns(2)
            with col1:
                dead_weight = st.number_input("Dead Weight per unit (kg)", min_value=0.0, step=0.01, format="%.3f")
            with col2:
                volumetric_weight = st.number_input("Volumetric Weight per unit (kg)", min_value=0.0, step=0.01, format="%.3f")
            
            if st.form_submit_button("➕ Add B2C Item", use_container_width=True):
                if item_name:
                    st.session_state.item_weights[item_name] = {
                        'dead_weight': dead_weight,
                        'volumetric_weight': volumetric_weight,
                        'type': 'B2C'
                    }
                    save_item_weights(st.session_state.item_weights)
                    st.success(f"✓ Added {item_name} (B2C)")
                    st.rerun()
                else:
                    st.error("Please enter an item name")
    
    else:  # B2B Case Pack mode
        st.markdown("#### Add B2B Item (Case Pack)")
        with st.form("add_b2b_item_form"):
            item_name = st.text_input("Item Name (e.g., Master Carton SKU)")
            col1, col2 = st.columns(2)
            with col1:
                case_pack_qty = st.number_input("Units per Case", min_value=1, step=1, value=75)
            with col2:
                case_weight = st.number_input("Chargeable Weight per Case (kg)", min_value=0.0, step=0.1, value=15.0, format="%.2f")
            
            st.info(f"📦 Each case contains {case_pack_qty} units and weighs {case_weight} kg")
            
            if st.form_submit_button("➕ Add B2B Item", use_container_width=True):
                if item_name:
                    st.session_state.item_weights[item_name] = {
                        'case_pack_qty': case_pack_qty,
                        'case_weight': case_weight,
                        'type': 'B2B'
                    }
                    save_item_weights(st.session_state.item_weights)
                    st.success(f"✓ Added {item_name} (B2B Case Pack)")
                    st.rerun()
                else:
                    st.error("Please enter an item name")
    
    st.markdown("---")
    
    # Display configured items
    if st.session_state.item_weights:
        st.markdown(f"#### Configured Items ({len(st.session_state.item_weights)})")
        
        # Search/filter
        search_term = st.text_input("🔍 Search items", "")
        
        # Filter by type
        filter_type = st.selectbox("Filter by Type", ["All", "B2C Only", "B2B Only"])
        
        filtered_items = {}
        for k, v in st.session_state.item_weights.items():
            if search_term.lower() in k.lower():
                item_type = v.get('type', 'B2C')  # Default to B2C for backward compatibility
                if filter_type == "All":
                    filtered_items[k] = v
                elif filter_type == "B2C Only" and item_type == 'B2C':
                    filtered_items[k] = v
                elif filter_type == "B2B Only" and item_type == 'B2B':
                    filtered_items[k] = v
        
        for item, weights in filtered_items.items():
            item_type = weights.get('type', 'B2C')
            
            if item_type == 'B2C':
                with st.expander(f"📦 {item[:30]}... (B2C)"):
                    st.write(f"**Type:** B2C (Unit Weight)")
                    st.write(f"**Dead Weight:** {weights.get('dead_weight', 0)} kg")
                    st.write(f"**Volumetric Weight:** {weights.get('volumetric_weight', 0)} kg")
                    if st.button(f"🗑️ Delete", key=f"del_{item}"):
                        del st.session_state.item_weights[item]
                        save_item_weights(st.session_state.item_weights)
                        st.rerun()
            else:  # B2B
                with st.expander(f"📦 {item[:30]}... (B2B Case Pack)"):
                    st.write(f"**Type:** B2B (Case Pack)")
                    st.write(f"**Units per Case:** {weights.get('case_pack_qty', 0)}")
                    st.write(f"**Weight per Case:** {weights.get('case_weight', 0)} kg")
                    if st.button(f"🗑️ Delete", key=f"del_{item}"):
                        del st.session_state.item_weights[item]
                        save_item_weights(st.session_state.item_weights)
                        st.rerun()
    else:
        st.info("No items configured yet. Add items above.")
    
    st.markdown("---")
    
    # Import/Export settings
    st.markdown("#### Import/Export Settings")
    
    # Export settings
    if st.session_state.item_weights:
        settings_json = json.dumps(st.session_state.item_weights, indent=2)
        st.download_button(
            label="📥 Export Settings",
            data=settings_json,
            file_name="item_weights_config.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Import settings
    uploaded_settings = st.file_uploader("📤 Import Settings", type=['json'], key="settings_upload")
    if uploaded_settings:
        try:
            imported_settings = json.loads(uploaded_settings.read())
            st.session_state.item_weights.update(imported_settings)
            save_item_weights(st.session_state.item_weights)
            st.success("✓ Settings imported successfully")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing settings: {str(e)}")

# Main content
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📋 B2C Validation", "🏢 B2B Validation", "💰 Rate Calculator", "📊 Results", "📄 Rate Card", "ℹ️ Instructions"])

with tab1:
    st.markdown("### B2C Billing Validation")
    
    st.info("📄 **Upload the required files:** Billing Excel (Freight sheet) and Order CSV")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Billing File (Excel)")
        billing_file = st.file_uploader(
            "Upload Mama Nourish billing file",
            type=['xlsx', 'xls'],
            key="b2c_billing_file",
            help="Upload the Excel file with 'Freight' sheet"
        )
    
    with col2:
        st.markdown("#### 📦 Order File (CSV)")
        order_file = st.file_uploader(
            "Upload order details CSV",
            type=['csv'],
            key="b2c_order_file",
            help="Upload the CSV containing SKU, AWB, and quantity"
        )
    
    # Validation button
    if st.button("🔍 Validate B2C Billing", use_container_width=True, type="primary", key="validate_b2c"):
        if not billing_file or not order_file:
            st.error("⚠️ Please upload both billing and order files")
        else:
            with st.spinner("Analyzing billing data..."):
                try:
                    # Read billing file (Freight sheet)
                    billing_df = pd.read_excel(billing_file, sheet_name='Freight')
                    
                    # Read order file
                    order_df = pd.read_csv(order_file)
                    
                    # Clean column names
                    billing_df.columns = billing_df.columns.str.strip()
                    order_df.columns = order_df.columns.str.strip()
                    
                    st.info(f"📊 Processing {len(billing_df)} billing records and {len(order_df)} order items...")
                    
                    # Process validation
                    results = []
                    
                    for idx, bill_row in billing_df.iterrows():
                        try:
                            awb = str(bill_row['AWB NUMBER']).strip() if pd.notna(bill_row.get('AWB NUMBER')) else ""
                            
                            # Skip if no AWB
                            if not awb:
                                continue
                            
                            # Get charged weight - handle non-numeric values
                            charged_weight_raw = bill_row.get('Weight', 0)
                            try:
                                charged_weight = float(charged_weight_raw)
                                # Check if weight is in grams (typically > 50 indicates grams not kg)
                                # If charged weight is abnormally high (> 50), it's likely in grams
                                if charged_weight > 50:
                                    charged_weight = charged_weight / 1000  # Convert grams to kg
                            except (ValueError, TypeError):
                                charged_weight = 0.0
                            
                            # Get other billing details
                            courier = str(bill_row.get('Courier Parent', '')).strip()
                            charged_amount = bill_row.get('Base Freight Cost WithOutTax(exCOD_exQC)', 0)
                            try:
                                charged_amount = float(charged_amount)
                            except:
                                charged_amount = 0.0
                            
                            origin_city = bill_row.get('Origin City', 'Bhiwandi')
                            dest_city = bill_row.get('Destination City', '')
                            dest_state = bill_row.get('Destination Pincode', '')  # We'll use state from orders
                            
                            # Find orders with this AWB
                            order_items = order_df[order_df['Awb No'].astype(str).str.strip() == awb]
                            
                            if order_items.empty:
                                # AWB not found in orders
                                results.append({
                                    'AWB Number': awb,
                                    'Courier': courier if courier else 'Not Specified',
                                    'Item Details': 'N/A',
                                    'Quantity': 0,
                                    'Calculated Dead Weight (kg)': 0,
                                    'Calculated Vol Weight (kg)': 0,
                                    'Billable Weight (kg)': 0,
                                    'Charged Weight (kg)': charged_weight,
                                    'Weight Status': 'N/A',
                                    'Zone': 'N/A',
                                    'Expected Freight (₹)': 0,
                                    'Charged Freight (₹)': charged_amount,
                                    'Freight Difference (₹)': 0,
                                    'Billing Status': 'Missing Order',
                                    'Analysis': 'Order ID not found in order file',
                                    'Status': 'Missing'
                                })
                            else:
                                # Calculate total weight for this AWB
                                total_dead_weight = 0
                                total_vol_weight = 0
                                items_list = []
                                items_not_configured = []
                                
                                # Get destination details from first order item
                                dest_state = str(order_items.iloc[0].get('State', '')).strip()
                                dest_city = str(order_items.iloc[0].get('city', '')).strip()
                                order_courier = str(order_items.iloc[0].get('Courier', '')).strip()
                                
                                # Use order courier if billing courier is empty
                                if not courier and order_courier:
                                    courier = order_courier
                                
                                for _, order_row in order_items.iterrows():
                                    sku_id = str(order_row.get('SKU ID', '')).strip()
                                    sku_title = str(order_row.get('SKU Title', '')).strip()
                                    quantity = order_row.get('Quantity', 1)
                                    try:
                                        quantity = int(float(quantity))
                                    except:
                                        quantity = 1
                                    
                                    # Try to find weight config (try SKU ID first, then title)
                                    item_weights = None
                                    item_name = None
                                    
                                    if sku_id in st.session_state.item_weights:
                                        item_weights = st.session_state.item_weights[sku_id]
                                        item_name = sku_id
                                    elif sku_title in st.session_state.item_weights:
                                        item_weights = st.session_state.item_weights[sku_title]
                                        item_name = sku_title
                                    
                                    if item_weights:
                                        # Check if this is a B2C item (has dead_weight/volumetric_weight)
                                        if 'dead_weight' in item_weights and 'volumetric_weight' in item_weights:
                                            total_dead_weight += item_weights['dead_weight'] * quantity
                                            total_vol_weight += item_weights['volumetric_weight'] * quantity
                                            items_list.append(f"{item_name[:20]} (x{quantity})")
                                        else:
                                            # This is a B2B case pack item, skip for B2C
                                            items_not_configured.append(f"{sku_id or sku_title} (x{quantity}) [B2B Item]")
                                    else:
                                        items_not_configured.append(f"{sku_id or sku_title} (x{quantity})")
                                
                                # Determine billable weight (higher of dead/vol)
                                billable_weight = max(total_dead_weight, total_vol_weight)
                                
                                # Calculate the weight slab boundaries
                                # Convert to grams for slab calculation
                                billable_weight_grams = billable_weight * 1000
                                charged_weight_grams = charged_weight * 1000
                                
                                # Calculate expected chargeable weight (rounded up to nearest 500g slab)
                                if billable_weight_grams <= 500:
                                    expected_chargeable_weight_kg = 0.5
                                else:
                                    # Round up to nearest 500g
                                    slabs_needed = int((billable_weight_grams - 1) / 500) + 1
                                    expected_chargeable_weight_kg = (slabs_needed * 500) / 1000
                                
                                # Determine which 500g slab the billable weight falls into
                                # Slab 1: 0-500g, Slab 2: 501-1000g, Slab 3: 1001-1500g, etc.
                                if billable_weight_grams <= 500:
                                    slab_min_kg = 0.0
                                    slab_max_kg = 0.5
                                else:
                                    # Calculate which slab the billable weight is in
                                    slab_number = int((billable_weight_grams - 1) / 500) + 1
                                    slab_min_kg = ((slab_number - 1) * 500) / 1000
                                    slab_max_kg = (slab_number * 500) / 1000
                                
                                # Determine zone
                                zone = determine_zone(origin_city, dest_city, dest_state)
                                
                                # Calculate expected freight
                                expected_freight = None
                                freight_calc_note = ""
                                
                                if courier and billable_weight > 0:
                                    expected_freight, freight_calc_note = calculate_freight_cost(billable_weight, zone, courier)
                                
                                # Determine statuses
                                weight_status = "OK"
                                billing_status = "OK"
                                analysis_parts = []
                                status_flag = 'OK'
                                
                                # Check weight discrepancy
                                # New Rule per user clarification:
                                # 1. If charged_weight <= expected_chargeable_weight (ideal 500g slab): OK
                                # 2. If charged_weight > expected_chargeable_weight: ERROR - Weight Overcharged
                                # 3. Validate shipping fee separately
                                
                                if charged_weight > 0 and billable_weight > 0:
                                    # Check if charged weight exceeds the expected chargeable weight slab
                                    if charged_weight > expected_chargeable_weight_kg:
                                        weight_status = "Weight Error - Overcharged"
                                        analysis_parts.append(f"Charged weight ({charged_weight:.3f}kg) exceeds expected chargeable slab ({expected_chargeable_weight_kg:.3f}kg)")
                                        status_flag = 'Error'
                                    # If charged weight is within expected slab, it's OK
                                    # (even if it's less than billable weight - shipper's choice)
                                
                                # Check courier
                                if not courier:
                                    analysis_parts.append("Courier not specified")
                                    if status_flag == 'OK':
                                        status_flag = 'Warning'
                                    billing_status = "Courier Missing"
                                
                                # Check freight amount validation
                                freight_status = "OK"
                                if expected_freight is not None and charged_amount > 0:
                                    freight_diff = charged_amount - expected_freight
                                    if abs(freight_diff) > 0.5:  # Allow 0.5 rupee tolerance
                                        if freight_diff > 0:
                                            freight_status = "Freight Overcharged"
                                            analysis_parts.append(f"Freight overcharged by ₹{freight_diff:.2f}")
                                            if status_flag == 'OK':
                                                status_flag = 'Warning'
                                        else:
                                            freight_status = "Freight Undercharged"
                                            analysis_parts.append(f"Freight undercharged by ₹{abs(freight_diff):.2f}")
                                            if status_flag == 'OK':
                                                status_flag = 'Warning'
                                    
                                    # Update billing status based on freight validation
                                    if freight_status != "OK":
                                        billing_status = freight_status
                                elif expected_freight is None and courier:
                                    analysis_parts.append(f"Cannot calculate freight: {freight_calc_note}")
                                    billing_status = "Cannot Verify Freight"
                                    if status_flag == 'OK':
                                        status_flag = 'Warning'
                                
                                # Check for unconfigured items
                                if items_not_configured:
                                    analysis_parts.append(f"Items not configured: {', '.join(items_not_configured)}")
                                    if status_flag == 'OK':
                                        status_flag = 'Warning'
                                
                                if not analysis_parts:
                                    analysis_parts.append("All checks passed")
                                
                                results.append({
                                    'AWB Number': awb,
                                    'Courier': courier if courier else '⚠️ NOT SPECIFIED',
                                    'Item Details': ', '.join(items_list) if items_list else 'Not configured',
                                    'Quantity': len(order_items),
                                    'Calculated Dead Weight (kg)': round(total_dead_weight, 3),
                                    'Calculated Vol Weight (kg)': round(total_vol_weight, 3),
                                    'Billable Weight (kg)': round(billable_weight, 3),
                                    'Expected Chargeable Weight (kg)': round(expected_chargeable_weight_kg, 3),
                                    'Charged Weight (kg)': round(charged_weight, 3),
                                    'Weight Status': weight_status,
                                    'Zone': zone,
                                    'Expected Freight (₹)': round(expected_freight, 2) if expected_freight else 'N/A',
                                    'Charged Freight (₹)': round(charged_amount, 2),
                                    'Freight Difference (₹)': round(freight_diff, 2) if expected_freight and charged_amount > 0 else 'N/A',
                                    'Freight Status': freight_status,
                                    'Analysis': ' | '.join(analysis_parts),
                                    'Status': status_flag
                                })
                        
                        except Exception as row_error:
                            st.warning(f"Error processing AWB {awb}: {str(row_error)}")
                            continue
                    
                    # Store results
                    if results:
                        st.session_state.validation_results = pd.DataFrame(results)
                        st.session_state.validation_type = 'B2C'
                        st.success(f"✅ Validation completed! Processed {len(results)} AWBs")
                        st.rerun()
                    else:
                        st.error("No valid results generated. Please check your files.")
                        
                except Exception as e:
                    st.error(f"❌ Error during validation: {str(e)}")
                    import traceback
                    with st.expander("View detailed error"):
                        st.code(traceback.format_exc())

with tab2:
    st.markdown("### B2B Billing Validation (Safexpress)")
    
    st.info("📄 **Upload B2B files:** Billing Excel (Invoice sheet) and Order CSV")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 B2B Billing File (Excel)")
        b2b_billing_file = st.file_uploader(
            "Upload B2B Invoice Excel",
            type=['xlsx', 'xls'],
            key="b2b_billing_file",
            help="Upload the Excel file with 'Invoice' sheet"
        )
    
    with col2:
        st.markdown("#### 📦 B2B Order File (CSV)")
        b2b_order_file = st.file_uploader(
            "Upload B2B order details CSV",
            type=['csv'],
            key="b2b_order_file",
            help="Upload the CSV containing SKU, AWB, and quantity"
        )
    
    # Safexpress rate card (from PDF)
    SAFEXPRESS_RATES = {
        'N1': {'N1': 6.48, 'N2': 6.48, 'E': 10.8, 'NE': 16.2, 'W1': 7.56, 'W2': 8.64, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
        'N2': {'N1': 6.48, 'N2': 6.48, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 8.64, 'S1': 10.8, 'S2': 10.8, 'C': 7.56},
        'E': {'N1': 8.64, 'N2': 10.8, 'E': 6.48, 'NE': 7.56, 'W1': 8.64, 'W2': 10.8, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
        'NE': {'N1': 8.64, 'N2': 10.8, 'E': 7.56, 'NE': 6.48, 'W1': 10.8, 'W2': 10.8, 'S1': 10.8, 'S2': 16.2, 'C': 8.64},
        'W1': {'N1': 7.56, 'N2': 8.64, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 6.48, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
        'W2': {'N1': 8.64, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 6.48, 'S1': 7.56, 'S2': 10.8, 'C': 7.56},
        'S1': {'N1': 8.64, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 7.56, 'S1': 6.48, 'S2': 7.56, 'C': 7.56},
        'S2': {'N1': 10.8, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 8.64, 'S1': 6.48, 'S2': 6.48, 'C': 7.56},
        'C': {'N1': 7.56, 'N2': 8.64, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 7.56, 'S1': 7.56, 'S2': 10.8, 'C': 6.48}
    }
    
    METRO_CITIES = ['AHMEDABAD', 'BENGALURU', 'CHENNAI', 'DELHI', 'HYDERABAD', 'KOLKATA', 'MUMBAI', 'PUNE']
    MIN_CHARGEABLE_WEIGHT = 15  # kg
    MIN_FREIGHT = 400  # Rs
    FSC_PERCENT = 20  # 20%
    DOCKET_CHARGE = 100  # Rs
    FOV_CHARGE = 100  # Rs (or 0.1% of invoice value, whichever is higher)
    METRO_CHARGE = 100  # Rs
    
    # B2B Validation button
    if st.button("🔍 Validate B2B Billing", use_container_width=True, type="primary", key="validate_b2b"):
        if not b2b_billing_file or not b2b_order_file:
            st.error("⚠️ Please upload both B2B billing and order files")
        else:
            with st.spinner("Analyzing B2B billing data..."):
                try:
                    # Read B2B billing file
                    b2b_billing_df = pd.read_excel(b2b_billing_file, sheet_name='Invoice')
                    
                    # The first row contains headers
                    b2b_billing_df.columns = b2b_billing_df.iloc[0]
                    b2b_billing_df = b2b_billing_df[1:].reset_index(drop=True)
                    
                    # Read B2B order file
                    b2b_order_df = pd.read_csv(b2b_order_file)
                    
                    st.info(f"📊 Processing {len(b2b_billing_df)} B2B billing records...")
                    
                    # Process B2B validation
                    b2b_results = []
                    
                    for idx, bill_row in b2b_billing_df.iterrows():
                        try:
                            awb = str(bill_row.get('AWB', '')).strip()
                            if not awb:
                                continue
                            
                            # Get billing details
                            courier = str(bill_row.get('Courier Name', '')).strip()
                            applied_zone = str(bill_row.get('Applied Zone', '')).strip()
                            
                            # Parse zone (e.g., "W1→S1" to pickup W1, drop S1)
                            if '→' in applied_zone:
                                pickup_zone, drop_zone = applied_zone.split('→')
                            else:
                                pickup_zone = drop_zone = applied_zone
                            
                            # Get charged weight (should already be in kg)
                            charged_weight_raw = bill_row.get('Chargeable Weight', 0)
                            try:
                                charged_weight = float(charged_weight_raw)
                            except:
                                charged_weight = 0.0
                            
                            # Get charged amounts
                            freight_charged = float(bill_row.get('Freight Amount (Billing)', 0) or 0)
                            fsc_charged = float(bill_row.get('Fuel Surcharge (Billing)', 0) or 0)
                            total_charged = float(bill_row.get('Total Charges (Billing)', 0) or 0)
                            
                            # Find orders with this AWB
                            order_items = b2b_order_df[b2b_order_df['Awb No'].astype(str).str.strip() == awb]
                            
                            if order_items.empty:
                                b2b_results.append({
                                    'AWB Number': awb,
                                    'Courier': courier,
                                    'Zone': applied_zone,
                                    'Item Details': 'N/A',
                                    'Quantity': 0,
                                    'Billable Weight (kg)': 0,
                                    'Expected Chargeable Weight (kg)': 0,
                                    'Charged Weight (kg)': charged_weight,
                                    'Weight Status': 'N/A',
                                    'Expected Freight (₹)': 0,
                                    'Charged Freight (₹)': freight_charged,
                                    'Expected Total (₹)': 0,
                                    'Charged Total (₹)': total_charged,
                                    'Analysis': 'Order ID not found in order file',
                                    'Status': 'Missing'
                                })
                            else:
                                # Calculate total weight using BOTH case pack logic AND unit weight logic
                                # A single AWB can have mixed items: B2B case packs AND B2C units
                                # B2C units are packed into loose cases (4kg or 8kg) based on volumetric weight
                                
                                LOOSE_CASE_4KG = 4.0  # 4 kg loose case
                                LOOSE_CASE_8KG = 8.0  # 8 kg loose case
                                
                                total_cases = 0
                                total_weight_from_cases = 0
                                total_loose_weight_volumetric = 0  # For determining loose case size
                                items_list = []
                                items_not_configured = []
                                loose_units_list = []
                                
                                for _, order_row in order_items.iterrows():
                                    sku_id = str(order_row.get('SKU ID', '')).strip()
                                    sku_title = str(order_row.get('SKU Title', '')).strip()
                                    quantity = order_row.get('Quantity', 1)
                                    try:
                                        quantity = int(float(quantity))
                                    except:
                                        quantity = 1
                                    
                                    # Try to find item config
                                    item_config = None
                                    item_name = None
                                    
                                    if sku_id in st.session_state.item_weights:
                                        item_config = st.session_state.item_weights[sku_id]
                                        item_name = sku_id
                                    elif sku_title in st.session_state.item_weights:
                                        item_config = st.session_state.item_weights[sku_title]
                                        item_name = sku_title
                                    
                                    if item_config:
                                        # Check if this is a B2B case pack item
                                        if 'case_pack_qty' in item_config and 'case_weight' in item_config:
                                            # B2B Case Pack Item
                                            case_pack_qty = item_config['case_pack_qty']
                                            case_weight = item_config['case_weight']
                                            
                                            # Calculate number of cases (round up for partial cases)
                                            import math
                                            num_cases = math.ceil(quantity / case_pack_qty)
                                            case_weight_total = num_cases * case_weight
                                            
                                            total_cases += num_cases
                                            total_weight_from_cases += case_weight_total
                                            
                                            items_list.append(f"{item_name[:30]} ({quantity} units = {num_cases} cases @ {case_weight}kg)")
                                        
                                        elif 'dead_weight' in item_config and 'volumetric_weight' in item_config:
                                            # B2C Unit Weight Item - these will be packed into loose cases
                                            dead_weight = item_config['dead_weight'] * quantity
                                            vol_weight = item_config['volumetric_weight'] * quantity
                                            
                                            # Accumulate volumetric weight for loose case determination
                                            total_loose_weight_volumetric += vol_weight
                                            
                                            loose_units_list.append({
                                                'name': item_name,
                                                'quantity': quantity,
                                                'dead_weight': dead_weight,
                                                'vol_weight': vol_weight
                                            })
                                        
                                        else:
                                            items_not_configured.append(f"{sku_id or sku_title} (x{quantity}) [Unknown Type]")
                                    else:
                                        items_not_configured.append(f"{sku_id or sku_title} (x{quantity})")
                                
                                # Now pack loose units into appropriate loose cases
                                loose_case_weight = 0
                                loose_case_count = 0
                                
                                if total_loose_weight_volumetric > 0:
                                    # Determine which loose case size to use based on volumetric weight
                                    # If volumetric weight fits in 4kg case, use 4kg, otherwise use 8kg
                                    import math
                                    
                                    if total_loose_weight_volumetric <= LOOSE_CASE_4KG:
                                        # Fits in single 4kg case
                                        loose_case_count = 1
                                        loose_case_weight = LOOSE_CASE_4KG
                                    elif total_loose_weight_volumetric <= LOOSE_CASE_8KG:
                                        # Fits in single 8kg case
                                        loose_case_count = 1
                                        loose_case_weight = LOOSE_CASE_8KG
                                    else:
                                        # Need multiple 8kg cases
                                        loose_case_count = math.ceil(total_loose_weight_volumetric / LOOSE_CASE_8KG)
                                        loose_case_weight = loose_case_count * LOOSE_CASE_8KG
                                    
                                    # Add loose units to items list
                                    loose_items_desc = ", ".join([f"{item['name'][:20]} (x{item['quantity']})" for item in loose_units_list])
                                    items_list.append(f"LOOSE UNITS: {loose_items_desc} → {loose_case_count} × {loose_case_weight/loose_case_count:.0f}kg case")
                                    
                                    total_cases += loose_case_count
                                
                                # Total billable weight
                                total_weight_from_units = loose_case_weight
                                
                                # Billable weight for B2B is TOTAL of case pack weight + unit weight
                                billable_weight = total_weight_from_cases + total_weight_from_units
                                
                                # Expected chargeable weight (minimum 15 kg for B2B)
                                expected_chargeable_weight = max(billable_weight, MIN_CHARGEABLE_WEIGHT)
                                
                                # Calculate expected freight
                                rate_per_kg = 0
                                if pickup_zone in SAFEXPRESS_RATES and drop_zone in SAFEXPRESS_RATES[pickup_zone]:
                                    rate_per_kg = SAFEXPRESS_RATES[pickup_zone][drop_zone]
                                
                                base_freight = expected_chargeable_weight * rate_per_kg
                                expected_freight = max(base_freight, MIN_FREIGHT)
                                expected_fsc = expected_freight * (FSC_PERCENT / 100)
                                
                                # Check if metro
                                pickup_city = str(bill_row.get('Pickup City', '')).strip().upper()
                                drop_city = str(bill_row.get('Drop City', '')).strip().upper()
                                is_metro = any(metro in pickup_city or metro in drop_city for metro in METRO_CITIES)
                                
                                metro_charge = METRO_CHARGE if is_metro else 0
                                
                                expected_total = expected_freight + expected_fsc + DOCKET_CHARGE + FOV_CHARGE + metro_charge
                                
                                # Validate weight
                                weight_status = "OK"
                                analysis_parts = []
                                status_flag = 'OK'
                                
                                if charged_weight > expected_chargeable_weight:
                                    weight_status = "Weight Error - Overcharged"
                                    analysis_parts.append(f"Charged weight ({charged_weight}kg) > Expected ({expected_chargeable_weight}kg)")
                                    status_flag = 'Error'
                                
                                # Validate freight
                                freight_diff = freight_charged - expected_freight
                                if abs(freight_diff) > 1:
                                    if freight_diff > 0:
                                        analysis_parts.append(f"Freight overcharged by ₹{freight_diff:.2f}")
                                        if status_flag == 'OK':
                                            status_flag = 'Warning'
                                    else:
                                        analysis_parts.append(f"Freight undercharged by ₹{abs(freight_diff):.2f}")
                                
                                # Validate total
                                total_diff = total_charged - expected_total
                                if abs(total_diff) > 10:
                                    if total_diff > 0:
                                        analysis_parts.append(f"Total overcharged by ₹{total_diff:.2f}")
                                        status_flag = 'Error'
                                
                                if items_not_configured:
                                    analysis_parts.append(f"Items not configured: {', '.join(items_not_configured)}")
                                    if status_flag == 'OK':
                                        status_flag = 'Warning'
                                
                                if not analysis_parts:
                                    analysis_parts.append("All checks passed")
                                
                                b2b_results.append({
                                    'AWB Number': awb,
                                    'Courier': courier,
                                    'Zone': applied_zone,
                                    'Item Details': ', '.join(items_list) if items_list else 'Not configured',
                                    'Total Units': sum([int(float(order_row.get('Quantity', 0))) for _, order_row in order_items.iterrows()]),
                                    'Total Cases': total_cases,
                                    'Master Carton Weight (kg)': round(total_weight_from_cases, 2),
                                    'Loose Case Weight (kg)': round(total_weight_from_units, 2),
                                    'Billable Weight (kg)': round(billable_weight, 2),
                                    'Expected Chargeable Weight (kg)': round(expected_chargeable_weight, 2),
                                    'Charged Weight (kg)': charged_weight,
                                    'Weight Status': weight_status,
                                    'Rate per KG (₹)': rate_per_kg,
                                    'Expected Freight (₹)': round(expected_freight, 2),
                                    'Charged Freight (₹)': round(freight_charged, 2),
                                    'Expected Total (₹)': round(expected_total, 2),
                                    'Charged Total (₹)': round(total_charged, 2),
                                    'Total Difference (₹)': round(total_diff, 2) if billable_weight > 0 else 0,
                                    'Analysis': ' | '.join(analysis_parts),
                                    'Status': status_flag
                                })
                        
                        except Exception as row_error:
                            st.warning(f"Error processing B2B AWB {awb}: {str(row_error)}")
                            continue
                    
                    if b2b_results:
                        st.session_state.validation_results = pd.DataFrame(b2b_results)
                        st.session_state.validation_type = 'B2B'
                        st.success(f"✅ B2B Validation completed! Processed {len(b2b_results)} AWBs")
                        st.rerun()
                    else:
                        st.error("No valid B2B results generated. Please check your files.")
                
                except Exception as e:
                    st.error(f"❌ Error during B2B validation: {str(e)}")
                    import traceback
                    with st.expander("View detailed error"):
                        st.code(traceback.format_exc())

with tab3:
    st.markdown("### 💰 Shipping Rate Calculator")
    st.info("Calculate shipping costs for B2C and B2B shipments based on weight and destination")
    
    # Calculator mode selection
    calc_mode = st.radio("Select Mode", ["B2C Shipping", "B2B Shipping"], horizontal=True, key="calc_mode")
    
    if calc_mode == "B2C Shipping":
        st.markdown("#### B2C Shipping Rate Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Shipment Details**")
            courier_calc = st.selectbox("Select Courier", 
                                        ["Bluedart Surface", "Bluedart Air", "Delhivery Surface", "Delhivery Air"],
                                        key="calc_courier")
            
            origin_city_calc = st.text_input("Origin City", value="Bhiwandi", key="calc_origin")
            origin_state_calc = st.text_input("Origin State", value="Maharashtra", key="calc_origin_state")
            
            dest_city_calc = st.text_input("Destination City", key="calc_dest_city")
            dest_state_calc = st.text_input("Destination State", key="calc_dest_state")
        
        with col2:
            st.markdown("**Package Weight**")
            
            weight_input_mode = st.radio("Weight Input Method", 
                                        ["Select from Item Master", "Enter Total Weight", "Manual Item Entry"], 
                                        key="weight_mode")
            
            if weight_input_mode == "Select from Item Master":
                st.markdown("**Select Items from Configured Inventory**")
                
                if not st.session_state.item_weights:
                    st.warning("⚠️ No items configured yet. Please add items in the sidebar first.")
                    total_weight_kg = 0
                else:
                    # Filter only B2C items
                    b2c_items = {k: v for k, v in st.session_state.item_weights.items() 
                                if v.get('type', 'B2C') == 'B2C' and 'dead_weight' in v}
                    
                    if not b2c_items:
                        st.warning("⚠️ No B2C items found. Please add B2C items in the sidebar.")
                        total_weight_kg = 0
                    else:
                        # Allow multiple item selection
                        st.markdown(f"**Available Items:** {len(b2c_items)}")
                        
                        # Initialize selected items in session state
                        if 'calc_selected_items' not in st.session_state:
                            st.session_state.calc_selected_items = []
                        
                        # Item selection
                        selected_item = st.selectbox(
                            "Choose an item to add",
                            [""] + list(b2c_items.keys()),
                            key="item_selector"
                        )
                        
                        col_qty, col_add = st.columns([3, 1])
                        with col_qty:
                            item_quantity = st.number_input("Quantity", min_value=1, value=1, key="item_qty_input")
                        with col_add:
                            st.write("")  # Spacing
                            if st.button("➕ Add", key="add_item_btn"):
                                if selected_item:
                                    st.session_state.calc_selected_items.append({
                                        'name': selected_item,
                                        'quantity': item_quantity,
                                        'dead_weight': b2c_items[selected_item]['dead_weight'],
                                        'vol_weight': b2c_items[selected_item]['volumetric_weight']
                                    })
                                    st.rerun()
                        
                        # Display selected items
                        if st.session_state.calc_selected_items:
                            st.markdown("**Items in Cart:**")
                            
                            total_dead_weight = 0
                            total_vol_weight = 0
                            
                            for idx, item in enumerate(st.session_state.calc_selected_items):
                                item_dead = item['dead_weight'] * item['quantity']
                                item_vol = item['vol_weight'] * item['quantity']
                                
                                total_dead_weight += item_dead
                                total_vol_weight += item_vol
                                
                                col_item, col_remove = st.columns([5, 1])
                                with col_item:
                                    st.text(f"{item['name'][:40]} (x{item['quantity']}) - {max(item_dead, item_vol):.3f} kg")
                                with col_remove:
                                    if st.button("🗑️", key=f"remove_{idx}"):
                                        st.session_state.calc_selected_items.pop(idx)
                                        st.rerun()
                            
                            total_weight_kg = max(total_dead_weight, total_vol_weight)
                            
                            st.success(f"**Total Items:** {len(st.session_state.calc_selected_items)} | **Total Weight:** {total_weight_kg:.3f} kg")
                            st.caption(f"Dead: {total_dead_weight:.3f} kg | Volumetric: {total_vol_weight:.3f} kg")
                            
                            if st.button("🗑️ Clear All Items", key="clear_all_items"):
                                st.session_state.calc_selected_items = []
                                st.rerun()
                        else:
                            st.info("No items added yet. Select an item and click 'Add'.")
                            total_weight_kg = 0
            
            elif weight_input_mode == "Enter Total Weight":
                # Clear selected items if switching modes
                if 'calc_selected_items' in st.session_state:
                    st.session_state.calc_selected_items = []
                
                total_weight_kg = st.number_input("Total Weight (kg)", min_value=0.0, step=0.1, 
                                                 format="%.3f", key="calc_total_weight")
            else:  # Manual Item Entry
                # Clear selected items if switching modes
                if 'calc_selected_items' in st.session_state:
                    st.session_state.calc_selected_items = []
                
                st.markdown("**Add Items Manually**")
                num_items = st.number_input("Number of different items", min_value=1, max_value=10, value=1, key="num_items")
                
                total_dead_weight = 0
                total_vol_weight = 0
                
                for i in range(num_items):
                    with st.expander(f"Item {i+1}", expanded=(i==0)):
                        item_col1, item_col2 = st.columns(2)
                        with item_col1:
                            qty = st.number_input(f"Quantity", min_value=1, value=1, key=f"qty_{i}")
                            dead_wt = st.number_input(f"Dead Weight per unit (kg)", min_value=0.0, step=0.01, 
                                                     format="%.3f", key=f"dead_{i}")
                        with item_col2:
                            vol_wt = st.number_input(f"Volumetric Weight per unit (kg)", min_value=0.0, step=0.01, 
                                                    format="%.3f", key=f"vol_{i}")
                        
                        total_dead_weight += dead_wt * qty
                        total_vol_weight += vol_wt * qty
                
                total_weight_kg = max(total_dead_weight, total_vol_weight)
                
                st.info(f"**Calculated Weight:** {total_weight_kg:.3f} kg (Dead: {total_dead_weight:.3f} kg, Vol: {total_vol_weight:.3f} kg)")
        
        # Calculate button
        if st.button("Calculate B2C Shipping Cost", type="primary", use_container_width=True, key="calc_b2c"):
            if not dest_city_calc or not dest_state_calc:
                st.error("Please enter destination city and state")
            elif total_weight_kg <= 0:
                st.error("Please enter a valid weight")
            else:
                # Determine zone
                zone = determine_zone(origin_city_calc, dest_city_calc, dest_state_calc)
                
                # Calculate freight
                freight_cost, calc_note = calculate_freight_cost(total_weight_kg, zone, courier_calc)
                
                # Calculate expected chargeable weight (500g slab)
                weight_grams = total_weight_kg * 1000
                if weight_grams <= 500:
                    expected_chargeable_kg = 0.5
                else:
                    import math
                    slabs_needed = math.ceil((weight_grams - 1) / 500) + 1
                    expected_chargeable_kg = (slabs_needed * 500) / 1000
                
                # Display results
                st.success("✅ Calculation Complete!")
                
                result_col1, result_col2, result_col3 = st.columns(3)
                
                with result_col1:
                    st.metric("Zone", zone)
                    st.metric("Courier", courier_calc)
                
                with result_col2:
                    st.metric("Billable Weight", f"{total_weight_kg:.3f} kg")
                    st.metric("Chargeable Weight", f"{expected_chargeable_kg:.3f} kg")
                
                with result_col3:
                    st.metric("Shipping Cost", f"₹{freight_cost:.2f}")
                    if calc_note:
                        st.caption(calc_note)
                
                # Show breakdown
                with st.expander("💡 Calculation Breakdown"):
                    st.markdown(f"""
                    **Route:** {origin_city_calc}, {origin_state_calc} → {dest_city_calc}, {dest_state_calc}
                    
                    **Zone Classification:** {zone}
                    
                    **Weight Calculation:**
                    - Billable Weight: {total_weight_kg:.3f} kg
                    - Expected Chargeable Weight Slab: {expected_chargeable_kg:.3f} kg (500g slabs)
                    
                    **Rate Applied:** {courier_calc} - {zone}
                    
                    **Calculation Note:** {calc_note if calc_note else 'Standard rate applied'}
                    
                    **Final Shipping Cost:** ₹{freight_cost:.2f}
                    """)
    
    else:  # B2B Shipping
        st.markdown("#### B2B Shipping Rate Calculator (Safexpress)")
        
        # Safexpress rate card
        SAFEXPRESS_RATES = {
            'N1': {'N1': 6.48, 'N2': 6.48, 'E': 10.8, 'NE': 16.2, 'W1': 7.56, 'W2': 8.64, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
            'N2': {'N1': 6.48, 'N2': 6.48, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 8.64, 'S1': 10.8, 'S2': 10.8, 'C': 7.56},
            'E': {'N1': 8.64, 'N2': 10.8, 'E': 6.48, 'NE': 7.56, 'W1': 8.64, 'W2': 10.8, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
            'NE': {'N1': 8.64, 'N2': 10.8, 'E': 7.56, 'NE': 6.48, 'W1': 10.8, 'W2': 10.8, 'S1': 10.8, 'S2': 16.2, 'C': 8.64},
            'W1': {'N1': 7.56, 'N2': 8.64, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 6.48, 'S1': 8.64, 'S2': 10.8, 'C': 7.56},
            'W2': {'N1': 8.64, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 6.48, 'S1': 7.56, 'S2': 10.8, 'C': 7.56},
            'S1': {'N1': 8.64, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 7.56, 'S1': 6.48, 'S2': 7.56, 'C': 7.56},
            'S2': {'N1': 10.8, 'N2': 10.8, 'E': 10.8, 'NE': 16.2, 'W1': 8.64, 'W2': 8.64, 'S1': 6.48, 'S2': 6.48, 'C': 7.56},
            'C': {'N1': 7.56, 'N2': 8.64, 'E': 10.8, 'NE': 16.2, 'W1': 6.48, 'W2': 7.56, 'S1': 7.56, 'S2': 10.8, 'C': 6.48}
        }
        
        METRO_CITIES_B2B = ['AHMEDABAD', 'BENGALURU', 'CHENNAI', 'DELHI', 'HYDERABAD', 'KOLKATA', 'MUMBAI', 'PUNE']
        MIN_CHARGEABLE_WEIGHT = 15  # kg
        MIN_FREIGHT = 400  # Rs
        FSC_PERCENT = 20  # 20%
        DOCKET_CHARGE = 100  # Rs
        FOV_CHARGE = 100  # Rs
        METRO_CHARGE = 100  # Rs
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Origin & Destination**")
            pickup_zone = st.selectbox("Pickup Zone", 
                                      ["N1 (Delhi, UP, Haryana, Rajasthan)",
                                       "N2 (Punjab, Chandigarh, HP, Uttarakhand, J&K)",
                                       "E (West Bengal, Odisha, Bihar, Jharkhand, Chhattisgarh)",
                                       "NE (Assam, Meghalaya, Tripura, etc.)",
                                       "W1 (Gujarat, Daman & Diu)",
                                       "W2 (Maharashtra, Goa)",
                                       "S1 (AP, Telangana, Karnataka, TN)",
                                       "S2 (Kerala)",
                                       "C (Madhya Pradesh)"],
                                      key="b2b_pickup_zone")
            
            drop_zone = st.selectbox("Drop Zone", 
                                    ["N1 (Delhi, UP, Haryana, Rajasthan)",
                                     "N2 (Punjab, Chandigarh, HP, Uttarakhand, J&K)",
                                     "E (West Bengal, Odisha, Bihar, Jharkhand, Chhattisgarh)",
                                     "NE (Assam, Meghalaya, Tripura, etc.)",
                                     "W1 (Gujarat, Daman & Diu)",
                                     "W2 (Maharashtra, Goa)",
                                     "S1 (AP, Telangana, Karnataka, TN)",
                                     "S2 (Kerala)",
                                     "C (Madhya Pradesh)"],
                                    key="b2b_drop_zone")
            
            pickup_city = st.text_input("Pickup City (for metro check)", value="Mumbai", key="b2b_pickup_city")
            drop_city = st.text_input("Drop City (for metro check)", value="", key="b2b_drop_city")
        
        with col2:
            st.markdown("**Package Weight**")
            
            b2b_weight_mode = st.radio("Weight Input Method", 
                                      ["Select from Item Master", "Enter Total Weight"], 
                                      key="b2b_weight_mode")
            
            if b2b_weight_mode == "Select from Item Master":
                st.markdown("**Select Items from Configured Inventory**")
                
                if not st.session_state.item_weights:
                    st.warning("⚠️ No items configured yet. Please add items in the sidebar first.")
                    b2b_weight = 0
                else:
                    # Get all items (both B2C and B2B)
                    all_items = st.session_state.item_weights
                    
                    # Initialize selected items for B2B
                    if 'calc_b2b_selected_items' not in st.session_state:
                        st.session_state.calc_b2b_selected_items = []
                    
                    # Item selection
                    selected_b2b_item = st.selectbox(
                        "Choose an item to add",
                        [""] + list(all_items.keys()),
                        key="b2b_item_selector"
                    )
                    
                    col_qty_b2b, col_add_b2b = st.columns([3, 1])
                    with col_qty_b2b:
                        b2b_item_quantity = st.number_input("Quantity", min_value=1, value=1, key="b2b_item_qty_input")
                    with col_add_b2b:
                        st.write("")  # Spacing
                        if st.button("➕ Add", key="add_b2b_item_btn"):
                            if selected_b2b_item:
                                item_config = all_items[selected_b2b_item]
                                st.session_state.calc_b2b_selected_items.append({
                                    'name': selected_b2b_item,
                                    'quantity': b2b_item_quantity,
                                    'config': item_config
                                })
                                st.rerun()
                    
                    # Display selected items and calculate weight
                    if st.session_state.calc_b2b_selected_items:
                        st.markdown("**Items in Cart:**")
                        
                        total_case_weight = 0
                        total_loose_weight = 0
                        total_cases = 0
                        
                        LOOSE_CASE_4KG = 4.0
                        LOOSE_CASE_8KG = 8.0
                        
                        for idx, item in enumerate(st.session_state.calc_b2b_selected_items):
                            config = item['config']
                            qty = item['quantity']
                            
                            # Check if B2B case pack or B2C unit
                            if 'case_pack_qty' in config and 'case_weight' in config:
                                # B2B Case Pack
                                import math
                                num_cases = math.ceil(qty / config['case_pack_qty'])
                                weight = num_cases * config['case_weight']
                                total_case_weight += weight
                                total_cases += num_cases
                                
                                col_item, col_remove = st.columns([5, 1])
                                with col_item:
                                    st.text(f"📦 {item['name'][:35]} (x{qty}) = {num_cases} cases @ {weight:.2f} kg")
                                with col_remove:
                                    if st.button("🗑️", key=f"remove_b2b_{idx}"):
                                        st.session_state.calc_b2b_selected_items.pop(idx)
                                        st.rerun()
                            
                            elif 'dead_weight' in config and 'volumetric_weight' in config:
                                # B2C Unit - accumulate for loose case
                                vol_weight = config['volumetric_weight'] * qty
                                total_loose_weight += vol_weight
                                
                                col_item, col_remove = st.columns([5, 1])
                                with col_item:
                                    st.text(f"📄 {item['name'][:35]} (x{qty}) - {vol_weight:.3f} kg vol")
                                with col_remove:
                                    if st.button("🗑️", key=f"remove_b2b_{idx}"):
                                        st.session_state.calc_b2b_selected_items.pop(idx)
                                        st.rerun()
                        
                        # Calculate loose case weight
                        loose_case_weight = 0
                        loose_case_count = 0
                        if total_loose_weight > 0:
                            import math
                            if total_loose_weight <= LOOSE_CASE_4KG:
                                loose_case_count = 1
                                loose_case_weight = LOOSE_CASE_4KG
                            elif total_loose_weight <= LOOSE_CASE_8KG:
                                loose_case_count = 1
                                loose_case_weight = LOOSE_CASE_8KG
                            else:
                                loose_case_count = math.ceil(total_loose_weight / LOOSE_CASE_8KG)
                                loose_case_weight = loose_case_count * LOOSE_CASE_8KG
                            
                            st.info(f"🎁 Loose units packed in: {loose_case_count} × {loose_case_weight/loose_case_count:.0f}kg case(s)")
                            total_cases += loose_case_count
                        
                        b2b_weight = total_case_weight + loose_case_weight
                        
                        st.success(f"**Total Items:** {len(st.session_state.calc_b2b_selected_items)} | **Total Cases:** {total_cases} | **Total Weight:** {b2b_weight:.2f} kg")
                        st.caption(f"Master Cartons: {total_case_weight:.2f} kg | Loose Cases: {loose_case_weight:.2f} kg")
                        
                        if st.button("🗑️ Clear All Items", key="clear_all_b2b_items"):
                            st.session_state.calc_b2b_selected_items = []
                            st.rerun()
                    else:
                        st.info("No items added yet. Select an item and click 'Add'.")
                        b2b_weight = 0
            
            else:  # Enter Total Weight
                # Clear selected items if switching modes
                if 'calc_b2b_selected_items' in st.session_state:
                    st.session_state.calc_b2b_selected_items = []
                
                b2b_weight = st.number_input("Total Weight (kg)", min_value=0.0, step=1.0, value=15.0, 
                                            format="%.2f", key="b2b_weight")
            
            st.info(f"Minimum chargeable weight: {MIN_CHARGEABLE_WEIGHT} kg")
        
        # Calculate button
        if st.button("Calculate B2B Shipping Cost", type="primary", use_container_width=True, key="calc_b2b_btn"):
            # Extract zone codes
            pickup_zone_code = pickup_zone.split()[0]
            drop_zone_code = drop_zone.split()[0]
            
            # Calculate chargeable weight
            chargeable_weight = max(b2b_weight, MIN_CHARGEABLE_WEIGHT)
            
            # Get rate
            rate_per_kg = SAFEXPRESS_RATES[pickup_zone_code][drop_zone_code]
            
            # Calculate charges
            base_freight = chargeable_weight * rate_per_kg
            freight = max(base_freight, MIN_FREIGHT)
            fsc = freight * (FSC_PERCENT / 100)
            
            # Check metro
            is_metro = any(metro in pickup_city.upper() or metro in drop_city.upper() 
                          for metro in METRO_CITIES_B2B)
            metro_charge = METRO_CHARGE if is_metro else 0
            
            total_cost = freight + fsc + DOCKET_CHARGE + FOV_CHARGE + metro_charge
            
            # Display results
            st.success("✅ Calculation Complete!")
            
            result_col1, result_col2, result_col3 = st.columns(3)
            
            with result_col1:
                st.metric("Zone", f"{pickup_zone_code} → {drop_zone_code}")
                st.metric("Rate per KG", f"₹{rate_per_kg}")
            
            with result_col2:
                st.metric("Actual Weight", f"{b2b_weight:.2f} kg")
                st.metric("Chargeable Weight", f"{chargeable_weight:.2f} kg")
            
            with result_col3:
                st.metric("Total Shipping Cost", f"₹{total_cost:.2f}")
                st.caption("Includes all charges")
            
            # Show breakdown
            with st.expander("💡 Cost Breakdown"):
                st.markdown(f"""
                **Route:** {pickup_zone_code} ({pickup_city}) → {drop_zone_code} ({drop_city})
                
                **Weight:**
                - Actual Weight: {b2b_weight:.2f} kg
                - Minimum Weight: {MIN_CHARGEABLE_WEIGHT} kg
                - Chargeable Weight: {chargeable_weight:.2f} kg
                
                **Charges Breakdown:**
                - Base Freight: ₹{freight:.2f} ({chargeable_weight:.2f} kg × ₹{rate_per_kg}/kg)
                - Fuel Surcharge (20%): ₹{fsc:.2f}
                - Docket Charges: ₹{DOCKET_CHARGE:.2f}
                - FOV Charges: ₹{FOV_CHARGE:.2f}
                - Metro Charges: ₹{metro_charge:.2f} {"(Applied)" if is_metro else "(Not applicable)"}
                
                **Total Cost:** ₹{total_cost:.2f}
                """)

with tab4:
    if st.session_state.validation_results is not None:
        results_df = st.session_state.validation_results
        validation_type = st.session_state.validation_type or 'Unknown'
        
        # Metrics
        st.markdown(f"### 📊 {validation_type} Validation Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_records = len(results_df)
        error_records = len(results_df[results_df['Status'] == 'Error'])
        warning_records = len(results_df[results_df['Status'] == 'Warning'])
        missing_records = len(results_df[results_df['Status'] == 'Missing'])
        ok_records = len(results_df[results_df['Status'] == 'OK'])
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_records}</div>
                <div class="metric-label">Total AWBs</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #10b981;">
                <div class="metric-value" style="color: #10b981;">{ok_records}</div>
                <div class="metric-label">Correct</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #ef4444;">
                <div class="metric-value" style="color: #ef4444;">{error_records}</div>
                <div class="metric-label">Errors</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #f59e0b;">
                <div class="metric-value" style="color: #f59e0b;">{warning_records}</div>
                <div class="metric-label">Warnings</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #8b5cf6;">
                <div class="metric-value" style="color: #8b5cf6;">{missing_records}</div>
                <div class="metric-label">Missing</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Financial summary
        if 'Freight Difference (₹)' in results_df.columns:
            valid_diffs = results_df[results_df['Freight Difference (₹)'] != 'N/A']['Freight Difference (₹)']
            if len(valid_diffs) > 0:
                total_overcharge = valid_diffs[valid_diffs > 0].sum()
                total_undercharge = abs(valid_diffs[valid_diffs < 0].sum())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Overcharged", f"₹{total_overcharge:,.2f}", delta=None, delta_color="inverse")
                with col2:
                    st.metric("Total Undercharged", f"₹{total_undercharge:,.2f}")
                with col3:
                    net_diff = total_overcharge - total_undercharge
                    st.metric("Net Difference", f"₹{net_diff:,.2f}", delta=None, delta_color="off")
        
        st.markdown("---")
        
        # Filter options
        st.markdown("### 🔍 Filter Results")
        filter_option = st.radio(
            "Show:",
            ["All Records", "Errors Only", "Warnings Only", "Missing Orders Only", "Correct Records Only"],
            horizontal=True
        )
        
        filtered_df = results_df.copy()
        if filter_option == "Errors Only":
            filtered_df = results_df[results_df['Status'] == 'Error']
        elif filter_option == "Warnings Only":
            filtered_df = results_df[results_df['Status'] == 'Warning']
        elif filter_option == "Missing Orders Only":
            filtered_df = results_df[results_df['Status'] == 'Missing']
        elif filter_option == "Correct Records Only":
            filtered_df = results_df[results_df['Status'] == 'OK']
        
        # Display results
        st.markdown(f"### 📋 Detailed Results ({len(filtered_df)} records)")
        
        # Configure column widths
        column_config = {}
        if 'Item Details' in filtered_df.columns:
            column_config['Item Details'] = st.column_config.TextColumn(
                "Item Details",
                width="large",
                help="Item names and quantities"
            )
        
        # Style the dataframe
        def highlight_status(row):
            if row['Status'] == 'Error':
                return ['background-color: #fee2e2'] * len(row)
            elif row['Status'] == 'Warning':
                return ['background-color: #fef3c7'] * len(row)
            elif row['Status'] == 'Missing':
                return ['background-color: #e0e7ff'] * len(row)
            elif row['Status'] == 'OK':
                return ['background-color: #d1fae5'] * len(row)
            return [''] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400, column_config=column_config)
        
        # Download options
        st.markdown("### 📥 Export Results")
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Validation Results')
            excel_data = output.getvalue()
            
            filename_prefix = f"mama_nourish_{validation_type.lower()}_validation" if validation_type else "billing_validation"
            
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"{filename_prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # CSV export
            csv_data = results_df.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_data,
                file_name=f"{filename_prefix}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("👆 Upload files and run validation to see results here")

with tab5:
    st.markdown("### 📄 Rate Card Management")
    
    st.info("**Current Status:** Rate card is hardcoded from the Prozo commercials PDF in the system")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Upload New Rate Card (PDF)")
        st.markdown("""
        Upload your commercials PDF to update the rate card. The system currently supports:
        - Bluedart Surface & Air
        - Delhivery Surface & Air
        - Xpressbees, DTDC, Ecom Express, Professional (can be added)
        """)
        
        rate_card_pdf = st.file_uploader(
            "Upload Rate Card PDF",
            type=['pdf'],
            key="rate_card_pdf",
            help="Upload the commercials PDF file"
        )
        
        if rate_card_pdf:
            st.success(f"✅ Uploaded: {rate_card_pdf.name}")
            st.warning("⚠️ **Note:** PDF parsing is not yet implemented. Currently using hardcoded rates from the Prozo commercials PDF.")
            st.info("💡 **Future Enhancement:** The system will automatically extract rates from uploaded PDFs.")
    
    with col2:
        st.markdown("#### Current Rate Card")
        st.markdown("**Configured Couriers:**")
        for courier in RATE_CARD.keys():
            st.write(f"✓ {courier}")
    
    st.markdown("---")
    
    # Display current rate card
    st.markdown("### 📊 Current Rate Card Details")
    
    courier_select = st.selectbox("Select Courier to View Rates", list(RATE_CARD.keys()))
    
    if courier_select:
        st.markdown(f"#### {courier_select} - Zone-wise Rates")
        
        # Convert rate card to dataframe for display
        zones = list(RATE_CARD[courier_select].keys())
        
        for zone in zones:
            with st.expander(f"🌍 {zone}"):
                rates = RATE_CARD[courier_select][zone]
                
                # Display rates nicely
                if 'Air' in courier_select:
                    st.markdown(f"""
                    - **0-500g:** ₹{rates['0-500']}
                    - **Additional 500g:** ₹{rates['add_500']}
                    """)
                else:
                    st.markdown(f"""
                    - **0-500g:** ₹{rates['0-500']}
                    - **Additional 500g (up to 2kg):** ₹{rates['add_500']}
                    - **2kg base:** ₹{rates['2kg']}
                    - **Additional 1kg (2-5kg):** ₹{rates['add_1kg_2-5']}
                    - **5kg base:** ₹{rates['5kg']}
                    - **Additional 1kg (5-10kg):** ₹{rates['add_1kg_5-10']}
                    - **10kg base:** ₹{rates['10kg']}
                    - **Additional 1kg (10kg+):** ₹{rates['add_1kg_10+']}
                    """)
    
    st.markdown("---")
    
    # Export rate card
    st.markdown("### 📥 Export Rate Card")
    rate_card_json = json.dumps(RATE_CARD, indent=2)
    st.download_button(
        label="💾 Download Rate Card as JSON",
        data=rate_card_json,
        file_name="rate_card_export.json",
        mime="application/json",
        use_container_width=True
    )

with tab6:
    st.markdown("""
    ### 📖 How to Use This Application
    
    This application validates billing for **Mama Nourish** shipments with:
    1. **B2C Validation** - Weight slab and rate card validation
    2. **B2B Validation** - Zone-based Safexpress validation with case packs
    3. **Rate Calculator** - Calculate shipping costs for new shipments
    4. **Rate Card Management** - View and upload commercials
    4. **Persistent Storage** - Item configurations saved permanently
    
    ---
    
    ## 🗂️ Application Tabs
    
    ### Tab 1: B2C Validation
    - Upload billing Excel (Freight sheet) and order CSV
    - Validates weight slabs (500g increments)
    - Compares against rate card
    - Flags overcharges and errors
    
    ### Tab 2: B2B Validation (Coming Soon)
    - Will support B2B-specific rules
    - Different rate structures
    - Separate validation logic
    - **Status:** Placeholder - will be activated after B2C is finalized
    
    ### Tab 3: Results
    - View validation summary with metrics
    - Filter by status (Errors, Warnings, OK, Missing)
    - Financial summary (overcharges, undercharges)
    - Export to Excel or CSV
    
    ### Tab 4: Rate Card
    - View current rate card details
    - Upload new commercials PDF (placeholder for future)
    - Export rate card as JSON
    - Currently using hardcoded Prozo rates
    
    ### Tab 5: Instructions
    - Complete user guide
    - Weight slab logic explanation
    - Troubleshooting tips
    
    ---
    
    ## 💾 Permanent Item Storage
    
    **Your item configurations are saved automatically and permanently!**
    
    ### How It Works:
    1. **Auto-Save:** Every time you add an item, it's saved to `item_weights_persistent.json`
    2. **Auto-Load:** When you open the app, all items load automatically
    3. **No Data Loss:** Items persist across sessions, restarts, and deployments
    4. **File Location:** Same directory as the application
    
    ### To Backup Your Items:
    1. Click "📥 Export Settings" in the sidebar
    2. Save the JSON file to your computer
    3. Store it safely for backup
    
    ### To Restore Items:
    1. Click "📤 Import Settings" in the sidebar
    2. Upload your saved JSON file
    3. All items will be added/updated
    
    ### To Share Items with Team:
    1. Export settings to JSON
    2. Share the file with team members
    3. They import it into their app instance
    
    ---
    
    ### Step 1: Configure Item Weights (One-Time Setup)
    
    Add each SKU with its weight information:
    - Use **SKU ID** or **SKU Title** from your order file
    - Enter **Dead Weight** (actual physical weight in kg)
    - Enter **Volumetric Weight** (L × B × H / 5000 in cm, result in kg)
    - Click "Add Item" - **IT SAVES PERMANENTLY!**
    
    💡 **Tips:**
    - Items persist forever - configure once, use always
    - Export settings regularly for backup
    - Use search to find items quickly
    - Delete items anytime if needed
    
    ### Step 2: Upload Required Files (B2C Tab)
    
    **1. Billing File (Excel):** 
    - Must have "Freight" sheet
    - Contains: AWB NUMBER, Weight, Courier Parent, Base Freight Cost
    - Example: Mama_Nourish__31_.xlsx
    
    **2. Order File (CSV):**
    - Contains: SKU ID, SKU Title, Awb No, Quantity, Courier, State, city
    - Example: Order export CSV
    
    ### Step 3: Run Validation
    
    Click "🔍 Validate B2C Billing" - The system will:
    - ✅ Sum all items per AWB (multi-item orders handled)
    - ✅ Calculate billable weight (max of dead/volumetric)
    - ✅ Determine weight slab (500g increments)
    - ✅ Validate charged weight within slab
    - ✅ Detect shipping zone automatically
    - ✅ Calculate expected freight from rate card
    - ✅ Compare and flag discrepancies
    
    ### 🎯 Weight Slab Validation Logic
    
    **Rule: Charged weight can be ANY value between billable weight and slab limit**
    
    ## 📏 Weight Slab Structure
    
    Billing slabs are in **500g increments**:
    - **Slab 1:** 0-500g (0.0-0.5 kg)
    - **Slab 2:** 501-1000g (0.501-1.0 kg)
    - **Slab 3:** 1001-1500g (1.001-1.5 kg)
    - **Slab 4:** 1501-2000g (1.501-2.0 kg)
    - And so on...
    
    ## ✅ Validation Rule (Applies to ALL couriers)
    
    **Charged weight is CORRECT if:**
    ```
    billable_weight ≤ charged_weight ≤ slab_maximum
    ```
    
    **Charged weight does NOT need to be exact 500g multiples!**
    - Any value within the slab range is acceptable
    - Flexibility within the slab is allowed
    
    ## 📊 Examples
    
    ### Example 1: Billable 200g (0.2 kg)
    - **Falls in Slab 1:** 0-500g (0.0-0.5 kg)
    - **Acceptable Range:** 200g to 500g (0.2 kg to 0.5 kg)
    
    | Charged Weight | Status | Reason |
    |---------------|--------|--------|
    | 150g (0.15 kg) | ❌ Error | Below billable weight |
    | 200g (0.2 kg) | ✅ OK | At billable weight |
    | 300g (0.3 kg) | ✅ OK | Within slab range |
    | 440g (0.44 kg) | ✅ OK | Within slab range |
    | 500g (0.5 kg) | ✅ OK | At slab maximum |
    | 550g (0.55 kg) | ❌ Error | Exceeds slab limit |
    
    ### Example 2: Billable 600g (0.6 kg)
    - **Falls in Slab 2:** 501-1000g (0.501-1.0 kg)
    - **Acceptable Range:** 600g to 1000g (0.6 kg to 1.0 kg)
    
    | Charged Weight | Status | Reason |
    |---------------|--------|--------|
    | 500g (0.5 kg) | ❌ Error | Below billable weight |
    | 600g (0.6 kg) | ✅ OK | At billable weight |
    | 750g (0.75 kg) | ✅ OK | Within slab range |
    | 880g (0.88 kg) | ✅ OK | Within slab range |
    | 1000g (1.0 kg) | ✅ OK | At slab maximum |
    | 1100g (1.1 kg) | ❌ Error | Exceeds slab limit |
    
    ### Example 3: Billable 1.2 kg
    - **Falls in Slab 3:** 1001-1500g (1.001-1.5 kg)
    - **Acceptable Range:** 1.2 kg to 1.5 kg
    
    | Charged Weight | Status | Reason |
    |---------------|--------|--------|
    | 1.0 kg | ❌ Error | Below billable weight |
    | 1.2 kg | ✅ OK | At billable weight |
    | 1.35 kg | ✅ OK | Within slab range |
    | 1.5 kg | ✅ OK | At slab maximum |
    | 1.6 kg | ❌ Error | Exceeds slab limit |
    
    ## 🎯 Key Points
    
    ✅ Charged weight can be **any decimal value** (not just 500g multiples)
    ✅ Must be **≥ billable weight** (shipper can't charge less than actual)
    ✅ Must be **≤ slab maximum** (can't jump to next slab)
    ✅ Same rule applies to **both Air and Surface** couriers
    
    ## ❌ Common Errors
    
    | Error Type | Example | Why It's Wrong |
    |------------|---------|----------------|
    | **Undercharged** | Billable 600g, Charged 500g | Charged < Billable |
    | **Overcharged** | Billable 600g, Charged 1100g | Exceeds slab limit (1000g) |
    | **Way Overcharged** | Billable 200g, Charged 1500g | Multiple slabs exceeded |
    
    ### Step 4: Review Results
    
    **Status Types:**
    - 🟢 **OK**: All checks passed
    - 🔴 **Error**: Weight mismatch or overcharging detected
    - 🟡 **Warning**: Courier not specified or items not configured
    - 🟣 **Missing**: AWB not found in order file
    
    **Key Columns:**
    - **Billable Weight (kg)**: Max(Dead Weight, Volumetric Weight) - Total calculated weight
    - **Slab Range (kg)**: Acceptable charged weight range (billable to slab max)
    - **Charged Weight (kg)**: Actual weight charged by shipper
    - **Weight Status**: 
      - ✅ OK: billable ≤ charged ≤ slab_max
      - ❌ Error - Overcharged: charged > slab_max
      - ❌ Error - Undercharged: charged < billable
    - **Billing Status**: Indicates freight overcharging, undercharging, or missing courier
    - **Expected Freight (₹)**: Calculated from rate card based on billable weight
    - **Freight Difference (₹)**: Charged - Expected (positive = overcharged)
    
    ### 📊 Rate Card Information
    
    The application uses the Prozo rate card for:
    - Bluedart Surface & Air
    - Delhivery Surface & Air
    - (Extensible to other couriers)
    
    **Zone Determination:**
    - **Local**: Same city (e.g., Mumbai to Mumbai)
    - **Within State**: Same state (e.g., Bhiwandi to Pune)
    - **Metro to Metro**: Between Delhi NCR, Mumbai, Chennai, Kolkata, Bangalore
    - **Rest of India**: Inter-region (excluding special zones)
    - **Special Zone**: J&K, HP, Kerala, NE states, Andaman, Lakshadweep
    
    ### 🔧 Common Issues
    
    **"Weight Error - Overcharged"**
    - Charged weight exceeds the 500g slab limit for the billable weight
    - Example: Billable 560g (Slab: 501-1000g), Charged 1100g → ERROR (exceeds 1000g limit)
    - Example: Billable 200g (Slab: 0-500g), Charged 660g → ERROR (exceeds 500g limit)
    - Shipper is charging for a higher slab than necessary
    
    **"Weight Error - Undercharged"**
    - Charged weight is less than the calculated billable weight
    - Example: Billable 560g, Charged 400g → ERROR
    - Indicates shipper used lower weight than actual (benefits customer but incorrect)
    
    **"Courier not specified"**
    - AWB has no courier in billing file
    - System checks order file as fallback
    - Flag indicates validation cannot proceed
    
    **"Items not configured"**
    - SKU ID or Title not in weight settings
    - Add missing items in sidebar
    - Export updated configuration
    
    **"Cannot calculate freight"**
    - Courier not in rate card
    - Zone not found for courier
    - Add custom rate card support if needed
    
    ### 💡 Best Practices
    
    1. **Configure all SKUs** before running validation
    2. **Export settings regularly** to avoid data loss
    3. **Review warnings** - they indicate missing data
    4. **Check weight errors** - focus on "Weight Error - Overcharged" entries
    5. **Check overcharges** - focus on freight difference column
    6. **Validate zone assignment** - ensure origin/destination logic is correct
    """)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #94a3b8; font-size: 0.875rem;">Mama Nourish Billing Validator • Built with Streamlit</p>',
    unsafe_allow_html=True
)
