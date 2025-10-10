from django.test import TestCase
from .models import *
from .serializers import *

# Create your tests here.


class PublisherSerializerTestCase(TestCase):
    def test_publisher_creation(self):
        serializer = PublisherSerializer(data={'name': 'publisher'})
        self.assertEqual(serializer.is_valid(), True)


class HeadlineSerializerTestCase(TestCase):
    def setUp(self):
        self.data = {
            'title': 'test title',
            'publisher': 'test publisher',
            'url': 'http://programmers.co.kr',
            'published_date': '2025-10-04',
            'view_count': 1,
            'crawled_at': '2025-10-04T16:18:00+09:00'
        }

    def test_create_headline_with_new_publisher(self):
        headline_serializer = HeadlineSerializer(data=self.data)
        self.assertEqual(headline_serializer.is_valid(), True)

    def test_create_headline_with_existing_publisher(self):
        publisher_serializer = PublisherSerializer(data={'name': 'test publisher'})
        publisher_serializer.is_valid()
        publisher = publisher_serializer.save()
        publisher_len = len(Publisher.objects.all())

        headline_serializer = HeadlineSerializer(data=self.data)
        headline_serializer.is_valid()
        headline = headline_serializer.save()

        self.assertEqual(headline_serializer.is_valid(), True)
        self.assertEqual(headline.publisher.id, publisher.id)
        self.assertEqual(publisher_len, len(Publisher.objects.all()))
