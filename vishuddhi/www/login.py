import frappe

from frappe.www.login import get_context as frappe_get_context


def get_context(context):
    """
    Use Frappe's standard login context so all built-in authentication
    features continue to work:

    - Username/email login
    - Signup
    - Forgot password
    - Google/social login
    - Email login link
    - LDAP login
    - Frappe Cloud login
    """

    # Get all standard Frappe login context variables.
    context = frappe_get_context(context)

    # ---------------------------------------------------------
    # VISHUDDHI BRANDING
    # ---------------------------------------------------------

    context.vishuddhi_logo = "/files/Vishuddhi-logo.png"
    context.vishuddhi_name = "Vishuddhi Home Garden"

    # These are also used by parts of the standard Frappe
    # login template/context.
    context.logo = "/files/Vishuddhi-logo.png"
    context.app_name = "Vishuddhi Home Garden"

    return context