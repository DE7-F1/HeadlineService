from django.db import models

# Create your models here.

# models.*field docs
# https://docs.djangoproject.com/en/5.2/ref/models/fields/#django.db.models.TextField

class Publisher(models.Model):
    name = models.CharField(max_length=90, verbose_name='발행처 이름 (예: YTN, 조선일보, KBS News)')

class News(models.Model):
    title = models.CharField(max_length=180, verbose_name='기사/영상 제목')
    publisher_id = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name='news_list')
    url = models.URLField(max_length=300, verbose_name='기사/영상 원본 URL')
    published_date = models.DateTimeField(verbose_name='최초 발행일')
    view_count = models.IntegerField(verbose_name='조회수')
    crawled_at = models.DateTimeField(verbose_name='최종 크롤링 시점')

class WordCloudResult(models.Model):
    # Many-to-Many 관계: Publisher 모델 참조로 변경
    included_publishers = models.ManyToManyField(
        Publisher,
        related_name='wordcloud_results',
        verbose_name="포함된 발행처 목록"
    )
    # 사용된 기간 (날짜가 선택되지 않았을 경우, 실제 데이터의 min/max 날짜가 저장됨)
    start_date = models.DateField(verbose_name="집계 시작일")
    end_date = models.DateField(verbose_name="집계 종료일")
    # 워드클라우드 빈도수 데이터 (JSON 형태)
    word_frequency_json = models.JSONField(verbose_name="빈도수 JSON 데이터")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="결과 생성 시각"
    )
    # 워드클라우드 이미지 경로 (이미지 저장을 안하지만, 필드는 확장성 때문에 남겨둠)
    image_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="이미지 파일 경로"
    )
    def __str__(self):
        return f"WC Result: {self.start_date} ~ {self.end_date}"
    class Meta:
        verbose_name = "워드클라우드 결과"
        verbose_name_plural = "워드클라우드 결과 목록"