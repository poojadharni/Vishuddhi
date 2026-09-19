import frappe


# ============================================================
# ADD TO CART
# ============================================================

@frappe.whitelist(allow_guest=True)
def add_to_cart(item_code, qty=1):

    if frappe.session.user == "Guest":
        frappe.throw("Please login to add items to cart")

    if not item_code:
        frappe.throw("Item Code is required")

    try:
        qty = int(qty)

        if qty <= 0:
            qty = 1

        from webshop.webshop.shopping_cart.cart import (
            _get_cart_quotation,
            get_party
        )

        party = get_party()

        quotation = _get_cart_quotation(party)

        if not quotation:
            frappe.throw("Unable to create cart")

        item_found = False

        for item in quotation.items:

            if item.item_code == item_code:

                item.qty = (item.qty or 0) + qty

                item_found = True

                break

        if not item_found:

            quotation.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": qty
                }
            )

        quotation.save(ignore_permissions=True)

        frappe.db.commit()

        cart_count = sum(
            item.qty or 0
            for item in quotation.items
        )

        return {
            "success": True,
            "message": "Item added to cart",
            "cart_count": cart_count
        }

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Add To Cart Error"
        )

        frappe.throw(
            "Unable to add item to cart. Please try again."
        )


# ============================================================
# GET CART COUNT
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_cart_count():

    if frappe.session.user == "Guest":
        return 0

    try:

        from webshop.webshop.shopping_cart.cart import (
            _get_cart_quotation,
            get_party
        )

        party = get_party()

        quotation = _get_cart_quotation(party)

        if not quotation:
            return 0

        if not quotation.get("items"):
            return 0

        return sum(
            item.qty or 0
            for item in quotation.items
        )

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Cart Count Error"
        )

        return 0


# ============================================================
# GET / CREATE USER WISHLIST
# ============================================================

def _get_user_wishlist():

    user = frappe.session.user

    if user == "Guest":
        return None

    wishlist_name = frappe.db.get_value(
        "Wishlist",
        {
            "user": user
        },
        "name"
    )

    if wishlist_name:

        return frappe.get_doc(
            "Wishlist",
            wishlist_name
        )

    # --------------------------------------------------------
    # CREATE WISHLIST FOR USER
    # --------------------------------------------------------

    wishlist = frappe.get_doc(
        {
            "doctype": "Wishlist",
            "user": user
        }
    )

    wishlist.insert(
        ignore_permissions=True
    )

    return wishlist


# ============================================================
# GET WISHLIST COUNT
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_wishlist_count():

    if frappe.session.user == "Guest":
        return 0

    try:

        wishlist = _get_user_wishlist()

        if not wishlist:
            return 0

        return len(
            wishlist.get("items") or []
        )

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Wishlist Count Error"
        )

        return 0


# ============================================================
# CHECK WISHLIST
# ============================================================

@frappe.whitelist(allow_guest=True)
def check_wishlist(item_code):

    if frappe.session.user == "Guest":
        return False

    if not item_code:
        return False

    try:

        wishlist = _get_user_wishlist()

        if not wishlist:
            return False

        for row in wishlist.get("items") or []:

            if row.item_code == item_code:
                return True

        return False

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Check Wishlist Error"
        )

        return False


# ============================================================
# ADD TO WISHLIST
# ============================================================

@frappe.whitelist(allow_guest=True)
def add_to_wishlist(item_code):

    if frappe.session.user == "Guest":
        frappe.throw(
            "Please login to add items to wishlist"
        )

    if not item_code:
        frappe.throw(
            "Item Code is required"
        )

    try:

        # ----------------------------------------------------
        # GET USER WISHLIST
        # ----------------------------------------------------

        wishlist = _get_user_wishlist()

        if not wishlist:
            frappe.throw(
                "Unable to create wishlist"
            )

        # ----------------------------------------------------
        # GET WEBSITE ITEM
        #
        # We get the warehouse from Website Item instead of
        # relying on the frontend.
        # ----------------------------------------------------

        website_item = frappe.db.get_value(
            "Website Item",
            {
                "item_code": item_code,
                "published": 1
            },
            [
                "name",
                "item_code",
                "web_item_name",
                "item_name",
                "item_group",
                "website_image",
                "route",
                "website_warehouse"
            ],
            as_dict=True
        )

        if not website_item:

            frappe.throw(
                "This product is not published on the website"
            )

        # ----------------------------------------------------
        # GET WEBSITE WAREHOUSE
        # ----------------------------------------------------

        warehouse = website_item.get(
            "website_warehouse"
        )

        # ----------------------------------------------------
        # CHECK EXISTING ITEM
        # ----------------------------------------------------

        for row in wishlist.get("items") or []:

            if row.item_code == item_code:

                # ------------------------------------------------
                # IMPORTANT:
                # Update warehouse for existing wishlist items
                # too. This fixes items that were added previously
                # without a warehouse.
                # ------------------------------------------------

                changed = False

                if warehouse and row.warehouse != warehouse:

                    row.warehouse = warehouse
                    changed = True

                # Update other Website Item information if missing
                if not row.website_item:

                    row.website_item = website_item.name
                    changed = True

                if not row.item_name:

                    row.item_name = (
                        website_item.get("item_name")
                        or website_item.get("web_item_name")
                        or item_code
                    )

                    changed = True

                if not row.web_item_name:

                    row.web_item_name = (
                        website_item.get("web_item_name")
                        or website_item.get("item_name")
                        or item_code
                    )

                    changed = True

                if not row.item_group:

                    row.item_group = website_item.get(
                        "item_group"
                    )

                    changed = True

                if not row.image:

                    row.image = website_item.get(
                        "website_image"
                    )

                    changed = True

                if not row.route:

                    row.route = website_item.get(
                        "route"
                    )

                    changed = True

                if changed:

                    wishlist.save(
                        ignore_permissions=True
                    )

                    frappe.db.commit()

                count = len(
                    wishlist.get("items") or []
                )

                return {
                    "success": True,
                    "already_exists": True,
                    "message": "Item already in wishlist",
                    "wishlist_count": count,
                    "warehouse": warehouse
                }

        # ----------------------------------------------------
        # ADD CHILD ROW
        #
        # IMPORTANT:
        # wishlist.append() automatically creates:
        # parent
        # parenttype
        # parentfield
        # idx
        # ----------------------------------------------------

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

                "website_item": website_item.get(
                    "name"
                ),

                # ------------------------------------------------
                # THIS IS THE IMPORTANT FIX
                # ------------------------------------------------

                "warehouse": warehouse,

                "image": website_item.get(
                    "website_image"
                ),

                "item_group": website_item.get(
                    "item_group"
                ),

                "route": website_item.get(
                    "route"
                )
            }
        )

        # ----------------------------------------------------
        # SAVE PARENT WISHLIST
        # ----------------------------------------------------

        wishlist.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        # ----------------------------------------------------
        # UPDATED COUNT
        # ----------------------------------------------------

        count = len(
            wishlist.get("items") or []
        )

        return {
            "success": True,
            "message": "Added to wishlist",
            "wishlist_count": count,
            "warehouse": warehouse
        }

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Add To Wishlist Error"
        )

        frappe.throw(
            "Unable to add item to wishlist. Please try again."
        )


# ============================================================
# REMOVE FROM WISHLIST
# ============================================================

@frappe.whitelist(allow_guest=True)
def remove_from_wishlist(item_code):

    if frappe.session.user == "Guest":
        frappe.throw(
            "Please login to remove items from wishlist"
        )

    if not item_code:
        frappe.throw(
            "Item Code is required"
        )

    try:

        # ----------------------------------------------------
        # GET USER WISHLIST
        # ----------------------------------------------------

        wishlist = _get_user_wishlist()

        if not wishlist:

            return {
                "success": True,
                "message": "Wishlist is empty",
                "wishlist_count": 0
            }

        # ----------------------------------------------------
        # FIND CHILD ROW
        # ----------------------------------------------------

        item_found = False

        for row in list(
            wishlist.get("items") or []
        ):

            if row.item_code == item_code:

                wishlist.remove(row)

                item_found = True

                break

        # ----------------------------------------------------
        # SAVE IF REMOVED
        # ----------------------------------------------------

        if item_found:

            wishlist.save(
                ignore_permissions=True
            )

            frappe.db.commit()

        # ----------------------------------------------------
        # UPDATED COUNT
        # ----------------------------------------------------

        count = len(
            wishlist.get("items") or []
        )

        return {
            "success": True,
            "message": (
                "Removed from wishlist"
                if item_found
                else "Item was not in wishlist"
            ),
            "wishlist_count": count
        }

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Remove From Wishlist Error"
        )

        frappe.throw(
            "Unable to remove item from wishlist. Please try again."
        )