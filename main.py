from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st

# 웹 앱의 제목과 레이아웃 설정
st.set_page_config(page_title="영화 박스오피스 순위", page_icon="🎬", layout="wide")

st.title("🎬 대한민국 박스오피스 순위 조회")
st.write(
    "영화진흥위원회(KOBIS) Open API를 활용하여 원하는 날짜의 박스오피스"
    " 순위를 확인하고 데이터를 다운로드하세요."
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

# 2. 날짜 선택기 추가 (사용자가 직접 날짜 선택 가능)
# 오늘 날짜 (한국 시간 기준)
kst = timezone(timedelta(hours=9))
today_kst = datetime.now(kst).date()
default_yesterday = today_kst - timedelta(days=1)

# 사이드바 또는 상단에 날짜 선택 캘린더 배치
selected_date = st.date_input(
    "📅 조회할 날짜를 선택하세요",
    value=default_yesterday,
    max_value=default_yesterday,  # 오늘 이후 데이터는 집계 전이므로 선택 제한
)

# API 요청용 YYYYMMDD 형식으로 변환
target_dt = selected_date.strftime("%Y%m%d")

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
        "⚠️ 조회된 영화 목록이 없습니다.\n\n안내: 선택한 날짜에 영화 상영"
        " 데이터가 존재하지 않거나 집계가 완료되지 않았을 수 있습니다. 다른"
        " 날짜를 선택해 보세요."
    )
  else:
    # API로 받아온 데이터는 문자열이므로 필요한 항목을 숫자로 변환하며 정리
    processed_data = []
    for movie in movie_list:
      # 순위 증감 및 신규 진입 여부 가공
      rank_inten = int(movie["rankInten"])
      old_new = movie["rankOldAndNew"]

      if old_new == "NEW":
        rank_display = "NEW 🔴"
      elif rank_inten > 0:
        rank_display = f"▲ {rank_inten}"
      elif rank_inten < 0:
        rank_display = f"▼ {abs(rank_inten)}"
      else:
        rank_display = "-"

      processed_data.append({
          "순위": int(movie["rank"]),
          "변동": rank_display,
          "영화명": movie["movieNm"],
          "개봉일": movie["openDt"],
          "관객수": int(movie["audiCnt"]),
          "누적관객": int(movie["audiAcc"]),
          "스크린수": int(movie["scrnCnt"]),
      })

    df = pd.DataFrame(processed_data)

    # 6. 1위 영화 지표 카드 3장 만들기
    st.markdown("---")
    st.subheader(
        f"🥇 [{selected_date.strftime('%Y년 %m월 %d일')}] 1위 영화 핵심 요약"
    )
    top_movie = df.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("영화명", top_movie["영화명"])
    col2.metric("당일 관객수", f"{top_movie['관객수']:,}명")
    col3.metric("누적 관객수", f"{top_movie['누적관객']:,}명")

    # 7. 관객수 상위 5편 막대그래프 보여주기
    st.markdown("---")
    st.subheader("📊 관객수 상위 5편 비교")
    top5_df = df.head(5).set_index("영화명")[["관객수"]]
    st.bar_chart(top5_df)

    # 8. 전체 박스오피스 순위 표 & CSV 다운로드 기능
    st.markdown("---")
    st.subheader("📋 전체 박스오피스 순위표")

    # 데이터프레임 시각화 (최신 Streamlit 호환을 위해 use_container_width 대신 파라미터 정리)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # CSV 다운로드 버튼
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 현재 순위표 CSV로 다운로드",
        data=csv_data,
        file_name=f"box_office_{target_dt}.csv",
        mime="text/csv",
    )
