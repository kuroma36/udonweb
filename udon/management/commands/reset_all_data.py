import os
import glob
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from udon.models import Shop, Trip, TripMember, TripStop, Review, UserProfile


class Command(BaseCommand):
    help = 'Reset all database records (Users, Trips, Shops, Reviews) and remove uploaded media files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Do not prompt for confirmation before deleting data.',
        )

    def handle(self, *args, **options):
        if not options['no_input']:
            confirm = input("⚠️ 全てのユーザー、旅程、店舗、レビュー、メディア画像が消去されます。本当に初期化しますか？ [y/N]: ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING("初期化を中止しました。"))
                return

        self.stdout.write("1. レビュー・写真データを削除中...")
        Review.objects.all().delete()

        self.stdout.write("2. 巡回ストップ・参加メンバー・旅程を削除中...")
        TripStop.objects.all().delete()
        TripMember.objects.all().delete()
        Trip.objects.all().delete()

        self.stdout.write("3. 店舗情報を削除中...")
        Shop.objects.all().delete()

        self.stdout.write("4. ユーザープロフィール・ユーザーアカウントを削除中...")
        UserProfile.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write("5. アップロードされたメディアファイルを削除中...")
        media_patterns = ['media/avatars/*', 'media/reviews/*', 'media/shops/*']
        deleted_files = 0
        for pattern in media_patterns:
            for f in glob.glob(pattern):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                        deleted_files += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"削除エラー {f}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✨ 全データの初期化が完了しました！（削除画像数: {deleted_files}件）"))
        self.stdout.write(
            f"  - ユーザー数: {User.objects.count()}件\n"
            f"  - 旅程数: {Trip.objects.count()}件\n"
            f"  - 店舗数: {Shop.objects.count()}件\n"
            f"  - レビュー数: {Review.objects.count()}件"
        )
