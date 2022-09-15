from django import template

register = template.Library()

@register.simple_tag
def ownership(project, user):
    return project.added_by_user == user