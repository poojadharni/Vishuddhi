import frappe

@frappe.whitelist(allow_guest=True)
def get_banner_image():
    banner = frappe.get_all(
        "Banner image",
        fields=["banner_image"],
        limit=1
    )

    return banner[0] if banner else {}