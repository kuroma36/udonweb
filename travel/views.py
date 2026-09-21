import json
import urllib.request
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.db.models import F, Q
from django.views.decorators.cache import never_cache
from .models import TravelTrip, TravelDay, TravelStop, TravelStopPhoto
from udon.models import UserProfile
from udon.views import get_or_create_user_by_nickname


@login_required(login_url='travel:login')
def home(request):
    """ルートURL: 旅行一覧へリダイレクト"""
    return redirect('travel:trip_list')


@login_required(login_url='travel:login')
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
    return Q(created_by=user) | Q(members=user)


@login_required(login_url='travel:login')
def trip_create(request):
    """旅行の新規作成"""
    all_users = User.objects.exclude(id=request.user.id).select_related('profile')

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


@login_required(login_url='travel:login')
def trip_edit(request, trip_id):
    """旅行の基本情報編集"""
    trip = get_object_or_404(TravelTrip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return HttpResponseForbidden('この旅程を編集する権限がありません。')

    all_users = User.objects.exclude(id=trip.created_by.id).select_related('profile')

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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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
    candidate_users = User.objects.exclude(id__in=existing_member_ids).select_related('profile')

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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
def stop_detail(request, trip_id, stop_id):
    """スポット専用詳細ページ: Googleクチコミ上位3件 ＆ 写真ギャラリー・投稿"""
    trip = get_object_or_404(
        TravelTrip.objects.prefetch_related('members__profile', 'created_by__profile'),
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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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

@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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


@login_required(login_url='travel:login')
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
# 旅ナビ専用 Auth ビュー（独立したログイン・登録）
# ==========================================

@never_cache
def login_view(request):
    """旅ナビ専用のログイン・新規登録画面"""
    next_url = request.GET.get('next') or request.POST.get('next') or 'travel:trip_list'

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        nickname = request.POST.get('nickname', '').strip()

        # 1. 登録済みユーザーチップからのワンタップ即時ログイン
        if user_id:
            user = get_object_or_404(User, id=user_id)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            profile = getattr(user, 'profile', None)
            name = profile.nickname if profile else user.username
            messages.success(request, f'おかえりなさい、{name}さん！')
            return redirect(next_url)

        # 2. お名前入力によるログインまたは自動登録
        if nickname:
            avatar_color = request.POST.get('avatar_color', '#0284C7')
            avatar_icon = request.POST.get('avatar_icon', 'traveler')
            
            user, profile = get_or_create_user_by_nickname(
                nickname,
                avatar_color=avatar_color,
                avatar_icon=avatar_icon,
                favorite_udon='旅行'
            )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            messages.success(request, f'ようこそ、{profile.nickname}さん！素敵な旅を計画しましょう。')
            return redirect(next_url)
        else:
            messages.error(request, 'お名前（ニックネーム）を入力してください。')

    if request.user.is_authenticated:
        return redirect(next_url)

    # 既存のユーザー一覧（最近利用順）
    existing_profiles = UserProfile.objects.select_related('user').order_by(
        F('user__last_login').desc(nulls_last=True),
        '-created_at'
    )[:50]

    colors = [
        {'hex': '#0284C7', 'name': 'スカイブルー'},
        {'hex': '#0F172A', 'name': 'ディープネイビー'},
        {'hex': '#0D9488', 'name': 'エメラルド'},
        {'hex': '#F59E0B', 'name': 'サンセット'},
        {'hex': '#E11D48', 'name': 'コーラル'},
        {'hex': '#7C3AED', 'name': 'パープル'},
    ]

    context = {
        'existing_profiles': existing_profiles,
        'colors': colors,
        'next': next_url,
    }
    return render(request, 'travel/auth/login.html', context)


def guest_mode(request):
    """ゲストとしてワンタップ体験ログイン"""
    next_url = request.GET.get('next') or 'travel:trip_list'
    import random
    random_id = random.randint(100, 999)
    guest_name = f"ゲストトラベラー{random_id}"

    user, profile = get_or_create_user_by_nickname(
        guest_name,
        avatar_color='#0284C7',
        avatar_icon='compass',
        favorite_udon='旅行'
    )
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    messages.info(request, f'ゲストモード（{guest_name}）でログインしました。旅程を自由に計画してみましょう！')
    return redirect(next_url)


def logout_view(request):
    """ログアウト"""
    logout(request)
    messages.info(request, 'ログアウトしました。またいつでも旅の計画をお待ちしています。')
    return redirect('travel:login')
