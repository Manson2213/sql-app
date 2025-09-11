import streamlit as st
import requests
import base64
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO
import json

# 頁面配置
st.set_page_config(
    page_title="會員客戶查詢系統",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置設定 - 靈活的API地址配置
# 本地測試時使用 localhost，部署時使用 tunnel
LOCAL_API_URL = "http://localhost:8000"
TUNNEL_API_URL = "https://parade-capture-folks-lf.trycloudflare.com"

# 你可以在這裡切換模式：
# True = 使用本地API (適合開發測試)
# False = 使用tunnel API (適合生產部署)
USE_LOCAL_API = True

API_BASE_URL = LOCAL_API_URL if USE_LOCAL_API else TUNNEL_API_URL

# 也可以從Streamlit secrets覆蓋設定
API_BASE_URL = st.secrets.get("API_BASE_URL", API_BASE_URL)

# CSS樣式
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
    }
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .print-button {
        background-color: #28a745;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        cursor: pointer;
        font-size: 1rem;
        width: 100%;
    }
    .item-detail {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def check_api_connection():
    """檢查API連接狀態"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        st.error(f"API連接失敗: {str(e)}")
        return False

@st.cache_data(ttl=60)  # 快取1分鐘
def search_customers(query=None, search_type="all"):
    """搜尋客戶資料"""
    try:
        params = {}
        if query:
            params["q"] = query
        if search_type:
            params["search_type"] = search_type
            
        response = requests.get(f"{API_BASE_URL}/customers/search", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("customers", [])
        else:
            st.error(f"搜尋客戶失敗: HTTP {response.status_code}")
            return []
    except Exception as e:
        st.error(f"無法搜尋客戶資料: {str(e)}")
        return []

@st.cache_data(ttl=300)  # 快取5分鐘
def get_customer_by_id(member_id):
    """根據會員編號獲取客戶詳情"""
    try:
        response = requests.get(f"{API_BASE_URL}/customers/{member_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("customer", {})
        elif response.status_code == 404:
            return None
        else:
            st.error(f"獲取客戶資料失敗: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"無法獲取客戶詳情: {str(e)}")
        return None

@st.cache_data(ttl=300)  # 快取5分鐘
def list_all_customers(limit=20, offset=0):
    """獲取所有客戶列表"""
    try:
        params = {"limit": limit, "offset": offset}
        response = requests.get(f"{API_BASE_URL}/customers", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("customers", []), data.get("total_count", 0)
        else:
            st.error(f"載入客戶列表失敗: HTTP {response.status_code}")
            return [], 0
    except Exception as e:
        st.error(f"無法載入客戶列表: {str(e)}")
        return [], 0

def display_customers_as_dataframe(customers):
    """將客戶資料顯示為互動式表格"""
    if not customers:
        st.info("沒有客戶資料")
        return
    
    # 創建 DataFrame
    df = pd.DataFrame(customers)
    
    # 自定義欄位顯示順序和名稱
    column_mapping = {
        'member_id': '會員編號',
        'name': '客戶姓名', 
        'phone': '聯絡電話',
        'email': '電子郵件',
        'address': '聯絡地址',
        'level': '會員等級',
        'status': '會員狀態',
        'points': '累積點數',
        'join_date': '加入日期',
        'last_visit': '最後來訪'
    }
    
    # 確保所有需要的欄位都存在，如果不存在則填入預設值
    for key in column_mapping.keys():
        if key not in df.columns:
            df[key] = 'N/A'
    
    # 重新排列和重新命名欄位
    df_display = df[list(column_mapping.keys())].rename(columns=column_mapping)
    
    # 格式化累積點數欄位
    if '累積點數' in df_display.columns:
        df_display['累積點數'] = df_display['累積點數'].apply(lambda x: f"{x:,} 點" if pd.notnull(x) and str(x).isdigit() else str(x))
    
    # 顯示表格
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "會員編號": st.column_config.TextColumn(
                "會員編號",
                width="small",
                help="客戶的唯一會員編號"
            ),
            "客戶姓名": st.column_config.TextColumn(
                "客戶姓名",
                width="medium"
            ),
            "聯絡電話": st.column_config.TextColumn(
                "聯絡電話",
                width="medium"
            ),
            "電子郵件": st.column_config.TextColumn(
                "電子郵件",
                width="medium"
            ),
            "會員等級": st.column_config.TextColumn(
                "會員等級",
                width="small"
            ),
            "會員狀態": st.column_config.TextColumn(
                "會員狀態",
                width="small"
            ),
            "累積點數": st.column_config.TextColumn(
                "累積點數",
                width="small"
            )
        }
    )
    
    return df_display

def generate_batch_pdf_reports(selected_customers, all_customers):
    """批量生成PDF報告"""
    import zipfile
    from io import BytesIO
    
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for customer_info in selected_customers:
            # 從 customer_info 中提取會員編號
            member_id = customer_info.split('(')[1].split(')')[0]
            
            # 找到對應的客戶資料
            customer = next((c for c in all_customers if c['member_id'] == member_id), None)
            
            if customer:
                try:
                    # 生成單個PDF
                    pdf_data = generate_pdf_report(customer)
                    
                    # 添加到ZIP檔案
                    filename = f"客戶資料_{customer['member_id']}_{customer['name']}.pdf"
                    zip_file.writestr(filename, pdf_data)
                    
                except Exception as e:
                    st.error(f"生成 {customer['name']} 的PDF時發生錯誤: {str(e)}")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()



def generate_pdf_report(customer_data):
    """生成客戶資料PDF報告 - 表格格式，上半部客戶資料，下半部備註區域"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # 註冊中文字體
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    import os
    
    try:
        # 嘗試使用專案內的中文字體檔案
        possible_paths = [
            'font/NotoSansTC-Regular.ttf',
            './font/NotoSansTC-Regular.ttf',
            os.path.join('.', 'font', 'NotoSansTC-Regular.ttf'),
            os.path.join(os.getcwd(), 'font', 'NotoSansTC-Regular.ttf')
        ]
        
        font_path = None
        for path in possible_paths:
            if os.path.exists(path):
                font_path = path
                break
        
        if font_path:
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                chinese_style = ParagraphStyle(
                    'Chinese',
                    parent=styles['Normal'],
                    fontName='ChineseFont',
                    fontSize=11,
                    leading=14
                )
                title_style = ParagraphStyle(
                    'ChineseTitle',
                    parent=styles['Title'],
                    fontName='ChineseFont',
                    fontSize=16,
                    leading=20,
                    alignment=1  # 置中
                )
            except Exception as font_error:
                chinese_style = styles['Normal']
                title_style = styles['Title']
        else:
            chinese_style = styles['Normal']
            title_style = styles['Title']
    except Exception as general_error:
        chinese_style = styles['Normal']
        title_style = styles['Title']
    
    # 標題
    title = Paragraph("客戶資料表", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # 客戶資料表格
    table_data = [
        ['項目', '內容', '項目', '內容'],
        ['會員編號', customer_data.get('member_id', 'N/A'), '客戶姓名', customer_data.get('name', 'N/A')],
        ['聯絡電話', customer_data.get('phone', 'N/A'), '電子郵件', customer_data.get('email', 'N/A')],
        ['聯絡地址', customer_data.get('address', 'N/A'), '加入日期', customer_data.get('join_date', 'N/A')],
        ['會員等級', customer_data.get('level', 'N/A'), '會員狀態', customer_data.get('status', 'N/A')],
        ['累積點數', f"{customer_data.get('points', 0):,} 點", '最後來訪', customer_data.get('last_visit', 'N/A')]
    ]
    
    # 創建表格
    table = Table(table_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    
    # 表格樣式
    table.setStyle(TableStyle([
        # 標題行樣式
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), chinese_style.fontName if hasattr(chinese_style, 'fontName') else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # 標題行字體大小
        ('FONTSIZE', (0, 1), (-1, -1), 10),  # 內容字體大小
        
        # 邊框
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        
        # 項目欄位樣式（第1, 3列）
        ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
        ('BACKGROUND', (2, 1), (2, -1), colors.lightblue),
        
        # 內容對齊
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # 系統資訊
    info_data = [
        ['報告生成時間', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['系統版本', '客戶查詢系統 v2.0']
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 5.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), chinese_style.fontName if hasattr(chinese_style, 'fontName') else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.4*inch))
    
    # 備註區域標題
    notes_title = Paragraph("<b>備註欄位</b>", chinese_style)
    story.append(notes_title)
    story.append(Spacer(1, 0.1*inch))
    
    # 空白備註表格 - 創建多行空白表格供手寫備註
    notes_data = []
    for i in range(10):  # 10行空白
        notes_data.append(['', ''])
    
    notes_table = Table(notes_data, colWidths=[0.8*inch, 6.2*inch], rowHeights=[0.3*inch]*10)
    notes_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), chinese_style.fontName if hasattr(chinese_style, 'fontName') else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(notes_table)
    story.append(Spacer(1, 0.2*inch))
    
    # 頁腳
    footer_style = ParagraphStyle(
        'Footer',
        parent=chinese_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1  # 置中
    )
    footer = Paragraph("此為系統自動生成的客戶資料表，請妥善保管客戶隱私資訊", footer_style)
    story.append(footer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def trigger_browser_print(pdf_data, item_name):
    """觸發瀏覽器列印功能"""
    pdf_base64 = base64.b64encode(pdf_data).decode()
    
    # 生成JavaScript代碼來觸發列印
    print_js = f"""
    <script>
        function printPDF() {{
            const pdfData = '{pdf_base64}';
            const binaryString = atob(pdfData);
            const bytes = new Uint8Array(binaryString.length);
            
            for (let i = 0; i < binaryString.length; i++) {{
                bytes[i] = binaryString.charCodeAt(i);
            }}
            
            const blob = new Blob([bytes], {{type: 'application/pdf'}});
            const url = URL.createObjectURL(blob);
            
            // 開啟新視窗並列印
            const printWindow = window.open(url, '_blank');
            printWindow.onload = function() {{
                setTimeout(function() {{
                    printWindow.print();
                }}, 500);
            }};
        }}
        
        // 自動觸發列印
        printPDF();
    </script>
    """
    
    st.components.v1.html(print_js, height=0)

def log_print_action(item_data):
    """記錄列印操作"""
    try:
        log_data = {
            "item_id": item_data.get("order_id") or item_data.get("product_id"),
            "item_name": item_data.get("product_name"),
            "channel": item_data.get("channel"),
            "store_code": item_data.get("store_code"),
            "print_timestamp": datetime.now().isoformat(),
            "user_agent": "Streamlit App"
        }
        requests.post(f"{API_BASE_URL}/print-log", json=log_data, timeout=5)
    except Exception as e:
        st.warning(f"列印記錄失敗: {str(e)}")

def main():
    """主程序"""
    st.title("🔍 會員客戶查詢系統")
    st.markdown("---")
    
    # 側邊欄功能選單
    with st.sidebar:
        st.header("功能選單")
        
        # 資料庫連接狀態
        if check_database_connection():
            st.success("✅ 資料庫連接正常")
        else:
            st.error(" 資料庫連接失敗")
        
        st.markdown("---")
        
        # 主要功能選項
        option = st.selectbox(
            "選擇功能",
            ["客戶搜尋", "資料庫管理", "系統設定"]
        )
    
    # 主要內容區域
    if option == "客戶搜尋":
        customer_search_interface()
    elif option == "資料庫管理":
        database_management_interface()
    elif option == "系統設定":
        system_settings_interface()

def customer_search_interface():
    """客戶搜尋界面"""
    st.header("🔍 客戶搜尋")
    
    # 搜尋方式選擇
    search_method = st.radio(
        "選擇搜尋方式",
        ["手動輸入", "資料庫查詢"],
        horizontal=True
    )
    
    if search_method == "手動輸入":
        manual_input_interface()
    else:
        database_search_interface()

def manual_input_interface():
    """手動輸入界面"""
    st.subheader("📝 手動輸入客戶資料")
    
    col1, col2 = st.columns(2)
    
    with col1:
        member_id = st.text_input("會員編號", placeholder="輸入會員編號")
        name = st.text_input("客戶姓名", placeholder="輸入客戶姓名")
        phone = st.text_input("聯絡電話", placeholder="輸入聯絡電話")
        email = st.text_input("電子郵件", placeholder="輸入電子郵件")
    
    with col2:
        address = st.text_area("聯絡地址", placeholder="輸入聯絡地址")
        join_date = st.date_input("加入日期", datetime.now().date())
        level = st.selectbox("會員等級", ["普通會員", "銀卡會員", "金卡會員", "鑽石會員"])
        status = st.selectbox("會員狀態", ["正常", "暫停", "註銷"])
    
    col3, col4 = st.columns(2)
    with col3:
        points = st.number_input("累積點數", min_value=0, value=0)
    with col4:
        last_visit = st.date_input("最後來訪", datetime.now().date())
    
    st.markdown("---")
    
    # 操作按鈕
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    with col_btn1:
        if st.button("🖨️ 列印報告", type="primary", use_container_width=True):
            if member_id and name:
                customer_data = {
                    'member_id': member_id,
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'join_date': join_date.strftime('%Y-%m-%d'),
                    'level': level,
                    'status': status,
                    'points': points,
                    'last_visit': last_visit.strftime('%Y-%m-%d')
                }
                
                try:
                    pdf_data = generate_pdf_report(customer_data)
                    st.download_button(
                        label="📄 下載PDF報告",
                        data=pdf_data,
                        file_name=f"客戶資料_{member_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("PDF報告生成成功！")
                except Exception as e:
                    st.error(f"PDF生成失敗: {str(e)}")
            else:
                st.warning("請至少填入會員編號和姓名")
    
    with col_btn2:
        if st.button("🗑️ 清除資料", use_container_width=True):
            st.rerun()

def database_search_interface():
    """資料庫搜尋界面"""
    st.subheader("🔍 資料庫搜尋")
    
    # 初始化 session state
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_performed' not in st.session_state:
        st.session_state.search_performed = False
    
    # 搜尋條件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_member_id = st.text_input("會員編號", placeholder="輸入會員編號進行搜尋")
    with col2:
        search_name = st.text_input("客戶姓名", placeholder="輸入姓名進行搜尋")
    with col3:
        search_phone = st.text_input("聯絡電話", placeholder="輸入電話進行搜尋")
    
    # 搜尋和清除按鈕
    col_search, col_clear = st.columns([2, 1])
    
    with col_search:
        if st.button("🔍 開始搜尋", type="primary"):
            customers = search_customers_from_db(search_member_id, search_name, search_phone)
            if customers is not None:
                st.session_state.search_results = customers
                st.session_state.search_performed = True
    
    with col_clear:
        if st.button("🗑️ 清除結果"):
            st.session_state.search_results = []
            st.session_state.search_performed = False
            st.rerun()
    
    # 顯示搜尋結果（如果有的話）
    if st.session_state.search_performed and st.session_state.search_results:
        display_search_results(st.session_state.search_results)
    elif st.session_state.search_performed and not st.session_state.search_results:
        st.info("未找到符合條件的客戶資料")

def display_search_results(customers):
    """顯示搜尋結果 - 統一使用互動式表格"""
    st.success(f"找到 {len(customers)} 筆客戶資料")
    
    # 直接使用互動式表格顯示
    st.subheader("📊 客戶資料表格")
    display_customers_as_dataframe(customers)
    
    # 批量操作功能
    st.markdown("---")
    st.subheader("🛠️ 批量操作")
    
    # 客戶選擇器
    customer_options = [f"{c['name']} ({c['member_id']})" for c in customers]
    selected_customers = st.multiselect(
        "選擇要產生PDF的客戶：",
        options=customer_options,
        help="可選擇多個客戶一次產生PDF報告"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("📄 單個PDF", help="為每個選中的客戶生成獨立的PDF"):
            if selected_customers:
                for customer_info in selected_customers:
                    member_id = customer_info.split('(')[1].split(')')[0]
                    customer = next((c for c in customers if c['member_id'] == member_id), None)
                    
                    if customer:
                        try:
                            pdf_data = generate_pdf_report(customer)
                            st.download_button(
                                label=f"📥 下載 {customer['name']} 的PDF",
                                data=pdf_data,
                                file_name=f"客戶資料_{customer['member_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                key=f"single_download_{customer['member_id']}"
                            )
                        except Exception as e:
                            st.error(f"生成 {customer['name']} 的PDF失敗: {str(e)}")
            else:
                st.warning("請先選擇客戶")
    
    with col2:
        if st.button("📦 批量ZIP", help="將選中客戶的PDF打包成ZIP檔案"):
            if selected_customers:
                try:
                    zip_data = generate_batch_pdf_reports(selected_customers, customers)
                    st.download_button(
                        label="📥 下載批量PDF (ZIP)",
                        data=zip_data,
                        file_name=f"客戶資料批量_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        key="batch_download"
                    )
                    st.success(f"成功生成 {len(selected_customers)} 個客戶的PDF報告")
                except Exception as e:
                    st.error(f"批量生成PDF失敗: {str(e)}")
            else:
                st.warning("請先選擇客戶")
    
    with col3:
        if selected_customers:
            st.info(f"已選擇 {len(selected_customers)} 個客戶")
        else:
            st.info("尚未選擇客戶")

def search_customers_from_db(member_id="", name="", phone=""):
    """從資料庫搜尋客戶 - 返回搜尋結果"""
    try:
        # 構建搜尋參數 - 根據輸入的條件確定搜尋類型和關鍵字
        query = None
        search_type = "all"
        
        if member_id:
            query = member_id
            search_type = "member_id"
        elif name:
            query = name
            search_type = "name"
        elif phone:
            query = phone
            search_type = "phone"
        
        if not query:
            st.warning("請至少輸入一個搜尋條件")
            return None
        
        # 調用API搜尋
        params = {"q": query, "search_type": search_type}
        response = requests.get(f"{API_BASE_URL}/customers/search", params=params)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("customers", [])
            return customers
        else:
            st.error(f"搜尋失敗: {response.text}")
            return None
    
    except Exception as e:
        st.error(f"搜尋過程發生錯誤: {str(e)}")
        return None

def database_management_interface():
    """資料庫管理界面"""
    st.header("🗄️ 資料庫管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 顯示所有客戶", type="primary", use_container_width=True):
            show_all_customers()

def show_all_customers():
    """顯示所有客戶"""
    try:
        response = requests.get(f"{API_BASE_URL}/customers")
        if response.status_code == 200:
            data = response.json()
            customers = data.get("customers", [])
            if customers:
                st.dataframe(customers, use_container_width=True)
            else:
                st.info("目前沒有客戶資料")
        else:
            st.error(f"載入失敗: {response.text}")
    except Exception as e:
        st.error(f"載入過程發生錯誤: {str(e)}")

def system_settings_interface():
    """系統設定界面"""
    st.header("⚙️ 系統設定")
    
    st.subheader("API 設定")
    new_api_url = st.text_input("API 基礎網址", value=API_BASE_URL)
    
    if st.button("💾 儲存設定"):
        st.success("設定已儲存！")
    
    st.markdown("---")
    
    st.subheader("系統資訊")
    st.write(f"**目前API網址:** {API_BASE_URL}")
    st.write(f"**系統版本:** 客戶查詢系統 v2.0")
    st.write(f"**最後更新:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def check_database_connection():
    """檢查資料庫連接狀態"""
    try:
        response = requests.get(f"{API_BASE_URL}/customers", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    main()