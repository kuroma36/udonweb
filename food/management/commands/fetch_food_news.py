from django.core.management.base import BaseCommand
from food.crawler import fetch_all_food_news


class Command(BaseCommand):
    help = 'Webから最新の食・新商品・グルメイベント記事を自動収集・集約します'

    def handle(self, *args, **options):
        self.stdout.write('Webから食ニュース・イベント記事を収集中...')
        result = fetch_all_food_news()
        self.stdout.write(
            self.style.SUCCESS(
                f"収集完了: 合計 {result['total_found']} 件取得 / 新規登録: {result['created_count']} 件 / 更新: {result['updated_count']} 件"
            )
        )
