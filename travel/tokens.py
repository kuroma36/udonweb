from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """たびしお本登録用ワンタイムトークン生成器"""
    def _make_hash_value(self, user, timestamp):
        profile = getattr(user, 'travel_profile', None)
        is_verified = profile.is_email_verified if profile else False
        return f"{user.pk}{timestamp}{is_verified}{user.is_active}"


account_activation_token = AccountActivationTokenGenerator()
