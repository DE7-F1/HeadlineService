from django.http import HttpResponse
from . import crawler_youtube
from . import crawler_naver
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET', 'POST'])
def youtube_crawling(request):
    """YouTube 크롤링을 실행하고 간단한 응답 반환"""
    try:
        crawler_youtube.crawl_youtube_data(request)
        return HttpResponse("YouTube crawling completed successfully!")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
    
@api_view(['GET'])  
def naver_crawling(request):
    result = crawler_naver.crawl()  
    return Response({'message': 'Naver crawling success', 'data': result})