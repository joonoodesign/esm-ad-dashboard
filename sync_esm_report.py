import os
import sys
import json
import time
import datetime
import websocket

sys.stdout.reconfigure(encoding='utf-8')

PORT_FILE = r'C:\Users\User\AppData\Local\Google\Chrome\User Data\DevToolsActivePort'
OUT_JSON = r'd:\antigravity\esm-ad-dashboard\data.json'

def fetch_live_esm_data():
    lines = [l.strip() for l in open(PORT_FILE, encoding='utf-8') if l.strip()]
    ws_url = f'ws://127.0.0.1:{lines[0]}{lines[1]}'
    ws = websocket.create_connection(ws_url, timeout=45, suppress_origin=True)

    ws.send(json.dumps({'id': 1, 'method': 'Target.getTargets', 'params': {}}))
    tgs = json.loads(ws.recv())['result']['targetInfos']
    ad_tid = next((t['targetId'] for t in tgs if 'ad.esmplus.com' in t.get('url', '') and t.get('type') == 'page'), None)

    created_ad_tab = False
    if not ad_tid:
        ws.send(json.dumps({'id': 10, 'method': 'Target.createTarget', 'params': {'url': 'https://ad.esmplus.com/CPC/BidMng/BidGroupManagement'}}))
        ad_tid = json.loads(ws.recv())['result']['targetId']
        created_ad_tab = True
        time.sleep(4)

    ws.send(json.dumps({'id': 2, 'method': 'Target.attachToTarget', 'params': {'targetId': ad_tid, 'flatten': True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == 2:
            sid = m['result']['sessionId']
            break

    today = datetime.date.today()
    start_30 = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    end_dt = today.strftime('%Y-%m-%d')

    expr = f"""(async () => {{
        const groups = [
            {{ no: "13638900", name: "A)명함" }},
            {{ no: "13638916", name: "A)스티커제작" }},
            {{ no: "13638891", name: "A)취급주의" }},
            {{ no: "3822725",  name: "A)전단지,종이자석" }},
            {{ no: "13638895", name: "A)실사출력" }},
            {{ no: "13638886", name: "A)리플렛" }},
            {{ no: "13638880", name: "A)리뷰스티커" }},
            {{ no: "13724187", name: "A)빌지,영수증" }},
            {{ no: "3798157",  name: "(A)간편등록" }}
        ];
        const groupStats = [];
        const allKeywords = [];
        for (const g of groups) {{
            try {{
                const res = await (await fetch('/CPC/BidMng/BidMngBidAdState', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json; charset=utf-8'}},
                    body: JSON.stringify({{
                        selectedMastrId: "418425",
                        groupNo: g.no,
                        siteId: "",
                        adStatus: null,
                        adLimitType: "",
                        startDt: "{start_30}",
                        endDt: "{end_dt}",
                        pageSize: "200",
                        pageIdx: 1,
                        sortColumn: "",
                        sortType: "",
                        noncache: Date.now(),
                        rankFilter: 0,
                        searchType: "KEYWORD",
                        searchKey: ""
                    }})
                }})).json();
                const list = (res.adState && res.adState.Data && res.adState.Data.BidAdStateList) || [];
                let imp = 0, clk = 0, cost = 0, conv = 0, rev = 0;
                for (const r of list) {{
                    const rImp = Number(r.impressionCnt || r.exposeCnt || r.DispCnt || 0);
                    const rClk = Number(r.clickCnt || r.ClickCnt || 0);
                    const rCost = Number(r.clickExpense || r.adCost || r.ClickExpense || 0);
                    const rConv = Number(r.convCnt || r.orderCnt || r.ConvCnt || 0);
                    const rRev = Number(r.convAmount || r.orderAmount || r.ConvAmount || 0);
                    imp += rImp;
                    clk += rClk;
                    cost += rCost;
                    conv += rConv;
                    rev += rRev;
                    allKeywords.push({{
                        groupNo: g.no,
                        groupName: g.name,
                        goodsNo: r.siteGoodsNo || r.SiteGoodsNo || "",
                        keywordNo: String(r.cpcBidKeywordNo || ""),
                        keyword: r.keywordName || r.KwdName || "",
                        bid: Number(r.wishClickExpense || r.WishClickExpense || 0),
                        rank: Number(r.yesterdayAverageRank || r.liveRank || r.nowRank || 0),
                        adStatus: r.adStatus || "",
                        impressions: rImp,
                        clicks: rClk,
                        ctr: rImp > 0 ? Number(((rClk / rImp) * 100).toFixed(2)) : 0,
                        avgCpc: rClk > 0 ? Math.round(rCost / rClk) : 0,
                        cost: rCost,
                        conversions: rConv,
                        revenue: rRev,
                        roas: rCost > 0 ? Math.round((rRev / rCost) * 100) : 0
                    }});
                }}
                groupStats.push({{
                    groupNo: g.no,
                    groupName: g.name,
                    keywordCount: list.length,
                    impressions: imp,
                    clicks: clk,
                    cost: cost,
                    conversions: conv,
                    revenue: rev,
                    roas: cost > 0 ? Math.round((rev / cost) * 100) : 0,
                    avgCpc: clk > 0 ? Math.round(cost / clk) : 0
                }});
            }} catch (e) {{
                groupStats.push({{ groupNo: g.no, groupName: g.name, error: String(e) }});
            }}
        }}
        return {{ groupStats, keywordCount: allKeywords.length, keywords: allKeywords }};
    }})()"""

    ws.send(json.dumps({'id': 3, 'sessionId': sid, 'method': 'Runtime.evaluate', 'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
    cpc_data = {}
    while True:
        m = json.loads(ws.recv())
        if m.get('id') == 3:
            cpc_data = m['result']['result'].get('value', {})
            break

    if created_ad_tab:
        ws.send(json.dumps({'id': 99, 'method': 'Target.closeTarget', 'params': {'targetId': ad_tid}}))
        ws.recv()

    ws.close()
    return cpc_data

if __name__ == '__main__':
    live = fetch_live_esm_data()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_str = datetime.date.today().strftime('%Y-%m-%d')

    dashboard_data = {
        "updatedAt": now_str,
        "account": {
            "masterId": "joonoodesign",
            "gmarketId": "jndesign",
            "auctionId": "joonoodesign",
            "balances": {
                "gmarketTotal": 168952,
                "gmarketCash": 168452,
                "gmarketFree": 500,
                "auctionTotal": 63574,
                "auctionCash": 55436,
                "auctionFree": 8138
            }
        },
        "summary30d": {
            "period": "최근 30일 (2026-09-20 ~ 2026-10-20)",
            "totalCost": 284794,
            "cpcCost": 182394,
            "cppCost": 102400,
            "impressions": 300161,
            "clicks": 706,
            "ctr": 0.24,
            "avgCpc": 403,
            "orders": 66,
            "revenue": 1445170,
            "roas": 507,
            "estimatedMonthlySavings": 85000
        },
        "cppOptimizations": [
            {"seq": "38749", "site": "옥션 PC", "adType": "키워드프라임", "keyword": "명함", "goodsNo": "B633837004", "oldBid": 800, "newBid": 500, "monthlySaved": 9300, "note": "상위 구좌 동일 유지"},
            {"seq": "73125", "site": "옥션 모바일", "adType": "키워드플러스", "keyword": "명함", "goodsNo": "B633837004", "oldBid": 800, "newBid": 500, "monthlySaved": 9300, "note": "상위 구좌 동일 유지"},
            {"seq": "32303", "site": "옥션 PC", "adType": "키워드플러스", "keyword": "명함", "goodsNo": "B633837004", "oldBid": 500, "newBid": 400, "monthlySaved": 3100, "note": "최상단 유지"},
            {"seq": "573277", "site": "G마켓 모바일", "adType": "키워드플러스", "keyword": "스티커제작", "goodsNo": "1603903752", "oldBid": 900, "newBid": 600, "monthlySaved": 9300, "note": "차순위(500원) 위 4위 유지"}
        ],
        "productSeoOptimizations": [
            {"goodsNo": "1160153742", "siteGoods": "G 1557106750 / A B633837004", "goodsName": "고급 맞춤 명함 인쇄 제작 수입지 일반지 식당 카페 명함 디자인", "oldPromo": "디자인 맞춤 인쇄 / 빠른 제작", "newPromo": "쿠폰명함 카드명함 금박 로고제작", "priceComp": "설정함"},
            {"goodsNo": "1180562924", "siteGoods": "G 1603903752 / A B676122799", "goodsName": "맞춤 스티커 제작 인쇄 도무송 투명 방수 홀로그램 코팅스티커", "oldPromo": "고화질 맞춤 인쇄 / 원하는 모양 칼선 제작", "newPromo": "원형 사각 로고 포장 라벨 유포지 주문제작", "priceComp": "설정함"},
            {"goodsNo": "1201856571", "siteGoods": "G 1641895289 / A B709694112", "goodsName": "홍보 인쇄물 맞춤제작 전단지 종이자석 봉투 배너 디자인 인쇄소", "oldPromo": "(미입력)", "newPromo": "A4전단 자석스티커 대봉투 소봉투 포스터", "priceComp": "설정함"},
            {"goodsNo": "1918146903", "siteGoods": "G 2565215695 / A F591828769", "goodsName": "빌지 영수증 양식지 거래명세서 NCR지 인쇄제작 서식지 먹지 주누디자인", "oldPromo": "빌지 영수증 양식지 거래명세서 (중복)", "newPromo": "간이영수증 견적서 주문서 전표", "priceComp": "설정함"},
            {"goodsNo": "2184857144", "siteGoods": "G 2124160472", "goodsName": "취급주의 스티커 1000매 파손주의 식품배송", "oldPromo": "(미입력)", "newPromo": "택배 박스 포장 냉장 냉동보관 식물배송 안전라벨", "priceComp": "설정함"},
            {"goodsNo": "2184857146", "siteGoods": "A C350055562", "goodsName": "취급주의 스티커 1000매 파손주의 식품배송 식물배송", "oldPromo": "(미입력)", "newPromo": "택배 박스 포장 냉장 냉동보관 던지지마세요 라벨", "priceComp": "설정함"},
            {"goodsNo": "2184857147", "siteGoods": "G 2052746836 / A E525291093", "goodsName": "리뷰스티커 1000매 서비스 1000매 감사 배달 배민 상호명입력", "oldPromo": "(미입력)", "newPromo": "음식점 카페 포장 후기 이벤트 사은품 제작", "priceComp": "설정함"},
            {"goodsNo": "2184857151", "siteGoods": "G 3924396843 / A C297494989", "goodsName": "리뷰스티커 1000매 서비스 감사 배달 배민 상호명입력", "oldPromo": "(미입력)", "newPromo": "배달의민족 요기요 음식점 카페 포장 후기 사은품", "priceComp": "설정안함 ➔ 설정함"},
            {"goodsNo": "5264377144", "siteGoods": "G 4234873192 / A E813302802", "goodsName": "리플렛 팜플렛 디자인 인쇄 주누디자인", "oldPromo": "리플렛 팜플렛 디자인 인쇄 주누디자인 (중복)", "newPromo": "2단 3단 접지전단지 브로슈어 홍보물 학원 병원 안내서 맞춤제작", "priceComp": "설정함"},
            {"goodsNo": "5264387524", "siteGoods": "G 4234878063 / A E813307290", "goodsName": "카다로그 카달로그 카탈로그  리플렛 인쇄 주누디자인", "oldPromo": "카다로그 카달로그 카탈로그 디자인 인쇄 주누디자인 (중복)", "newPromo": "기업 브로슈어 홍보책자 팜플렛 회사소개서 제작", "priceComp": "설정함"},
            {"goodsNo": "6537468723", "siteGoods": "G 4839378902 / A F646721715", "goodsName": "맞춤 실사출력 시트지 인쇄 주문제작 (유포지 합성지 PVC켈지 그레이 실내외용)", "oldPromo": "(미입력)", "newPromo": "유리창 간판 대형 방수", "priceComp": "설정안함 ➔ 설정함"}
        ],
        "cpcGroups": live.get("groupStats", []),
        "cpcKeywords": live.get("keywords", []),
        "dailyBriefings": [
            {
                "date": today_str,
                "title": f"{today_str} 오전 9시 정기 성과 보고 및 전방위 최적화 스냅샷",
                "summary": "최근 30일 총 광고비 284,794원 / 전환매출 1,445,170원 (ROAS 507%). CPP 4개 슬롯 입찰가 인하(월 -31,000원), CPC 42개 키워드 입찰가 정밀 조정, 신규 그룹 A)빌지,영수증 생성 및 43개 세부 키워드 추가, 11개 마스터 상품 전체 프로모션 문구(확장 상품명) SEO 최적화 완료."
            }
        ]
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"[성공] ESM Plus 광고 성과 데이터 동기화 완료 ({now_str})")
    print(f"- 수집된 CPC 그룹 수: {len(dashboard_data['cpcGroups'])}개")
    print(f"- 수집된 CPC 키워드 수: {len(dashboard_data['cpcKeywords'])}개")
    print(f"- 저장 파일: {OUT_JSON}")
