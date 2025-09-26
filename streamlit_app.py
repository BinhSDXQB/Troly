import streamlit as st
import requests
import uuid
import re
import time
import json

# Hàm đọc nội dung từ file văn bản
def rfile(name_file):
    try:
        with open(name_file, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"File {name_file} không tồn tại.")
        return ""

# Constants với validation
def get_config():
    """Lấy cấu hình từ secrets với validation"""
    bearer_token = st.secrets.get("BEARER_TOKEN")
    webhook_url = st.secrets.get("WEBHOOK_URL")
    
    if not bearer_token:
        st.error("❌ BEARER_TOKEN không được cấu hình trong secrets")
        st.stop()
    
    if not webhook_url:
        st.error("❌ WEBHOOK_URL không được cấu hình trong secrets")
        st.stop()
    
    return bearer_token, webhook_url

def generate_session_id():
    return str(uuid.uuid4())

def send_message_to_llm(session_id, message, max_retries=3):
    """Gửi message đến LLM với retry logic và error handling chi tiết"""
    bearer_token, webhook_url = get_config()
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "User-Agent": "Streamlit-Chat-App/1.0"
    }
    
    payload = {
        "sessionId": session_id,
        "chatInput": message
    }
    
    for attempt in range(max_retries):
        try:
            # Hiển thị attempt nếu > 1
            if attempt > 0:
                st.info(f"Thử lại lần {attempt + 1}/{max_retries}...")
            
            response = requests.post(
                webhook_url, 
                json=payload, 
                headers=headers,
                timeout=30  # Timeout 30 giây
            )
            
            # Debug response status
            if response.status_code != 200:
                st.error(f"HTTP Status: {response.status_code}")
                if hasattr(response, 'text'):
                    st.error(f"Response: {response.text[:500]}")
            
            response.raise_for_status()
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                return f"Error: Invalid JSON response from server", None
            
            # Xử lý response data với nhiều format khác nhau
            content = None
            image_url = None
            
            # Format 1: Direct response
            if isinstance(response_data, dict):
                content = response_data.get("content") or response_data.get("output") or response_data.get("text")
                image_url = response_data.get('url') or response_data.get('image_url')
            
            # Format 2: Array response
            elif isinstance(response_data, list) and len(response_data) > 0:
                first_item = response_data[0]
                content = first_item.get("content") or first_item.get("output") or first_item.get("text")
                image_url = first_item.get('url') or first_item.get('image_url')
            
            # Format 3: Nested response
            elif "data" in response_data and isinstance(response_data["data"], dict):
                data = response_data["data"]
                content = data.get("content") or data.get("output") or data.get("text")
                image_url = data.get('url') or data.get('image_url')
            
            if content is None:
                return f"Error: No content found in response. Response structure: {str(response_data)[:200]}...", None
            
            return content, image_url
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Error: Không thể kết nối đến server (lần {attempt + 1})"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return error_msg, None
            
        except requests.exceptions.Timeout:
            error_msg = f"Error: Timeout - Server không phản hồi trong 30s (lần {attempt + 1})"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return error_msg, None
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                return "Error: 403 Forbidden - Kiểm tra BEARER_TOKEN hoặc quyền truy cập", None
            elif response.status_code == 401:
                return "Error: 401 Unauthorized - BEARER_TOKEN không hợp lệ", None
            elif response.status_code == 429:
                error_msg = f"Error: 429 Rate Limited - Quá nhiều request (lần {attempt + 1})"
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait longer for rate limit
                    continue
                return error_msg, None
            else:
                return f"Error: HTTP {response.status_code} - {str(e)}", None
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error: Request failed - {str(e)}"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return error_msg, None
        
        except Exception as e:
            return f"Error: Unexpected error - {str(e)}", None
    
    return "Error: Đã thử lại nhiều lần nhưng vẫn không thành công", None

def extract_text(output):
    """Trích xuất văn bản từ chuỗi output (loại bỏ hình ảnh)"""
    # Loại bỏ tất cả các phần chứa hình ảnh
    text_only = re.sub(r'!\[.*?\]\(.*?\)', '', output)
    return text_only

def display_message_with_image(text, image_url):
    """Hiển thị tin nhắn với văn bản và hình ảnh"""
    if image_url:
        st.markdown(
            f"""
            <a href="{image_url}" target="_blank">
                <img src="{image_url}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
            </a>
            """,
            unsafe_allow_html=True
        )
    
    # Hiển thị văn bản
    st.markdown(text, unsafe_allow_html=True)

def reset_session():
    """Reset session và tạo session ID mới"""
    st.session_state.messages = []
    st.session_state.session_id = generate_session_id()
    st.success("Đã reset cuộc hội thoại!")

def main():
    st.set_page_config(
        page_title="Trợ lý AI", 
        page_icon="🤖", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # CSS styling
    st.markdown(
        """
        <style>
            .assistant {
                padding: 10px;
                border-radius: 10px;
                max-width: 75%;
                background: none;
                text-align: left;
                margin-bottom: 10px;
            }
            .user {
                padding: 10px;
                border-radius: 10px;
                max-width: 75%;
                background: none;
                text-align: right;
                margin-left: auto;
                margin-bottom: 10px;
            }
            .assistant::before { content: "🤖 "; font-weight: bold; }
            .user::before { content: " "; font-weight: bold; }
            .error-message {
                background-color: #ffebee;
                border-left: 4px solid #f44336;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Sidebar cho debug và settings
    with st.sidebar:
        st.header("🔧 Debug & Settings")
        
        # Hiển thị trạng thái cấu hình
        try:
            bearer_token, webhook_url = get_config()
            st.success("✅ Cấu hình OK")
            st.text(f"URL: {webhook_url[:30]}...")
            st.text(f"Token: {bearer_token[:10]}...")
        except:
            st.error("❌ Cấu hình thiếu")
        
        # Reset button
        if st.button("🔄 Reset Chat", key="reset_btn"):
            reset_session()
        
        # Test connection
        if st.button("🔍 Test Connection", key="test_btn"):
            with st.spinner("Testing..."):
                session_id = generate_session_id()
                response, _ = send_message_to_llm(session_id, "test")
                if "Error" in response:
                    st.error(f"Connection failed: {response}")
                else:
                    st.success("✅ Connection OK")
    
    # Hiển thị logo (nếu có)
    try:
        col1, col2, col3 = st.columns([3, 2, 3])
        with col2:
            st.image("logo.png")
    except:
        pass
    
    # Đọc nội dung tiêu đề từ file
    try:
        title_content = rfile("00.xinchao.txt")
        if not title_content:
            title_content = "Trợ lý AI"
    except Exception as e:
        title_content = "Trợ lý AI"

    st.markdown(
        f"""<h1 style="text-align: center; font-size: 24px;">{title_content}</h1>""",
        unsafe_allow_html=True
    )

    # Khởi tạo session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()

    # Hiển thị lịch sử tin nhắn
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            # Kiểm tra nếu là error message
            if message["content"].startswith("Error:"):
                st.markdown(f'<div class="error-message">❌ {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant">{message["content"]}</div>', unsafe_allow_html=True)
                # Hiển thị hình ảnh nếu có
                if "image_url" in message and message["image_url"]:
                    st.markdown(
                        f"""
                        <a href="{message['image_url']}" target="_blank">
                            <img src="{message['image_url']}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
                        </a>
                        """,
                        unsafe_allow_html=True
                    )
        elif message["role"] == "user":
            st.markdown(f'<div class="user">{message["content"]}</div>', unsafe_allow_html=True)

    # Ô nhập liệu cho người dùng
    if prompt := st.chat_input("Nhập nội dung cần trao đổi ở đây nhé?"):
        # Validate input
        if len(prompt.strip()) == 0:
            st.warning("⚠️ Vui lòng nhập nội dung!")
            return
        
        # Thêm tin nhắn người dùng vào lịch sử
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Hiển thị tin nhắn người dùng ngay lập tức
        st.markdown(f'<div class="user">{prompt}</div>', unsafe_allow_html=True)
        
        # Gửi yêu cầu đến LLM và nhận phản hồi
        with st.spinner("Đang chờ phản hồi từ AI..."):
            llm_response, image_url = send_message_to_llm(st.session_state.session_id, prompt)
    
        # Xử lý phản hồi
        if isinstance(llm_response, str) and llm_response.startswith("Error"):
            # Hiển thị lỗi
            st.markdown(f'<div class="error-message">❌ {llm_response}</div>', unsafe_allow_html=True)
            # Thêm tin nhắn lỗi vào lịch sử
            st.session_state.messages.append({
                "role": "assistant", 
                "content": llm_response,
                "image_url": None
            })
        else:
            # Hiển thị phản hồi từ AI
            st.markdown(f'<div class="assistant">{llm_response}</div>', unsafe_allow_html=True)
            
            # Hiển thị hình ảnh nếu có
            if image_url:
                st.markdown(
                    f"""
                    <a href="{image_url}" target="_blank">
                        <img src="{image_url}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            
            # Thêm phản hồi AI vào lịch sử
            st.session_state.messages.append({
                "role": "assistant", 
                "content": llm_response,
                "image_url": image_url
            })
        
        # Rerun để cập nhật giao diện
        st.rerun()

if __name__ == "__main__":
    main()