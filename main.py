from datetime import datetime, timedelta, timezone
import requests
import streamlit as st

# 웹 앱의 제목 설정
st.title("🎬 어제의 영화 박스오피스 순위")
st.write(
    "영화진흥위원회(KOBIS) Open API를 활용해 어제의 박스오피스 순위를"
    " 보여드립니다."
)

# 1. 비밀 금고(secrets)에서 인증키 불러오기
try:
  api_key = st.secrets["KOBIS_KEY"]
except Exception:
  st.error(
      "⚠️ 인증키를 찾을 수 없습니다.\n\n안내: Streamlit 클라우드 설정(Settings"
      " -> Secrets)에 'KOBIS_KEY = \"발급받은키\"'가 올바르게 등록되어 있는지"
      " 확인해 주세요."
  )
  st.stop()

# 2. 한국 시간(KST) 기준으로 '어제' 날짜 자동 계산하기 (YYYYMMDD 형식)
kst = timezone(timedelta(hours=9))
yesterday = datetime.now(kst) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

st.info(
    f"📅 조회 기준일 (한국 시간 어제): {yesterday.strftime('%Y년 %m월 %d일')}"
)

# 3. KOBIS API 요청 주소 및 파라미터 설정
url = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
)
params = {"key": api_key, "targetDt": target_dt}


# 4. API 데이터를 안전하게 가져오는 함수 (캐시 적용)
@st.cache_data(ttl=3600)
def fetch_box_office(request_url, request_params):
  try:
    response = requests.get(request_url, params=request_params)
    response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
    return response.json()
  except requests.exceptions.RequestException as e:
    return {"error": f"네트워크 연결 오류: {e}"}


# 데이터 요청 실행
data = fetch_box_office(url, params)

# 5. 오류 및 예외 상황 처리 (한국어 안내)
if "error" in data:
  st.error(
      "❌ 서버와 통신하는 중 문제가 발생했습니다.\n\n안내: 인터넷 연결 상태나"
      f" API 서버 상태를 확인해 주세요. (상세 오류: {data['error']})"
  )
elif "faultInfo" in data:
  st.error(
      "❌ API 인증 또는 요청 오류가 발생했습니다.\n\n안내: KOBIS 인증키(KOBIS_KEY)"
      "가 올바른지, 혹은 일일 요청 허용량을 초과하지 않았는지 확인해 주세요."
  )
else:
  # 데이터 구조에서 영화 목록 추출
  box_office_result = data.get("boxOfficeResult", {})
  movie_list = box_office_result.get("dailyBoxOfficeList", [])

  # 영화 목록이 비어 있는 경우 처리
  if not movie_list:
    st.warning(
        "⚠️ 조회된 영화 목록이 없습니다.\n\n안내: 아직 어제 날짜의 박스오피스"
        " 집계가 완료되지 않았거나, 해당 날짜에 데이터가 없을 수 있습니다."
    )
  else:
    import pandas as pd

    # API로 받아온 데이터는 문자열이므로 필요한 항목을 숫자로 변환하며 정리
    processed_data = []
    for movie in movie_list:
      processed_data.append({
          "순위": int(movie["rank"]),
          "영화명": movie["movieNm"],
          "개봉일": movie["openDt"],
          "관객수": int(movie["audiCnt"]),
          "누적관객": int(movie["audiAcc"]),
          "스크린수": int(movie["scrnCnt"]),
      })

    df = pd.DataFrame(processed_data)

    # 6. 1위 영화 지표 카드 3장 만들기
    st.markdown("---")
    st.subheader("🥇 어제의 1위 영화 핵심 요약")
    top_movie = df.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("영화명", top_movie["영화명"])
    col2.metric("어제 관객수", f"{top_movie['관객수']:,}명")
    col3.metric("누적 관객수", f"{top_movie['누적관객']:,}명")

    # 7. 관객수 상위 5편 막대그래프 보여주기
    st.markdown("---")
    st.subheader("📊 관객수 상위 5편 비교")
    top5_df = df.head(5).set_index("영화명")[["관객수"]]
    st.bar_chart(top5_df)

    # 8. 전체 박스오피스 순위 표 보여주기
    st.markdown("---")
    st.subheader("📋 전체 박스오피스 순위표")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )
