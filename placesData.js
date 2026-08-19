// 서울 핵심 데이트 맛집 & 카페 도감 (상호명 정제 및 별점 탑재 버전)
const CURATED_PLACES = [
  // ================= 1. 강남 / 서초 / 송파 / 강동권 =================
  { id: "gn_1", type: "food", cat: "분식", name: "도산분식", cuisine: "분식 > 돈까스샌드/육회김밥", addr: "강남구 도산대로49길 10-6", rating: "4.7", reviews: "줄서서 먹는 분식 맛집", lat: 37.5241, lon: 127.0371 },
  { id: "gn_2", type: "food", cat: "일식", name: "형훈라멘", cuisine: "일식 > 대창덮밥/아부라소바", addr: "강남구 압구정로14길 39", rating: "4.8", reviews: "고소한 대창덮밥 명가", lat: 37.5218, lon: 127.0215 },
  { id: "gn_3", type: "food", cat: "양식", name: "쵸이닷 강남", cuisine: "양식 > 파인다이닝", addr: "강남구 도산대로 457", rating: "4.9", reviews: "기념일 데이트 최적", lat: 37.5245, lon: 127.0468 },
  { id: "gn_4", type: "food", cat: "고기", name: "영동교집", cuisine: "고기 > 제주 흑돼지 냉동삼겹살", addr: "강남구 압구정로2길 46", rating: "4.7", reviews: "두툼한 냉삼과 볶음밥 예술", lat: 37.5188, lon: 127.0195 },
  { id: "gn_5", type: "food", cat: "양식", name: "클랩피자", cuisine: "양식 > 콘치즈/트러플 피자", addr: "강남구 압구정로46길 71", rating: "4.6", reviews: "도우가 쫄깃하고 토핑 가득", lat: 37.5262, lon: 127.0358 },
  { id: "gn_6", type: "food", cat: "한식", name: "영천영화", cuisine: "한식 > 한우 육회비빔밥/갈비살", addr: "강남구 도산대로90길 3", rating: "4.8", reviews: "입에서 녹는 육회비빔밥", lat: 37.5248, lon: 127.0498 },
  { id: "gn_7", type: "food", cat: "일식", name: "대성식당", cuisine: "일식 > 츠케멘/자가제면", addr: "강남구 언주로168길 33", rating: "4.7", reviews: "진한 소스의 츠케멘", lat: 37.5252, lon: 127.0342 },
  { id: "gn_8", type: "food", cat: "양식", name: "보보식당", cuisine: "퓨전중식 > 버터탕수육/마파두부", addr: "강남구 언주로174길 30", rating: "4.9", reviews: "이색적이고 고급진 중식", lat: 37.5272, lon: 127.0345 },
  { id: "gn_9", type: "food", cat: "한식", name: "마녀주방", cuisine: "테마식당 > 이색 파스타/리조또", addr: "강남구 강남대로94길 9", rating: "4.5", reviews: "이색적인 분위기 데이트", lat: 37.4985, lon: 127.0275 },
  { id: "gn_10", type: "food", cat: "양식", name: "낙원타코", cuisine: "멕시칸 > 파히타/퀘사디아", addr: "강남구 강남대로94길 24", rating: "4.6", reviews: "푸짐한 파히타 세트", lat: 37.4982, lon: 127.0285 },
  { id: "gn_11", type: "food", cat: "고기", name: "진대감 강남점", cuisine: "고기 > 한우 차돌삼합", addr: "강남구 봉은사로1인길 36", rating: "4.7", reviews: "환상적인 차돌삼합 조합", lat: 37.5052, lon: 127.0285 },
  { id: "gn_12", type: "food", cat: "일식", name: "스오모", cuisine: "일식 > 가성비 오마카세", addr: "강남구 선릉로86길 31", rating: "4.8", reviews: "가격 대비 훌륭한 구성", lat: 37.5042, lon: 127.0512 },
  { id: "gn_13", type: "food", cat: "양식", name: "팀호완 코엑스점", cuisine: "딤섬 > 홍콩식 딤섬/하가우", addr: "강남구 봉은사로 86길 30", rating: "4.6", reviews: "육즙 가득 촉촉한 딤섬", lat: 37.5125, lon: 127.0605 },
  { id: "gn_14", type: "food", cat: "한식", name: "중앙해장", cuisine: "한식 > 곱창전골/해장국", addr: "강남구 영동대로85길 38", rating: "4.9", reviews: "인생 곱창전골 맛집", lat: 37.5085, lon: 127.0618 },

  { id: "gn_c1", type: "cafe", name: "새들러하우스", cuisine: "디저트 > 원조 와플크로플", addr: "강남구 도산대로17길 10", rating: "4.7", reviews: "겉바속촉 크로플의 성지", lat: 37.5195, lon: 127.0211, desserts: ["🧇 프렌치 크로플", "🧀 콘치즈 크로플"] },
  { id: "gn_c2", type: "cafe", name: "누데이크 도산", cuisine: "아티스틱 > 말차 피크케이크", addr: "강남구 압구정로46길 50", rating: "4.6", reviews: "비주얼 폭발 예술 디저트", lat: 37.5255, lon: 127.0365, desserts: ["🌋 피크 말차케이크", "🥐 미니 크루아상"] },
  { id: "gn_c3", type: "cafe", name: "카멜커피 도산점", cuisine: "감성빈티지 > 크림라떼", addr: "강남구 도산대로45길 16-8", rating: "4.7", reviews: "고소하고 달콤한 크림라떼", lat: 37.5238, lon: 127.0355, desserts: ["☕ 카멜커피", "🥐 앙버터 브레드"] },
  { id: "gn_c4", type: "cafe", name: "버터풀앤크리멀러스", cuisine: "프렌치베이커리 > 크러핀", addr: "강남구 언주로172길 59", rating: "4.6", reviews: "고급스러운 버터 향 가득", lat: 37.5268, lon: 127.0385, desserts: ["🥐 크리미 크루아상", "🍰 바스크 치즈"] },
  { id: "gn_c5", type: "cafe", name: "미뉴트빠삐용", cuisine: "츄러스 > 유럽 감성 딥초코", addr: "강남구 도산대로51길 37", rating: "4.8", reviews: "바삭한 인생 츄러스", lat: 37.5249, lon: 127.0378, desserts: ["🥖 딥초코 츄러스", "☕ 에스프레소"] },
  { id: "gn_c6", type: "cafe", name: "알베르", cuisine: "대형카페 > 테라스/주택개조", addr: "강남구 강남대로102길 34", rating: "4.5", reviews: "도심 속 넓고 편안한 공간", lat: 37.5008, lon: 127.0281, desserts: ["🍰 티라미수", "☕ 아메리카노"] },

  { id: "sc_1", type: "food", cat: "고기", name: "꿉당", cuisine: "고기 > 목살 숯불구이/코쿠미쌀밥", addr: "서초구 강남대로 615", rating: "4.9", reviews: "목살의 신세계, 육즙 폭발", lat: 37.5165, lon: 127.0198 },
  { id: "sc_2", type: "food", cat: "한식", name: "진미평양냉면", cuisine: "한식 > 미쉐린 평양냉면", addr: "서초구 선암로 10", rating: "4.8", reviews: "깔끔하고 깊은 육수 평냉", lat: 37.5115, lon: 127.0212 },
  { id: "sc_3", type: "food", cat: "중식", name: "방배동 주", cuisine: "중식 > 탕수육/어향동고 명가", addr: "서초구 동광로 113", rating: "4.7", reviews: "바삭함이 남다른 탕수육", lat: 37.4892, lon: 126.9925 },
  { id: "sc_4", type: "food", cat: "양식", name: "볼트스테이크하우스", cuisine: "양식 > 포터하우스 스테이크", addr: "서초구 동광로24길 34", rating: "4.8", reviews: "풍미 깊은 정통 스테이크", lat: 37.4925, lon: 126.9982 },

  { id: "sp_1", type: "food", cat: "한식", name: "방이옥", cuisine: "한식 > 수비드 우대갈비/김치찜", addr: "송파구 올림픽로32길 22-13", rating: "4.8", reviews: "입에서 살살 녹는 우대갈비", lat: 37.5142, lon: 127.1082 },
  { id: "sp_2", type: "food", cat: "일식", name: "멘야하나비", cuisine: "일식 > 원조 나고야 마제소바", addr: "송파구 백제고분로45길 38", rating: "4.7", reviews: "꾸덕하고 감칠맛 넘치는 마제소바", lat: 37.5112, lon: 127.1115 },
  { id: "sp_3", type: "food", cat: "양식", name: "엘리스리틀이태리", cuisine: "양식 > 참나무 화덕피자/뇨끼", addr: "송파구 백제고분로45길 21-1", rating: "4.8", reviews: "쫀득한 화덕피자와 뇨끼", lat: 37.5108, lon: 127.1102 },
  { id: "sp_4", type: "food", cat: "고기", name: "고도식", cuisine: "고기 > 지리산 알등심/삼겹살", addr: "송파구 백제고분로45길 28", rating: "4.8", reviews: "특별한 육즙의 알등심", lat: 37.5115, lon: 127.1108 },
  { id: "sp_c1", type: "cafe", name: "진저베어 파이샵", cuisine: "파이전문 > 미트파이 성지", addr: "송파구 백제고분로41길 43-7", rating: "4.8", reviews: "고소하고 든든한 미트파이", lat: 37.5088, lon: 127.1072, desserts: ["🥧 클래식 미트파이", "🥧 피스타치오 파이"] },
  { id: "sp_c2", type: "cafe", name: "피스피스", cuisine: "호수뷰 > 펌킨파이", addr: "송파구 석촌호수로 258", rating: "4.7", reviews: "꾸덕달달한 단호박 파이", lat: 37.5122, lon: 127.1042, desserts: ["🥧 펌킨파이", "☕ 솔티 크림라떼"] },

  // ================= 2. 마포 / 연남 / 홍대 / 합정권 =================
  { id: "hd_1", type: "food", cat: "일식", name: "온정", cuisine: "일식 > 프리미엄 카이센동", addr: "마포구 동교로38길 33", rating: "4.8", reviews: "신선한 해산물이 가득한 덮밥", lat: 37.5615, lon: 126.9248 },
  { id: "hd_2", type: "food", cat: "중식", name: "하하", cuisine: "중식 > 겉바속촉 가지튀김", addr: "마포구 동교로 263", rating: "4.7", reviews: "인생 가지튀김을 만나는 곳", lat: 37.5621, lon: 126.9241 },
  { id: "hd_3", type: "food", cat: "양식", name: "오스테리아 오라", cuisine: "양식 > 단호박뇨끼/화덕피자", addr: "마포구 망원로 107", rating: "4.8", reviews: "부드러운 단호박 뇨끼", lat: 37.5562, lon: 126.9065 },
  { id: "hd_4", type: "food", cat: "일식", name: "오레노라멘 합정본점", cuisine: "일식 > 미쉐린 토리파이탄 라멘", addr: "마포구 독막로9길 14", rating: "4.9", reviews: "진하고 크리미한 닭 육수 라멘", lat: 37.5485, lon: 126.9182 },
  { id: "hd_5", type: "food", cat: "한식", name: "바다회사랑 1호점", cuisine: "한식 > 대방어/연어회 성지", addr: "마포구 동교로27길 60", rating: "4.8", reviews: "두툼하고 고소한 방어회", lat: 37.5582, lon: 126.9215 },
  { id: "hd_6", type: "food", cat: "일식", name: "헤키", cuisine: "일식 > 히레카츠/특로스카츠", addr: "마포구 포은로 100", rating: "4.8", reviews: "육즙이 가득한 부드러운 돈카츠", lat: 37.5548, lon: 126.9048 },
  { id: "hd_7", type: "food", cat: "고기", name: "육지", cuisine: "고기 > 돈대갈비/이불갈비", addr: "마포구 독막로3길 34", rating: "4.8", reviews: "독특한 식감의 돈대갈비", lat: 37.5492, lon: 126.9168 },
  { id: "hd_c1", type: "cafe", name: "테일러커피 서교본점", cuisine: "스페셜티 > 크림모카 원조", addr: "마포구 와우산로33길 46", rating: "4.8", reviews: "달콤 쌉싸름한 크림모카", lat: 37.5552, lon: 126.9298, desserts: ["☕ 크림모카", "🥧 더치타르트"] },
  { id: "hd_c2", type: "cafe", name: "레이어드", cuisine: "디저트 > 수제 스콘 성지", addr: "마포구 성미산로 161-4", rating: "4.7", reviews: "종류별로 담고 싶은 스콘", lat: 37.5638, lon: 126.9249, desserts: ["🧁 바질 스콘", "🍓 빅토리아 케이크"] },
  { id: "hd_c3", type: "cafe", name: "코코로카라", cuisine: "디저트 > 푸딩/티케이크 전문", addr: "마포구 월드컵북로8길 17", rating: "4.8", reviews: "꾸덕하고 부드러운 바나나푸딩", lat: 37.5592, lon: 126.9198, desserts: ["🍮 바나나 오레오 푸딩", "🍪 미소 쿠키"] },

  // ================= 3. 종로 / 안국 / 서촌 / 익선권 =================
  { id: "jn_1", type: "food", cat: "한식", name: "익선애뜻", cuisine: "퓨전한식 > 차돌박이 쌈밥/칼비빔면", addr: "종로구 돈화문로11다길 24", rating: "4.7", reviews: "정갈하고 깔끔한 퓨전 한식", lat: 37.5742, lon: 126.9899 },
  { id: "jn_2", type: "food", cat: "한식", name: "토속촌 삼계탕", cuisine: "한식 > 전통 삼계탕/해물파전", addr: "종로구 자하문로5길 5", rating: "4.6", reviews: "진하고 보양되는 전통 삼계탕", lat: 37.5775, lon: 126.9719 },
  { id: "jn_3", type: "food", cat: "일식", name: "솟구쳐차기", cuisine: "일식 > 진한 돈코츠라멘", addr: "종로구 율곡로3길 74", rating: "4.7", reviews: "국물이 진한 일본식 라멘", lat: 37.5788, lon: 126.9835 },
  { id: "jn_4", type: "food", cat: "양식", name: "살라댕방콕", cuisine: "태국요리 > 팟타이/푸팟퐁커리", addr: "종로구 돈화문로11다길 40", rating: "4.7", reviews: "휴양지 분위기 가득한 타이 요리", lat: 37.5739, lon: 126.9895 },
  { id: "jn_5", type: "food", cat: "한식", name: "삼청동수제비", cuisine: "한식 > 미쉐린 옹기 수제비/감자전", addr: "종로구 삼청로 101-1", rating: "4.6", reviews: "쫄깃한 수제비와 바삭한 감자전", lat: 37.5852, lon: 126.9818 },
  { id: "jn_c1", type: "cafe", name: "런던 베이글 뮤지엄 안국", cuisine: "베이글 > 줄서는 핫플", addr: "종로구 북촌로4길 20", rating: "4.8", reviews: "쫄깃한 베이글과 크림치즈 조화", lat: 37.5791, lon: 126.9862, desserts: ["🥯 대파 크림치즈 베이글", "🥔 감자치즈 베이글"] },
  { id: "jn_c2", type: "cafe", name: "아베베 베이커리", cuisine: "도넛/크림빵 > 제주 핫플", addr: "종로구 청계천로 201", rating: "4.7", reviews: "크림이 가득 찬 뚱도넛", lat: 37.5701, lon: 126.9995, desserts: ["🍩 우도 땅콩 도넛", "🥐 찰떡도넛"] },
  { id: "jn_c3", type: "cafe", name: "청수당", cuisine: "한옥정원 > 수플레 명소", addr: "종로구 돈화문로11나길 31-9", rating: "4.7", reviews: "도심 속 한옥에서 즐기는 수플레", lat: 37.5748, lon: 126.9902, desserts: ["🥞 에그 수플레", "🍵 말차 프로마쥬"] },

  // ================= 4. 용산 / 한남 / 이태원 / 삼각지권 =================
  { id: "ys_1", type: "food", cat: "고기", name: "몽탄", cuisine: "고기 > 짚불 우대갈비", addr: "용산구 백범로99길 50", rating: "4.9", reviews: "짚불 향이 가득 밴 감격의 우대갈비", lat: 37.5348, lon: 126.9729 },
  { id: "ys_2", type: "food", cat: "양식", name: "쌤쌤쌤", cuisine: "양식 > 샌프란시스코 가정식/라자냐", addr: "용산구 한강대로50길 25", rating: "4.8", reviews: "미국 감성 넘치는 라자냐 맛집", lat: 37.5312, lon: 126.9712 },
  { id: "ys_3", type: "food", cat: "양식", name: "오스테리아 오르조", cuisine: "양식 > 미쉐린 생면 우니파스타", addr: "용산구 이태원로54길 58", rating: "4.9", reviews: "고급스러운 화이트 라구 파스타", lat: 37.5365, lon: 127.0012 },
  { id: "ys_4", type: "food", cat: "고기", name: "남영돈", cuisine: "고기 > 숯불 항정살/가브리살 성지", addr: "용산구 한강대로84길 5-7", rating: "4.9", reviews: "육즙이 팡팡 터지는 항정살", lat: 37.5418, lon: 126.9728 },
  { id: "ys_c1", type: "cafe", name: "테디뵈르하우스", cuisine: "베이커리 > 크루아상 전문", addr: "용산구 한강대로40가길 42", rating: "4.7", reviews: "고소한 버터 향 가득한 크루아상", lat: 37.5305, lon: 126.9715, desserts: ["🥐 피스타치오 퀸아망", "🥐 콘에그 크루아상"] },
  { id: "ys_c2", type: "cafe", name: "마일스톤 커피", cuisine: "스페셜티 > 플랫화이트 성지", addr: "용산구 한남대로27가길 26", rating: "4.8", reviews: "인생 플랫화이트와 티라미수", lat: 37.5358, lon: 127.0028, desserts: ["🍰 수제 티라미수", "☕ 플랫화이트"] },

  // ================= 5. 성수 / 서울숲권 =================
  { id: "ss_1", type: "food", cat: "한식", name: "성수 난포", cuisine: "퓨전한식 > 강된장쌈밥/제철회국수", addr: "성동구 서울숲4길 18-8", rating: "4.8", reviews: "눈과 입이 즐거운 예쁜 한식", lat: 37.5471, lon: 127.0426 },
  { id: "ss_2", type: "food", cat: "양식", name: "중앙감속기", cuisine: "퓨전양식 > 바질크림짬뽕/어향가지", addr: "성동구 성원정길 16", rating: "4.7", reviews: "이색적이고 매력적인 퓨전 요리", lat: 37.5422, lon: 127.0545 },
  { id: "ss_3", type: "food", cat: "고기", name: "뚝도농원", cuisine: "고기 > 숯불 오리구이/특수부위", addr: "성동구 아차산로 82", rating: "4.8", reviews: "특별한 날 방문하기 좋은 오리구이", lat: 37.5431, lon: 127.0541 },
  { id: "ss_4", type: "food", cat: "일식", name: "소바식당", cuisine: "일식 > 전복단새우냉소바", addr: "성동구 연무장7가길 6", rating: "4.7", reviews: "시원하고 깔끔한 냉소바", lat: 37.5439, lon: 127.0558 },
  { id: "ss_c1", type: "cafe", name: "어니언 성수", cuisine: "베이커리 > 빈티지 인더스트리얼", addr: "성동구 아차산로9길 8", rating: "4.7", reviews: "공장 개조 감성과 맛있는 빵", lat: 37.5445, lon: 127.0578, desserts: ["🏔️ 슈가 팡도르", "🥐 앙버터 소금빵"] },
  { id: "ss_c2", type: "cafe", name: "대림창고", cuisine: "대형카페 > 붉은벽돌 갤러리", addr: "성동구 성수이로 78", rating: "4.6", reviews: "멋진 예술 작품과 커피가 함께", lat: 37.5412, lon: 127.0556, desserts: ["🍓 생딸기 타르트", "☕ 시그니처라떼"] },
  { id: "ss_c3", type: "cafe", name: "카멜커피", cuisine: "빈티지 > 크림 시그니처", addr: "성동구 서울숲2길 16-8", rating: "4.7", reviews: "중독성 있는 시그니처 커피", lat: 37.5468, lon: 127.0435, desserts: ["☕ 카멜커피", "🥐 티가렛 소금빵"] }
];
