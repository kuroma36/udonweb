from django.db import models

class FoodItem(models.Model):
    SOURCE_CHOICES = [
        ('openfoodfacts', 'Open Food Facts'),
        ('user', 'ユーザー登録'),
        ('manual', '手動登録'),
    ]

    barcode = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="バーコード(JAN/EAN)")
    name = models.CharField(max_length=255, verbose_name="商品名")
    brand = models.CharField(max_length=255, blank=True, default="", verbose_name="メーカー・ブランド")
    category = models.CharField(max_length=255, blank=True, default="", verbose_name="カテゴリ")
    image_url = models.URLField(max_length=1000, blank=True, default="", verbose_name="商品画像URL")
    
    # 栄養成分 (原則100gまたは1包装あたり)
    serving_size = models.CharField(max_length=100, blank=True, default="100g", verbose_name="内容量/基準単位")
    calories = models.FloatField(null=True, blank=True, verbose_name="エネルギー (kcal)")
    protein = models.FloatField(null=True, blank=True, verbose_name="たんぱく質 (g)")
    fat = models.FloatField(null=True, blank=True, verbose_name="脂質 (g)")
    carbohydrates = models.FloatField(null=True, blank=True, verbose_name="炭水化物 (g)")
    sugar = models.FloatField(null=True, blank=True, verbose_name="糖質 (g)")
    fiber = models.FloatField(null=True, blank=True, verbose_name="食物繊維 (g)")
    salt = models.FloatField(null=True, blank=True, verbose_name="食塩相当量 (g)")
    
    ingredients = models.TextField(blank=True, default="", verbose_name="原材料名")
    allergens = models.CharField(max_length=500, blank=True, default="", verbose_name="アレルゲン (カンマ区切り)")
    
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='openfoodfacts', verbose_name="データ取得元")
    scan_count = models.PositiveIntegerField(default=1, verbose_name="スキャン回数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        verbose_name = "食品データ"
        verbose_name_plural = "食品データ一覧"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.barcode})"

    def to_dict(self):
        # PFC比率計算 (P: 4kcal/g, F: 9kcal/g, C: 4kcal/g)
        p = self.protein or 0.0
        f = self.fat or 0.0
        c = self.carbohydrates or 0.0
        p_cal = p * 4.0
        f_cal = f * 9.0
        c_cal = c * 4.0
        total_pfc_cal = p_cal + f_cal + c_cal
        
        pfc = {
            "p_cal": round(p_cal, 1),
            "f_cal": round(f_cal, 1),
            "c_cal": round(c_cal, 1),
            "p_ratio": round((p_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0,
            "f_ratio": round((f_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0,
            "c_ratio": round((c_cal / total_pfc_cal * 100), 1) if total_pfc_cal > 0 else 0,
        }

        # アレルゲンリスト
        allergen_list = [a.strip() for a in self.allergens.split(',') if a.strip()] if self.allergens else []

        return {
            "id": self.id,
            "barcode": self.barcode,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "image_url": self.image_url,
            "serving_size": self.serving_size,
            "calories": self.calories,
            "protein": self.protein,
            "fat": self.fat,
            "carbohydrates": self.carbohydrates,
            "sugar": self.sugar,
            "fiber": self.fiber,
            "salt": self.salt,
            "pfc": pfc,
            "ingredients": self.ingredients,
            "allergens": allergen_list,
            "source": self.get_source_display(),
            "scan_count": self.scan_count,
            "updated_at": self.updated_at.strftime('%Y-%m-%d %H:%M'),
        }


class ScanLog(models.Model):
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name="scan_logs", verbose_name="対象食品")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IPアドレス")
    user_agent = models.TextField(blank=True, default="", verbose_name="User-Agent")
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name="スキャン日時")

    class Meta:
        verbose_name = "スキャン履歴"
        verbose_name_plural = "スキャン履歴一覧"
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.food_item.name} at {self.scanned_at.strftime('%Y-%m-%d %H:%M')}"
