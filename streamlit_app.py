import streamlit as st
import requests
import uuid
import re

# Hàm đọc nội dung từ file văn bản
def rfile(name_file):
    try:
        with open(name_file, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"File {name_file} không tồn tại.")
        return ""

def generate_session_id():
    return str(uuid.uuid4())

def send_message_to_llm(session_id, message):
    # Lấy config từ secrets
    try:
        bearer_token = st.secrets.get("BEARER_TOKEN", "")
        webhook_url = st.secrets.get("WEBHOOK_URL", "")
        
        # Nếu không có trong secrets, thử đọc từ file
        if not webhook_url:
            webhook_url = rfile("WEBHOOK_URL.txt").strip()
        
        if not bearer_token:
            return "Error: BEARER_TOKEN không được cấu hình", None
        
        if not webhook_url:
            return "Error: WEBHOOK_URL không được cấu hình", None
            
    except Exception as e:
        return f"Error: Lỗi đọc cấu hình - {str(e)}", None
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sessionId": session_id,
        "chatInput": message
    }
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        
        # Xử lý response
        try:
            content = response_data.get("content") or response_data.get("output")
            image_url = response_data.get('url', None)
            return content, image_url
        except:
            content = response_data[0].get("content") or response_data[0].get("output")
            image_url = response_data[0].get('url', None)
            return content, image_url
            
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to connect to the LLM - {str(e)}", None

def main():
    st.set_page_config(page_title="Trợ lý AI", page_icon="🤖", layout="centered")
    
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
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Debug panel
    with st.sidebar:
        st.header("🔧 Debug Info")
        
        # Kiểm tra secrets
        bearer_token = st.secrets.get("BEARER_TOKEN", "")
        webhook_url = st.secrets.get("WEBHOOK_URL", "") or rfile("WEBHOOK_URL.txt").strip()
        
        if bearer_token:
            st.success("✅ BEARER_TOKEN: OK")
        else:
            st.error("❌ BEARER_TOKEN: Missing")
        
        if webhook_url:
            st.success("✅ WEBHOOK_URL: OK")
            st.text(webhook_url)
        else:
            st.error("❌ WEBHOOK_URL: Missing")
        
        # Test connection button
        if st.button("Test Connection"):
            if bearer_token and webhook_url:
                test_response, _ = send_message_to_llm(generate_session_id(), "test")
                if "Error" in test_response:
                    st.error(f"❌ {test_response}")
                else:
                    st.success("✅ Connection OK")
            else:
                st.error("❌ Missing configuration")
    
    # Đọc tiêu đề từ file
    title_content = rfile("00.xinchao.txt")
    if not title_content:
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
            st.markdown(f'<div class="assistant">{message["content"]}</div>', unsafe_allow_html=True)
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

    # Ô nhập liệu
    if prompt := st.chat_input("Nhập nội dung cần trao đổi ở đây nhé?"):
        # Thêm tin nhắn user
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(f'<div class="user">{prompt}</div>', unsafe_allow_html=True)
        
        # Gửi request tới LLM
        with st.spinner("Đang chờ phản hồi từ AI..."):
            llm_response, image_url = send_message_to_llm(st.session_state.session_id, prompt)
    
        # Hiển thị response
        if isinstance(llm_response, str) and "Error" in llm_response:
            st.error(llm_response)
        else:
            st.markdown(f'<div class="assistant">{llm_response}</div>', unsafe_allow_html=True)
            
            if image_url:
                st.markdown(
                    f"""
                    <a href="{image_url}" target="_blank">
                        <img src="{image_url}" alt="Biểu đồ" style="width: 100%; height: auto; margin-bottom: 10px;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
        
        # Thêm response vào lịch sử
        st.session_state.messages.append({
            "role": "assistant", 
            "content": llm_response,
            "image_url": image_url
        })
        
        st.rerun()

if __name__ == "__main__":
    main()