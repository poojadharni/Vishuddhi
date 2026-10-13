
import frappe
from frappe.utils import flt


@frappe.whitelist()
def create_item_records(item_code):
    """
    Create or update Website Item and Item Price.
    Create an opening Stock Entry when opening stock is supplied.
    """

    if not item_code:
        frappe.throw("Item Code is required.")

    item = frappe.get_doc("Item", item_code)

    # --------------------------------------------------
    # 1. CREATE OR UPDATE WEBSITE ITEM
    # --------------------------------------------------
    if item.get("published_in_website"):
        website_item_name = frappe.db.get_value(
            "Website Item",
            {"item_code": item.name},
            "name",
        )

        if website_item_name:
            website_item = frappe.get_doc(
                "Website Item", website_item_name
            )
        else:
            website_item = frappe.new_doc("Website Item")

        website_item.item_code = item.name
        website_item.web_item_name = (
            item.get("item_name") or item.name
        )
        website_item.published = 1

        if item.get("item_group"):
            website_item.item_group = item.item_group

        if item.get("stock_uom"):
            website_item.stock_uom = item.stock_uom

        if item.get("description"):
            website_item.description = item.description

        website_item.save(ignore_permissions=True)

    # --------------------------------------------------
    # 2. CREATE OR UPDATE ITEM PRICE
    # --------------------------------------------------
    selling_rate = flt(item.get("custom_selling_rate"))

    if selling_rate > 0:
        price_list = "Standard Selling"

        if not frappe.db.exists("Price List", price_list):
            frappe.throw(
                f"Price List '{price_list}' does not exist."
            )

        existing_price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item.name,
                "price_list": price_list,
                "selling": 1,
            },
            "name",
        )

        if existing_price:
            price = frappe.get_doc(
                "Item Price", existing_price
            )
        else:
            price = frappe.new_doc("Item Price")
            price.item_code = item.name
            price.price_list = price_list
            price.selling = 1

        price.price_list_rate = selling_rate
        price.save(ignore_permissions=True)

    # --------------------------------------------------
    # 3. CREATE OPENING STOCK ENTRY
    # --------------------------------------------------
    opening_qty = flt(item.get("opening_stock"))

    if opening_qty > 0:
        if not item.get("is_stock_item"):
            frappe.throw(
                f"{item.name} is not configured as a stock item."
            )

        # Prefer the item's configured company.
        company = frappe.db.get_value(
            "Item Default",
            {"parent": item.name},
            "company",
        )

        if not company:
            company = frappe.defaults.get_user_default("Company")

        if not company:
            frappe.throw(
                "Set a default Company before creating opening stock."
            )

        warehouse = frappe.db.get_value(
            "Item Default",
            {
                "parent": item.name,
                "company": company,
            },
            "default_warehouse",
        )

        if not warehouse:
            frappe.throw(
                f"Set Default Warehouse for {item.name} "
                f"under company {company} in Item Defaults."
            )

        if not frappe.db.exists("Warehouse", warehouse):
            frappe.throw(
                f"Warehouse '{warehouse}' does not exist."
            )

        # Check for an existing submitted opening-stock receipt
        # for this item before creating another one.
        existing_stock_entry = frappe.db.sql(
            """
            SELECT DISTINCT se.name
            FROM `tabStock Entry` se
            INNER JOIN `tabStock Entry Detail` sed
                ON sed.parent = se.name
            WHERE se.docstatus = 1
                AND se.purpose = 'Material Receipt'
                AND se.company = %s
                AND se.remarks LIKE %s
                AND sed.item_code = %s
            LIMIT 1
            """,
            (
                company,
                f"%Opening stock for {item.name}%",
                item.name,
            ),
            as_dict=True,
        )

        if not existing_stock_entry:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Receipt"
            stock_entry.company = company
            stock_entry.set_posting_time = 1
            stock_entry.remarks = (
                f"Opening stock for {item.name}"
            )

            stock_entry.append(
                "items",
                {
                    "item_code": item.name,
                    "qty": opening_qty,
                    "t_warehouse": warehouse,
                    "basic_rate": flt(
                        item.get("valuation_rate")
                    ),
                },
            )

            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()

    # Do not commit here.
    # Frappe manages the transaction for the document hook.

    return {
        "status": "success",
        "item_code": item.name,
        "message": "Item records processed successfully.",
    }


def create_item_records_from_hook(doc, method=None):
    """
    Called automatically when an Item is saved.
    """
    create_item_records(doc.name)
