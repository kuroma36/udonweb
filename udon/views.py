import json
import urllib.request
import urllib.parse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Avg, F
from django.utils import timezone
from datetime import date, timedelta
from .models import Shop, Trip, TripMember, TripStop, Review, UserProfile, ShopPhoto, ReviewLike, ReviewComment, Notification, ShopFavorite


def home(request):
    """Home view: redirect to login if not authenticated, otherwise first accessible trip map."""
    if not request.user.is_authenticated:
        return redirect('udon:login')
    trip = Trip.objects.for_user(request.user).first()
    if trip:
        return redirect('udon:trip_map', trip_id=trip.id)
    return redirect('udon:trip_list')


@login_required(login_url='udon:login')
def trip_map(request, trip_id):
    """Screen 1: Map Route & Shop Order View."""
    trip = get_object_or_404(Trip.objects.prefetch_related('stops__shop', 'members'), id=trip_id)
    if not trip.is_accessible_by(request.user):
        messages.error(request, 'この旅程を閲覧する権限がありません（参加メンバーのみ閲覧可能です）。')
        return redirect('udon:trip_list')

    trip.update_travel_times()
    stops = trip.ordered_stops
    
    # Prepare stops data for JS map
    stops_data = []
    for s in stops:
        stops_data.append({
            'id': s.id,
            'order': s.visit_order,
            'trip_id': trip.id,
            'shop_id': s.shop.id,
            'name': s.shop.name,
            'lat': s.shop.lat,
            'lng': s.shop.lng,
            'address': s.shop.address,
            'featured_menu': s.shop.featured_menu,
            'travel_time': s.travel_time_text,
            'status': s.status,
            'badge_color': s.badge_color,
            'score': s.shop.average_score_total,
            'photo': s.shop.display_photo,
        })
    
    all_trips = Trip.objects.for_user(request.user)[:10]
    
    context = {
        'trip': trip,
        'stops': stops,
        'stops_json': json.dumps(stops_data),
        'all_trips': all_trips,
    }
    return render(request, 'udon/trip_map.html', context)


@login_required(login_url='udon:login')
def trip_list(request):
    """Dashboard of user's accessible trips."""
    trips = Trip.objects.for_user(request.user).prefetch_related('stops__shop', 'members')
    context = {
        'trips': trips,
    }
    return render(request, 'udon/trip_list.html', context)


def get_or_create_user_by_nickname(nickname, avatar_color='#E67E22', avatar_icon='🧑', favorite_udon='かけうどん'):
    """Find existing user by nickname or username, or automatically create a new User & UserProfile."""
    nickname = nickname.strip() if nickname else ''
    if not nickname:
        return None, None

    # 1. Look up UserProfile by nickname
    profile = UserProfile.objects.filter(nickname=nickname).first()
    if profile:
        return profile.user, profile

    # 2. Look up User by username
    user = User.objects.filter(username=nickname).first()
    if user:
        profile = getattr(user, 'profile', None)
        return user, profile

    # 3. Automatically create new User and UserProfile
    base_username = f"udon_{abs(hash(nickname)) % 1000000}"
    while User.objects.filter(username=base_username).exists():
        base_username = f"udon_{abs(hash(nickname + timezone.now().isoformat())) % 1000000}"

    user = User.objects.create_user(username=base_username, password='udonuser1234')
    profile = UserProfile.objects.create(
        user=user,
        nickname=nickname,
        avatar_color=avatar_color,
        avatar_icon=avatar_icon,
        favorite_udon=favorite_udon,
        level_title='香川うどん人'
    )
    return user, profile


@login_required(login_url='udon:login')
def trip_create(request):
    """Screen 3: Create Trip with DND Stops."""
    shops = Shop.objects.all()
    registered_profiles = UserProfile.objects.exclude(user=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title', '香川うどん巡礼')
        date_str = request.POST.get('date') or request.POST.get('start_date')
        memo = request.POST.get('memo', '').strip()
        
        user = request.user
        trip_date = date.fromisoformat(date_str) if date_str else date.today()
        
        with transaction.atomic():
            trip = Trip.objects.create(
                title=title,
                owner=user,
                date=trip_date,
                start_date=trip_date,
                end_date=trip_date,
                memo=memo,
                is_public=True,
            )
            # Add owner as member
            owner_name = user.profile.nickname if hasattr(user, 'profile') and user.profile.nickname else user.username
            owner_color = user.profile.avatar_color if hasattr(user, 'profile') and user.profile.avatar_color else '#D99B26'
            TripMember.objects.create(
                trip=trip,
                user=user,
                name=owner_name,
                avatar_color=owner_color,
                avatar_icon='👩',
                role='owner'
            )
            # Add invited members with strict de-duplication & automatic User creation
            member_names = request.POST.getlist('members')
            seen_names = {owner_name, user.username}
            for m_name in member_names:
                m_name = m_name.strip() if m_name else ''
                if m_name and m_name not in seen_names:
                    seen_names.add(m_name)
                    m_user, m_profile = get_or_create_user_by_nickname(m_name)
                    if m_user:
                        seen_names.add(m_user.username)
                    TripMember.objects.create(
                        trip=trip,
                        user=m_user,
                        name=m_name,
                        avatar_color=m_profile.avatar_color if m_profile else '#E67E22',
                        role='member'
                    )
            
            # Add selected shops
            shop_ids = request.POST.getlist('shop_ids')
            travel_times = request.POST.getlist('travel_times')
            for idx, shop_id in enumerate(shop_ids, start=1):
                if shop_id:
                    shop = Shop.objects.get(id=shop_id)
                    t_time = travel_times[idx-1] if idx-1 < len(travel_times) and travel_times[idx-1] else '車で18分'
                    TripStop.objects.create(
                        trip=trip,
                        shop=shop,
                        visit_order=idx,
                        travel_time_text=t_time,
                    )
        
        messages.success(request, f'旅「{trip.title}」を作成しました！')
        return redirect('udon:trip_map', trip_id=trip.id)
    
    context = {
        'shops': shops,
        'today': date.today().isoformat(),
        'registered_profiles': registered_profiles,
    }
    return render(request, 'udon/trip_form.html', context)


@login_required(login_url='udon:login')
def trip_edit(request, trip_id):
    """Screen 3: Edit Trip and Reorder Stops."""
    trip = get_object_or_404(Trip.objects.prefetch_related('stops__shop', 'members'), id=trip_id)
    if not trip.is_accessible_by(request.user):
        messages.error(request, 'この旅程を編集する権限がありません。')
        return redirect('udon:trip_list')

    shops = Shop.objects.all()
    registered_profiles = UserProfile.objects.exclude(user=request.user)
    
    if request.method == 'POST':
        trip.title = request.POST.get('title', trip.title)
        date_str = request.POST.get('date') or request.POST.get('start_date')
        if date_str:
            trip.date = date.fromisoformat(date_str)
            trip.start_date = trip.date
            trip.end_date = trip.date
        if 'memo' in request.POST:
            trip.memo = request.POST.get('memo', '').strip()
        trip.save()
        
        messages.success(request, '旅行内容を更新しました。')
        return redirect('udon:trip_map', trip_id=trip.id)
        
    context = {
        'trip': trip,
        'stops': trip.ordered_stops,
        'members': trip.members.all(),
        'shops': shops,
        'registered_profiles': registered_profiles,
    }
    return render(request, 'udon/trip_form.html', context)


@login_required(login_url='udon:login')
@require_POST
def trip_delete(request, trip_id):
    """Delete a trip. Only the owner or superuser can delete it.
    Note: Reviews, photos, shops, and users remain intact.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.owner != request.user and not request.user.is_superuser:
        messages.error(request, '旅程の削除は主催者のみ実行できます。')
        return redirect('udon:trip_list')

    title = trip.title
    trip.delete()
    messages.success(request, f'旅程「{title}」を削除しました。（店舗レビューや写真は保持されます）')
    return redirect('udon:trip_list')


@login_required(login_url='udon:login')
def shop_detail(request, shop_id, trip_id=None):
    """Screen 2: Shop Detail & 5-Axis Score Breakdown & Member Comments (Accessible after login)."""
    shop = get_object_or_404(Shop.objects.prefetch_related('reviews__user', 'reviews__trip'), id=shop_id)
    trip = None
    if trip_id:
        candidate_trip = Trip.objects.filter(id=trip_id).first()
        if candidate_trip and candidate_trip.is_accessible_by(request.user):
            trip = candidate_trip
        
    # Deduplicate reviews per user, showing only the latest review per member
    reviews = shop.get_latest_unique_reviews()
    for r in reviews:
        r.user_has_liked = r.is_liked_by(request.user)
    
    # Calculate score metrics for 1~10 scale bars
    avg_scores = shop.average_scores
    
    # List of 5 axis definitions
    axes = [
        {'key': 'noodle', 'label': '[麺]', 'score': avg_scores['noodle'], 'int_score': int(round(avg_scores['noodle']))},
        {'key': 'soup', 'label': '[出汁]', 'score': avg_scores['soup'], 'int_score': int(round(avg_scores['soup']))},
        {'key': 'atmosphere', 'label': '[店の雰囲気]', 'score': avg_scores['atmosphere'], 'int_score': int(round(avg_scores['atmosphere']))},
        {'key': 'tempura', 'label': '[天ぷら]', 'score': avg_scores['tempura'], 'int_score': int(round(avg_scores['tempura']))},
        {'key': 'cost', 'label': '[コスパ]', 'score': avg_scores['cost'], 'int_score': int(round(avg_scores['cost']))},
    ]

    # Build photo gallery from ShopPhoto, reviews, and shop direct photo
    raw_gallery = []
    for sp in shop.photos.all().order_by('-created_at'):
        if sp.image:
            raw_gallery.append({
                'id': sp.id,
                'type': 'shop_photo',
                'url': sp.image.url,
                'caption': sp.caption or f'{sp.author_name} さんの投稿写真',
                'author': sp.author_name,
                'user_id': sp.user_id,
                'created_at': sp.created_at,
            })

    for r in reviews:
        if r.photo:
            raw_gallery.append({
                'id': r.id,
                'type': 'review',
                'url': r.photo.url,
                'caption': r.comment[:40] if r.comment else f'{r.author_name} さんの投稿',
                'author': r.author_name,
                'user_id': r.user_id,
                'created_at': r.created_at,
            })
        elif r.photo_url and not any(ph in r.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
            raw_gallery.append({
                'id': r.id,
                'type': 'review',
                'url': r.photo_url,
                'caption': r.comment[:40] if r.comment else f'{r.author_name} さんの投稿',
                'author': r.author_name,
                'user_id': r.user_id,
                'created_at': r.created_at,
            })

    # Sort newest first
    raw_gallery.sort(key=lambda x: x['created_at'], reverse=True)

    # Deduplicate URLs
    seen_urls = set()
    photo_gallery = []
    for item in raw_gallery:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            photo_gallery.append(item)

    if shop.photo and shop.photo.url not in seen_urls:
        photo_gallery.append({
            'id': None,
            'type': 'shop',
            'url': shop.photo.url,
            'caption': f'{shop.name} 店舗写真',
            'author': '店舗',
            'created_at': shop.created_at,
        })
    elif shop.photo_url and not any(ph in shop.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']) and shop.photo_url not in seen_urls:
        photo_gallery.append({
            'id': None,
            'type': 'shop',
            'url': shop.photo_url,
            'caption': f'{shop.name} 名物メニュー',
            'author': '店舗',
            'created_at': shop.created_at,
        })

    # Fetch top 3 Google Reviews & update rating if place_id exists
    google_reviews = []
    if shop.place_id:
        g_details = fetch_google_place_details(shop.place_id)
        if g_details:
            if g_details.get('rating') and not shop.google_rating:
                shop.google_rating = g_details['rating']
                shop.google_user_ratings_total = g_details.get('user_ratings_total', 0)
                shop.save(update_fields=['google_rating', 'google_user_ratings_total'])
            google_reviews = g_details.get('reviews', [])[:3]
    
    user_favorite = None
    if request.user.is_authenticated:
        user_favorite = ShopFavorite.objects.filter(user=request.user, shop=shop).first()

    context = {
        'shop': shop,
        'trip': trip,
        'reviews': reviews,
        'photo_gallery': photo_gallery,
        'google_reviews': google_reviews,
        'avg_scores': avg_scores,
        'axes': axes,
        'scale_10': list(range(1, 11)),
        'user_favorite': user_favorite,
    }
    return render(request, 'udon/shop_detail.html', context)


@login_required(login_url='udon:login')
def review_create(request, shop_id, trip_id=None):
    """Create or update a 5-axis review for a shop (Accessible after login)."""
    shop = get_object_or_404(Shop, id=shop_id)
    trip = None
    if trip_id:
        candidate_trip = Trip.objects.filter(id=trip_id).first()
        if candidate_trip and candidate_trip.is_accessible_by(request.user):
            trip = candidate_trip

    # Look for user's latest existing review for this shop
    existing_review = Review.objects.filter(shop=shop, user=request.user).order_by('-created_at').first()
        
    if request.method == 'POST':
        # Always use logged in user's profile nickname (login name)
        user_profile = getattr(request.user, 'profile', None)
        if user_profile and user_profile.nickname:
            author_name = user_profile.nickname
        else:
            posted_name = request.POST.get('author_name', '').strip()
            author_name = posted_name if posted_name and not posted_name.startswith('udon_') else request.user.username

        avatar_color = request.POST.get('avatar_color', '')
        if not avatar_color and user_profile and user_profile.avatar_color:
            avatar_color = user_profile.avatar_color
        elif not avatar_color:
            avatar_color = '#D99B26'

        score_noodle = int(request.POST.get('score_noodle', 8))
        score_soup = int(request.POST.get('score_soup', 8))
        score_atmosphere = int(request.POST.get('score_atmosphere', 8))
        score_tempura = int(request.POST.get('score_tempura', 8))
        score_cost = int(request.POST.get('score_cost', 9))
        score_total = float(request.POST.get('score_total', 4.8))
        comment = request.POST.get('comment', '')
        stamp_type = request.POST.get('stamp_type', '香川人選')
        
        is_update = existing_review is not None
        if is_update:
            review = existing_review
            review.trip = trip or existing_review.trip
            review.author_name = author_name
            review.author_avatar_color = avatar_color
            review.score_noodle = score_noodle
            review.score_soup = score_soup
            review.score_atmosphere = score_atmosphere
            review.score_tempura = score_tempura
            review.score_cost = score_cost
            review.score_total = score_total
            review.comment = comment
            review.stamp_type = stamp_type
        else:
            review = Review(
                shop=shop,
                trip=trip,
                user=request.user,
                author_name=author_name,
                author_avatar_color=avatar_color,
                score_noodle=score_noodle,
                score_soup=score_soup,
                score_atmosphere=score_atmosphere,
                score_tempura=score_tempura,
                score_cost=score_cost,
                score_total=score_total,
                comment=comment,
                stamp_type=stamp_type,
            )

        # Handle uploaded photos: supports both single and multiple
        uploaded_photos = request.FILES.getlist('photos')
        if not uploaded_photos and 'photo' in request.FILES:
            uploaded_photos = [request.FILES['photo']]

        if uploaded_photos:
            # First photo goes to review.photo
            review.photo = uploaded_photos[0]
            review.photo_url = ''

        review.save()

        # Additional photos in review form are stored as ShopPhoto records
        if len(uploaded_photos) > 1:
            for extra_img in uploaded_photos[1:]:
                ShopPhoto.objects.create(
                    shop=shop,
                    user=request.user,
                    author_name=author_name,
                    image=extra_img,
                    caption=f'{author_name} さんの投稿写真',
                )

        # Update shop top photo if review has photo
        if review.photo:
            shop.photo = review.photo
            shop.photo_url = ''
            shop.save(update_fields=['photo', 'photo_url'])
        
        if is_update:
            messages.success(request, f'「{shop.name}」のレビューを更新しました！')
        else:
            messages.success(request, f'「{shop.name}」のレビューを投稿しました！')

        if trip:
            return redirect('udon:shop_detail_in_trip', trip_id=trip.id, shop_id=shop.id)
        return redirect('udon:shop_detail', shop_id=shop.id)
        
    # Collect all photos posted by this user for this shop
    user_photos = []
    if existing_review and existing_review.photo:
        user_photos.append({
            'id': existing_review.id,
            'type': 'review',
            'type_label': 'レビュー添付写真',
            'url': existing_review.photo.url,
            'caption': existing_review.comment[:30] if existing_review.comment else 'レビュー写真',
            'created_at': existing_review.created_at,
        })
    elif existing_review and existing_review.photo_url and not any(ph in existing_review.photo_url for ph in ['no_image', 'udon_default', 'sanuki_hero']):
        user_photos.append({
            'id': existing_review.id,
            'type': 'review',
            'type_label': 'レビュー添付写真',
            'url': existing_review.photo_url,
            'caption': existing_review.comment[:30] if existing_review.comment else 'レビュー写真',
            'created_at': existing_review.created_at,
        })

    for sp in ShopPhoto.objects.filter(shop=shop, user=request.user).order_by('-created_at'):
        if sp.image:
            user_photos.append({
                'id': sp.id,
                'type': 'shop_photo',
                'type_label': '店舗写真',
                'url': sp.image.url,
                'caption': sp.caption or '店舗写真',
                'created_at': sp.created_at,
            })

    user_photos.sort(key=lambda x: x['created_at'], reverse=True)

    context = {
        'shop': shop,
        'trip': trip,
        'existing_review': existing_review,
        'user_photos': user_photos,
        'scale_10': list(range(1, 11)),
    }
    return render(request, 'udon/review_form.html', context)


@login_required(login_url='udon:login')
@require_POST
def shop_photo_upload(request, shop_id, trip_id=None):
    """Upload one or multiple photos for a shop outside of reviews."""
    shop = get_object_or_404(Shop, id=shop_id)
    trip = None
    if trip_id:
        candidate_trip = Trip.objects.filter(id=trip_id).first()
        if candidate_trip and candidate_trip.is_accessible_by(request.user):
            trip = candidate_trip

    uploaded_files = request.FILES.getlist('photos')
    if not uploaded_files and 'photo' in request.FILES:
        uploaded_files = [request.FILES['photo']]

    if not uploaded_files:
        messages.error(request, '写真が選択されていません')
        if trip:
            return redirect('udon:shop_detail_in_trip', trip_id=trip.id, shop_id=shop.id)
        return redirect('udon:shop_detail', shop_id=shop.id)

    user_profile = getattr(request.user, 'profile', None)
    author_name = user_profile.nickname if user_profile and user_profile.nickname else request.user.username
    caption = request.POST.get('caption', '').strip()

    created_photos = []
    for f in uploaded_files:
        sp = ShopPhoto.objects.create(
            shop=shop,
            user=request.user,
            author_name=author_name,
            image=f,
            caption=caption or f'{author_name} さんの投稿写真',
        )
        created_photos.append(sp)

    # Automatically set the latest uploaded photo as the shop's top photo
    if created_photos:
        shop.photo = created_photos[-1].image
        shop.photo_url = ''
        shop.save(update_fields=['photo', 'photo_url'])

    messages.success(request, f'{len(created_photos)}枚の写真を投稿しました！✨')
    if trip:
        return redirect('udon:shop_detail_in_trip', trip_id=trip.id, shop_id=shop.id)
    return redirect('udon:shop_detail', shop_id=shop.id)


@login_required(login_url='udon:login')
def shop_list(request):
    """Explore all Kagawa Udon shops (Accessible after login)."""
    query = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'all')

    # User's favorites dictionary: {shop_id: reason}
    user_fav_map = {}
    if request.user.is_authenticated:
        for fav in ShopFavorite.objects.filter(user=request.user):
            user_fav_map[fav.shop_id] = fav.reason

    favorites_count = len(user_fav_map)

    if tab == 'favorites':
        shops = Shop.objects.filter(id__in=user_fav_map.keys())
    else:
        shops = Shop.objects.all()

    if query:
        shops = shops.filter(Q(name__icontains=query) | Q(address__icontains=query) | Q(featured_menu__icontains=query))

    shop_list_data = []
    for s in shops:
        s.is_favorited = s.id in user_fav_map
        s.user_favorite_reason = user_fav_map.get(s.id, '')
        shop_list_data.append(s)

    context = {
        'shops': shop_list_data,
        'query': query,
        'current_tab': tab,
        'favorites_count': favorites_count,
    }
    return render(request, 'udon/shop_list.html', context)


# ===================== JSON APIs for Live Drag & Drop =====================

@require_POST
def api_reorder_stops(request, trip_id):
    """Reorder stops in a trip via AJAX drag & drop."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)
    try:
        data = json.loads(request.body)
        # Expected format: {"stops": [{"id": 1, "order": 1}, {"id": 2, "order": 2}, ...]}
        stops_list = data.get('stops', [])
        
        with transaction.atomic():
            # Temporarily offset visit_order to avoid unique constraint collisions
            for item in stops_list:
                TripStop.objects.filter(trip=trip, id=item['id']).update(visit_order=1000 + int(item['order']))
            
            for item in stops_list:
                stop = TripStop.objects.get(trip=trip, id=item['id'])
                stop.visit_order = int(item['order'])
                stop.save()
                
            trip.update_travel_times()
                
        return JsonResponse({'status': 'ok', 'message': 'ストップ順序を保存しました'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def fetch_google_place_details(place_id):
    """Fetch rating, user_ratings_total, address, and top reviews from Google Place Details API."""
    if not place_id:
        return {}
    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if not google_api_key:
        return {}

    try:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,rating,user_ratings_total,formatted_address,reviews&language=ja&key={google_api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'UdonWeb/1.0'})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
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
                    'reviews': parsed_reviews,
                }
    except Exception:
        pass
    return {}


@require_POST
def api_add_stop(request, trip_id):
    """Add a new stop to a trip (supports existing shop_id or Google Places data)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    shop_id = request.POST.get('shop_id')
    travel_time = request.POST.get('travel_time', '車で18分')
    
    if shop_id:
        shop = get_object_or_404(Shop, id=shop_id)
    else:
        # Created from Google Places Autocomplete Search
        name = request.POST.get('name')
        address = request.POST.get('address', '香川県')
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        place_id = request.POST.get('place_id', '')

        if not name or not lat or not lng:
            return JsonResponse({'status': 'error', 'message': '店舗名と位置情報が不足しています'}, status=400)

        # Check if shop already exists by place_id or name
        if place_id:
            shop = Shop.objects.filter(place_id=place_id).first()
        else:
            shop = Shop.objects.filter(name=name).first()

        if not shop:
            g_rating = request.POST.get('rating') or request.POST.get('google_rating')
            g_reviews = request.POST.get('user_ratings_total') or request.POST.get('google_user_ratings_total')
            
            # Fetch directly from Google Place Details API if not supplied
            if (not g_rating or not g_reviews) and place_id:
                details = fetch_google_place_details(place_id)
                if details.get('rating'):
                    g_rating = details['rating']
                    g_reviews = details.get('user_ratings_total', 0)

            shop = Shop.objects.create(
                name=name,
                address=address,
                lat=float(lat),
                lng=float(lng),
                place_id=place_id,
                google_rating=float(g_rating) if g_rating else None,
                google_user_ratings_total=int(g_reviews) if g_reviews else 0,
                featured_menu='香川手打うどん',
                price_range='300円〜700円',
                photo_url=''
            )
        elif place_id and not shop.google_rating:
            g_rating = request.POST.get('rating') or request.POST.get('google_rating')
            g_reviews = request.POST.get('user_ratings_total') or request.POST.get('google_user_ratings_total')
            if not g_rating:
                details = fetch_google_place_details(place_id)
                if details.get('rating'):
                    g_rating = details['rating']
                    g_reviews = details.get('user_ratings_total', 0)
            if g_rating:
                shop.google_rating = float(g_rating)
                if g_reviews:
                    shop.google_user_ratings_total = int(g_reviews)
                shop.save()

    # Calculate visit order as next available
    max_order = trip.stops.count()
    stop = TripStop.objects.create(
        trip=trip,
        shop=shop,
        visit_order=max_order + 1,
        travel_time_text=travel_time,
        status='planned'
    )
    trip.update_travel_times()
    stop.refresh_from_db()
    return JsonResponse({
        'status': 'ok',
        'stop': {
            'id': stop.id,
            'shop_id': shop.id,
            'shop_name': shop.name,
            'order': stop.visit_order,
            'travel_time': stop.travel_time_text,
        }
    })


@require_POST
def api_create_shop_from_place(request):
    """Create or get a Shop from Google Places search before trip creation."""
    name = request.POST.get('name')
    address = request.POST.get('address', '香川県')
    lat = request.POST.get('lat')
    lng = request.POST.get('lng')
    place_id = request.POST.get('place_id', '')

    if not name or not lat or not lng:
        return JsonResponse({'status': 'error', 'message': '情報が不足しています'}, status=400)

    if place_id:
        shop = Shop.objects.filter(place_id=place_id).first()
    else:
        shop = Shop.objects.filter(name=name).first()

    g_rating = request.POST.get('rating') or request.POST.get('google_rating')
    g_reviews = request.POST.get('user_ratings_total') or request.POST.get('google_user_ratings_total')

    if (not g_rating or not g_reviews) and place_id:
        details = fetch_google_place_details(place_id)
        if details.get('rating'):
            g_rating = details['rating']
            g_reviews = details.get('user_ratings_total', 0)

    if not shop:
        shop = Shop.objects.create(
            name=name,
            address=address,
            lat=float(lat),
            lng=float(lng),
            place_id=place_id,
            google_rating=float(g_rating) if g_rating else None,
            google_user_ratings_total=int(g_reviews) if g_reviews else 0,
            featured_menu='香川手打うどん',
            price_range='300円〜700円',
            photo_url=''
        )
    elif g_rating and not shop.google_rating:
        shop.google_rating = float(g_rating)
        if g_reviews:
            shop.google_user_ratings_total = int(g_reviews)
        shop.save()

    return JsonResponse({
        'status': 'ok',
        'shop': {
            'id': shop.id,
            'name': shop.name,
            'address': shop.address,
            'lat': shop.lat,
            'lng': shop.lng,
            'google_rating': shop.google_rating,
        }
    })


def api_search_shops(request):
    """Search food/udon shops using registered database and Google Places Text Search API."""
    query = request.GET.get('q', '').strip()
    results = []

    # 1. Search local registered database
    if query:
        shops = Shop.objects.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(featured_menu__icontains=query)
        )[:6]
    else:
        shops = Shop.objects.all()[:8]

    for s in shops:
        results.append({
            'id': s.id,
            'name': s.name,
            'address': s.address,
            'lat': float(s.lat),
            'lng': float(s.lng),
            'score': s.average_score_total,
            'google_rating': s.google_rating,
            'google_reviews': s.google_user_ratings_total,
            'review_count': s.review_count,
            'featured_menu': s.featured_menu,
            'place_id': s.place_id or '',
            'photo': s.display_photo,
            'source': 'db',
        })

    # 2. Query Google Places Text Search API for food & restaurant spots in Kagawa
    google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    if query and google_api_key:
        try:
            search_text = f"{query} 香川" if "香川" not in query and "うどん" not in query else query
            encoded_query = urllib.parse.quote(search_text)
            url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={encoded_query}&language=ja&region=jp&location=34.34,134.04&radius=35000&type=food&key={google_api_key}"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'UdonWeb/1.0'})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 'OK' and data.get('results'):
                    existing_names = {r['name'].lower() for r in results}
                    for place in data['results'][:8]:
                        p_name = place.get('name', '')
                        if p_name.lower() in existing_names:
                            continue
                        loc = place.get('geometry', {}).get('location', {})
                        if loc.get('lat') and loc.get('lng'):
                            p_rating = place.get('rating')
                            results.append({
                                'id': None,
                                'name': p_name,
                                'address': place.get('formatted_address', '香川県'),
                                'lat': float(loc['lat']),
                                'lng': float(loc['lng']),
                                'score': None,
                                'google_rating': float(p_rating) if p_rating else None,
                                'google_reviews': place.get('user_ratings_total', 0),
                                'review_count': 0,
                                'featured_menu': '',
                                'place_id': place.get('place_id', ''),
                                'photo': '/static/udon/images/no_image.svg',
                                'source': 'google',
                            })
                            existing_names.add(p_name.lower())
        except Exception as e:
            # Silently fallback to DB results
            pass

    return JsonResponse({'status': 'ok', 'shops': results})


@require_POST
def api_delete_stop(request, trip_id, stop_id):
    """Delete a stop and re-number subsequent stops."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    stop = get_object_or_404(TripStop, id=stop_id, trip=trip)
    deleted_order = stop.visit_order
    stop.delete()
    
    # Reorder remaining stops
    for s in trip.stops.filter(visit_order__gt=deleted_order).order_by('visit_order'):
        s.visit_order -= 1
        s.save()
        
    return JsonResponse({'status': 'ok', 'message': 'ストップを削除しました'})


@require_POST
def api_add_member(request, trip_id):
    """Add a member avatar to trip with duplicate prevention and automatic User creation."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'status': 'error', 'message': 'メンバー名を入力してください'}, status=400)

    avatar_color = request.POST.get('avatar_color', '#C84B31')
    avatar_icon = request.POST.get('avatar_icon', '🧑')

    target_user, profile = get_or_create_user_by_nickname(name, avatar_color=avatar_color, avatar_icon=avatar_icon)

    # Check duplicate by name or linked user
    existing_by_name = trip.members.filter(name=name).exists()
    existing_by_user = trip.members.filter(user=target_user).exists() if target_user else False

    if existing_by_name or existing_by_user:
        return JsonResponse({'status': 'error', 'message': f'「{name}」さんは既に参加メンバーに含まれています。'}, status=400)

    member = TripMember.objects.create(
        trip=trip,
        user=target_user,
        name=name,
        avatar_color=profile.avatar_color if profile else avatar_color,
        avatar_icon=avatar_icon,
        role='member'
    )
    return JsonResponse({
        'status': 'ok',
        'message': f'「{member.name}」さんを参加メンバーに追加しました！',
        'member': {
            'id': member.id,
            'name': member.name,
            'initial': member.initial,
            'avatar_color': member.avatar_color,
            'avatar_image': member.avatar_image,
            'role': member.role,
        }
    })


@require_POST
def api_delete_member(request, trip_id, member_id):
    """Remove a member from trip (owner cannot be removed)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    trip = get_object_or_404(Trip, id=trip_id)
    if not trip.is_accessible_by(request.user):
        return JsonResponse({'status': 'error', 'message': '権限がありません'}, status=403)

    member = get_object_or_404(TripMember, trip=trip, id=member_id)
    if member.role == 'owner' or (member.user and member.user == trip.owner):
        return JsonResponse({'status': 'error', 'message': '主催者はメンバーから外すことができません'}, status=400)

    member_name = member.name
    member.delete()
    return JsonResponse({
        'status': 'ok',
        'message': f'「{member_name}」さんを旅から外しました。',
        'member_id': member_id
    })


# ===================== Auth Views =====================

@never_cache
def login_view(request):
    """Easy Name-based login and registration with Udonchu mascot."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        nickname = request.POST.get('nickname', '').strip()

        # 1. Direct Quick Login from registered user chip
        if user_id:
            user = get_object_or_404(User, id=user_id)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            profile = getattr(user, 'profile', None)
            name = profile.nickname if profile else user.username
            messages.success(request, f'おかえりなさい、{name}さん！')
            return redirect('udon:home')

        # 2. Login or Register by Name
        if nickname:
            avatar_color = request.POST.get('avatar_color', '#E67E22')
            avatar_icon = request.POST.get('avatar_icon', 'udonchu')
            favorite_udon = request.POST.get('favorite_udon', '釜玉うどん')
            
            user, profile = get_or_create_user_by_nickname(
                nickname,
                avatar_color=avatar_color,
                avatar_icon=avatar_icon,
                favorite_udon=favorite_udon
            )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            messages.success(request, f'ようこそ、{profile.nickname}さん！')
            return redirect('udon:home')
        else:
            messages.error(request, 'お名前（ニックネーム）を入力してください。')

    if request.user.is_authenticated:
        return redirect('udon:home')

    existing_profiles = UserProfile.objects.select_related('user').order_by(
        F('user__last_login').desc(nulls_last=True),
        '-created_at'
    )[:50]
    
    context = {
        'existing_profiles': existing_profiles,
        'colors': [
            {'hex': '#E67E22', 'name': '香川橙'},
            {'hex': '#2980B9', 'name': '藍色'},
            {'hex': '#27AE60', 'name': '抹茶'},
            {'hex': '#8E44AD', 'name': '紫根'},
            {'hex': '#C84B31', 'name': '朱赤'},
            {'hex': '#1E2B37', 'name': '紺青'},
        ],
        'favorite_options': ['釜玉うどん', '温かけうどん', '冷やしぶっかけ', '生じょうゆうどん', 'ざるうどん', '肉うどん', '天ぷらうどん'],
    }
    return render(request, 'udon/auth/login.html', context)


def guest_mode(request):
    """Guest mode is deprecated, redirect to login."""
    return redirect('udon:login')


def logout_view(request):
    logout(request)
    messages.info(request, 'ログアウトしました。またのお越しをお待ちしております！')
    return redirect('udon:login')


def signup_view(request):
    return redirect('udon:login')


@login_required(login_url='udon:login')
def profile_edit(request):
    """View and edit user profile (avatar image, nickname, favorite udon, bio). Username cannot be changed."""
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'nickname': request.user.username,
            'avatar_color': '#E67E22',
            'favorite_udon': '釜玉うどん',
            'level_title': '見習いうどん人',
        }
    )

    if request.method == 'POST':
        # Display name (nickname) and username cannot be changed (used as login identifier)
        favorite_udon = request.POST.get('favorite_udon', '').strip()
        avatar_color = request.POST.get('avatar_color', profile.avatar_color)
        level_title = request.POST.get('level_title', profile.level_title)
        bio = request.POST.get('bio', '').strip()

        if favorite_udon:
            profile.favorite_udon = favorite_udon
        if avatar_color:
            profile.avatar_color = avatar_color
        if level_title:
            profile.level_title = level_title
        profile.bio = bio

        # Custom Avatar Image upload (Base64 data or standard multipart file)
        avatar_base64 = request.POST.get('avatar_base64', '').strip()
        if avatar_base64 and avatar_base64.startswith('data:image'):
            import base64
            import uuid
            from django.core.files.base import ContentFile

            try:
                header, imgstr = avatar_base64.split(';base64,', 1)
                ext = 'jpg'
                if 'png' in header:
                    ext = 'png'
                elif 'webp' in header:
                    ext = 'webp'
                file_name = f"avatar_{request.user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=file_name)
                profile.avatar_image.save(file_name, data, save=False)
            except Exception as e:
                pass
        elif 'avatar_image' in request.FILES:
            profile.avatar_image = request.FILES['avatar_image']
        elif request.POST.get('remove_avatar') == 'true':
            if profile.avatar_image:
                profile.avatar_image.delete(save=False)
            profile.avatar_image = None

        profile.save()
        messages.success(request, 'プロフィールを更新しました！✨')
        return redirect('udon:profile_edit')

    context = {
        'profile': profile,
        'colors': [
            {'hex': '#E67E22', 'name': '香川橙'},
            {'hex': '#D99B26', 'name': '黄金'},
            {'hex': '#2980B9', 'name': '藍色'},
            {'hex': '#27AE60', 'name': '抹茶'},
            {'hex': '#8E44AD', 'name': '紫根'},
            {'hex': '#C84B31', 'name': '朱赤'},
            {'hex': '#1E2B37', 'name': '紺青'},
        ],
        'favorite_options': ['釜玉うどん', '温かけうどん', '冷やしぶっかけ', '生じょうゆうどん', 'ざるうどん', '肉うどん', '天ぷらうどん', 'しっぽくうどん'],
        'level_options': ['見習いうどん人', '香川うどん愛好家', 'うどん巡礼マスター', '香川うどん仙人'],
        'favorites_count': ShopFavorite.objects.filter(user=request.user).count(),
    }
    return render(request, 'udon/profile_form.html', context)


@require_POST
def api_delete_review(request, review_id):
    """Delete a review (only owner or superuser)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)
    
    review = get_object_or_404(Review, id=review_id)
    if review.user != request.user and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': '他のユーザーのレビューは削除できません'}, status=403)
    
    shop = review.shop
    review.delete()
    shop.sync_top_photo()

    return JsonResponse({'status': 'ok', 'message': 'レビューを削除しました'})


@require_POST
def api_delete_review_photo(request, review_id):
    """Clear photo from a review without deleting the review itself."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    review = get_object_or_404(Review, id=review_id)
    if review.user != request.user and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': '他のユーザーのレビュー写真は削除できません'}, status=403)

    shop = review.shop
    review.photo = None
    review.photo_url = ''
    review.save(update_fields=['photo', 'photo_url'])
    shop.sync_top_photo()

    return JsonResponse({'status': 'ok', 'message': 'レビュー写真を削除しました'})


@require_POST
def api_delete_shop_photo(request, photo_id):
    """Delete a shop photo (only owner or superuser)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    photo_obj = get_object_or_404(ShopPhoto, id=photo_id)
    if photo_obj.user != request.user and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': '他のユーザーの写真は削除できません'}, status=403)

    shop = photo_obj.shop
    photo_obj.delete()
    shop.sync_top_photo()

    return JsonResponse({'status': 'ok', 'message': '写真を削除しました'})


@require_POST
def api_toggle_review_like(request, review_id):
    """Toggle like for a review by the logged-in user."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'いいねをするにはログインが必要です'}, status=401)

    review = get_object_or_404(Review, id=review_id)
    like_obj = ReviewLike.objects.filter(review=review, user=request.user).first()
    if like_obj:
        like_obj.delete()
        liked = False
        # Remove any unread like notification to prevent stale alerts
        Notification.objects.filter(
            recipient=review.user,
            sender=request.user,
            notification_type='like',
            review=review,
            is_read=False,
        ).delete()
    else:
        ReviewLike.objects.create(review=review, user=request.user)
        liked = True
        # Create notification for review author if different user
        if review.user and review.user != request.user:
            sender_name = request.user.profile.nickname if hasattr(request.user, 'profile') and request.user.profile.nickname else request.user.username
            Notification.objects.create(
                recipient=review.user,
                sender=request.user,
                notification_type='like',
                review=review,
                message=f'{sender_name} さんがあなたの「{review.shop.name}」のレビューにいいねしました！'
            )

    return JsonResponse({
        'status': 'ok',
        'liked': liked,
        'like_count': review.likes.count(),
    })


@require_POST
def api_create_review_comment(request, review_id):
    """Post a comment/reply to a review."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'コメントを投稿するにはログインが必要です'}, status=401)

    review = get_object_or_404(Review, id=review_id)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'status': 'error', 'message': 'コメント内容を入力してください'}, status=400)

    author_name = request.user.profile.nickname if hasattr(request.user, 'profile') and request.user.profile.nickname else request.user.username
    comment = ReviewComment.objects.create(
        review=review,
        user=request.user,
        author_name=author_name,
        content=content,
    )

    # Notify review author if different user
    if review.user and review.user != request.user:
        Notification.objects.create(
            recipient=review.user,
            sender=request.user,
            notification_type='comment',
            review=review,
            comment=comment,
            message=f'{comment.display_author_name} さんがあなたの「{review.shop.name}」のレビューにコメントしました: {comment.content[:35]}'
        )

    avatar_color = request.user.profile.avatar_color if hasattr(request.user, 'profile') else '#E67E22'
    avatar_image = request.user.profile.avatar_image.url if hasattr(request.user, 'profile') and request.user.profile.avatar_image else None

    return JsonResponse({
        'status': 'ok',
        'comment': {
            'id': comment.id,
            'author_name': comment.display_author_name,
            'initial': comment.initial,
            'avatar_color': avatar_color,
            'avatar_image': avatar_image,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%Y/%m/%d %H:%M'),
            'can_delete': True,
        },
        'comment_count': review.comments.count(),
    })


@require_POST
def api_delete_review_comment(request, comment_id):
    """Delete a comment (only owner or superuser)."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    comment = get_object_or_404(ReviewComment, id=comment_id)
    if comment.user != request.user and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': '他のユーザーのコメントは削除できません'}, status=403)

    review = comment.review
    comment.delete()
    return JsonResponse({
        'status': 'ok',
        'message': 'コメントを削除しました',
        'comment_count': review.comments.count(),
    })


def api_get_notifications(request):
    """Fetch user notifications and unread count."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    notifications_qs = Notification.objects.filter(recipient=request.user).select_related(
        'sender__profile', 'review__shop', 'comment'
    )[:30]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    items = []
    for n in notifications_qs:
        items.append({
            'id': n.id,
            'type': n.notification_type,
            'sender_name': n.sender_name,
            'sender_avatar_image': n.sender_avatar_image,
            'sender_avatar_color': n.sender_avatar_color,
            'sender_initial': n.sender_initial,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y/%m/%d %H:%M'),
            'time_ago': n.time_ago_str,
            'target_url': n.target_url,
        })

    return JsonResponse({
        'status': 'ok',
        'unread_count': unread_count,
        'notifications': items,
    })


@require_POST
def api_mark_notification_read(request, notification_id):
    """Mark single notification as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({
        'status': 'ok',
        'unread_count': unread_count,
    })


@require_POST
def api_mark_all_notifications_read(request):
    """Mark all notifications for current user as read."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'ログインが必要です'}, status=401)

    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({
        'status': 'ok',
        'unread_count': 0,
    })


@require_POST
def api_toggle_shop_favorite(request, shop_id):
    """Toggle shop favorite status and update optional reason/memo."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'お気に入り登録にはログインが必要です'}, status=401)

    shop = get_object_or_404(Shop, id=shop_id)

    action = 'save'
    reason = ''

    if request.content_type == 'application/json':
        try:
            body_data = json.loads(request.body)
            action = body_data.get('action', 'save')
            reason = str(body_data.get('reason', '')).strip()
        except (ValueError, json.JSONDecodeError):
            pass
    else:
        action = request.POST.get('action', 'save')
        reason = request.POST.get('reason', '').strip()

    if action == 'delete':
        ShopFavorite.objects.filter(user=request.user, shop=shop).delete()
        return JsonResponse({
            'status': 'ok',
            'favorited': False,
            'is_favorited': False,
            'reason': '',
            'message': f'「{shop.name}」をお気に入りから解除しました',
        })
    else:
        fav, created = ShopFavorite.objects.update_or_create(
            user=request.user,
            shop=shop,
            defaults={'reason': reason}
        )
        return JsonResponse({
            'status': 'ok',
            'favorited': True,
            'is_favorited': True,
            'reason': fav.reason,
            'message': f'「{shop.name}」をお気に入りに登録しました！',
        })





