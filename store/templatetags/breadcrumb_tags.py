from django import template
from django.utils.text import capfirst

register = template.Library()


def humanize_segment(segment):
    if not segment:
        return ''
    label = segment.replace('-', ' ').replace('_', ' ')
    return capfirst(label)


@register.simple_tag(takes_context=True)
def auto_breadcrumbs(context):
    request = context.get('request')
    if not request:
        return []

    path = request.path.strip('/')
    if not path:
        return [{'label': 'Trang chủ', 'url': '/'}]

    parts = path.split('/')
    breadcrumbs = [{'label': 'Trang chủ', 'url': '/'}]
    current_path = ''

    for index, part in enumerate(parts):
        current_path += '/' + part
        label = humanize_segment(part)
        if index == len(parts) - 1:
            breadcrumbs.append({'label': label, 'url': ''})
        else:
            breadcrumbs.append({'label': label, 'url': current_path + '/'})

    return breadcrumbs
