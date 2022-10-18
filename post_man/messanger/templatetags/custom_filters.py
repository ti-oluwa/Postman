from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
import re
from datetime import date, datetime, timedelta
from django.utils import timesince, timezone


register = template.Library()

@register.filter(needs_autoescape=True)
@stringfilter
def mailify(text, autoescape=True):
    """Converts a string to a mailto link"""
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    text = text.split(' ')
    for i, word in enumerate(text, start=0):
        if '@' in word:
            text[i] = '<a href="mailto:%s">%s</a>' % (esc(word), esc(word))
    return mark_safe(' '.join(text))


@register.filter(needs_autoescape=True)
@stringfilter
def telify(text, autoescape=True):
    """NEEDS TO BE FIXED"""
    """Converts a string to a tel link"""
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    text = ' '.join(re.split(r'[\s`,;.]', text))
    for i, word in enumerate(text, start=0):
        if '+' in word and len(word) >= 10 and len(word) <= 20:
            print(word)
            text[i] = '<a href="tel:%s">%s</a>' % (esc(word), esc(word))
    return mark_safe(' '.join(text))

@register.filter(needs_autoescape=True)
@stringfilter
def showHTML5(text, autoescape=True):
    '''Return HTML5'''
    return mark_safe(text)


@register.filter(needs_autoescape=True)
def mytimesincer(date_time: datetime, autoescape=True):
    '''Return Custom Time'''
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    if date_time and isinstance(date_time, datetime):
        now = timezone.now()
        time_delta = max(now - date_time, timedelta(seconds=0))
        time_since = ''
        if time_delta <= timedelta(minutes=1):
            time_since = 'Just Now'
        elif time_delta <= timedelta(days=2) and (now.date().day - date_time.date().day) == 1:
            time_since = 'Yesterday'
        elif time_delta > timedelta(minutes=1) and time_delta < timedelta(days=1):
            time_since = date_time.strftime('%H:%M')
        elif time_delta >= timedelta(days=1) and time_delta < timedelta(days=7):
            time_since = date_time.strftime('%a %d')
        elif time_delta >= timedelta(days=7) and time_delta < timedelta(days=365):
            time_since = date_time.strftime('%d %b')
        elif time_delta >= timedelta(days=365):
            time_since = date_time.strftime('%d %b %Y')
        return mark_safe(time_since)
    return mark_safe(date_time)


# @register.filter(needs_autoescape=True)
# @stringfilter
# def emphasai(text, autoescape=True):
#     '''Emphasizes a string wrapped in double underscores'''
#     if autoescape:
#         esc = conditional_escape
#     else:
#         esc = lambda x: x
#     text = text.split(' ')
#     for i, word in enumerate(text, start=0):
#         if '__' in word:
#             text[i] = '<em>%s</em>' % esc(word)
#     return mark_safe(' '.join(text))


# @register.filter(needs_autoescape=True)
# @stringfilter
# def strongify(text, autoescape=True):
#     '''Bolds a string wrapped in double asterisks'''
#     if autoescape:
#         esc = conditional_escape
#     else:
#         esc = lambda x: x
#     text = text.split(' ')
#     for i, word in enumerate(text, start=0):
#         if '**' in word:
#             text[i] = '<strong>%s</strong>' % esc(word)
#     return mark_safe(' '.join(text))

# @register.filter(needs_autoescape=True)
# @stringfilter
# def strikethrough(text, autoescape=True):
#     '''Strikes through a string wrapped in double asterisks'''
#     if autoescape:
#         esc = conditional_escape
#     else:
#         esc = lambda x: x
#     text = text.split(' ')
#     for i, word in enumerate(text, start=0):
#         if '~~' in word:
#             text[i] = '<strike>%s</strike>' % esc(word)
#     return mark_safe(' '.join(text))