
from .serializers import *
from rest_framework import generics, status
from rest_framework.response import Response
from django.http import JsonResponse
from django.db.models import Count,Q
from .models import *
from .data_processing.wordcloud_generator import generate_word_frequencies
from .serializers import NewsSearchSerializer 
from rest_framework.views import APIView



class PublisherList(generics.ListCreateAPIView):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer


class PublisherDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer


class HeadlineList(generics.ListCreateAPIView):
    queryset = Headline.objects.all()
    serializer_class = HeadlineSerializer

    def post(self, request, *args, **kwargs):
        title = request.data.get('title')

        if self.queryset.filter(title=title).exists():
            instance = Headline.objects.get(title=title)
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return self.create(request, *args, **kwargs)


class DeletePublisher(generics.RetrieveDestroyAPIView):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    

class HeadlineDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Headline.objects.all()
    serializer_class = HeadlineSerializer

def get_wordcloud_data(request):
    
    #사용자 요청 파라미터 가져오기 
    start_date_req = request.GET.get('start_date')
    end_date_req = request.GET.get('end_date')
    publishers_param = request.GET.get('publishers', '')
    publisher_ids_param = request.GET.get('publisher_ids') 

    # 둘 중 값이 있는 것을 target_param으로 설정
    target_param = publishers_param if publishers_param is not None else publisher_ids_param

    publisher_ids_req = []

    
    if target_param:
        # URL에 publishers 값이 있으면 해당 ID만 사용
        try:
            publisher_ids_req = [int(p_id) for p_id in target_param.split(',')]
        except ValueError:
            return JsonResponse({'success': False, 'message': '유효하지 않은 발행처 ID입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # URL에 publishers 값이 없으면 DB에 있는 모든 발행처 ID를 가져옴
        publisher_ids_req = list(Publisher.objects.values_list('id', flat=True))
    
    publisher_ids_req.sort()
    #캐싱된 결과 조회 
    latest_cached=None
    
    cached_results=WordCloudResult.objects.all()
    
    if start_date_req and end_date_req:
        cached_results = cached_results.filter(
            start_date=start_date_req,
            end_date=end_date_req,
        )
    else: pass
    
    cached_results=cached_results.annotate(p_count=Count('included_publishers') #언론사 총 개수 
    ).filter(p_count=len(publisher_ids_req)) # 연결된 언론사 수 = 요청된 발행사 수 
    
    #언론사 id 모두 포함하는지 
    for pub_id in publisher_ids_req:
        cached_results=cached_results.filter(included_publishers__id=pub_id)
    latest_cached=cached_results.order_by('-created_at').first()
    
    #캐싱된 결과가 있으면 해당 결과 반환
    if latest_cached:
        print(">> 캐싱된 워드클라우드 결과를 반환합니다.")
        return JsonResponse({
            'success': True,
            'result_id': latest_cached.id,
            'data': latest_cached.word_frequency_json
        },status=status.HTTP_200_OK)
    else:
        print(">> 캐싱된 결과가 없습니다. 새로운 워드클라우드 생성 작업을 시작합니다.")
        
        result=generate_word_frequencies(
            start_date=start_date_req,
            end_date=end_date_req,
            selected_publisher_ids=publisher_ids_req
        )
        if result is None:
            return JsonResponse({'success': False, 'message': '조건에 맞는 기사가 없어 워드클라우드 생성에 실패했습니다.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return JsonResponse({
                'success': True,
                'result_id': result.id,
                'data': result.word_frequency_json
            }, status=status.HTTP_200_OK)

class NewsSearchList(APIView):
    """
    GET /api/news 에 대한 응답 처리 (키워드/검색어)
    """
    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('q')
        keyword_query = request.GET.get('keyword')
        
        filters = Q()
        if search_query:
            filters |= Q(title__icontains=search_query)
        elif keyword_query:
            filters |= Q(title__icontains=keyword_query)
        else:
            return Response({'success': False, 'message': '검색어(q) 또는 키워드(keyword)를 입력해주세요.'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        queryset = Headline.objects.filter(filters).order_by('-published_date', '-view_count')
        
        if not queryset.exists():
            return Response({'success': False, 'message': '검색 결과가 없습니다.'}, 
                            status=status.HTTP_404_NOT_FOUND)

        serializer = NewsSearchSerializer(queryset, many=True)
    
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)