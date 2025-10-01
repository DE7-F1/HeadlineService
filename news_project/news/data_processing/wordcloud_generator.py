from datetime import date
from collections import Counter
import json
from konlpy.tag import Okt # 한국어 형태소 분석기 (설치 필요)
from django.db.models import Q, Min, Max

from ..models import News, Publisher, WordCloudResult

STOPWORDS = set([
    '뉴스', '기자', '오늘', '이슈', '속보', '있다', '것이다', '하다', '등', '이번', '그것', '지난', '합니다', '한다'
])

def generate_word_frequencies(start_date: date=None, end_date: date=None, selected_publisher_ids: list=None):
    """
    지정된 기간, 신문사 ID, 그리고 조회수(view_count)를 가중치로 사용하여
    단어 빈도수를 계산하고 WordCloudResult에 JSON 형태로 저장합니다.
    """
    okt = Okt()
    
    filters= Q()
    if selected_publisher_ids:
        filters &= Q(publisher_id__in=selected_publisher_ids)
        
    if start_date and end_date:# start_date와 end_date가 모두 제공된 경우에만 필터링
        filters &= Q(published_date__range=(start_date, end_date))
    
    # 1. 데이터 필터링 및 조회: title과 view_count를 함께 가져와야 가중치 적용이 가능합니다.
    # view_count가 없는 경우를 대비해 기본값 0을 적용합니다.
    headlines = News.objects.filter(filters).values('title', 'view_count', 'published_date') # 딕셔너리 형태로 조회

    if not headlines:
        print(">> 조회된 헤드라인이 없습니다. WordCloud 생성을 건너뜁니다.")
        return None

    # 빈도수를 저장할 Counter 객체 초기화
    word_counts = Counter()
    
    # 2. 텍스트 전처리, 명사 추출, 가중치 적용 (핵심 T 로직)
    for headline in headlines:
        title = headline['title']
        # 조회수(view_count)를 가중치로 사용. 값이 None이면 1로 처리하여 기본 가중치 적용.
        view_weight = headline['view_count'] if headline['view_count'] is not None and headline['view_count'] > 0 else 1
        
        # 형태소 분석을 통해 명사만 추출
        nouns = okt.nouns(title) 
        
        # 1글자 단어 및 불용어 제거
        filtered_nouns = [
            noun for noun in nouns 
            if len(noun) > 1 and noun not in STOPWORDS
        ]
        
        # 빈도수에 가중치 적용
        for noun in filtered_nouns:
            # 단어의 빈도수에 view_weight만큼 더하여 가중치 적용
            word_counts[noun] += view_weight

    # 3. 워드클라우드에 사용할 상위 100개 단어만 추출
    top_words = word_counts.most_common(100)
    
    # 4. JSON 포맷으로 변환 (프론트엔드 시각화용)
    # [{'text': '단어', 'value': 빈도수}, ...] 형태로 변환
    frequency_data = [
        {'text': word, 'value': count} 
        for word, count in top_words
    ]
    final_start_date = start_date
    final_end_date = end_date
    if not start_date or not end_date:
        
        date_range=headlines.aggregate(min_date=Min('published_date'), max_date=Max('published_date'))
        final_start_date=date_range['min_date']
        final_end_date=date_range['max_date']
    
    publishers_to_log=selected_publisher_ids
    if not selected_publisher_ids:
        publishers_to_log=Publisher.objects.all().values_list('id', flat=True)
    # 5. WordCloudResult 테이블에 결과 저장
    result_obj = WordCloudResult.objects.create(
        start_date=final_start_date,
        end_date=final_end_date,
        word_frequency_json=json.dumps(frequency_data)
    )
    
    # Many-to-Many 관계 설정 (어떤 신문사가 사용되었는지 기록)
    # Note: WordCloudResult 모델에 included_publishers 필드가 ManyToManyField로 정의되어 있어야 합니다.
    result_obj.included_publishers.set(publishers_to_log)
    
    print(f">> WordCloud 가중치 결과 저장 완료. ID: {result_obj.id}. 기간: {final_start_date} ~ {final_end_date}")
    return result_obj.id

# 사용 예시 (특정 신문사 1, 2, 3으로 2025-09-01부터 2025-09-30까지 실행)
# generate_word_frequencies(date(2025, 9, 1), date(2025, 9, 30), [1, 2, 3])