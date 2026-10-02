import frappe

from frappe.www.login import get_context as frappe_get_context


def get_context(context):
    context = frappe_get_context(context)

    context.vishuddhi_logo = "/files/Vishuddhi-logo.png"
    context.vishuddhi_name = "Vishuddhi Home Garden"

    return context