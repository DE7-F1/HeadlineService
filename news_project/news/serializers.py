from rest_framework import serializers
from .models import *


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name']


class CreateOrGetSlugRelatedField(serializers.SlugRelatedField):
    """
    SlugRelatedField 확장: 값이 없으면 새로 Publisher를 생성
    """

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return queryset.get(**{self.slug_field: data})
        except queryset.model.DoesNotExist:
            return queryset.create(**{self.slug_field: data})


class HeadlineSerializer(serializers.ModelSerializer):
    publisher = CreateOrGetSlugRelatedField(
        slug_field='name',
        queryset=Publisher.objects.all(),
        style={'base_template': 'input.html'}
    )

    class Meta:
        model = Headline
        fields = ['id', 'title', 'publisher', 'url',
                'published_date', 'view_count', 'crawled_at']

    def create(self, validated_data):
        publisher_name = validated_data.pop("publisher")
        publisher, _ = Publisher.objects.get_or_create(name=publisher_name)
        headline = Headline.objects.create(
            publisher=publisher, **validated_data)
        return headline
    
# class WordCloudResultSerializer(serializers.ModelSerializer):
#     included_publishers = serializers.PrimaryKeyRelatedField(
#         many=True,
#         read_only=True,
#         source='included_publishers'  # 모델의 필드 이름과 일치시킴
#     )
#     class Meta:
#         model = WordCloudResult
#         fields = '__all__'
        
class NewsSearchSerializer(serializers.Serializer):
    press = serializers.CharField(source='publisher.name', read_only=True) 
    
    date = serializers.DateField(source='published_date', read_only=True) 

    class Meta:
        model = Headline
        fields = ['title', 'url', 'press', 'date']

