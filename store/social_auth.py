from django.contrib.auth.models import User


def associate_by_email(strategy, details, user=None, social=None, *args, **kwargs):
    """Associate existing account by matching email for social auth."""
    email = (details.get('email') or '').strip().lower()
    if not email:
        response = kwargs.get('response') or {}
        email = (response.get('email') or '').strip().lower()
    if not email:
        return None

    existing = User.objects.filter(email__iexact=email).first()
    if not existing:
        return None

    if user and user.id == existing.id:
        return None

    if social and social.user_id != existing.id:
        social.user = existing
        social.save(update_fields=['user'])
        return {'user': existing, 'is_new': False}

    if not user:
        return {'user': existing, 'is_new': False}

    return None
