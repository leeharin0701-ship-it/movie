import streamlit as st
from openai import OpenAI

# 페이지 제목 설정
st.title("⏰ 팩폭 만렙 시간 관리 플래너 AI")
st.write("시간을 효율적으로 쓰도록 팩트 폭력과 다정한 조언을 건네는 플래너입니다.")

# 1. 시크릿(Secrets)에서 Gemini API 키 불러오기
# Streamlit Cloud나 .streamlit/secrets.toml에 GEMINI_API_KEY가 등록되어 있어야 합니다.
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("비밀 금고(secrets)에 GEMINI_API_KEY가 설정되어 있지 않습니다.")
    st.stop()

# 2. OpenAI 라이브러리를 통해 Gemini API 연결 설정 (요청하신 접속 주소와 모델명 사용)
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 3. 대화 기록을 기억하기 위한 세션 상태(st.session_state) 초기화 (시간 관리 플래너 성격 부여)
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "system",
            "content": "너는 사용자의 시간 관리를 엄격하면서도 다정하게 도와주는 시간 관리 플래너야. 사용자가 게으름을 피우거나 계획을 미루면 팩폭(팩트 폭력)을 날리되, 실천 가능한 현실적인 대안을 제시해 줘. 반드시 순수 한국어로만 답해."
        }
    ]

# 4. 화면에 이전 대화 내용(말풍선) 출력하기 (시스템 성격 프롬프트는 화면에 보이지 않게 제외)
for message in st.session_state["messages"]:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 5. 사용자가 채팅 입력창에 메시지를 입력했을 때 처리
if prompt := st.chat_input("오늘 할 일이나 고민을 털어놓으세요!"):
    
    # 사용자가 입력한 메시지를 세션 대화 기록에 저장
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    # 사용자 말풍선을 화면에 즉시 표시
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # AI의 답변을 출력할 말풍선 준비 및 실시간 스트리밍 처리
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # OpenAI 라이브러리로 Gemini API 호출 (스트리밍 활성화)
            stream = client.chat.completions.create(
                model="gemini-3.5-flash-lite",
                messages=st.session_state["messages"],
                stream=True
            )
            
            # 글자가 실시간으로 흘러나오도록 조각(chunk)을 이어붙임
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            # 최종 완성된 답변을 화면에 업데이트 (커서 제거)
            message_placeholder.markdown(full_response)
            
            # AI의 답변을 세션 대화 기록에 저장 (이전 대화 기억용)
            st.session_state["messages"].append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            # 요청 실패 시 빨간 오류 화면 대신 친절한 한국어 안내 문구 한 줄 출력
            message_placeholder.error("죄송해요, 답변을 가져오는 중에 문제가 발생했어요. 잠시 후 다시 시도해 주세요!")
