from django.http import JsonResponse
from django.http import HttpResponse
from django.utils import timezone
import datetime
import time
import re
import os
import sys

# Django 설정 추가
import django
from django.conf import settings

# Django 앱이 아직 설정되지 않았다면 설정
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news_project.settings')
    django.setup()

# HeadlineSerializer import
from news.serializers import HeadlineSerializer

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def crawl_youtube_data(request=None, crawl_until=7):
    """
    유튜브 링크로 접속해서 무한 스크롤을 하여 받아온 비디오 갯수만큼의 데이터를 크롤링
    """
    chrome_options = Options() 
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # 봇 감지 우회 강화
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 더 실제적인 User-Agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # GitHub Actions 환경에서 Chrome 바이너리 위치 설정
    if os.environ.get('GITHUB_ACTIONS'):
        chrome_options.binary_location = "/usr/bin/google-chrome"
        print("GitHub Actions 환경에서 실행 중")

    try:
        driver_path = ChromeDriverManager().install()
        print(f"ChromeDriver 경로: {driver_path}")
        service = Service(driver_path)
    except Exception as e:
        print(f"ChromeDriverManager 에러: {e}")
        if os.environ.get('GITHUB_ACTIONS'):
            import shutil
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                print(f"시스템 ChromeDriver 발견: {chromedriver_path}")
                service = Service(chromedriver_path)
            else:
                print("ChromeDriver를 찾을 수 없습니다. 기본 Service 사용")
                service = Service()
        else:
            service = Service()

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # 봇 감지 우회
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("Chrome WebDriver 초기화 성공")
    except Exception as e:
        print(f"Chrome WebDriver 초기화 실패: {e}")
        raise

    urls = [
        "https://www.youtube.com/@MBCNEWS11/videos",
        "https://www.youtube.com/@sbsnews8/videos",
        "https://www.youtube.com/@newskbs/videos",
        "https://www.youtube.com/@jtbc_news/videos",
        "https://www.youtube.com/@ytnnews24/videos",
    ]

    try:
        for url in urls:
            print(f"URL 접속: {url}")
            driver.get(url)
            
            # 충분한 로딩 시간 확보
            print("페이지 로딩 대기 중...")
            time.sleep(10)  # 기본 10초 대기
            
            # JavaScript 완전 로딩 확인
            wait = WebDriverWait(driver, 30)
            try:
                # 페이지 완전 로딩 대기
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                print("페이지 로딩 완료")
                
                # YouTube 비디오 컨테이너 로딩 대기
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-item-renderer")))
                print("비디오 컨테이너 로딩 완료")
                
            except Exception as e:
                print(f"페이지 로딩 대기 중 에러: {e}")
            
            # 추가 JavaScript 실행 대기
            time.sleep(5)
            
            # 스크롤링으로 더 많은 콘텐츠 로드
            print("스크롤링 시작...")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(4)
                print(f"스크롤 {i+1}/3 완료")
            
            # 비디오 컨테이너 수집
            video_containers = driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer")
            print(f"발견된 비디오 컨테이너 수: {len(video_containers)}")
            
            if not video_containers:
                print("비디오 컨테이너를 찾을 수 없습니다.")
                return JsonResponse({
                    'status': 'error',
                    'message': '비디오를 찾을 수 없습니다.'
                })
            
            # 채널명 추출 (더 정확한 선택자들)
            channel_name = "MBCNEWS"  # 기본값
            channel_selectors = [
                "ytd-channel-name #text",
                "yt-formatted-string#text:not([aria-label*='Skip'])",  # Skip navigation 제외
                "#channel-name #text",
                "a#channel-name #text",
                "#owner-text a",
                "ytd-video-owner-renderer #text"
            ]
            
            for selector in channel_selectors:
                try:
                    channel_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in channel_elements:
                        text = elem.text.strip()
                        if text and 'skip' not in text.lower() and 'navigation' not in text.lower():
                            channel_name = text
                            print(f"채널명 추출 성공: {channel_name} (selector: {selector})")
                            break
                    if channel_name != "MBCNEWS":  # 기본값이 아니면 찾았다는 의미
                        break
                except:
                    continue
            
            print(f"최종 채널명: {channel_name}")
            
            processed_count = 0
            max_videos = 10
            
            # 비디오 처리
            for i, container in enumerate(video_containers[:max_videos]):
                try:
                    print(f"\n=== 비디오 {i+1} 처리 중 ===")
                    
                    # 제목 추출
                    title_element = container.find_element(By.CSS_SELECTOR, "#video-title")
                    title_text = title_element.text.strip()
                    
                    if not title_text:
                        print("제목이 없는 비디오, 건너뜀")
                        continue
                    
                    # 제목 정리
                    original_title = title_text
                    title_text = re.sub(r'\[.*?\]', '', title_text)
                    title_text = re.sub(r'\(.*?\)', '', title_text)
                    title_text = re.sub(r'\s*/.*$', '', title_text)
                    title_text = re.sub(r'\s*ㅣ.*$', '', title_text)
                    title_text = re.sub(r'\s*｜.*$', '', title_text)
                    title_text = re.sub(r'\s*\|.*$', '', title_text)
                    title_text = re.sub(r'\s*#.*$', '', title_text)
                    title_text = re.sub(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', '', title_text)
                    title_text = re.sub(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}', '', title_text)
                    title_text = re.sub(r'\s*(다시보기|뉴스룸|뉴스데스크)\s*', ' ', title_text)
                    title_text = re.sub(r'\s+', ' ', title_text).strip()
                    
                    print(f"원본 제목: {original_title}")
                    print(f"정리된 제목: {title_text}")
                    
                    # URL 추출
                    video_url = container.find_element(By.CSS_SELECTOR, '#video-title-link').get_attribute('href')
                    print(f"비디오 URL: {video_url}")
                    
                    # 메타데이터 추출 - 다양한 방법 시도
                    view_count = 0
                    upload_date = None
                    
                    print("메타데이터 추출 시작...")
                    
                    # 방법 1: 기본 span 요소들
                    metadatas = container.find_elements(By.CSS_SELECTOR, "span")
                    print(f"기본 span 요소 개수: {len(metadatas)}")
                    
                    for j, span in enumerate(metadatas):
                        span_text = span.text.strip()
                        if not span_text:
                            continue
                        
                        print(f"  Span {j}: '{span_text}'")
                        
                        # 조회수 추출 (한국어/영어)
                        if (('조회수' in span_text or '회' in span_text or 'views' in span_text.lower() or 'view' in span_text.lower()) 
                            and view_count == 0):
                            try:
                                view_count = trans_view_count(span_text)
                                print(f"  --> 조회수 추출 성공: {view_count}")
                            except Exception as e:
                                print(f"  --> 조회수 추출 실패: {e}")
                        
                        # 업로드 날짜 추출 (한국어/영어)
                        elif (any(keyword in span_text for keyword in ['일 전', '주 전', '개월 전', '년 전', '시간 전', '분 전']) or
                              any(keyword in span_text.lower() for keyword in ['ago', 'hour', 'day', 'week', 'month', 'year', 'minute'])) and upload_date is None:
                            try:
                                upload_date = trans_upload_date(span_text)
                                print(f"  --> 업로드 날짜 추출 성공: {upload_date}")
                            except Exception as e:
                                print(f"  --> 업로드 날짜 추출 실패: {e}")
                    
                    # 방법 2: 더 구체적인 선택자들 시도
                    if view_count == 0 or upload_date is None:
                        print("추가 선택자로 메타데이터 검색...")
                        additional_selectors = [
                            "div#metadata span",
                            "ytd-video-meta-block span", 
                            "#metadata-line span",
                            "div#details span",
                            "[class*='metadata'] span"
                        ]
                        
                        for selector in additional_selectors:
                            try:
                                elements = container.find_elements(By.CSS_SELECTOR, selector)
                                print(f"선택자 '{selector}': {len(elements)}개 요소")
                                
                                for elem in elements:
                                    text = elem.text.strip()
                                    if not text:
                                        continue
                                    
                                    print(f"    '{text}'")
                                    
                                    # 조회수 추출 (한국어/영어)
                                    if (('조회수' in text or '회' in text or 'views' in text.lower() or 'view' in text.lower()) 
                                        and view_count == 0):
                                        try:
                                            view_count = trans_view_count(text)
                                            print(f"    --> 조회수 추출: {view_count}")
                                        except:
                                            pass
                                    
                                    # 업로드 날짜 추출 (한국어/영어)
                                    elif (any(keyword in text for keyword in ['일 전', '주 전', '개월 전', '년 전', '시간 전', '분 전']) or
                                          any(keyword in text.lower() for keyword in ['ago', 'hour', 'day', 'week', 'month', 'year', 'minute'])) and upload_date is None:
                                        try:
                                            upload_date = trans_upload_date(text)
                                            print(f"    --> 날짜 추출: {upload_date}")
                                        except:
                                            pass
                                            
                            except Exception as e:
                                print(f"선택자 '{selector}' 에러: {e}")
                    
                    # 기본값 설정
                    if upload_date is None:
                        upload_date = timezone.now().date()
                        print(f"기본 업로드 날짜 설정: {upload_date}")
                    
                    if view_count == 0:
                        print("조회수를 찾을 수 없어 0으로 설정")
                    
                    # 데이터 저장
                    now = timezone.now()
                    crawled_data = {
                        "title": title_text,
                        "publisher": channel_name,
                        "url": video_url,
                        "view_count": view_count,
                        "published_date": upload_date,
                        "crawled_at": now,
                    }
                    
                    print(f"최종 데이터: {crawled_data}")
                    success = db_save(crawled_data)
                    
                    if success:
                        processed_count += 1
                        print(f"비디오 {i+1} 저장 완료")
                    else:
                        print(f"비디오 {i+1} 저장 실패")
                        
                except Exception as e:
                    print(f"비디오 {i+1} 처리 중 오류: {e}")
                    continue
            
            print(f"\n총 {processed_count}개 비디오 처리 완료")

        return JsonResponse({
            'status': 'success',
            'count': processed_count
        })
    
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'크롤링 중 오류가 발생했습니다: {str(e)}'
        })
        
    finally:
        driver.quit()
        print("Chrome WebDriver 종료")


def trans_view_count(view):
    """조회수 텍스트를 숫자로 변환 (한국어/영어 지원)"""
    print(f"조회수 변환 입력: '{view}'")
    
    view_text = view.replace('조회수', '').replace('회', '').replace('views', '').replace('view', '').strip()
    view_text = view_text.replace('.', '').replace(',', '')
    
    try:
        # 영어 처리
        if 'K' in view_text.upper():
            number_str = view_text.upper().replace('K', '')
            number = float(number_str) 
            result = int(number * 1000)
        elif 'M' in view_text.upper():
            number_str = view_text.upper().replace('M', '')
            number = float(number_str)
            result = int(number * 1000000)
        elif 'B' in view_text.upper():
            number_str = view_text.upper().replace('B', '')
            number = float(number_str)
            result = int(number * 1000000000)
        # 한국어 처리
        elif '만' in view_text:
            number_str = view_text.replace('만', '')
            number = float(number_str) 
            result = int(number * 10000)
        elif '천' in view_text:
            number_str = view_text.replace('천', '')
            number = float(number_str)
            result = int(number * 1000)
        else:
            result = int(view_text)
        
        print(f"조회수 변환 결과: {result}")
        return result
    except Exception as e:
        print(f"조회수 변환 실패: {e}")
        return 0


def trans_upload_date(date_text):
    """업로드 날짜 텍스트로 업로드 시간 계산 (한국어/영어 지원)"""
    print(f"날짜 변환 입력: '{date_text}'")
    
    now = timezone.now()
    
    try:
        numbers = re.findall(r'\d+', date_text)
        if not numbers:
            return now.date()
            
        time_value = int(numbers[0])

        # 영어 처리
        if 'minute' in date_text.lower() or 'min' in date_text.lower():
            upload_time = now - datetime.timedelta(minutes=time_value)
        elif 'hour' in date_text.lower():
            upload_time = now - datetime.timedelta(hours=time_value)
        elif 'day' in date_text.lower():
            upload_time = now - datetime.timedelta(days=time_value)
        elif 'week' in date_text.lower():
            upload_time = now - datetime.timedelta(weeks=time_value)
        elif 'month' in date_text.lower():
            upload_time = now - datetime.timedelta(days=time_value * 30)
        elif 'year' in date_text.lower():
            upload_time = now - datetime.timedelta(days=time_value * 365)
        # 한국어 처리
        elif '분 전' in date_text:
            upload_time = now - datetime.timedelta(minutes=time_value)
        elif '시간 전' in date_text:
            upload_time = now - datetime.timedelta(hours=time_value)
        elif '일 전' in date_text:
            upload_time = now - datetime.timedelta(days=time_value)
        elif '주 전' in date_text:
            upload_time = now - datetime.timedelta(weeks=time_value)
        elif '개월 전' in date_text:
            upload_time = now - datetime.timedelta(days=time_value * 30)
        elif '년 전' in date_text:
            upload_time = now - datetime.timedelta(days=time_value * 365)
        else:
            return now.date()

        result = upload_time.date()
        print(f"날짜 변환 결과: {result}")
        return result
        
    except Exception as e:
        print(f"날짜 변환 실패: {e}")
        return now.date()


def db_save(data):
    try:
        # serializer에 전달할 데이터 포맷 정리
        api_data = {
            "title": data['title'],
            "publisher": data['publisher'],
            "url": data['url'],
            "published_date": data['published_date'].isoformat() if hasattr(data['published_date'], 'isoformat') else str(data['published_date']),
            "view_count": data['view_count'],
            "crawled_at": data['crawled_at'].isoformat()
        }
        
        print(f"Serializer에 전달할 데이터: {api_data}")
        
        # HeadlineSerializer 사용해서 데이터 저장
        serializer = HeadlineSerializer(data=api_data)
        
        if serializer.is_valid():
            # 저장 성공
            instance = serializer.save()
            print(f"데이터 저장 성공 - ID: {instance.id}")
            return True
        else:
            # 유효성 검사 실패
            print(f"Serializer 유효성 검사 실패: {serializer.errors}")
            return False
        
    except Exception as e:
        print(f"db_save에서 예상치 못한 오류: {e}")
        return False
