
import frappe


def sync_website_item(doc, method=None):
    """Create or update a Website Item when an Item is published."""

    if not doc.published_in_website:
        return

    # Find an existing Website Item linked to this Item.
    website_item_name = frappe.db.get_value(
        "Website Item",
        {"item_code": doc.name},
        "name",
    )

    if website_item_name:
        website_item = frappe.get_doc(
            "Website Item", website_item_name
        )
    else:
        website_item = frappe.new_doc("Website Item")

    # Link to the existing Item.
    website_item.item_code = doc.name
    website_item.published = 1

    # Copy variant information where applicable.
    if doc.meta.has_field("has_variants"):
        website_item.has_variants = doc.has_variants

    if doc.meta.has_field("variant_of") and doc.variant_of:
        parent_website_item = frappe.db.get_value(
            "Website Item",
            {"item_code": doc.variant_of},
            "name",
        )

        if parent_website_item:
            website_item.variant_of = parent_website_item

    # Let the Website Item controller populate other fields.
    if website_item_name:
        website_item.save(ignore_permissions=True)
    else:
        website_item.insert(ignore_permissions=True)
