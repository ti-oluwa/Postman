from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
import re


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
    """Converts a string to a tel link"""
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    text = re.split(r'[\s`,;.]', text)
    for i, word in enumerate(text, start=0):
        if '+' in word and len(word) >= 10:
            text[i] = '<a href="tel:%s">%s</a>' % (esc(word), esc(word))
    return mark_safe(' '.join(text))


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