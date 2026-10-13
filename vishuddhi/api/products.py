import frappe


# ============================================================
# PRODUCT ROUTE
# ============================================================

def get_product_route(item_code):
    """Get Website Item route."""

    route = frappe.db.get_value(
        "Website Item",
        {"item_code": item_code},
        "route"
    )

    return route or ""


# ============================================================
# PRODUCT PRICE
# ============================================================

def get_product_price(item_code):
    """Get Standard Selling price."""

    price = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item_code,
            "price_list": "Standard Selling",
            "selling": 1
        },
        "price_list_rate"
    )

    return price or 0


# ============================================================
# BESTSELLER FIELD
# ============================================================

def _get_bestseller_field():
    """
    Get Bestseller checkbox field.

    Current fieldname:
        bestsellers
    """

    meta = frappe.get_meta("Item")

    if meta.has_field("bestsellers"):
        return "bestsellers"

    return None


# ============================================================
# ITEM FIELDS
# ============================================================

def _get_item_fields():
    """
    Return Item fields used by Vishuddhi webshop.
    """

    meta = frappe.get_meta("Item")

    fields = [
        "name",
        "item_name",
        "item_group",
        "image",
        "description",
    ]

    optional_fields = [

        # ----------------------------------------------------
        # EXISTING SHOP BY CATEGORY CHECKBOXES
        # ----------------------------------------------------

        "indoor",
        "outdoor",
        "flowering",
        "pots",
        "garden_essentials",
        "seeds",

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        "terrace",
        "garden",

        # ----------------------------------------------------
        # SUNLIGHT
        # ----------------------------------------------------

        "low",
        "medium",
        "high",

        # ----------------------------------------------------
        # CARE
        # ----------------------------------------------------

        "easy",
        "moderate",
        "advanced",

        # ----------------------------------------------------
        # PURPOSE
        # ----------------------------------------------------

        "air_purifying",
        "decorative",
        "fruit",
        "vegetable",
        "low_maintenance",

        # ----------------------------------------------------
        # BESTSELLER
        # ----------------------------------------------------

        "bestsellers",

        # ----------------------------------------------------
        # OPTIONAL CUSTOM FIELDS
        # ----------------------------------------------------

        "custom_location",
        "custom_sunlight",
        "custom_care",
        "custom_purpose",
    ]

    for field in optional_fields:

        if (
            meta.has_field(field)
            and field not in fields
        ):
            fields.append(field)

    return fields


# ============================================================
# ADD CATEGORY INFORMATION
# ============================================================

def _add_categories(item):
    """
    Existing custom checkbox based categories.

    These are kept for your existing filters and
    bestseller category functionality.
    """

    categories = []

    if item.get("indoor"):
        categories.append("Indoor Plants")

    if item.get("outdoor"):
        categories.append("Outdoor Plants")

    if item.get("flowering"):
        categories.append("Flowering Plants")

    if item.get("pots"):
        categories.append("Pots")

    if item.get("garden_essentials"):
        categories.append("Garden Essentials")

    if item.get("seeds"):
        categories.append("Seeds")

    item["categories"] = categories

    return item


# ============================================================
# ADD DISCOVERY DATA
# ============================================================

def _add_discovery_data(item):

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    location = []

    if item.get("indoor"):
        location.append("indoor")

    if item.get("outdoor"):
        location.append("outdoor")

    if item.get("terrace"):
        location.append("terrace")

    if item.get("garden"):
        location.append("garden")

    item["location"] = location

    # --------------------------------------------------------
    # SUNLIGHT
    # --------------------------------------------------------

    sunlight = []

    if item.get("low"):
        sunlight.append("low")

    if item.get("medium"):
        sunlight.append("medium")

    if item.get("high"):
        sunlight.append("high")

    item["sunlight"] = sunlight

    # --------------------------------------------------------
    # CARE
    # --------------------------------------------------------

    care = []

    if item.get("easy"):
        care.append("easy")

    if item.get("moderate"):
        care.append("moderate")

    if item.get("advanced"):
        care.append("advanced")

    item["care"] = care

    # --------------------------------------------------------
    # PURPOSE
    # --------------------------------------------------------

    purpose = []

    if item.get("air_purifying"):
        purpose.append("air_purifying")

    if item.get("decorative"):
        purpose.append("decorative")

    if item.get("fruit"):
        purpose.append("fruit")

    if item.get("vegetable"):
        purpose.append("vegetable")

    if item.get("low_maintenance"):
        purpose.append("low_maintenance")

    item["purpose"] = purpose

    return item


# ============================================================
# PREPARE PRODUCT
# ============================================================

def _prepare_product(item, bestseller_field=None):

    item["price"] = get_product_price(
        item["name"]
    )

    item["route"] = get_product_route(
        item["name"]
    )

    # Existing checkbox categories
    _add_categories(item)

    # Existing Smart Plant Discovery data
    _add_discovery_data(item)

    # Bestseller
    if bestseller_field:

        item["is_bestseller"] = bool(
            item.get(bestseller_field)
        )

    else:

        item["is_bestseller"] = False

    return item


# ============================================================
# COMMON PRODUCT QUERY
# ============================================================

def _get_products(filters=None, limit=100, include_templates=False):
    """
    Fetch enabled Items.

    include_templates=True:
        Include parent template Items (has_variants=1) and normal Items.
        Used by All Products and category listings.

    include_templates=False:
        Keep the previous behavior for bestseller listings by excluding
        parent templates.
    """

    item_filters = {"disabled": 0}

    if not include_templates:
        item_filters["has_variants"] = 0

    discovery_checkbox_fields = {
        "indoor", "outdoor", "flowering", "pots",
        "garden_essentials", "seeds", "terrace", "garden",
        "low", "medium", "high", "easy", "moderate", "advanced",
        "air_purifying", "decorative", "fruit", "vegetable",
        "low_maintenance",
    }

    # When templates are included, discovery/category flags may live only
    # on their variants. Apply these filters after merging variant flags.
    deferred_filters = {}
    if filters:
        for key, value in filters.items():
            if include_templates and key in discovery_checkbox_fields:
                deferred_filters[key] = value
            else:
                item_filters[key] = value

    fields = _get_item_fields()
    meta = frappe.get_meta("Item")

    for field in ("has_variants", "variant_of"):
        if meta.has_field(field) and field not in fields:
            fields.append(field)

    products = frappe.get_all(
        "Item",
        filters=item_filters,
        fields=fields,
        order_by="creation desc",
        # Fetch enough rows before applying deferred filters so a template
        # is not omitted just because its own checkbox is empty.
        limit_page_length=0 if deferred_filters else limit,
    )

    # Template Items often have no discovery checkboxes of their own.
    # Merge checkbox values from their enabled variants so Smart Discover
    # can match and display the parent template too.
    if include_templates:
        _merge_variant_discovery_data(products, fields)

    if deferred_filters:
        products = [
            item for item in products
            if all(item.get(field) == value for field, value in deferred_filters.items())
        ]
        if limit:
            products = products[:limit]

    bestseller_field = _get_bestseller_field()

    for item in products:
        _prepare_product(item, bestseller_field)

    return products


def _merge_variant_discovery_data(products, item_fields=None):
    """Merge discovery/category checkbox values from variants into templates."""

    if not products:
        return

    template_names = [
        item.get("name")
        for item in products
        if item.get("has_variants")
    ]

    if not template_names:
        return

    meta = frappe.get_meta("Item")
    checkbox_fields = [
        field for field in (
            "indoor", "outdoor", "flowering", "pots",
            "garden_essentials", "seeds",
            "terrace", "garden",
            "low", "medium", "high",
            "easy", "moderate", "advanced",
            "air_purifying", "decorative", "fruit",
            "vegetable", "low_maintenance",
        )
        if meta.has_field(field)
    ]

    if not checkbox_fields:
        return

    variant_fields = ["name", "variant_of"] + checkbox_fields

    variants = frappe.get_all(
        "Item",
        filters={
            "disabled": 0,
            "variant_of": ["in", template_names],
        },
        fields=variant_fields,
        limit_page_length=0,
    )

    templates_by_name = {
        item.get("name"): item
        for item in products
        if item.get("has_variants")
    }

    for variant in variants:
        template = templates_by_name.get(variant.get("variant_of"))
        if not template:
            continue

        for field in checkbox_fields:
            if variant.get(field):
                template[field] = 1


# ============================================================
# ALL PRODUCTS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_products():
    """Return regular Items and parent templates for the All Products page."""
    return _get_products(
        limit=1000,
        include_templates=True,
    )


# ============================================================
# BESTSELLERS / POPULAR PICKS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_bestsellers():

    bestseller_field = _get_bestseller_field()

    if not bestseller_field:
        return []

    products = _get_products(
        filters={
            bestseller_field: 1
        },
        limit=100
    )

    for item in products:
        item["is_bestseller"] = True

    return products


# ============================================================
# BESTSELLER CATEGORIES
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_bestseller_categories():

    bestseller_field = _get_bestseller_field()

    if not bestseller_field:
        return []

    products = _get_products(
        filters={
            bestseller_field: 1
        },
        limit=1000
    )

    category_set = set()

    for item in products:

        for category in item.get(
            "categories",
            []
        ):

            category_set.add(category)

    return sorted(
        list(category_set)
    )


# ============================================================
# EXISTING CUSTOM CATEGORY FIELD MAPPING
# ============================================================

CATEGORY_FIELDS = {

    "Indoor Plants":
        "indoor",

    "Outdoor Plants":
        "outdoor",

    "Flowering Plants":
        "flowering",

    "Pots":
        "pots",

    "Garden Essentials":
        "garden_essentials",

    "Seeds":
        "seeds",
}


# ============================================================
# GET PRODUCTS BY EXISTING CUSTOM CATEGORY
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_products_by_category(category=None):

    if not category:
        return []

    category = str(category).strip()

    fieldname = CATEGORY_FIELDS.get(
        category
    )

    if not fieldname:
        return []

    return _get_products(
        filters={
            fieldname: 1
        },
        limit=1000,
        include_templates=True,
    )


# ============================================================
# SHOP BY CATEGORY
# ERPNext ITEM GROUPS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_item_groups():
    """
    Get ERPNext Item Groups for Shop by Category.

    Uses the actual Item Group records instead of the
    custom Item checkbox fields.

    Example result:

        Flowering Plants
        Indoor Plants
        Outdoor Plants

    "All Item Groups" is always excluded.
    """

    meta = frappe.get_meta("Item Group")

    # -----------------------------------------------
    # Fields
    # -----------------------------------------------

    fields = [
        "name"
    ]

    if meta.has_field("route"):
        fields.append("route")

    if meta.has_field("image"):
        fields.append("image")

    # -----------------------------------------------
    # Website filter
    # -----------------------------------------------

    if meta.has_field("show_in_website"):

        filters = {
            "show_in_website": 1
        }

    else:

        filters = {}

    # -----------------------------------------------
    # Get Item Groups
    # -----------------------------------------------

    groups = frappe.get_all(
        "Item Group",
        filters=filters,
        fields=fields,
        order_by="name asc",
        limit_page_length=100
    )

    result = []

    # -----------------------------------------------
    # Prepare response
    # -----------------------------------------------

    for group in groups:

        group_name = group.get("name")

        # Never show root Item Group
        if group_name == "All Item Groups":
            continue

        result.append({
            "name": group_name,
            "route": group.get("route") or "",
            "image": group.get("image") or ""
        })

    return result


# ============================================================
# GET PRODUCTS BY ERPNext ITEM GROUP
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_products_by_item_group(item_group=None):
    """
    Get products using the actual ERPNext Item Group.

    This does NOT replace get_products_by_category().
    Both systems remain available.
    """

    if not item_group:
        return []

    item_group = str(
        item_group
    ).strip()

    # -----------------------------------------------
    # Check Item Group exists
    # -----------------------------------------------

    if not frappe.db.exists(
        "Item Group",
        item_group
    ):
        return []

    # -----------------------------------------------
    # Get products
    # -----------------------------------------------

    return _get_products(
        filters={
            "item_group": item_group
        },
        limit=1000,
        include_templates=True,
    )