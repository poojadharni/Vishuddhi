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

        # ----------------------------------------------------
        # GET CUSTOMER / PARTY FROM WEBSHOP
        # ----------------------------------------------------

        party = get_party()

        if not party:
            frappe.throw("Unable to identify customer")

        # ----------------------------------------------------
        # GET / CREATE CART QUOTATION
        # ----------------------------------------------------

        quotation = _get_cart_quotation(party)

        if not quotation:
            frappe.throw("Unable to create cart")

        # ----------------------------------------------------
        # CHECK WHETHER ITEM ALREADY EXISTS
        # ----------------------------------------------------

        item_found = False

        for item in quotation.items:

            if item.item_code == item_code:

                item.qty = (item.qty or 0) + qty
                item_found = True
                break

        # ----------------------------------------------------
        # ADD NEW ITEM
        # ----------------------------------------------------

        if not item_found:

            quotation.append(
                "items",
                {
                    "item_code": item_code,
                    "qty": qty
                }
            )

        # ----------------------------------------------------
        # SAVE CART
        # ----------------------------------------------------

        quotation.save(ignore_permissions=True)

        frappe.db.commit()

        # ----------------------------------------------------
        # CART COUNT
        # ----------------------------------------------------

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

        if not party:
            return 0

        quotation = _get_cart_quotation(party)

        if not quotation:
            return 0

        items = quotation.get("items") or []

        return sum(
            item.qty or 0
            for item in items
        )

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            "Vishuddhi Cart Count Error"
        )

        return 0


# ============================================================
# GET EXISTING USER WISHLIST
#
# IMPORTANT:
# This function DOES NOT create a Wishlist.
#
# Frappe/Webshop is responsible for creating the Wishlist.
# This function only retrieves the existing Wishlist.
# ============================================================

def _get_user_wishlist():

    user = frappe.session.user

    if user == "Guest":
        return None

    # --------------------------------------------------------
    # FIND EXISTING WISHLIST
    # --------------------------------------------------------

    wishlist_name = frappe.db.get_value(
        "Wishlist",
        {
            "user": user
        },
        "name"
    )

    # --------------------------------------------------------
    # NO WISHLIST
    #
    # Do NOT create one here.
    # --------------------------------------------------------

    if not wishlist_name:
        return None

    # --------------------------------------------------------
    # RETURN EXISTING WISHLIST
    # --------------------------------------------------------

    return frappe.get_doc(
        "Wishlist",
        wishlist_name
    )


# ============================================================
# GET WISHLIST COUNT
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_wishlist_count():

    if frappe.session.user == "Guest":
        return 0

    try:

        wishlist = _get_user_wishlist()

        # ----------------------------------------------------
        # Wishlist has not been created yet
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # No Wishlist yet
        # ----------------------------------------------------

        if not wishlist:
            return False

        # ----------------------------------------------------
        # CHECK ITEMS
        # ----------------------------------------------------

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
        # GET EXISTING WISHLIST
        #
        # This DOES NOT create a Wishlist.
        # ----------------------------------------------------

        wishlist = _get_user_wishlist()

        if not wishlist:

            frappe.throw(
                "Wishlist is not available for this user. "
                "Please refresh the page and try again."
            )

        # ----------------------------------------------------
        # GET WEBSITE ITEM
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
        # CHECK IF ITEM ALREADY EXISTS
        # ----------------------------------------------------

        for row in wishlist.get("items") or []:

            if row.item_code == item_code:

                changed = False

                # ------------------------------------------------
                # UPDATE WAREHOUSE
                # ------------------------------------------------

                if warehouse and row.warehouse != warehouse:

                    row.warehouse = warehouse
                    changed = True

                # ------------------------------------------------
                # UPDATE WEBSITE ITEM
                # ------------------------------------------------

                if not row.website_item:

                    row.website_item = website_item.name
                    changed = True

                # ------------------------------------------------
                # UPDATE ITEM NAME
                # ------------------------------------------------

                if not row.item_name:

                    row.item_name = (
                        website_item.get("item_name")
                        or website_item.get("web_item_name")
                        or item_code
                    )

                    changed = True

                # ------------------------------------------------
                # UPDATE WEB ITEM NAME
                # ------------------------------------------------

                if not row.web_item_name:

                    row.web_item_name = (
                        website_item.get("web_item_name")
                        or website_item.get("item_name")
                        or item_code
                    )

                    changed = True

                # ------------------------------------------------
                # UPDATE ITEM GROUP
                # ------------------------------------------------

                if not row.item_group:

                    row.item_group = website_item.get(
                        "item_group"
                    )

                    changed = True

                # ------------------------------------------------
                # UPDATE IMAGE
                # ------------------------------------------------

                if not row.image:

                    row.image = website_item.get(
                        "website_image"
                    )

                    changed = True

                # ------------------------------------------------
                # UPDATE ROUTE
                # ------------------------------------------------

                if not row.route:

                    row.route = website_item.get(
                        "route"
                    )

                    changed = True

                # ------------------------------------------------
                # SAVE ONLY IF SOMETHING CHANGED
                # ------------------------------------------------

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

        # ====================================================
        # ADD ITEM TO EXISTING WISHLIST
        # ====================================================

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
        # SAVE EXISTING WISHLIST
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
        # GET EXISTING WISHLIST
        #
        # This DOES NOT create one.
        # ----------------------------------------------------

        wishlist = _get_user_wishlist()

        if not wishlist:

            return {
                "success": True,
                "message": "Wishlist is empty",
                "wishlist_count": 0
            }

        # ----------------------------------------------------
        # FIND ITEM
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
