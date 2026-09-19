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

    Your current fieldname is:
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
    Return Item fields used by the webshop.

    These use the actual fieldnames configured
    in the Item DocType.
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
        # SHOP BY CATEGORY
        # ----------------------------------------------------

        "indoor",
        "outdoor",
        "flowering",
        "pots",
        "garden_essentials",
        "seeds",

        # ----------------------------------------------------
        # WHERE WILL IT LIVE
        # ----------------------------------------------------

        "terrace",
        "garden",

        # ----------------------------------------------------
        # HOW MUCH SUNLIGHT
        # ----------------------------------------------------

        "low",
        "medium",
        "high",

        # ----------------------------------------------------
        # HOW MUCH CARE
        # ----------------------------------------------------

        "easy",
        "moderate",
        "advanced",

        # ----------------------------------------------------
        # WHAT DO YOU WANT
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
        # OPTIONAL PRODUCT INFORMATION
        # ----------------------------------------------------

        "custom_location",
        "custom_sunlight",
        "custom_care",
        "custom_purpose",
    ]

    for field in optional_fields:

        if meta.has_field(field) and field not in fields:
            fields.append(field)

    return fields


# ============================================================
# ADD CATEGORY INFORMATION
# ============================================================

def _add_categories(item):
    """
    Build category list from independent checkbox fields.

    A product can belong to MULTIPLE categories.

    Example:

        indoor = 1
        flowering = 1

    Result:

        [
            "Indoor Plants",
            "Flowering Plants"
        ]
    """

    categories = []

    # --------------------------------------------------------
    # INDOOR
    # --------------------------------------------------------

    if item.get("indoor"):
        categories.append("Indoor Plants")

    # --------------------------------------------------------
    # OUTDOOR
    # --------------------------------------------------------

    if item.get("outdoor"):
        categories.append("Outdoor Plants")

    # --------------------------------------------------------
    # FLOWERING
    # --------------------------------------------------------

    if item.get("flowering"):
        categories.append("Flowering Plants")

    # --------------------------------------------------------
    # POTS
    # --------------------------------------------------------

    if item.get("pots"):
        categories.append("Pots")

    # --------------------------------------------------------
    # GARDEN ESSENTIALS
    # --------------------------------------------------------

    if item.get("garden_essentials"):
        categories.append("Garden Essentials")

    # --------------------------------------------------------
    # SEEDS
    # --------------------------------------------------------

    if item.get("seeds"):
        categories.append("Seeds")

    item["categories"] = categories

    return item


# ============================================================
# ADD PLANT DISCOVERY DATA
# ============================================================

def _add_discovery_data(item):
    """
    Add normalized Smart Plant Discovery values.

    The frontend can use these values if needed.
    """

    # --------------------------------------------------------
    # WHERE WILL IT LIVE
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
    # WHAT DO YOU WANT
    # --------------------------------------------------------

    purpose = []

    if item.get("air_purifying"):
        purpose.append("air_purifying")

    if item.get("flowering"):
        purpose.append("flowering")

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
# ADD COMMON PRODUCT DATA
# ============================================================

def _prepare_product(item, bestseller_field=None):
    """
    Add price, route, categories, discovery data,
    and bestseller status.
    """

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    item["price"] = get_product_price(
        item["name"]
    )

    # --------------------------------------------------------
    # WEBSITE ROUTE
    # --------------------------------------------------------

    item["route"] = get_product_route(
        item["name"]
    )

    # --------------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------------

    _add_categories(item)

    # --------------------------------------------------------
    # DISCOVERY DATA
    # --------------------------------------------------------

    _add_discovery_data(item)

    # --------------------------------------------------------
    # BESTSELLER
    # --------------------------------------------------------

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

def _get_products(filters=None, limit=100):
    """
    Get active Item products.

    Additional filters are applied directly
    in the backend.
    """

    item_filters = {
        "disabled": 0,
        "has_variants": 0
    }

    if filters:
        item_filters.update(filters)

    fields = _get_item_fields()

    products = frappe.get_all(
        "Item",
        filters=item_filters,
        fields=fields,
        order_by="creation desc",
        limit_page_length=limit
    )

    bestseller_field = _get_bestseller_field()

    for item in products:
        _prepare_product(
            item,
            bestseller_field
        )

    return products


# ============================================================
# ALL PRODUCTS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_products():
    """
    Return all active webshop products.
    """

    return _get_products(
        limit=100
    )


# ============================================================
# BESTSELLERS / POPULAR PICKS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_bestsellers():
    """
    Return ONLY products where:

        bestsellers = 1

    Used by Popular Picks.
    """

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
    """
    Return categories containing Bestseller products.

    A Bestseller can belong to multiple categories.
    """

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
# CATEGORY FIELD MAPPING
# ============================================================

CATEGORY_FIELDS = {
    "Indoor Plants": "indoor",
    "Outdoor Plants": "outdoor",
    "Flowering Plants": "flowering",
    "Pots": "pots",
    "Garden Essentials": "garden_essentials",
    "Seeds": "seeds",
}


# ============================================================
# GET PRODUCTS BY CATEGORY
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_products_by_category(category=None):
    """
    Get ALL active products belonging to the selected
    Shop by Category.

    IMPORTANT:

    This does NOT restrict the result to Bestsellers.

    Examples:

        Indoor Plants
            -> indoor = 1

        Outdoor Plants
            -> outdoor = 1

        Flowering Plants
            -> flowering = 1

        Pots
            -> pots = 1

        Garden Essentials
            -> garden_essentials = 1

        Seeds
            -> seeds = 1
    """

    if not category:
        return []

    category = str(category).strip()

    fieldname = CATEGORY_FIELDS.get(category)

    if not fieldname:
        return []

    return _get_products(
        filters={
            fieldname: 1
        },
        limit=100
    )


# ============================================================
# SMART PLANT DISCOVERY
# ============================================================

@frappe.whitelist(allow_guest=True)
def find_plants(
    location=None,
    sunlight=None,
    care=None,
    purpose=None
):
    """
    Smart Plant Discovery.

    Supports multiple filters.

    FILTER LOGIC
    ------------

    Different groups = AND

        location + sunlight + care + purpose

    Same group = OR

        indoor OR outdoor
        low OR medium
        easy OR moderate
        decorative OR flowering

    Example:

        Indoor
        Low sunlight
        Easy care
        Decorative

    Result:

        indoor = 1
        AND
        low = 1
        AND
        easy = 1
        AND
        decorative = 1

    Only matching products are returned.
    """

    # --------------------------------------------------------
    # NORMALIZE INPUT
    # --------------------------------------------------------

    location_values = _normalize_filter_values(
        location
    )

    sunlight_values = _normalize_filter_values(
        sunlight
    )

    care_values = _normalize_filter_values(
        care
    )

    purpose_values = _normalize_filter_values(
        purpose
    )

    # --------------------------------------------------------
    # VALID FILTER FIELDS
    # --------------------------------------------------------

    location_fields = {
        "indoor",
        "outdoor",
        "terrace",
        "garden"
    }

    sunlight_fields = {
        "low",
        "medium",
        "high"
    }

    care_fields = {
        "easy",
        "moderate",
        "advanced"
    }

    purpose_fields = {
        "air_purifying",
        "flowering",
        "decorative",
        "fruit",
        "vegetable",
        "low_maintenance"
    }

    # --------------------------------------------------------
    # CLEAN INVALID VALUES
    # --------------------------------------------------------

    location_values = [
        value
        for value in location_values
        if value in location_fields
    ]

    sunlight_values = [
        value
        for value in sunlight_values
        if value in sunlight_fields
    ]

    care_values = [
        value
        for value in care_values
        if value in care_fields
    ]

    purpose_values = [
        value
        for value in purpose_values
        if value in purpose_fields
    ]

    # --------------------------------------------------------
    # GET ALL ACTIVE PRODUCTS
    # --------------------------------------------------------

    products = _get_products(
        limit=1000
    )

    # --------------------------------------------------------
    # APPLY SMART FILTERS
    # --------------------------------------------------------

    result = []

    for item in products:

        # ====================================================
        # LOCATION GROUP
        # ====================================================

        if location_values:

            location_match = False

            for field in location_values:

                if item.get(field):
                    location_match = True
                    break

            if not location_match:
                continue

        # ====================================================
        # SUNLIGHT GROUP
        # ====================================================

        if sunlight_values:

            sunlight_match = False

            for field in sunlight_values:

                if item.get(field):
                    sunlight_match = True
                    break

            if not sunlight_match:
                continue

        # ====================================================
        # CARE GROUP
        # ====================================================

        if care_values:

            care_match = False

            for field in care_values:

                if item.get(field):
                    care_match = True
                    break

            if not care_match:
                continue

        # ====================================================
        # PURPOSE GROUP
        # ====================================================

        if purpose_values:

            purpose_match = False

            for field in purpose_values:

                if item.get(field):
                    purpose_match = True
                    break

            if not purpose_match:
                continue

        # ====================================================
        # PRODUCT MATCHED
        # ====================================================

        result.append(item)

    return result


# ============================================================
# NORMALIZE FILTER VALUES
# ============================================================

def _normalize_filter_values(value):
    """
    Convert frontend filter input into a list.

    Supports:

        "indoor"

        "indoor,outdoor"

        ["indoor", "outdoor"]

        JSON array:
        ["indoor", "outdoor"]
    """

    if not value:
        return []

    # --------------------------------------------------------
    # ALREADY LIST / TUPLE
    # --------------------------------------------------------

    if isinstance(value, (list, tuple)):
        values = list(value)

    else:

        value = str(value).strip()

        if not value:
            return []

        # ----------------------------------------------------
        # JSON ARRAY
        # ----------------------------------------------------

        if value.startswith("[") and value.endswith("]"):

            try:
                import json

                parsed = json.loads(value)

                if isinstance(parsed, list):
                    values = parsed
                else:
                    values = [value]

            except Exception:
                values = [
                    value
                ]

        # ----------------------------------------------------
        # COMMA SEPARATED
        # ----------------------------------------------------

        elif "," in value:

            values = [
                x.strip()
                for x in value.split(",")
                if x.strip()
            ]

        # ----------------------------------------------------
        # SINGLE VALUE
        # ----------------------------------------------------

        else:
            values = [
                value
            ]

    # --------------------------------------------------------
    # CLEAN VALUES
    # --------------------------------------------------------

    return [
        str(x).strip()
        for x in values
        if str(x).strip()
    ]