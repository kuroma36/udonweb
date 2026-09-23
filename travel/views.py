import json
import urllib.request
from datetime import datetime, timedelta
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.db.models import F, Q
from django.views.decorators.cache import never_cache
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import TravelTrip, TravelDay, TravelStop, TravelStopPhoto, TravelProfile
from .tokens import account_activation_token


def travel_login_required(view_func):
    """たびしお専用のログイン検証デコレータ（メール認証完了が必須）"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('travel:login')}?next={request.path}")
        tp = getattr(request.user, 'travel_profile', None)
        if not tp or not tp.is_email_verified:
            messages.warning(request, 'たびしおのアカウントでログイン、またはメールアドレス認証を完了してください。')
            return redirect(f"{reverse('travel:login')}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@travel_login_required
def home(request):
    """ルートURL: 旅行一覧へリダイレクト"""
    return redirect('travel:trip_list')


@travel_login_required
def trip_list(request):
    """旅行一覧画面: 計画中の旅と過去の旅"""
    today = timezone.now().date()
    user = request.user

    # ユーザーが作成した、またはメンバーとして参加している旅行
    user_trips = TravelTrip.objects.filter(
        models_filter_user(user)
    ).distinct().prefetch_related('members', 'days')

    upcoming_trips = [t for t in user_trips if t.end_date >= today]
    past_trips = [t for t in user_trips if t.end_date < today]

    context = {
        'upcoming_trips': upcoming_trips,
        'past_trips': past_trips,
        'all_trips_count': len(user_trips),
    }
    return render(request, 'travel/trip_list.html', context)


def models_filter_user(user):
    from django.db.models import Q
    if not user.is_authenticated:
        return Q(id__isnull=True)
    return Q(created_by=user) | Q(members=user)


@travel_login_required
def trip_create(request):
    """旅行の新規作成"""
    all_users = User.objects.exclude(id=request.user.id).select_related('travel_profile')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        destination = request.POST.get('destination', '').strip()
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        cover_preset = request.POST.get('cover_preset', 'hokkaido')
        description = request.POST.get('description', '').strip()
        member_ids = request.POST.getlist('members')
        cover_image = request.FILES.get('cover_image')

        if not title:
            messages.error(request, '旅行タイトルを入力してください。')
            return render(request, 'travel/trip_form.html', {'all_users': all_users, 'is_create': True})

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else timezone.now().date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else start_date
        except ValueError:
            start_date = timezone.now().date()
            end_date = start_date

        if end_date < start_date:
            end_date = start_date

        trip = TravelTrip.objects.create(
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            cover_preset=cover_preset,
            cover_image=cover_image,
            description=description,
            created_by=request.user
        )

        if member_ids:
            trip.members.set(User.objects.filter(id__in=member_ids))

        # 日程 (Day 1, Day 2...) を自動作成
        trip.ensure_days()

        messages.success(request, f'旅行「{trip.title}」を作成しました。')
        return redirect('travel:trip_detail', trip_id=trip.id)

    return render(request, 'travel/trip_form.html', {
        'all_users': all_users,
        'is_create': True,
        'today': timezone.now().date().strftime('%Y-%m-%d'),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    })


@travel_login_required
def trip_edit(request, trip_id):
    """旅行の基本情報編集"""
    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return HttpResponseForbidden('この旅程を編集する権限がありません。')

    all_users = User.objects.exclude(id=trip.created_by.id).select_related('travel_profile')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        destination = request.POST.get('destination', '').strip()
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        cover_preset = request.POST.get('cover_preset', trip.cover_preset)
        description = request.POST.get('description', '').strip()
        member_ids = request.POST.getlist('members')
        cover_image = request.FILES.get('cover_image')

        if not title:
            messages.error(request, '旅行タイトルを入力してください。')
            return render(request, 'travel/trip_form.html', {
                'trip': trip,
                'all_users': all_users,
                'is_create': False,
                'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
            })

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else trip.start_date
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else trip.end_date
        except ValueError:
            start_date = trip.start_date
            end_date = trip.end_date

        if end_date < start_date:
            end_date = start_date

        trip.title = title
        trip.destination = destination
        trip.start_date = start_date
        trip.end_date = end_date
        trip.cover_preset = cover_preset
        trip.description = description
        if cover_image:
            trip.cover_image = cover_image
        trip.save()

        if member_ids is not None:
            trip.members.set(User.objects.filter(id__in=member_ids))

        # 日程の同期
        trip.ensure_days()

        messages.success(request, '旅行情報を更新しました。')
        return redirect('travel:trip_detail', trip_id=trip.id)

    return render(request, 'travel/trip_form.html', {
        'trip': trip,
        'all_users': all_users,
        'is_create': False,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    })


@travel_login_required
def trip_delete(request, trip_id):
    """旅行の削除（作成者のみ）"""
    trip = get_object_or_404(TravelTrip, id=trip_id)
    if trip.created_by != request.user and not request.user.is_superuser:
        messages.error(request, '旅行を削除できるのは作成者のみです。')
        return redirect('travel:trip_detail', trip_id=trip.id)

    if request.method == 'POST':
        title = trip.title
        trip.delete()
        messages.success(request, f'旅行「{title}」を削除しました。')
        return redirect('travel:trip_list')

    return redirect('travel:trip_detail', trip_id=trip.id)


@travel_login_required
def trip_detail(request, trip_id):
    """メイン画面: ルートマップ ＆ Day別タイムライン ＆ 共同編集"""
    trip = get_object_or_404(
        TravelTrip.objects.prefetch_related('days__stops__paired_stop__day', 'members__profile', 'created_by__profile'),
        id=trip_id
    )
    if not trip.is_accessible_by(request.user):
        messages.error(request, 'この旅程を閲覧する権限がありません。')
        return redirect('travel:trip_list')

    trip.ensure_days()
    days = list(trip.days.all())

    # 現在選択されているDay（デフォルトはDay 1）
    day_num = request.GET.get('day', '1')
    try:
        active_day_num = int(day_num)
    except ValueError:
        active_day_num = 1

    active_day = next((d for d in days if d.day_number == active_day_num), days[0] if days else None)
    stops = list(active_day.ordered_stops) if active_day else []

    # JS用スポットデータ
    stops_json_data = []
    for s in stops:
        stops_json_data.append({
            'id': s.id,
            'order': s.order,
            'name': s.name,
            'category': s.category,
            'category_display': s.get_category_display(),
            'address': s.address,
            'lat': s.latitude,
            'lng': s.longitude,
            'google_place_id': s.google_place_id,
            'photo_url': s.photo_image.url if s.photo_image else (s.photo_url or ''),
            'arrival_time': s.arrival_time.strftime('%H:%M') if s.arrival_time else '',
            'departure_time': s.departure_time.strftime('%H:%M') if s.departure_time else '',
            'stay_duration': s.stay_duration,
            'memo': s.memo,
            # 宿泊連動情報
            'is_paired': bool(s.paired_stop_id),
            'paired_stop_id': s.paired_stop_id,
            'paired_day_number': s.paired_stop.day.day_number if s.paired_stop else None,
            'is_hotel_start': bool(s.paired_stop and s.day.day_number > s.paired_stop.day.day_number),
            # 移動情報
            'transport_mode': s.transport_mode,
            'transport_mode_display': s.get_transport_mode_display(),
            'transport_departure_time': s.transport_departure_time.strftime('%H:%M') if s.transport_departure_time else '',
            'transport_arrival_time': s.transport_arrival_time.strftime('%H:%M') if s.transport_arrival_time else '',
            'transport_time_text': s.transport_time_text or '',
            'transport_memo': s.transport_memo or '',
        })

    # メンバー追加モーダル用の既存ユーザー一覧
    existing_member_ids = set(trip.members.values_list('id', flat=True))
    existing_member_ids.add(trip.created_by.id)
    candidate_users = User.objects.exclude(id__in=existing_member_ids).select_related('travel_profile')

    context = {
        'trip': trip,
        'days': days,
        'active_day': active_day,
        'stops': stops,
        'stops_json': json.dumps(stops_json_data),
        'candidate_users': candidate_users,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'travel/trip_detail.html', context)


@travel_login_required
def trip_guide(request, trip_id):
    """旅のしおり画面: 全日程のタイムライン・メモ・印刷ビュー"""
    trip = get_object_or_404(
        TravelTrip.objects.prefetch_related('days__stops', 'members__profile', 'created_by__profile'),
        id=trip_id
    )
    if not trip.is_accessible_by(request.user):
        messages.error(request, 'この旅程を閲覧する権限がありません。')
        return redirect('travel:trip_list')

    days = trip.days.all()

    context = {
        'trip': trip,
        'days': days,
        'is_guide_mode': True,
    }
    return render(request, 'travel/trip_guide.html', context)


def fetch_google_place_details(place_id):
    """Google Place Details API から星評価・総件数・公式住所・クチコミ（上位3件）を取得"""
    if not place_id:
        return {}
    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not google_api_key:
        return {}

    try:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,user_ratings_total,formatted_address,reviews&language=ja&key={google_api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'TabishioWeb/1.0'})
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 'OK' and data.get('result'):
                res = data['result']
                rating = res.get('rating')
                user_ratings_total = res.get('user_ratings_total', 0)
                raw_reviews = res.get('reviews', [])
                parsed_reviews = []
                for r in raw_reviews:
                    parsed_reviews.append({
                        'author_name': r.get('author_name', 'Google ユーザー'),
                        'profile_photo_url': r.get('profile_photo_url', ''),
                        'rating': r.get('rating', 5),
                        'relative_time_description': r.get('relative_time_description', ''),
                        'text': r.get('text', ''),
                    })
                return {
                    'rating': float(rating) if rating is not None else None,
                    'user_ratings_total': int(user_ratings_total) if user_ratings_total else 0,
                    'address': res.get('formatted_address', ''),
                    'reviews': parsed_reviews[:3],
                }
    except Exception:
        pass
    return {}


@travel_login_required
def stop_detail(request, trip_id, stop_id):
    """スポット専用詳細ページ: Googleクチコミ上位3件 ＆ 写真ギャラリー・投稿"""
    trip = get_object_or_404(
        TravelTrip.objects.prefetch_related('members__travel_profile', 'created_by__travel_profile'),
        id=trip_id
    )
    if not trip.is_accessible_by(request.user):
        messages.error(request, 'この旅程を閲覧する権限がありません。')
        return redirect('travel:trip_list')

    stop = get_object_or_404(
        TravelStop.objects.select_related('day').prefetch_related('photos__user__profile'),
        id=stop_id,
        day__trip=trip
    )

    # Google Place Details クチコミ取得
    google_details = {}
    google_reviews = []
    if stop.google_place_id:
        google_details = fetch_google_place_details(stop.google_place_id)
        google_reviews = google_details.get('reviews', [])

    # その日の前後のスポット（ナビゲーション用）
    day_stops = list(stop.day.ordered_stops)
    current_idx = next((i for i, s in enumerate(day_stops) if s.id == stop.id), -1)
    prev_stop = day_stops[current_idx - 1] if current_idx > 0 else None
    next_stop = day_stops[current_idx + 1] if current_idx >= 0 and current_idx < len(day_stops) - 1 else None

    # ユーザー投稿写真一覧（連動スポットがある場合は双方の写真を合算表示）
    if stop.paired_stop:
        user_photos = TravelStopPhoto.objects.filter(stop__in=[stop, stop.paired_stop]).select_related('user__profile')
    else:
        user_photos = stop.photos.all()

    context = {
        'trip': trip,
        'stop': stop,
        'day': stop.day,
        'prev_stop': prev_stop,
        'next_stop': next_stop,
        'google_details': google_details,
        'google_reviews': google_reviews,
        'user_photos': user_photos,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
    }
    return render(request, 'travel/stop_detail.html', context)


@travel_login_required
def api_upload_stop_photo(request, trip_id, stop_id):
    """スポットへの写真投稿（複数枚対応）"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    stop = get_object_or_404(TravelStop, id=stop_id, day__trip=trip)

    uploaded_files = request.FILES.getlist('photos')
    if not uploaded_files and 'photo' in request.FILES:
        uploaded_files = [request.FILES['photo']]

    if not uploaded_files:
        messages.error(request, '写真が選択されていません')
        return redirect('travel:stop_detail', trip_id=trip.id, stop_id=stop.id)

    caption = request.POST.get('caption', '').strip()
    created_count = 0
    for f in uploaded_files:
        TravelStopPhoto.objects.create(
            stop=stop,
            user=request.user,
            image=f,
            caption=caption
        )
        created_count += 1

    messages.success(request, f'{created_count}枚の思い出写真を投稿しました。')
    return redirect('travel:stop_detail', trip_id=trip.id, stop_id=stop.id)


@travel_login_required
def api_delete_stop_photo(request, trip_id, stop_id, photo_id):
    """スポット投稿写真の削除"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    stop = get_object_or_404(TravelStop, id=stop_id, day__trip=trip)
    photo = get_object_or_404(TravelStopPhoto, id=photo_id, stop=stop)

    # 投稿者本人、旅行作成者、またはスタッフのみ削除可能
    if photo.user != request.user and trip.created_by != request.user and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': '削除権限がありません'}, status=403)

    photo.delete()
    messages.success(request, '写真を削除しました。')
    return redirect('travel:stop_detail', trip_id=trip.id, stop_id=stop.id)


# ==========================================
# REST / AJAX API エンドポイント群
# ==========================================

@travel_login_required
def api_add_stop(request, trip_id):
    """スポットの追加（Places検索または手動）"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    trip = TravelTrip.objects.filter(id=trip_id).first()
    if not trip:
        return JsonResponse({'status': 'error', 'message': '旅行が見つかりません'}, status=404)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    day_id = request.POST.get('day_id')
    if day_id:
        day = TravelDay.objects.filter(id=day_id, trip=trip).first()
    else:
        day = trip.days.order_by('day_number').first()

    if not day:
        # 日程が存在しない場合は自動作成
        trip.ensure_days()
        day = trip.days.order_by('day_number').first()

    if not day:
        return JsonResponse({'status': 'error', 'message': '日程が見つかりませんでした'}, status=400)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'status': 'error', 'message': 'スポット名を入力してください'}, status=400)

    category = request.POST.get('category', 'sightseeing')
    address = request.POST.get('address', '').strip()
    lat = request.POST.get('lat')
    lng = request.POST.get('lng')
    place_id = request.POST.get('place_id', '').strip()
    photo_url = request.POST.get('photo_url', '').strip()
    arrival_time_str = request.POST.get('arrival_time')
    stay_duration = request.POST.get('stay_duration', '').strip()
    memo = request.POST.get('memo', '').strip()
    transport_mode = request.POST.get('transport_mode', 'car')

    latitude = None
    longitude = None
    if lat:
        try:
            latitude = float(lat)
        except (ValueError, TypeError):
            latitude = None
    if lng:
        try:
            longitude = float(lng)
        except (ValueError, TypeError):
            longitude = None

    arrival_time = None
    if arrival_time_str:
        try:
            arrival_time = datetime.strptime(arrival_time_str, '%H:%M').time()
        except ValueError:
            pass

    # 現在の最大orderを取得
    current_max_order = day.stops.count()

    stop = TravelStop.objects.create(
        day=day,
        order=current_max_order + 1,
        name=name,
        category=category,
        address=address,
        latitude=latitude,
        longitude=longitude,
        google_place_id=place_id,
        photo_url=photo_url,
        arrival_time=arrival_time,
        stay_duration=stay_duration,
        memo=memo,
        transport_mode=transport_mode,
    )

    # 宿設定時の翌日スタート自動登録
    sync_next_day_val = request.POST.get('sync_next_day', 'true').lower()
    sync_next_day = sync_next_day_val in ('true', '1', 'on')

    next_day_stop = None
    if category == 'hotel' and sync_next_day:
        next_day = TravelDay.objects.filter(trip=trip, day_number=day.day_number + 1).first()
        if next_day:
            # 翌日の既存スポットのorderをすべて+1して繰り下げ
            for existing in next_day.stops.all().order_by('-order'):
                existing.order += 1
                existing.save(update_fields=['order'])

            # 翌日の先頭（order=1）に同じ宿をスタート地点として作成
            next_day_stop = TravelStop.objects.create(
                day=next_day,
                order=1,
                name=name,
                category='hotel',
                address=address,
                latitude=latitude,
                longitude=longitude,
                google_place_id=place_id,
                photo_url=photo_url,
                memo=f"Day {day.day_number}の宿泊先よりスタート",
                transport_mode='car',
                paired_stop=stop,
            )
            stop.paired_stop = next_day_stop
            stop.save(update_fields=['paired_stop'])

    msg = f'「{stop.name}」を旅程に追加しました！'
    if next_day_stop:
        msg = f'「{stop.name}」をDay {day.day_number}および翌日（Day {day.day_number + 1}）のスタート地点に追加しました！'

    return JsonResponse({
        'status': 'ok',
        'stop_id': stop.id,
        'paired_stop_id': next_day_stop.id if next_day_stop else None,
        'message': msg
    })


@travel_login_required
def api_reorder_stops(request, trip_id):
    """ドラッグ＆ドロップによるスポットの巡回順更新"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = TravelTrip.objects.filter(id=trip_id).first()
    if not trip:
        return JsonResponse({'status': 'error', 'message': '旅行が見つかりません'}, status=404)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    try:
        data = json.loads(request.body)
        stops_payload = data.get('stops', [])
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    for item in stops_payload:
        stop_id = item.get('id')
        new_order = item.get('order')
        if stop_id and new_order is not None:
            TravelStop.objects.filter(id=stop_id, day__trip=trip).update(order=new_order)

    return JsonResponse({'status': 'ok', 'message': '順序を更新しました'})


@travel_login_required
def api_delete_stop(request, trip_id, stop_id):
    """スポットの削除（連動する宿泊スポットがある場合は両方削除）"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = TravelTrip.objects.filter(id=trip_id).first()
    if not trip:
        return JsonResponse({'status': 'error', 'message': '旅行が見つかりません'}, status=404)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    stop = TravelStop.objects.filter(id=stop_id, day__trip=trip).first()
    if not stop:
        return JsonResponse({'status': 'error', 'message': 'スポットが見つかりません'}, status=404)

    day = stop.day
    paired = stop.paired_stop
    paired_day = paired.day if paired else None

    # 連動スポットが存在する場合、両方削除
    if paired:
        stop.paired_stop = None
        stop.save(update_fields=['paired_stop'])
        paired.paired_stop = None
        paired.save(update_fields=['paired_stop'])

        stop.delete()
        paired.delete()
    else:
        stop.delete()

    # 当日残りのストップのorderを再採番
    for idx, s in enumerate(day.ordered_stops, start=1):
        if s.order != idx:
            s.order = idx
            s.save(update_fields=['order'])

    # 連動先の日程がある場合、その日程のストップも再採番
    if paired_day and paired_day.id != day.id:
        for idx, s in enumerate(paired_day.ordered_stops, start=1):
            if s.order != idx:
                s.order = idx
                s.save(update_fields=['order'])

    msg = 'スポットと連動する宿泊スポットを削除しました' if paired else 'スポットを削除しました'
    return JsonResponse({
        'status': 'ok',
        'message': msg,
        'deleted_paired': bool(paired)
    })


@travel_login_required
def api_update_transport(request, trip_id, stop_id):
    """交通手段・ダイヤ情報（案1）の更新"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = TravelTrip.objects.filter(id=trip_id).first()
    if not trip:
        return JsonResponse({'status': 'error', 'message': '旅行が見つかりません'}, status=404)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    stop = TravelStop.objects.filter(id=stop_id, day__trip=trip).first()
    if not stop:
        return JsonResponse({'status': 'error', 'message': 'スポットが見つかりません'}, status=404)

    if 'transport_mode' in request.POST:
        stop.transport_mode = request.POST.get('transport_mode', stop.transport_mode)

    if 'transport_departure_time' in request.POST:
        dep_str = request.POST.get('transport_departure_time', '').strip()
        if dep_str:
            try:
                stop.transport_departure_time = datetime.strptime(dep_str, '%H:%M').time()
            except ValueError:
                stop.transport_departure_time = None
        else:
            stop.transport_departure_time = None

    if 'transport_arrival_time' in request.POST:
        arr_str = request.POST.get('transport_arrival_time', '').strip()
        if arr_str:
            try:
                stop.transport_arrival_time = datetime.strptime(arr_str, '%H:%M').time()
            except ValueError:
                stop.transport_arrival_time = None
        else:
            stop.transport_arrival_time = None

    if 'transport_memo' in request.POST:
        stop.transport_memo = request.POST.get('transport_memo', '').strip()

    # 所要時間の自動計算（案1: 出発時刻・到着時刻がある場合は最優先で自動計算）
    calculated_text = stop.calculate_transport_duration()
    if calculated_text:
        stop.transport_time_text = calculated_text
    elif 'transport_time_text' in request.POST:
        manual_time_text = request.POST.get('transport_time_text', '').strip()
        if manual_time_text:
            stop.transport_time_text = manual_time_text
        elif not stop.transport_departure_time and not stop.transport_arrival_time:
            stop.transport_time_text = ''

    stop.save()

    return JsonResponse({
        'status': 'ok',
        'transport_mode': stop.transport_mode,
        'transport_mode_display': stop.get_transport_mode_display(),
        'transport_departure_time': stop.transport_departure_time.strftime('%H:%M') if stop.transport_departure_time else '',
        'transport_arrival_time': stop.transport_arrival_time.strftime('%H:%M') if stop.transport_arrival_time else '',
        'transport_time_text': stop.transport_time_text,
        'transport_memo': stop.transport_memo,
    })


@travel_login_required
def api_add_member(request, trip_id):
    """共同編集メンバーの追加"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    user_id = request.POST.get('user_id')
    user = get_object_or_404(User, id=user_id)

    trip.members.add(user)

    profile = getattr(user, 'profile', None)
    initial = (profile.nickname[0] if profile and profile.nickname else user.username[0]).upper()
    avatar_color = profile.avatar_color if profile else '#0284C7'
    avatar_image = profile.avatar_image.url if profile and profile.avatar_image else None
    nickname = profile.nickname if profile and profile.nickname else user.username

    return JsonResponse({
        'status': 'ok',
        'member': {
            'id': user.id,
            'name': nickname,
            'initial': initial,
            'avatar_color': avatar_color,
            'avatar_image': avatar_image,
        }
    })


@travel_login_required
def api_delete_member(request, trip_id, member_id):
    """共同編集メンバーの解除"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    user = get_object_or_404(User, id=member_id)
    trip.members.remove(user)

    return JsonResponse({'status': 'ok', 'message': 'メンバーを解除しました'})




# ==========================================
# たびしお専用 認証ビュー（メール認証・本登録フロー）
# ==========================================

AVATAR_COLORS = [
    {'hex': '#0284C7', 'name': 'スカイブルー'},
    {'hex': '#0F172A', 'name': 'ディープネイビー'},
    {'hex': '#0D9488', 'name': 'エメラルド'},
    {'hex': '#F59E0B', 'name': 'サンセット'},
    {'hex': '#E11D48', 'name': 'コーラル'},
    {'hex': '#7C3AED', 'name': 'パープル'},
]


@never_cache
def login_view(request):
    """たびしお専用のログイン画面（メールアドレス＋パスワード）"""
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:trip_list'

    if request.user.is_authenticated:
        tp = getattr(request.user, 'travel_profile', None)
        if tp and tp.is_email_verified:
            return redirect(next_url)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not email or not password:
            return render(request, 'travel/auth/login.html', {
                'error_message': 'メールアドレスとパスワードを入力してください。',
                'email': email,
                'next': next_url,
            })

        user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()

        if user and user.check_password(password):
            tp = getattr(user, 'travel_profile', None)
            if not tp or not tp.is_email_verified:
                return render(request, 'travel/auth/login.html', {
                    'error_message': 'メールアドレスの確認が完了していません。受信トレイの確認メールをクリックして本登録を完了してください。',
                    'email': email,
                    'next': next_url,
                })

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            messages.success(request, f'おかえりなさい、{tp.nickname}さん！')
            return redirect(next_url)
        else:
            return render(request, 'travel/auth/login.html', {
                'error_message': 'メールアドレスまたはパスワードが正しくありません。',
                'email': email,
                'next': next_url,
            })

    return render(request, 'travel/auth/login.html', {'next': next_url})


@never_cache
def register_view(request):
    """たびしお専用の新規アカウント登録画面（確認メール送信）"""
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:trip_list'

    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        avatar_color = request.POST.get('avatar_color', '#0284C7')

        form_data = {
            'nickname': nickname,
            'email': email,
        }

        if not nickname or not email or not password:
            return render(request, 'travel/auth/register.html', {
                'error_message': 'すべての必須項目を入力してください。',
                'form_data': form_data,
                'colors': AVATAR_COLORS,
                'next': next_url,
            })

        if password != password2:
            return render(request, 'travel/auth/register.html', {
                'error_message': 'パスワードが一致しません。もう一度ご確認ください。',
                'form_data': form_data,
                'colors': AVATAR_COLORS,
                'next': next_url,
            })

        if len(password) < 8:
            return render(request, 'travel/auth/register.html', {
                'error_message': 'パスワードは8文字以上で設定してください。',
                'form_data': form_data,
                'colors': AVATAR_COLORS,
                'next': next_url,
            })

        existing_user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
        if existing_user:
            existing_tp = getattr(existing_user, 'travel_profile', None)
            if existing_tp and existing_tp.is_email_verified:
                return render(request, 'travel/auth/register.html', {
                    'error_message': 'このメールアドレスは既に本登録されています。ログイン画面からログインしてください。',
                    'form_data': form_data,
                    'colors': AVATAR_COLORS,
                    'next': next_url,
                })
            else:
                user = existing_user
                user.set_password(password)
                user.is_active = False
                user.save()
                if existing_tp:
                    existing_tp.nickname = nickname
                    existing_tp.avatar_color = avatar_color
                    existing_tp.save()
                else:
                    TravelProfile.objects.create(
                        user=user,
                        nickname=nickname,
                        avatar_color=avatar_color,
                        is_email_verified=False
                    )
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                is_active=False
            )
            TravelProfile.objects.create(
                user=user,
                nickname=nickname,
                avatar_color=avatar_color,
                is_email_verified=False
            )

        send_activation_email(request, user, nickname, email)
        request.session['registered_email'] = email
        return redirect('travel:register_sent')

    return render(request, 'travel/auth/register.html', {
        'colors': AVATAR_COLORS,
        'next': next_url,
    })


def send_activation_email(request, user, nickname, email):
    """本登録用のアクティベーションメールを生成・送信"""
    token = account_activation_token.make_token(user)
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    activation_url = request.build_absolute_uri(
        reverse('travel:activate', kwargs={'uidb64': uidb64, 'token': token})
    )

    context = {
        'nickname': nickname,
        'activation_url': activation_url,
    }
    subject = '【たびしお】メールアドレスの確認と本登録のお願い'
    text_content = render_to_string('travel/emails/activation_email.txt', context)
    html_content = render_to_string('travel/emails/activation_email.html', context)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'たびしお <noreply@krmts.com>')
    send_mail(
        subject=subject,
        message=text_content,
        from_email=from_email,
        recipient_list=[email],
        html_message=html_content,
        fail_silently=False,
    )


def register_sent_view(request):
    """仮登録完了・確認メール送信済み案内"""
    email = request.session.get('registered_email') or request.GET.get('email', '')
    return render(request, 'travel/auth/register_sent.html', {'email': email})


@never_cache
def activate_view(request, uidb64, token):
    """受信メールのリンクをクリックした時の本登録（アクティベーション）"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid).first()
    except (TypeError, ValueError, OverflowError):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])

        tp = getattr(user, 'travel_profile', None)
        if tp:
            tp.is_email_verified = True
            tp.email_verified_at = timezone.now()
            tp.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'メールアドレスの認証が完了しました！ようこそ、{tp.nickname if tp else user.username}さん。')
        return redirect('travel:activation_success')
    else:
        return render(request, 'travel/auth/activation_invalid.html')


def activation_success_view(request):
    """本登録完了画面"""
    return render(request, 'travel/auth/activation_success.html')


def resend_activation_view(request):
    """認証メール再送"""
    email = request.GET.get('email', '')
    error_message = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()

        if user:
            tp = getattr(user, 'travel_profile', None)
            if tp and tp.is_email_verified:
                error_message = 'このメールアドレスは既に本登録が完了しています。ログイン画面からログインしてください。'
            else:
                nickname = tp.nickname if tp else user.username
                send_activation_email(request, user, nickname, email)
                request.session['registered_email'] = email
                messages.info(request, f'{email} 宛に認証メールを再送しました。')
                return redirect('travel:register_sent')
        else:
            error_message = '入力されたメールアドレスのアカウントは見つかりませんでした。新規登録をお願いします。'

    return render(request, 'travel/auth/resend_activation.html', {
        'email': email,
        'error_message': error_message,
    })


@travel_login_required
def profile_view(request):
    """たびしおプロフィール設定画面"""
    profile = request.user.travel_profile

    if request.method == 'POST':
        nickname = request.POST.get('nickname', '').strip()
        avatar_color = request.POST.get('avatar_color', profile.avatar_color)
        bio = request.POST.get('bio', '').strip()

        if nickname:
            profile.nickname = nickname
            profile.avatar_color = avatar_color
            profile.bio = bio
            profile.save()
            messages.success(request, 'プロフィール設定を保存しました。')
            return redirect('travel:profile')
        else:
            messages.error(request, 'お名前（ニックネーム）を入力してください。')

    return render(request, 'travel/auth/profile.html', {
        'profile': profile,
        'colors': AVATAR_COLORS,
    })


def logout_view(request):
    """たびしお専用ログアウト"""
    logout(request)
    messages.info(request, 'たびしおからログアウトしました。')
    return redirect('travel:login')
