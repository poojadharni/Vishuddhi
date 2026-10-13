
import frappe
from frappe.utils import flt


def create_item_records(item_code):
    """
    Create or update Website Item and Item Price.
    Use Item.valuation_rate for the Standard Selling Item Price.
    Create opening stock only once per item and company.
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
        website_item.web_item_name = item.item_name or item.name
        website_item.published = 1

        if item.get("item_group"):
            website_item.item_group = item.item_group

        if item.get("stock_uom"):
            website_item.stock_uom = item.stock_uom

        if item.get("description"):
            website_item.description = item.description

        website_item.save(ignore_permissions=True)

    # --------------------------------------------------
    # 2. CREATE OR UPDATE ITEM PRICE FROM VALUATION RATE
    # --------------------------------------------------
    valuation_rate = flt(item.get("valuation_rate"))

    if valuation_rate > 0:
        price_list = "Standard Selling"

        if not frappe.db.exists("Price List", price_list):
            frappe.throw(
                f"Price List '{price_list}' does not exist."
            )

        price_name = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item.name,
                "price_list": price_list,
                "selling": 1,
            },
            "name",
        )

        if price_name:
            price = frappe.get_doc("Item Price", price_name)
        else:
            price = frappe.new_doc("Item Price")
            price.item_code = item.name
            price.price_list = price_list
            price.selling = 1

        price.price_list_rate = valuation_rate
        price.save(ignore_permissions=True)

    # --------------------------------------------------
    # 3. CREATE OPENING STOCK ONLY ONCE
    # --------------------------------------------------
    opening_qty = flt(item.get("opening_stock"))

    # A template item is not a stock-bearing variant.
    if opening_qty > 0 and item.get("has_variants"):
        frappe.logger("vishuddhi").warning(
            f"Opening stock skipped for template item {item.name}. "
            "Set opening stock on the child variant instead."
        )

    elif opening_qty > 0:
        if not item.get("is_stock_item"):
            frappe.throw(
                f"{item.name} must have Maintain Stock enabled "
                "before opening stock can be created."
            )

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

        opening_reference = f"Opening stock for {item.name}"

        # Check submitted or draft receipts for this exact item,
        # company and opening-stock reference.
        existing_entry = frappe.db.sql(
            """
            SELECT DISTINCT se.name
            FROM `tabStock Entry` se
            INNER JOIN `tabStock Entry Detail` sed
                ON sed.parent = se.name
            WHERE se.docstatus IN (0, 1)
              AND se.purpose = 'Material Receipt'
              AND se.company = %s
              AND se.remarks = %s
              AND sed.item_code = %s
            LIMIT 1
            """,
            (company, opening_reference, item.name),
            as_dict=True,
        )

        if not existing_entry:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Receipt"
            stock_entry.company = company
            stock_entry.set_posting_time = 1
            stock_entry.remarks = opening_reference

            stock_entry.append(
                "items",
                {
                    "item_code": item.name,
                    "qty": opening_qty,
                    "t_warehouse": warehouse,
                    "basic_rate": valuation_rate,
                },
            )

            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()

    return {
        "status": "success",
        "item_code": item.name,
        "valuation_rate": valuation_rate,
        "message": "Item records processed successfully.",
    }


@frappe.whitelist()
def create_item_records_from_hook(doc, method=None):
    """
    Hook called when an Item is inserted or updated.
    """
    return create_item_records(doc.name)
