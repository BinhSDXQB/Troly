import streamlit as st
import requests
import uuid
import json

def debug_request():
    """Debug chi tiết request để xác định nguyên nhân 403"""
    
    st.header("🔍 Debug 403 Forbidden Error")
    
    # Cấu hình
    bearer_token = st.text_input("BEARER_TOKEN:", type="password", help="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjN2FiMTU0ZS02NWZjLTQzYTQtYjM2OS04MjhiMTE5Njk4MWMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzU3OTI3NzIxLCJleHAiOjE3NjA0NjEyMDB9.FRkdwfFLF-Syc-QiBScOgQu2QT20P4kCQjX9kFtlrks")
    webhook_url = st.text_input("WEBHOOK_URL:", value="https://sxdqt.com.vn/webhook/5e7bc971-122a-4d85-9bbd-34b5cf75104d-6868")
    
    if st.button("🔍 Debug Request"):
        if not bearer_token:
            st.error("❌ Vui lòng nhập BEARER_TOKEN")
            return
            
        st.write("---")
        st.subheader("📋 Thông tin Request")
        
        # Hiển thị thông tin request
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "User-Agent": "Streamlit-Debug/1.0"
        }
        
        payload = {
            "sessionId": str(uuid.uuid4()),
            "chatInput": "test message"
        }
        
        st.write("**Headers:**")
        st.json({
            "Authorization": f"Bearer {bearer_token[:10]}...{bearer_token[-5:] if len(bearer_token) > 15 else bearer_token}",
            "Content-Type": "application/json",
            "User-Agent": "Streamlit-Debug/1.0"
        })
        
        st.write("**Payload:**")
        st.json(payload)
        
        st.write("**URL:**")
        st.code(webhook_url)
        
        st.write("---")
        st.subheader("🚀 Gửi Request")
        
        try:
            with st.spinner("Đang gửi request..."):
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            
            st.write(f"**Status Code:** {response.status_code}")
            
            if response.status_code == 403:
                st.error("❌ 403 Forbidden - Server từ chối truy cập")
                
                # Phân tích nguyên nhân
                st.write("**Các nguyên nhân có thể:**")
                st.write("1. 🔑 Bearer Token không hợp lệ hoặc hết hạn")
                st.write("2. 🚫 IP bị chặn hoặc không được whitelist")
                st.write("3. 📝 Format request không đúng")
                st.write("4. ⏰ Token có time-based restrictions")
                st.write("5. 🌐 CORS hoặc referrer policy")
                
            elif response.status_code == 200:
                st.success("✅ Request thành công!")
                try:
                    response_data = response.json()
                    st.json(response_data)
                except:
                    st.text(response.text)
            else:
                st.warning(f"⚠️ HTTP {response.status_code}")
            
            # Headers của response
            st.write("**Response Headers:**")
            st.json(dict(response.headers))
            
            # Body của response (nếu có)
            if response.text:
                st.write("**Response Body:**")
                try:
                    response_json = response.json()
                    st.json(response_json)
                except:
                    st.text(response.text[:1000] + "..." if len(response.text) > 1000 else response.text)
                    
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Request Error: {str(e)}")
            
    st.write("---")
    st.subheader("🛠️ Các cách khắc phục")
    
    with st.expander("1. Kiểm tra Bearer Token"):
        st.write("""
        - Token có đúng format không? (thường bắt đầu bằng các tiền tố như `sk-`, `bearer_`, etc.)
        - Token còn hạn sử dụng không?
        - Token có quyền truy cập endpoint này không?
        - Thử generate token mới từ dashboard
        """)
    
    with st.expander("2. Thử các Header khác"):
        if st.button("Test với headers khác nhau"):
            test_headers = [
                {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"},
                {"Authorization": bearer_token, "Content-Type": "application/json"},  # Không có "Bearer "
                {"X-API-Key": bearer_token, "Content-Type": "application/json"},  # API Key header
                {"Authorization": f"Token {bearer_token}", "Content-Type": "application/json"},  # Token thay Bearer
            ]
            
            for i, test_header in enumerate(test_headers):
                st.write(f"**Test {i+1}:** {test_header}")
                try:
                    resp = requests.post(webhook_url, json=payload, headers=test_header, timeout=10)
                    st.write(f"Status: {resp.status_code}")
                    if resp.status_code != 403:
                        st.success(f"✅ Header {i+1} hoạt động!")
                        break
                except Exception as e:
                    st.write(f"Error: {e}")
    
    with st.expander("3. Test với payload khác"):
        st.write("Thử các format payload khác nhau:")
        
        test_payloads = [
            {"sessionId": str(uuid.uuid4()), "chatInput": "test"},
            {"session_id": str(uuid.uuid4()), "chat_input": "test"},  # snake_case
            {"message": "test", "sessionId": str(uuid.uuid4())},  # order khác
            {"prompt": "test"},  # minimal payload
            {}  # empty payload
        ]
        
        if st.button("Test payloads"):
            for i, test_payload in enumerate(test_payloads):
                st.write(f"**Payload {i+1}:**")
                st.json(test_payload)
                try:
                    resp = requests.post(
                        webhook_url, 
                        json=test_payload, 
                        headers={"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}, 
                        timeout=10
                    )
                    st.write(f"Status: {resp.status_code}")
                    if resp.status_code != 403:
                        st.success(f"✅ Payload {i+1} hoạt động!")
                except Exception as e:
                    st.write(f"Error: {e}")
    
    with st.expander("4. Test endpoint availability"):
        if st.button("Ping endpoint"):
            try:
                # Test basic connectivity
                resp = requests.get("https://sxdqt.com.vn/", timeout=10)
                st.write(f"Main site status: {resp.status_code}")
                
                # Test webhook endpoint với GET
                resp = requests.get(webhook_url, timeout=10)
                st.write(f"Webhook GET status: {resp.status_code}")
                
                # Test với OPTIONS (CORS preflight)
                resp = requests.options(webhook_url, timeout=10)
                st.write(f"OPTIONS status: {resp.status_code}")
                
            except Exception as e:
                st.error(f"Connection error: {e}")
                
    with st.expander("5. Liên hệ Admin"):
        st.write("""
        Nếu tất cả các cách trên đều không được:
        - Liên hệ admin của sxdqt.com.vn
        - Kiểm tra xem có thông báo maintenance không
        - Xác nhận API endpoint và token còn active
        - Yêu cầu whitelist IP (nếu cần)
        """)

def main():
    st.set_page_config(page_title="Debug 403 Error", page_icon="🔍")
    debug_request()

if __name__ == "__main__":
    main()