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
    page_title="遠端資料庫列印系統",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置設定
API_BASE_URL = st.secrets.get("API_BASE_URL", "https://parade-capture-folks-lf.trycloudflare.com")  # 從Streamlit secrets獲取API地址

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
def load_data():
    """從本地API載入資料"""
    try:
        response = requests.get(f"{API_BASE_URL}/data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            st.error(f"載入資料失敗: HTTP {response.status_code}")
            return []
    except Exception as e:
        st.error(f"無法載入資料: {str(e)}")
        return []

@st.cache_data(ttl=300)  # 快取5分鐘
def load_categories():
    """載入產品類別"""
    try:
        response = requests.get(f"{API_BASE_URL}/data/categories", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("categories", [])
        return []
    except Exception as e:
        st.error(f"無法載入類別: {str(e)}")
        return []

def get_item_details(item_id):
    """獲取特定產品詳情"""
    try:
        response = requests.get(f"{API_BASE_URL}/data/item/{item_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("item", {})
        return {}
    except Exception as e:
        st.error(f"無法載入產品詳情: {str(e)}")
        return {}

def generate_pdf_report(item_data):
    """生成PDF報告 - 支援中文字體"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # 註冊中文字體
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    
    try:
        # 嘗試註冊中文字體（Windows系統）
        pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/simsun.ttc'))
        chinese_style = ParagraphStyle(
            'Chinese',
            parent=styles['Normal'],
            fontName='SimSun',
            fontSize=12,
            leading=16
        )
        title_style = ParagraphStyle(
            'ChineseTitle',
            parent=styles['Title'],
            fontName='SimSun',
            fontSize=18,
            leading=22
        )
    except:
        # 如果中文字體載入失敗，使用預設字體
        chinese_style = styles['Normal']
        title_style = styles['Title']
    
    # 標題
    title = Paragraph("銷售資料列印報告", title_style)
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # 銷售資訊
    content = [
        f"<b>通路:</b> {item_data.get('channel', 'N/A')}",
        f"<b>門市代碼:</b> {item_data.get('store_code', 'N/A')}",
        f"<b>訂單ID:</b> {item_data.get('order_id', 'N/A')}",
        f"<b>會員ID:</b> {item_data.get('member_id', 'N/A')}",
        f"<b>業務代表:</b> {item_data.get('sales_rep_id', 'N/A')}",
        f"<b>銷售日期:</b> {item_data.get('sale_date', 'N/A')}",
        f"<b>產品ID:</b> {item_data.get('product_id', 'N/A')}",
        f"<b>產品名稱:</b> {item_data.get('product_name', 'N/A')}",
        f"<b>數量:</b> {item_data.get('quantity', 'N/A')}",
        f"<b>價格:</b> NT$ {float(item_data.get('price', 0)):,.0f}",
        f"<b>一級分類:</b> {item_data.get('category_l1', 'N/A')}",
        f"<b>二級分類:</b> {item_data.get('category_l2', 'N/A')}",
        f"<b>三級分類:</b> {item_data.get('category_l3', 'N/A')}",
        f"<b>列印時間:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    
    for line in content:
        para = Paragraph(line, chinese_style)
        story.append(para)
        story.append(Spacer(1, 0.1*inch))
    
    # 分隔線
    story.append(Spacer(1, 0.3*inch))
    separator = Paragraph("─" * 50, chinese_style)
    story.append(separator)
    story.append(Spacer(1, 0.2*inch))
    
    # 備註
    note_style = ParagraphStyle(
        'ChineseNote',
        parent=chinese_style,
        fontSize=10,
        fontStyle='italic' if chinese_style.fontName == 'Helvetica' else 'normal'
    )
    note = Paragraph("此為系統自動生成的銷售資料報告", note_style)
    story.append(note)
    
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
    """主應用程式"""
    # 標題
    st.markdown('<h1 class="main-header">🖨️ 遠端資料庫列印系統</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # 側邊欄 - 系統狀態和設定
    with st.sidebar:
        st.header("📊 系統狀態")
        
        # API連接狀態
        if check_api_connection():
            st.markdown('<div class="status-success">✅ API連接正常</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-error">❌ API連接失敗</div>', unsafe_allow_html=True)
            st.error("請確認本地API服務正在運行")
            st.stop()
        
        st.markdown("---")
        
        # 重新整理資料
        if st.button("🔄 重新載入資料"):
            st.cache_data.clear()
            st.rerun()
        
        # API地址顯示
        st.header("⚙️ 設定資訊")
        st.text(f"API地址: {API_BASE_URL}")
        
        # 使用說明
        st.header("📖 使用說明")
        st.markdown("""
        1. 選擇產品類別 (可選)
        2. 從下拉選單選擇產品
        3. 查看產品詳情
        4. 點擊列印按鈕
        5. 瀏覽器會自動開啟列印對話框
        """)
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📋 產品選擇")
        
        # 載入資料
        data = load_data()
        categories = load_categories()
        
        if not data:
            st.warning("無法載入產品資料，請檢查API連接")
            return
        
        # 類別篩選
        category_filter = "全部"
        if categories:
            category_options = ["全部"] + categories
            category_filter = st.selectbox("🏷️ 選擇產品類別:", category_options)
        
        # 根據類別篩選資料
        if category_filter != "全部":
            filtered_data = [item for item in data if item.get("category") == category_filter]
        else:
            filtered_data = data
        
        if not filtered_data:
            st.warning(f"類別 '{category_filter}' 中沒有產品")
            return
        
        # 產品選擇下拉選單 - 適應不同的欄位名稱
        product_options = []
        for item in filtered_data:
            # 嘗試不同的名稱欄位
            name = (item.get('name') or
                   item.get('product_name') or
                   item.get('order_id') or
                   str(item.get(list(item.keys())[0], 'Unknown')))
            
            # 嘗試不同的ID欄位
            item_id = (item.get('id') or
                      item.get('order_id') or
                      item.get('product_id') or
                      item.get('member_id') or
                      str(list(item.values())[0]))
            
            # 獲取價格
            price = item.get('price', 0)
            if price is None:
                price = 0
            
            option_text = f"{name} (ID: {item_id}) - NT${float(price):,.0f}"
            product_options.append(option_text)
        
        selected_option = st.selectbox(
            "🔍 選擇要列印的產品:",
            options=range(len(product_options)),
            format_func=lambda x: product_options[x] if x < len(product_options) else ""
        )
        
        # 顯示選中產品的詳細資訊
        if selected_option is not None and selected_option < len(filtered_data):
            selected_item = filtered_data[selected_option]
            
            st.subheader("📝 產品詳細資訊")
            
            # 取得完整產品詳情 - 使用適當的ID欄位
            item_id = (selected_item.get('order_id') or
                      selected_item.get('product_id') or
                      selected_item.get('member_id') or
                      list(selected_item.values())[0])  # 使用第一個值作為ID
            
            try:
                item_details = get_item_details(item_id)
                if item_details:
                    selected_item = item_details
            except:
                # 如果獲取詳情失敗，使用原始資料
                pass
            
            # 使用表格顯示產品資訊 - 適應不同的欄位名稱
            detail_df = pd.DataFrame([
                {"項目": "通路", "內容": selected_item.get('channel', 'N/A')},
                {"項目": "門市代碼", "內容": selected_item.get('store_code', 'N/A')},
                {"項目": "訂單ID", "內容": selected_item.get('order_id', 'N/A')},
                {"項目": "會員ID", "內容": selected_item.get('member_id', 'N/A')},
                {"項目": "業務代表", "內容": selected_item.get('sales_rep_id', 'N/A')},
                {"項目": "銷售日期", "內容": selected_item.get('sale_date', 'N/A')},
                {"項目": "產品ID", "內容": selected_item.get('product_id', 'N/A')},
                {"項目": "產品名稱", "內容": selected_item.get('product_name', 'N/A')},
                {"項目": "數量", "內容": str(selected_item.get('quantity', 'N/A'))},
                {"項目": "價格", "內容": f"NT$ {float(selected_item.get('price', 0)):,.0f}"},
                {"項目": "一級分類", "內容": selected_item.get('category_l1', 'N/A')},
                {"項目": "二級分類", "內容": selected_item.get('category_l2', 'N/A')},
                {"項目": "三級分類", "內容": selected_item.get('category_l3', 'N/A')}
            ])
            
            st.dataframe(detail_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.header("🖨️ 列印操作")
        
        if 'selected_item' in locals() and selected_item:
            # 列印預覽
            st.subheader("列印預覽")
            st.info(f"📄 將列印: {selected_item.get('name', 'N/A')}")
            
            # 列印按鈕
            if st.button("🖨️ 立即列印", type="primary", use_container_width=True):
                with st.spinner("正在準備列印..."):
                    try:
                        # 生成PDF
                        pdf_data = generate_pdf_report(selected_item)
                        
                        # 記錄列印操作
                        log_print_action(selected_item)
                        
                        # 觸發瀏覽器列印
                        trigger_browser_print(pdf_data, selected_item.get('name', ''))
                        
                        # 顯示成功訊息
                        st.success("列印指令已發送！")
                        st.balloons()
                        
                        # 提供下載選項
                        st.download_button(
                            label="📄 下載PDF",
                            data=pdf_data,
                            file_name=f"product_{selected_item.get('id', 'unknown')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"列印失敗: {str(e)}")
            
            st.markdown("---")
            
            # 列印說明
            st.subheader("💡 列印提示")
            st.markdown("""
            - 點擊列印後，瀏覽器會自動開啟列印對話框
            - 請確保印表機已連接並可用
            - 可以選擇下載PDF後手動列印
            - 支援各種印表機和紙張大小
            """)
        
        else:
            st.info("請先選擇要列印的產品")
    
    # 頁腳資訊
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 總產品數", len(data) if data else 0)
    
    with col2:
        st.metric("🏷️ 產品類別", len(categories) if categories else 0)
    
    with col3:
        if 'filtered_data' in locals():
            st.metric("🔍 篩選結果", len(filtered_data))
        else:
            st.metric("🔍 篩選結果", 0)

if __name__ == "__main__":
    main()