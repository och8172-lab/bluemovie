import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 1. 페이지 기본 설정
st.set_page_config(page_title="박스오피스 대시보드", layout="wide")
st.title("🎬 어제의 박스오피스 & 타임머신")

# 2. 비밀 금고에서 인증키 꺼내기 (코드에는 키를 적지 않는다)
KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 3. 한국 시간 기준 어제 날짜 구하기
yesterday = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")
st.caption(f"📅 조회 기준일(어제): {yesterday.strftime('%Y년 %m월 %d일')}")


# 4. KOBIS API 데이터 호출 함수 (캐싱 적용으로 속도 향상 & 반복 요청 방지)
@st.cache_data(ttl="1h")
def fetch_boxoffice_data(key, dt_str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    try:
        res = requests.get(url, params={"key": key, "targetDt": dt_str}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "faultInfo" in data:
                return "KEY_ERROR", None
            box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            return "SUCCESS", box_list
    except Exception:
        return "NET_ERROR", None
    return "NO_DATA", None


# 어제 날짜 데이터 불러오기
status, box_list = fetch_boxoffice_data(KOBIS_KEY, target_dt)

if status == "KEY_ERROR":
    st.error("인증키가 올바르지 않습니다. 금고(Secrets)의 KOBIS_KEY를 확인해 주세요.")
    st.stop()
elif status != "SUCCESS" or not box_list:
    st.warning("박스오피스 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.")
    st.stop()

df = pd.DataFrame(box_list)

# 글자로 온 숫자들을 진짜 숫자로 바꾸기 (매출액 포함)
numeric_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "salesAmt", "salesAcc"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col])

# 1위 영화 추출
top = df.sort_values("rank").iloc[0]

# --- 🥇 어제 1위 영화 기본 지표 카드 ---
st.subheader(f"🥇 어제 1위: {top['movieNm']}")
c1, c2, c3 = st.columns(3)
c1.metric("어제 관객수", f"{top['audiCnt']:,}명")
c2.metric("어제 매출액", f"{top['salesAmt']:,}원")
c3.metric("누적 관객수", f"{top['audiAcc']:,}명")

st.write("")

# --- 🍗 [위트 & 팩트] 흥행 수입 실감 변환기 ---
st.subheader("🍗 흥행 수입 실감 변환기 (1위 영화 기준)")
st.caption("1위 영화의 어제 하루 매출액과 누적 매출액을 실생활 가치로 환산해 보았습니다!")

sales_amt = top["salesAmt"]  # 어제 하루 매출액
sales_acc = top["salesAcc"]  # 누적 매출액

# 금액 환산 공식 (치킨 2만원, 커피 4.5천원, 서울 아파트 12억원 기준)
chicken_amt = int(sales_amt // 20000)
coffee_amt = int(sales_amt // 4500)
chicken_acc = int(sales_acc // 20000)
apt_acc = sales_acc / 1_200_000_000

m1, m2, m3, m4 = st.columns(4)
m1.metric("어제 매출 = 🍗 치킨", f"{chicken_amt:,}마리", help="치킨 1마리 20,000원 기준")
m2.metric("어제 매출 = ☕ 아메리카노", f"{coffee_amt:,}잔", help="아메리카노 1잔 4,500원 기준")
m3.metric("누적 매출 = 🍗 치킨", f"{chicken_acc:,}마리", help="누적 매출액 기준 치킨 마리 수")
m4.metric("누적 매출 = 🏢 서울 아파트", f"{apt_acc:.1f}채", help="서울 아파트 평균 12억 원 기준")

st.markdown("---")

# --- 📋 TOP 10 표 & 📈 상위 5편 그래프 ---
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("📋 박스오피스 TOP 10")
    table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
    table.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
    table = table.sort_values("순위").reset_index(drop=True)
    st.dataframe(table, use_container_width=True)

with col_right:
    st.subheader("📈 관객수 상위 5편")
    top5 = table.sort_values("관객수", ascending=False).head(5)
    st.bar_chart(top5.set_index("영화명")["관객수"])

st.markdown("---")

# --- 🕰️ [감성 추억 여행] 박스오피스 타임머신 ---
st.subheader("🕰️ 박스오피스 타임머신 (N년 전 오늘은?)")
st.caption(f"과거의 오늘({yesterday.strftime('%m월 %d일')}) 박스오피스 1위는 어떤 영화였을까요?")


# 과거 날짜 계산 함수 (윤년 2월 29일 예외 처리 포함)
def get_past_date_str(base_dt, years_ago):
    try:
        past_dt = base_dt.replace(year=base_dt.year - years_ago)
    except ValueError:
        past_dt = base_dt.replace(year=base_dt.year - years_ago, day=28)
    return past_dt, past_dt.strftime("%Y%m%d")


years_list = [1, 3, 5, 10]
time_cols = st.columns(len(years_list))

for idx, years_ago in enumerate(years_list):
    past_dt_obj, past_dt_str = get_past_date_str(yesterday, years_ago)
    p_status, p_box_list = fetch_boxoffice_data(KOBIS_KEY, past_dt_str)

    with time_cols[idx]:
        st.markdown(f"#### 📅 {years_ago}년 전 ({past_dt_obj.year}년)")
        if p_status == "SUCCESS" and p_box_list:
            past_top = p_box_list[0]
            past_audi = int(past_top["audiCnt"])
            past_acc = int(past_top["audiAcc"])

            st.info(f"**🎬 {past_top['movieNm']}**")
            st.caption(f"🍿 당일 관객: **{past_audi:,}명**")
            st.caption(f"👥 누적 관객: **{past_acc:,}명**")
            st.caption(f"🗓️ 개봉일: {past_top.get('openDt', '정보없음')}")
        else:
            st.warning("데이터가 없습니다.")
