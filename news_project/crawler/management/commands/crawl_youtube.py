from django.core.management.base import BaseCommand
from crawler import crawler_youtube


class Command(BaseCommand):
    help = 'Run YouTube crawler (used by CI / GitHub Actions)'

    def handle(self, *args, **options):
        self.stdout.write('Starting YouTube crawl...')
        result = crawler_youtube.crawl_youtube_data(request=None)
        self.stdout.write('Crawl finished: %s' % (getattr(result, 'status', 'done')))