from django.db import models
from django.contrib.auth.models import User
from datetime import date

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('male', '男性'),
        ('female', '女性'),
    ]
    ACTIVITY_CHOICES = [
        ('sedentary', '低い (デスクワーク中心・運動少なめ)'),
        ('moderate', '普通 (立ち仕事・軽い運動あり)'),
        ('active', '高い (活発な運動・肉体労働)'),
    ]
    GOAL_CHOICES = [
        ('maintain', '現状維持 (体重キープ)'),
        ('lose_slow', 'ゆるやか減量 (-0.5〜1kg/月)'),
        ('lose_fast', 'しっかり減量 (-1〜2kg/月)'),
        ('muscle', '筋肉量アップ・増量'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='foodlog_profile')
    nickname = models.CharField(max_length=50, default="ゲストダイエッター", verbose_name="ニックネーム")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male', verbose_name="性別")
    birth_year = models.IntegerField(default=1995, verbose_name="生年")
    height = models.FloatField(default=170.0, verbose_name="身長(cm)")
    current_weight = models.FloatField(default=65.0, verbose_name="現在の体重(kg)")
    target_weight = models.FloatField(default=62.0, verbose_name="目標体重(kg)")
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='moderate', verbose_name="身体活動レベル")
    goal_type = models.CharField(max_length=20, choices=GOAL_CHOICES, default='lose_slow', verbose_name="ダイエット目標")
    
    # 目標値 (自動計算可能)
    target_calories = models.FloatField(default=2000.0, verbose_name="目標カロリー(kcal)")
    target_p_ratio = models.FloatField(default=20.0, verbose_name="目標たんぱく質比率(%)")
    target_f_ratio = models.FloatField(default=25.0, verbose_name="目標脂質比率(%)")
    target_c_ratio = models.FloatField(default=55.0, verbose_name="目標炭水化物比率(%)")
    target_salt = models.FloatField(default=7.5, verbose_name="目標塩分上限(g)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ユーザー栄養目標"
        verbose_name_plural = "ユーザー栄養目標一覧"

    def __str__(self):
        return f"{self.nickname} (目標: {self.target_calories:.0f}kcal)"

    def calc_bmr_and_tdee(self):
        """基礎代謝量(BMR)と活動消費量(TDEE)の自動計算 (厚労省改訂ハリス・ベネディクト基準)"""
        current_year = date.today().year
        age = max(18, current_year - self.birth_year)
        w = self.current_weight
        h = self.height

        if self.gender == 'male':
            # 男性基準
            bmr = 66.47 + (13.75 * w) + (5.003 * h) - (6.75 * age)
        else:
            # 女性基準
            bmr = 655.1 + (9.563 * w) + (1.850 * h) - (4.676 * age)

        # 活動係数
        act_mult = {
            'sedentary': 1.45,
            'moderate': 1.70,
            'active': 1.95,
        }.get(self.activity_level, 1.70)

        tdee = bmr * act_mult

        # 目標調整
        goal_adj = {
            'maintain': 0,
            'lose_slow': -250,
            'lose_fast': -500,
            'muscle': +300,
        }.get(self.goal_type, -250)

        cal = max(1300.0, round(tdee + goal_adj, 0))
        return round(bmr, 0), round(tdee, 0), cal

    def to_dict(self):
        bmr, tdee, auto_cal = self.calc_bmr_and_tdee()
        return {
            'nickname': self.nickname,
            'gender': self.gender,
            'birth_year': self.birth_year,
            'height': self.height,
            'current_weight': self.current_weight,
            'target_weight': self.target_weight,
            'activity_level': self.activity_level,
            'goal_type': self.goal_type,
            'target_calories': self.target_calories,
            'target_p_ratio': self.target_p_ratio,
            'target_f_ratio': self.target_f_ratio,
            'target_c_ratio': self.target_c_ratio,
            'target_salt': self.target_salt,
            'bmr': bmr,
            'tdee': tdee,
            'auto_cal': auto_cal,
        }


class DailyLog(models.Model):
    date = models.DateField(db_index=True, verbose_name="記録日")
    weight = models.FloatField(null=True, blank=True, verbose_name="当日体重(kg)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "日別食事ログ"
        verbose_name_plural = "日別食事ログ一覧"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} 食事記録"

    def get_summary(self, profile=None):
        """1日の総栄養素、PFCバランス、目標差分、あすけん風スコア(0〜100点)を算出"""
        if not profile:
            profile = UserProfile.objects.first()
            if not profile:
                profile = UserProfile.objects.create()

        entries = self.meal_entries.prefetch_related('items').all()
        
        meals_dict = {
            'breakfast': {'label': '朝食', 'icon': 'fa-sun', 'color': 'amber', 'items': [], 'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbs': 0.0, 'salt': 0.0},
            'lunch': {'label': '昼食', 'icon': 'fa-utensils', 'color': 'emerald', 'items': [], 'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbs': 0.0, 'salt': 0.0},
            'dinner': {'label': '夕食', 'icon': 'fa-moon', 'color': 'indigo', 'items': [], 'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbs': 0.0, 'salt': 0.0},
            'snack': {'label': '間食・夜食', 'icon': 'fa-cookie-bite', 'color': 'rose', 'items': [], 'calories': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbs': 0.0, 'salt': 0.0},
        }

        total_cal = 0.0
        total_p = 0.0
        total_f = 0.0
        total_c = 0.0
        total_salt = 0.0

        for entry in entries:
            m_type = entry.meal_type
            if m_type not in meals_dict:
                continue
            for item in entry.items.all():
                item_data = item.to_dict()
                meals_dict[m_type]['items'].append(item_data)
                meals_dict[m_type]['calories'] += item.calories
                meals_dict[m_type]['protein'] += item.protein
                meals_dict[m_type]['fat'] += item.fat
                meals_dict[m_type]['carbs'] += item.carbohydrates
                meals_dict[m_type]['salt'] += item.salt

                total_cal += item.calories
                total_p += item.protein
                total_f += item.fat
                total_c += item.carbohydrates
                total_salt += item.salt

        # PFC比率
        p_cal = total_p * 4.0
        f_cal = total_f * 9.0
        c_cal = total_c * 4.0
        total_pfc_cal = p_cal + f_cal + c_cal

        p_ratio = round((p_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0
        f_ratio = round((f_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0
        c_ratio = round((c_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0

        # あすけん風スコアリング (100点満点)
        score, score_items, advice_text, badge_color = self.calc_health_score(
            total_cal, total_p, total_f, total_c, total_salt,
            p_ratio, f_ratio, c_ratio, meals_dict, profile
        )

        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'weight': self.weight,
            'total_calories': round(total_cal, 1),
            'total_protein': round(total_p, 1),
            'total_fat': round(total_f, 1),
            'total_carbs': round(total_c, 1),
            'total_salt': round(total_salt, 2),
            'pfc_ratios': {
                'p': p_ratio,
                'f': f_ratio,
                'c': c_ratio,
            },
            'target_calories': profile.target_calories,
            'remaining_calories': round(profile.target_calories - total_cal, 1),
            'score': score,
            'score_breakdown': score_items,
            'advice': advice_text,
            'badge_color': badge_color,
            'meals': meals_dict,
        }

    def calc_health_score(self, cal, p, f, c, salt, p_ratio, f_ratio, c_ratio, meals_dict, profile):
        """あすけん風スコア採点アルゴリズム (100点満点) & アドバイス生成"""
        # 食事記録が全くない場合
        if cal == 0:
            return 0, {}, "まだ本日の食事が記録されていません。食べたものを記録してみましょう！", "slate"

        score = 0
        score_breakdown = {}
        advices = []

        # 1. カロリー適合度 (25点満点)
        target = profile.target_calories
        diff_pct = abs(cal - target) / target * 100
        if diff_pct <= 10:
            cal_score = 25
            cal_eval = "適正"
        elif diff_pct <= 20:
            cal_score = 18
            cal_eval = "ほぼ適正"
        elif diff_pct <= 35:
            cal_score = 10
            cal_eval = "過剰/不足"
        else:
            cal_score = 5
            cal_eval = "大幅乖離"
        score += cal_score
        score_breakdown['calorie'] = {'score': cal_score, 'max': 25, 'status': cal_eval}

        if cal > target * 1.15:
            advices.append(f"目標より {cal - target:.0f}kcal 多めでした。次の食事で調整してみましょう。")
        elif cal < target * 0.7:
            advices.append("摂取カロリーが控えめすぎます。無理な減食は代謝低下を招くため、栄養をしっかり補給しましょう。")
        else:
            advices.append("摂取カロリーは理想的なペースです！")

        # 2. PFCバランス適合度 (30点満点: P=10, F=10, C=10)
        pfc_score = 0
        # たんぱく質 (目標20%前後)
        if 13 <= p_ratio <= 28:
            pfc_score += 10
        elif 10 <= p_ratio <= 35:
            pfc_score += 6
        else:
            pfc_score += 2

        # 脂質 (目標25%前後)
        if 18 <= f_ratio <= 30:
            pfc_score += 10
        elif 15 <= f_ratio <= 38:
            pfc_score += 6
            if f_ratio > 30: advices.append("脂質比率がやや高めです。揚げ物やスナックを控えめにするとより良くなります。")
        else:
            pfc_score += 2
            if f_ratio > 38: advices.append("脂質が大幅に過剰です。油物やお菓子の摂取に注意しましょう。")

        # 炭水化物 (目標55%前後)
        if 45 <= c_ratio <= 65:
            pfc_score += 10
        elif 35 <= c_ratio <= 75:
            pfc_score += 6
        else:
            pfc_score += 2
        
        score += pfc_score
        score_breakdown['pfc'] = {'score': pfc_score, 'max': 30, 'p': p_ratio, 'f': f_ratio, 'c': c_ratio}

        # 3. 塩分上限適合度 (20点満点)
        salt_limit = profile.target_salt
        if salt <= salt_limit:
            salt_score = 20
            salt_status = "適正"
        elif salt <= salt_limit * 1.25:
            salt_score = 12
            salt_status = "やや多め"
            advices.append(f"塩分が {salt:.1f}g と少し多めです（目標{salt_limit}g未満）。汁物のつゆを残すなどの工夫が有効です。")
        else:
            salt_score = 5
            salt_status = "過剰"
            advices.append(f"塩分が {salt:.1f}g と高めです。カリウムを含む野菜や海藻を摂って排出を促しましょう。")
        score += salt_score
        score_breakdown['salt'] = {'score': salt_score, 'max': 20, 'status': salt_status}

        # 4. 食事リズム (25点満点: 3食きちんと食べたか)
        rhythm_score = 0
        has_bf = len(meals_dict['breakfast']['items']) > 0
        has_lu = len(meals_dict['lunch']['items']) > 0
        has_dn = len(meals_dict['dinner']['items']) > 0
        
        meals_count = sum([1 for m in [has_bf, has_lu, has_dn] if m])
        if meals_count == 3:
            rhythm_score = 25
        elif meals_count == 2:
            rhythm_score = 16
        else:
            rhythm_score = 8
        score += rhythm_score
        score_breakdown['rhythm'] = {'score': rhythm_score, 'max': 25, 'count': meals_count}

        # スコアに応じたバッジ色
        if score >= 85:
            badge_color = "emerald"
            prefix = "👑 素晴らしい！高得点です。"
        elif score >= 70:
            badge_color = "blue"
            prefix = "👍 なかなか良いバランスです！"
        elif score >= 50:
            badge_color = "amber"
            prefix = "⚠️ 改善の余地があります。"
        else:
            badge_color = "rose"
            prefix = "🚨 栄養バランスの見直しをおすすめします。"

        final_advice = f"{prefix} " + " ".join(advices[:2])
        return score, score_breakdown, final_advice, badge_color


class MealEntry(models.Model):
    MEAL_TYPES = [
        ('breakfast', '朝食'),
        ('lunch', '昼食'),
        ('dinner', '夕食'),
        ('snack', '間食・夜食'),
    ]

    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='meal_entries')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    memo = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "食事区分"
        verbose_name_plural = "食事区分一覧"
        unique_together = ('daily_log', 'meal_type')

    def __str__(self):
        return f"{self.daily_log.date} - {self.get_meal_type_display()}"


class MealItem(models.Model):
    meal_entry = models.ForeignKey(MealEntry, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey('foodscan.FoodItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='logged_meals')
    name = models.CharField(max_length=255, verbose_name="食品・料理名")
    serving_amount = models.FloatField(default=1.0, verbose_name="数量(倍率)")
    serving_unit = models.CharField(max_length=50, default="人前", verbose_name="単位")
    calories = models.FloatField(default=0.0, verbose_name="カロリー(kcal)")
    protein = models.FloatField(default=0.0, verbose_name="たんぱく質(g)")
    fat = models.FloatField(default=0.0, verbose_name="脂質(g)")
    carbohydrates = models.FloatField(default=0.0, verbose_name="炭水化物(g)")
    salt = models.FloatField(default=0.0, verbose_name="食塩相当量(g)")
    image_url = models.URLField(max_length=1000, blank=True, default="", verbose_name="写真URL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "食事品目明細"
        verbose_name_plural = "食事品目明細一覧"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.calories:.0f}kcal)"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'serving_amount': self.serving_amount,
            'serving_unit': self.serving_unit,
            'calories': round(self.calories, 1),
            'protein': round(self.protein, 1),
            'fat': round(self.fat, 1),
            'carbohydrates': round(self.carbohydrates, 1),
            'salt': round(self.salt, 2),
            'image_url': self.image_url,
            'is_scanned': bool(self.food_item_id),
            'barcode': self.food_item.barcode if self.food_item else None,
        }


class GeneralFood(models.Model):
    """一般料理・定番食品プリセットマスタ (初期シード用)"""
    CATEGORY_CHOICES = [
        ('staple', '主食 (ご飯・パン・麺)'),
        ('main', '主菜 (肉・魚・卵・大豆)'),
        ('side', '副菜 (野菜・サラダ・海藻)'),
        ('soup', '汁物 (味噌汁・スープ)'),
        ('udon', 'うどんメニュー (讃岐)'),
        ('snack', '間食・デザート・飲料'),
    ]

    name = models.CharField(max_length=150, unique=True, verbose_name="食品・料理名")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='staple')
    serving_size = models.CharField(max_length=100, default="1人前", verbose_name="目安量")
    calories = models.FloatField(verbose_name="エネルギー(kcal)")
    protein = models.FloatField(default=0.0, verbose_name="たんぱく質(g)")
    fat = models.FloatField(default=0.0, verbose_name="脂質(g)")
    carbohydrates = models.FloatField(default=0.0, verbose_name="炭水化物(g)")
    salt = models.FloatField(default=0.0, verbose_name="食塩相当量(g)")
    icon = models.CharField(max_length=50, default="fa-utensils", verbose_name="アイコン")

    class Meta:
        verbose_name = "一般料理マスタ"
        verbose_name_plural = "一般料理マスタ一覧"
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.calories:.0f}kcal)"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'serving_size': self.serving_size,
            'calories': self.calories,
            'protein': self.protein,
            'fat': self.fat,
            'carbohydrates': self.carbohydrates,
            'salt': self.salt,
            'icon': self.icon,
        }
