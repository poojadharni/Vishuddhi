import frappe
from frappe import _


@frappe.whitelist()
def get_user_account():

    if frappe.session.user == "Guest":
        return {
            "logged_in": False,
            "message": _("Guest User")
        }

    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)

    # --------------------------
    # Get Customer from Portal User
    # --------------------------
    customer = frappe.db.get_value(
        "Portal User",
        {"user": user},
        "parent"
    )

    # Phone
    phone = user_doc.mobile_no or user_doc.phone or ""

    # Order Count
    order_count = 0
    if customer:
        order_count = frappe.db.count(
            "Sales Order",
            {
                "customer": customer,
                "docstatus": 1
            }
        )

    # --------------------------
    # Customer Address
    # --------------------------
    address_name = ""
    address_title = ""
    city = ""
    pincode = ""

    if customer:

        address = frappe.db.sql("""
            SELECT
                addr.name,
                addr.address_title,
                addr.city,
                addr.pincode
            FROM `tabAddress` addr
            INNER JOIN `tabDynamic Link` dl
                ON dl.parent = addr.name
            WHERE
                dl.link_doctype = 'Customer'
                AND dl.link_name = %s
            LIMIT 1
        """, (customer,), as_dict=True)

        if address:
            address = address[0]

            address_name = address.get("name", "")
            address_title = address.get("address_title", "")
            city = address.get("city", "")
            pincode = address.get("pincode", "")

    return {
        "logged_in": True,
        "user": {
            "full_name": user_doc.full_name or "",
            "email": user_doc.email or "",
            "phone": phone,
            "user_image": user_doc.user_image or "",
            "customer": customer,
            "order_count": order_count,
            "address": {
                "name": address_name,
                "title": address_title,
                "city": city,
                "pincode": pincode
            }
        }
    }