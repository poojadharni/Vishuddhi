import frappe

from frappe.www.login import get_context as frappe_get_context


def get_context(context):
    """
    Vishuddhi custom login context.

    Frappe's standard login context is retained so that all
    built-in authentication features continue to work.
    """

    context = frappe_get_context(context)

    # Vishuddhi branding
    context.vishuddhi_logo = "/files/Vishuddhi-logo.png"
    context.vishuddhi_name = "Vishuddhi Home Garden"

    # Standard Frappe branding variables
    context.logo = "/files/Vishuddhi-logo.png"
    context.app_name = "Vishuddhi Home Garden"

    return context