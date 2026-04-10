from django import template

register = template.Library()


@register.filter
def label_for_cat(code, code_to_label):
    """Look up the human-readable label for an arXiv category code.

    Usage:  {{ cat_code|label_for_cat:code_to_label }}
    """
    if isinstance(code_to_label, dict):
        return code_to_label.get(code, code)
    return code
