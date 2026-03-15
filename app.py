import streamlit as st
import pandas as pd
import json
from pathlib import Path
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Shipment Billing Validator",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for refined, data-focused aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 600 !important;
    }
    
    p, div, span, label {
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    
    code, pre {
        font-family: 'IBM Plex Mono', monospace !important;
    }
    
    /* Main title */
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
    
    /* Cards */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.5rem;
        border-left: 4px solid #667eea;
    }
    
    /* Metric cards */
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
    
    /* Status badges */
    .status-ok {
        background: #d1fae5;
        color: #065f46;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-error {
        background: #fee2e2;
        color: #991b1b;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-warning {
        background: #fef3c7;
        color: #92400e;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-block;
    }
    
    /* File uploader */
    .uploadedFile {
        border: 2px dashed #cbd5e1 !important;
        border-radius: 8px !important;
        background: #f8fafc !important;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.625rem 1.5rem;
        font-weight: 500;
        font-family: 'IBM Plex Sans', sans-serif;
        transition: transform 0.2s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .css-1d391kg .sidebar-content, [data-testid="stSidebar"] .sidebar-content {
        color: white;
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }
    
    /* Info boxes */
    .info-box {
        background: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'item_weights' not in st.session_state:
    st.session_state.item_weights = {}
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None

# Header
st.markdown('<h1 class="main-title">📦 Shipment Billing Validator</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Automated weight-based billing verification system</p>', unsafe_allow_html=True)

# Sidebar - Settings
with st.sidebar:
    st.markdown("### ⚙️ Item Weight Configuration")
    st.markdown("---")
    
    # Add new item
    st.markdown("#### Add New Item")
    with st.form("add_item_form"):
        item_name = st.text_input("Item Name")
        col1, col2 = st.columns(2)
        with col1:
            dead_weight = st.number_input("Dead Weight (kg)", min_value=0.0, step=0.1, format="%.2f")
        with col2:
            volumetric_weight = st.number_input("Volumetric Weight (kg)", min_value=0.0, step=0.1, format="%.2f")
        
        if st.form_submit_button("➕ Add Item", use_container_width=True):
            if item_name:
                st.session_state.item_weights[item_name] = {
                    'dead_weight': dead_weight,
                    'volumetric_weight': volumetric_weight
                }
                st.success(f"✓ Added {item_name}")
            else:
                st.error("Please enter an item name")
    
    st.markdown("---")
    
    # Display configured items
    if st.session_state.item_weights:
        st.markdown("#### Configured Items")
        for item, weights in st.session_state.item_weights.items():
            with st.expander(f"📦 {item}"):
                st.write(f"**Dead Weight:** {weights['dead_weight']} kg")
                st.write(f"**Volumetric Weight:** {weights['volumetric_weight']} kg")
                if st.button(f"🗑️ Delete", key=f"del_{item}"):
                    del st.session_state.item_weights[item]
                    st.rerun()
    
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
            st.success("✓ Settings imported successfully")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing settings: {str(e)}")

# Main content
tab1, tab2, tab3 = st.tabs(["📋 Validation", "📊 Results", "ℹ️ Instructions"])

with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### File Upload")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Billing File (Excel)")
        billing_file = st.file_uploader(
            "Upload billing summary file",
            type=['xlsx', 'xls'],
            key="billing_file",
            help="Upload the Excel file containing billing information"
        )
        
        if billing_file:
            try:
                excel_file = pd.ExcelFile(billing_file)
                sheet_names = excel_file.sheet_names
                billing_sheet = st.selectbox("Select Billing Sheet", sheet_names)
            except Exception as e:
                st.error(f"Error reading Excel file: {str(e)}")
                billing_sheet = None
        else:
            billing_sheet = None
    
    with col2:
        st.markdown("#### 📦 Order File (Excel/CSV)")
        order_file = st.file_uploader(
            "Upload order details file",
            type=['xlsx', 'xls', 'csv'],
            key="order_file",
            help="Upload the file containing order, item, and quantity mapping"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Validation button
    if st.button("🔍 Validate Billing", use_container_width=True, type="primary"):
        if not st.session_state.item_weights:
            st.error("⚠️ Please configure item weights in the sidebar first")
        elif not billing_file or not order_file:
            st.error("⚠️ Please upload both billing and order files")
        else:
            with st.spinner("Analyzing billing data..."):
                try:
                    # Read billing file
                    billing_df = pd.read_excel(billing_file, sheet_name=billing_sheet)
                    
                    # Read order file
                    if order_file.name.endswith('.csv'):
                        order_df = pd.read_csv(order_file)
                    else:
                        order_df = pd.read_excel(order_file)
                    
                    # Validate column names (flexible matching)
                    billing_cols = billing_df.columns.str.lower().str.strip()
                    order_cols = order_df.columns.str.lower().str.strip()
                    
                    # Expected columns
                    required_billing_cols = ['awb', 'charged_weight', 'weight']
                    required_order_cols = ['awb', 'item', 'quantity', 'order', 'order_id']
                    
                    # Find matching columns
                    awb_col_billing = next((col for col in billing_df.columns if 'awb' in col.lower()), None)
                    weight_col_billing = next((col for col in billing_df.columns if 'weight' in col.lower() or 'charged' in col.lower()), None)
                    
                    awb_col_order = next((col for col in order_df.columns if 'awb' in col.lower()), None)
                    item_col_order = next((col for col in order_df.columns if 'item' in col.lower()), None)
                    qty_col_order = next((col for col in order_df.columns if 'quantity' in col.lower() or 'qty' in col.lower()), None)
                    
                    if not all([awb_col_billing, weight_col_billing, awb_col_order, item_col_order, qty_col_order]):
                        st.error("❌ Required columns not found in uploaded files. Please check column names.")
                        st.info(f"Billing columns found: {', '.join(billing_df.columns)}")
                        st.info(f"Order columns found: {', '.join(order_df.columns)}")
                    else:
                        # Process validation
                        results = []
                        
                        for _, bill_row in billing_df.iterrows():
                            awb = str(bill_row[awb_col_billing]).strip()
                            charged_weight = float(bill_row[weight_col_billing])
                            
                            # Find orders with this AWB
                            order_items = order_df[order_df[awb_col_order].astype(str).str.strip() == awb]
                            
                            if order_items.empty:
                                results.append({
                                    'AWB Number': awb,
                                    'Item Name': 'N/A',
                                    'Item Quantity': 0,
                                    'Calculated Dead Weight': 0,
                                    'Calculated Volume Weight': 0,
                                    'Charged Weight': charged_weight,
                                    'Analysis': 'Order ID not found',
                                    'Status': 'Missing'
                                })
                            else:
                                # Calculate total weight for this AWB
                                total_dead_weight = 0
                                total_vol_weight = 0
                                items_list = []
                                
                                for _, order_row in order_items.iterrows():
                                    item_name = str(order_row[item_col_order]).strip()
                                    quantity = int(order_row[qty_col_order])
                                    
                                    if item_name in st.session_state.item_weights:
                                        item_weights = st.session_state.item_weights[item_name]
                                        total_dead_weight += item_weights['dead_weight'] * quantity
                                        total_vol_weight += item_weights['volumetric_weight'] * quantity
                                        items_list.append(f"{item_name} (x{quantity})")
                                    else:
                                        items_list.append(f"{item_name} (x{quantity}) [NOT CONFIGURED]")
                                
                                calculated_weight = max(total_dead_weight, total_vol_weight)
                                
                                # Compare with charged weight
                                if calculated_weight > charged_weight:
                                    analysis = "Incorrect weight - Calculated weight exceeds charged weight"
                                    status = 'Error'
                                else:
                                    analysis = "OK"
                                    status = 'OK'
                                
                                results.append({
                                    'AWB Number': awb,
                                    'Item Name': ', '.join(items_list),
                                    'Item Quantity': len(order_items),
                                    'Calculated Dead Weight': round(total_dead_weight, 2),
                                    'Calculated Volume Weight': round(total_vol_weight, 2),
                                    'Charged Weight': charged_weight,
                                    'Analysis': analysis,
                                    'Status': status
                                })
                        
                        # Store results
                        st.session_state.validation_results = pd.DataFrame(results)
                        st.success("✅ Validation completed successfully!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error during validation: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

with tab2:
    if st.session_state.validation_results is not None:
        results_df = st.session_state.validation_results
        
        # Metrics
        st.markdown("### 📊 Validation Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        total_records = len(results_df)
        error_records = len(results_df[results_df['Status'] == 'Error'])
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
                <div class="metric-label">Weight Errors</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-top-color: #f59e0b;">
                <div class="metric-value" style="color: #f59e0b;">{missing_records}</div>
                <div class="metric-label">Missing Orders</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filter options
        st.markdown("### 🔍 Filter Results")
        filter_option = st.radio(
            "Show:",
            ["All Records", "Errors Only", "Missing Orders Only", "Correct Records Only"],
            horizontal=True
        )
        
        filtered_df = results_df.copy()
        if filter_option == "Errors Only":
            filtered_df = results_df[results_df['Status'] == 'Error']
        elif filter_option == "Missing Orders Only":
            filtered_df = results_df[results_df['Status'] == 'Missing']
        elif filter_option == "Correct Records Only":
            filtered_df = results_df[results_df['Status'] == 'OK']
        
        # Display results
        st.markdown("### 📋 Detailed Results")
        
        # Style the dataframe
        def highlight_status(row):
            if row['Status'] == 'Error':
                return ['background-color: #fee2e2'] * len(row)
            elif row['Status'] == 'Missing':
                return ['background-color: #fef3c7'] * len(row)
            elif row['Status'] == 'OK':
                return ['background-color: #d1fae5'] * len(row)
            return [''] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Download options
        st.markdown("### 📥 Export Results")
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Validation Results')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name="billing_validation_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # CSV export
            csv_data = results_df.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_data,
                file_name="billing_validation_results.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("👆 Upload files and run validation to see results here")

with tab3:
    st.markdown("""
    <div class="info-box">
        <h3>📖 How to Use This Application</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### Step 1: Configure Item Weights
    
    Use the sidebar to configure weight settings for each item:
    - Click **"Add New Item"** in the sidebar
    - Enter the item name exactly as it appears in your order file
    - Set the **Dead Weight** (actual physical weight in kg)
    - Set the **Volumetric Weight** (dimensional weight in kg)
    - Click **"Add Item"** to save
    
    ### Step 2: Upload Files
    
    **Billing File (Excel):**
    - Must contain columns for AWB number and charged weight
    - Common column names: `AWB`, `AWB Number`, `Charged Weight`, `Weight`
    
    **Order File (Excel/CSV):**
    - Must contain columns for AWB, Item Name, and Quantity
    - Common column names: `AWB`, `Item`, `Item Name`, `Quantity`, `Qty`
    - Can have multiple items per AWB
    
    ### Step 3: Run Validation
    
    Click the **"Validate Billing"** button to:
    - Calculate total weight per AWB (using higher of dead/volumetric weight)
    - Compare calculated weight with charged weight
    - Flag discrepancies where charged weight < calculated weight
    - Identify missing AWBs (present in billing but not in orders)
    
    ### Step 4: Review Results
    
    The results will show:
    - ✅ **OK**: Charged weight is appropriate
    - ❌ **Error**: Calculated weight exceeds charged weight (billing issue)
    - ⚠️ **Missing**: AWB not found in order file
    
    ### Step 5: Export
    
    Download results as Excel or CSV for further analysis.
    
    ---
    
    ### 💡 Tips
    
    - **Save your settings**: Use Export Settings to save item configurations
    - **Reuse settings**: Import previously saved configurations
    - **Exact matching**: Ensure item names in settings match exactly with order file
    - **Multiple items**: System automatically sums weights for multi-item orders
    
    ---
    
    ### ⚖️ Billing Logic
    
    For each AWB:
    1. Calculate total dead weight = Σ (item dead weight × quantity)
    2. Calculate total volumetric weight = Σ (item volumetric weight × quantity)
    3. Billable weight = MAX(dead weight, volumetric weight)
    4. If billable weight > charged weight → Flag as error
    5. If billable weight ≤ charged weight → OK
    """)

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #94a3b8; font-size: 0.875rem;">Built with Streamlit • Powered by Python</p>',
    unsafe_allow_html=True
)
