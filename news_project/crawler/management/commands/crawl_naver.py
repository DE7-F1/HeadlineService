# crawl_naver.py
from django.core.management.base import BaseCommand
from crawler.crawler_naver import crawl_naver_ranking  

class Command(BaseCommand):
    help = "네이버 인기 뉴스 크롤링"

    def handle(self, *args, **kwargs):
        self.stdout.write("네이버 뉴스 크롤링 시작...")
        articles = crawl_naver_ranking(days=7, top_n=20)
        self.stdout.write(f"크롤링 완료: {len(articles)}개 기사 수집")
