import frappe


# ============================================================
# CART HELPERS
# ============================================================

def _get_cart_count_from_quotation(quotation):
    """Return the total quantity of all items in the cart."""

    if not quotation:
        return 0

    return sum(
        int(item.qty or 0)
        for item in (quotation.get("items") or [])
    )


def _get_current_cart():
    """Get the current Webshop cart quotation."""

    from webshop.webshop.shopping_cart.cart import (
        _get_cart_quotation,
        get_party,
    )

    party = get_party()

    if not party:
        return None

    return _get_cart_quotation(party)


# ============================================================
# ADD TO CART
#
# Use Webshop's standard update_cart method as the only
# cart mutation path. Do not load and save a second copy of
# the same Quotation here.
# ============================================================

@frappe.whitelist()
def add_to_cart(item_code, qty=1):
    if frappe.session.user == "Guest":
        frappe.throw("Please login to add items to cart")

    if not item_code:
        frappe.throw("Item Code is required")

    try:
        qty = int(qty)

        if qty < 1:
            qty = 1

        # Delegate cart mutation to the standard Webshop method.
        from webshop.webshop.shopping_cart.cart import update_cart

        result = update_cart(
            item_code=item_code,
            qty=qty,
            cmd="add",
        )

        # Fetch the latest cart state after the update.
        quotation = _get_current_cart()
        cart_count = _get_cart_count_from_quotation(quotation)

        return {
            "success": True,
            "message": "Item added to cart",
            "cart_count": cart_count,
            "cart": result,
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Add To Cart Error",
        )
        raise


# ============================================================
# GET CART COUNT
# ============================================================

@frappe.whitelist()
def get_cart_count():
    if frappe.session.user == "Guest":
        return 0

    try:
        quotation = _get_current_cart()
        return _get_cart_count_from_quotation(quotation)

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Cart Count Error",
        )
        return 0


# ============================================================
# GET EXISTING USER WISHLIST
#
# Does not create a Wishlist.
# ============================================================

def _get_user_wishlist():
    user = frappe.session.user

    if user == "Guest":
        return None

    wishlist_name = frappe.db.get_value(
        "Wishlist",
        {"user": user},
        "name",
    )

    if not wishlist_name:
        return None

    return frappe.get_doc("Wishlist", wishlist_name)


# ============================================================
# GET WISHLIST COUNT
# ============================================================

@frappe.whitelist()
def get_wishlist_count():
    if frappe.session.user == "Guest":
        return 0

    try:
        wishlist = _get_user_wishlist()

        if not wishlist:
            return 0

        return len(wishlist.get("items") or [])

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Wishlist Count Error",
        )
        return 0


# ============================================================
# CHECK WISHLIST
# ============================================================

@frappe.whitelist()
def check_wishlist(item_code):
    if frappe.session.user == "Guest" or not item_code:
        return False

    try:
        wishlist = _get_user_wishlist()

        if not wishlist:
            return False

        return any(
            row.item_code == item_code
            for row in (wishlist.get("items") or [])
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Check Wishlist Error",
        )
        return False


# ============================================================
# ADD TO WISHLIST
# ============================================================

@frappe.whitelist()
def add_to_wishlist(item_code):
    if frappe.session.user == "Guest":
        frappe.throw("Please login to add items to wishlist")

    if not item_code:
        frappe.throw("Item Code is required")

    try:
        wishlist = _get_user_wishlist()

        if not wishlist:
            frappe.throw(
                "Wishlist is not available for this user. "
                "Please refresh the page and try again."
            )

        website_item = frappe.db.get_value(
            "Website Item",
            {
                "item_code": item_code,
                "published": 1,
            },
            [
                "name",
                "item_code",
                "web_item_name",
                "item_name",
                "item_group",
                "website_image",
                "route",
                "website_warehouse",
            ],
            as_dict=True,
        )

        if not website_item:
            frappe.throw(
                "This product is not published on the website"
            )

        warehouse = website_item.get("website_warehouse")

        # Update an existing wishlist row if needed.
        for row in wishlist.get("items") or []:
            if row.item_code != item_code:
                continue

            values = {
                "warehouse": warehouse,
                "website_item": website_item.name,
                "item_name": (
                    website_item.get("item_name")
                    or website_item.get("web_item_name")
                    or item_code
                ),
                "web_item_name": (
                    website_item.get("web_item_name")
                    or website_item.get("item_name")
                    or item_code
                ),
                "item_group": website_item.get("item_group"),
                "image": website_item.get("website_image"),
                "route": website_item.get("route"),
            }

            changed = False

            for field, value in values.items():
                if value and row.get(field) != value:
                    row.set(field, value)
                    changed = True

            if changed:
                wishlist.save(ignore_permissions=True)

            return {
                "success": True,
                "already_exists": True,
                "message": "Item already in wishlist",
                "wishlist_count": len(wishlist.get("items") or []),
                "warehouse": warehouse,
            }

        # Add a new row to the existing wishlist.
        wishlist.append(
            "items",
            {
                "item_code": item_code,
                "item_name": (
                    website_item.get("item_name")
                    or website_item.get("web_item_name")
                    or item_code
                ),
                "web_item_name": (
                    website_item.get("web_item_name")
                    or website_item.get("item_name")
                    or item_code
                ),
                "website_item": website_item.name,
                "warehouse": warehouse,
                "image": website_item.get("website_image"),
                "item_group": website_item.get("item_group"),
                "route": website_item.get("route"),
            },
        )

        wishlist.save(ignore_permissions=True)

        return {
            "success": True,
            "message": "Added to wishlist",
            "wishlist_count": len(wishlist.get("items") or []),
            "warehouse": warehouse,
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Add To Wishlist Error",
        )
        raise


# ============================================================
# REMOVE FROM WISHLIST
# ============================================================

@frappe.whitelist()
def remove_from_wishlist(item_code):
    if frappe.session.user == "Guest":
        frappe.throw("Please login to remove items from wishlist")

    if not item_code:
        frappe.throw("Item Code is required")

    try:
        wishlist = _get_user_wishlist()

        if not wishlist:
            return {
                "success": True,
                "message": "Wishlist is empty",
                "wishlist_count": 0,
            }

        item_found = False

        for row in list(wishlist.get("items") or []):
            if row.item_code == item_code:
                wishlist.remove(row)
                item_found = True
                break

        if item_found:
            wishlist.save(ignore_permissions=True)

        return {
            "success": True,
            "message": (
                "Removed from wishlist"
                if item_found
                else "Item was not in wishlist"
            ),
            "wishlist_count": len(wishlist.get("items") or []),
        }

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Remove From Wishlist Error",
        )
        raise

