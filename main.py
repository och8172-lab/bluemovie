import streamlit as st
import pandas as pd
import requests
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 1. 페이지 기본 설정
st.set_page_config(page_title="박스오피스 대시보드", layout="wide")
st.title("🎬 박스오피스 종합 올인원 대시보드")

# 2. 비밀 금고에서 인증키 꺼내기
KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 3. 한국 시간 기준 어제 날짜 구하기
yesterday = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")
st.caption(f"📅 조회 기준일(어제): {yesterday.strftime('%Y년 %m월 %d일')}")


# 4. KOBIS API 데이터 호출 함수 (캐싱 적용)
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

# 숫자로 변환
numeric_cols = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt", "salesAmt", "salesAcc"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col])

# 어제 1위 영화
top = df.sort_values("rank").iloc[0]

# --- 🥇 어제 1위 영화 기본 지표 카드 ---
st.subheader(f"🥇 어제 1위: {top['movieNm']}")
c1, c2, c3 = st.columns(3)
c1.metric("어제 관객수", f"{top['audiCnt']:,}명")
c2.metric("어제 매출액", f"{top['salesAmt']:,}원")
c3.metric("누적 관객수", f"{top['audiAcc']:,}명")

st.write("")

# --- 🥊 [1] 어제 1위 VS 2위 라이벌 매치 ---
if len(df) >= 2:
    st.subheader("🥊 어제 1위 VS 2위 벼랑끝 맞대결")
    top1 = df.sort_values("rank").iloc[0]
    top2 = df.sort_values("rank").iloc[1]

    diff_audi = top1["audiCnt"] - top2["audiCnt"]
    eff1 = top1["audiCnt"] / top1["scrnCnt"] if top1["scrnCnt"] > 0 else 0
    eff2 = top2["audiCnt"] / top2["scrnCnt"] if top2["scrnCnt"] > 0 else 0

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.info(f"### 🥇 1위: {top1['movieNm']}\n"
                f"- 👥 **관객수**: {top1['audiCnt']:,}명\n"
                f"- 🖥️ **스크린수**: {top1['scrnCnt']:,}개\n"
                f"- ⚡ **스크린 1개당 관객**: **{eff1:.1f}명**")
    with col_v2:
        st.warning(f"### 🥈 2위: {top2['movieNm']}\n"
                   f"- 👥 **관객수**: {top2['audiCnt']:,}명\n"
                   f"- 🖥️ **스크린수**: {top2['scrnCnt']:,}개\n"
                   f"- ⚡ **스크린 1개당 관객**: **{eff2:.1f}명**")

    eff_winner = top1['movieNm'] if eff1 >= eff2 else top2['movieNm']
    st.success(f"💡 **관객수 격차**: 1위가 2위를 **{diff_audi:,}명** 차이로 앞섰습니다!\n\n"
               f"🔥 **스크린 가성비(알짜배기 효율) 승자**: **[{eff_winner}]** (스크린 1개당 더 많은 관객을 끌어모음)")

st.markdown("---")

# --- 🍗 [2] 흥행 수입 실감 변환기 ---
st.subheader("🍗 흥행 수입 실감 변환기 (1위 영화 기준)")
st.caption("1위 영화의 매출액을 일상 생활 물가로 체감해 보세요!")

sales_amt = top["salesAmt"]
sales_acc = top["salesAcc"]

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

# --- 📋 TOP 10 표 & 📈 관객수 상위 5편 ---
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("📋 어제 박스오피스 TOP 10")
    table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
    table.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
    table = table.sort_values("순위").reset_index(drop=True)
    st.dataframe(table, use_container_width=True)

with col_right:
    st.subheader("📈 관객수 상위 5편")
    top5 = table.sort_values("관객수", ascending=False).head(5)
    st.bar_chart(top5.set_index("영화명")["관객수"])

st.markdown("---")

# --- 🎰 [3] 오늘 뭐 보지? TOP 10 영화 랜덤 추천 ---
st.subheader("🎰 오늘 뭐 보지? TOP 10 영화 랜덤 룰렛")
st.caption("무슨 영화를 볼지 결정하기 힘들다면 룰렛을 눌러보세요!")

if st.button("🎲 오늘 볼 영화 랜덤 뽑기!"):
    chosen = random.choice(df.to_dict("records"))
    st.balloons()
    st.success(f"🎉 **오늘의 추천 영화**: **[{chosen['rank']}위] {chosen['movieNm']}**")
    st.write(f"🍿 **정보**: 개봉일 {chosen.get('openDt', '정보없음')} / 누적관객 {chosen['audiAcc']:,}명")
    st.info("💡 **추천 꿀조합**: 고소한 팝콘 L 사이즈 + 시원한 제로 콜라! (화장실은 미리 다녀오세요 🏃‍♂️)")

st.markdown("---")

# --- 🕰️ [4] 박스오피스 타임머신 ---
st.subheader("🕰️ 박스오피스 타임머신 (N년 전 오늘은?)")
st.caption(f"과거의 오늘({yesterday.strftime('%m월 %d일')}) 박스오피스 1위는 어떤 영화였을까요?")


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

st.markdown("---")

# --- 💳 [5] 영화 티켓값 변천사 & 추억의 관람료 계산기 ---
st.subheader("💳 [라떼는 말이야...] 영화 티켓값 변천사 & 관람료 계산기")
st.caption("시대별 영화 티켓 가격 변천사와 인원수별 예상 금액을 확인해 보세요!")

num_people = st.number_input("👥 관람 인원 수를 입력하세요 (명)", min_value=1, max_value=20, value=2, step=1)

prices = {
    "2000년대 (6,000원)": 6000,
    "2010년대 (8,000원)": 8000,
    "2018년 (11,000원)": 11000,
    "현재 기준 (15,000원)": 15000,
}

tc1, tc2, tc3, tc4 = st.columns(4)
cols = [tc1, tc2, tc3, tc4]
for idx, (year_label, price) in enumerate(prices.items()):
    total_cost = price * num_people
    cols[idx].metric(year_label, f"{total_cost:,}원", help=f"1인당 {price:,}원 기준")

st.markdown("---")

# --- 🏛️ [6] 대한민국 역대 영화 흥행 순위 ---
st.subheader("🏛️ 대한민국 영화 역사상 역대 흥행 순위 (KOBIS 공식 집계)")

all_time_data = [
    {"순위": 1, "영화명": "명량", "개봉연도": "2014년", "국가": "한국", "관객수(명)": 17616299, "비고": "역대 전체 1위"},
    {"순위": 2, "영화명": "극한직업", "개봉연도": "2019년", "국가": "한국", "관객수(명)": 16266480, "비고": "역대 코미디 1위"},
    {"순위": 3, "영화명": "신과함께-죄와 벌", "개봉연도": "2017년", "국가": "한국", "관객수(명)": 14414658, "비고": "판타지 1위"},
    {"순위": 4, "영화명": "국제시장", "개봉연도": "2014년", "국가": "한국", "관객수(명)": 14265682, "비고": "드라마 1위"},
    {"순위": 5, "영화명": "아바타", "개봉연도": "2009년", "국가": "미국", "관객수(명)": 14003138, "비고": "외화 전체 1위"},
    {"순위": 6, "영화명": "어벤져스: 엔드게임", "개봉연도": "2019년", "국가": "미국", "관객수(명)": 13977602, "비고": "히어로물 1위"},
    {"순위": 7, "영화명": "겨울왕국 2", "개봉연도": "2019년", "국가": "미국", "관객수(명)": 13768797, "비고": "애니메이션 1위"},
    {"순위": 8, "영화명": "베테랑", "개봉연도": "2015년", "국가": "한국", "관객수(명)": 13414484, "비고": "액션 1위"},
    {"순위": 9, "영화명": "서울의 봄", "개봉연도": "2023년", "국가": "한국", "관객수(명)": 13123641, "비고": "시대극 1위"},
    {"순위": 10, "영화명": "도둑들", "개봉연도": "2012년", "국가": "한국", "관객수(명)": 12983178, "비고": "케이퍼 무비 1위"},
]

df_alltime = pd.DataFrame(all_time_data)

tab1, tab2, tab3 = st.tabs(["🏆 역대 통합 TOP 10", "🇰🇷 역대 한국영화 TOP 10", "🌎 역대 외화 TOP 5"])

with tab1:
    col_t1, col_t2 = st.columns([1.3, 1])
    with col_t1:
        st.dataframe(df_alltime.style.format({"관객수(명)": "{:,}"}), use_container_width=True)
    with col_t2:
        st.bar_chart(df_alltime.set_index("영화명")["관객수(명)"])

with tab2:
    df_korea = df_alltime[df_alltime["국가"] == "한국"].reset_index(drop=True)
    st.dataframe(df_korea.style.format({"관객수(명)": "{:,}"}), use_container_width=True)

with tab3:
    df_foreign = df_alltime[df_alltime["국가"] != "한국"].reset_index(drop=True)
    st.dataframe(df_foreign.style.format({"관객수(명)": "{:,}"}), use_container_width=True)

st.markdown("---")

# --- 🏆 [7] 숫자로 보는 영화판 레전드 기록 TMI ---
st.subheader("🏆 [영화계 기네스북] 숫자로 보는 영화판 레전드 기록 TMI")
g1, g2, g3, g4 = st.columns(4)
g1.metric("⚡ 역대 하루 최다 관객", "1,665,653명", "명량 (2014.08.03)")
g2.metric("🚀 개봉일 최다 관객", "1,340,824명", "어벤져스: 엔드게임 (2019)")
g3.metric("⏱️ 최단기 천만 돌파", "12일 만에 달성", "명량 (2014)")
g4.metric("📽️ 역대 최다 스크린 수", "2,835개", "어벤져스: 엔드게임 (2019)")
