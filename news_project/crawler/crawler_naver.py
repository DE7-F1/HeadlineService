# news/naver_crawler.py
import re
import os
import django
import time
import requests
from datetime import datetime, timedelta
from django.utils import timezone

# Django 프로젝트 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_project.settings')
django.setup()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from news.models import Headline, Publisher

# 제목 전처리 함수
def clean_title(title):
    return re.sub(r"\[[^\]]*\]", "", title).strip()

# Selenium 드라이버 설정
def get_driver():
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    #GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        options.binary_location = "/usr/bin/google-chrome"
        return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)

    #로컬 실행
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    

def post_to_backend(news_obj):
    backend_url = os.environ.get('BACKEND_URL', 'http://127.0.0.1:8000/news/headline/')
    try:
        data = {    
            "title": news_obj.title,
            "publisher": news_obj.publisher_id,
            "url": news_obj.url,
            "published_date": news_obj.published_date.isoformat(),  
            "view_count": news_obj.view_count,
            "crawled_at": news_obj.crawled_at.isoformat()  
        }

        response = requests.post(
            backend_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print(f"POST 성공: {news_obj.title}")
            return True
        else:
            print(f"POST 실패 [{response.status_code}]: {news_obj.title}")
            return False
        
    except Exception as e:
        print(f"POST 에러: {e}")
        return False
    

# 네이버 인기 뉴스 크롤링 (7일 분량)
def crawl_naver_ranking(days=7, top_n=20):
    collected_articles=[]
    driver = get_driver()
    today = datetime.today()

    for delta in range(1, days + 1):
        target_date = today - timedelta(days=delta)
        date_str = target_date.strftime("%Y%m%d")
        url = f"https://news.naver.com/main/ranking/popularDay.naver?date={date_str}"
        print(f"\n크롤링 날짜: {target_date.date()} | URL: {url}")

        driver.get(url)
        time.sleep(2)

        try:
            boxes = driver.find_elements(By.CSS_SELECTOR, ".rankingnews_box")
            for box in boxes:
                try:
                    publisher_name = box.find_element(By.CLASS_NAME, "rankingnews_name").text.strip()
                    publisher, _ = Publisher.objects.get_or_create(name=publisher_name)
                    articles = box.find_elements(By.CSS_SELECTOR, "ul.rankingnews_list li")[:top_n]

                    for article in articles:
                        try:
                            link = article.find_element(By.TAG_NAME, "a")
                            title = clean_title(link.text.strip())
                            href = link.get_attribute("href")

                            # 중복 뉴스는 건너뜀
                            if not title or not href:
                                continue

                            # 상세 페이지 접속 후 발행일 추출
                            driver.execute_script("window.open('');")
                            driver.switch_to.window(driver.window_handles[1])
                            driver.get(href)
                            time.sleep(1)

                            try:
                                date_el = driver.find_element(
                                    By.CSS_SELECTOR, 
                                    "span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME"
                                )
                                published_str = date_el.get_attribute("data-date-time")
                                published_date = timezone.make_aware(
                                    datetime.strptime(published_str, "%Y-%m-%d %H:%M:%S")
                                )   
                            except:
                                published_date = timezone.make_aware(target_date) #실패 시 target_date로 fallback

                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])

                            # DB에 저장
                            headline_obj, created = Headline.objects.update_or_create(
                                url=href,
                                defaults={
                                "publisher":publisher,
                                "title":title,
                                "published_date":published_date.date(),
                                "crawled_at":timezone.now(),
                                "view_count":0
                                }
                            )

                            # API POST
                            #post_to_backend(headline_obj)

                            collected_articles.append({
                                "title": title,
                                "url": href,
                                "published_date": str(published_date),
                                "publisher": publisher.name
                            })
                        
                        except Exception as e:
                            print("기사 처리 오류:", e)
                            continue

                except Exception as e:
                    print("박스 처리 오류:", e)
                    continue
        except Exception as e:
            print("날짜 페이지 처리 오류:", e)
            continue

    driver.quit()
    print("전체 크롤링 및 POST 완료")
    return collected_articles
# 실행
if __name__ == "__main__": 
    crawl_naver_ranking(days=7, top_n=20)

def crawl():
    collected = crawl_naver_ranking(days=3, top_n=20)
    return {"status": "success", 
            "message": "네이버 뉴스 크롤링 완료",
            "items": collected
    }