import frappe

@frappe.whitelist(allow_guest=True)
def get_promotion_videos():

    videos = frappe.get_all(
        "Promotion Videos",
        filters={"is_active": 1},
        fields=[
            "name",
            "order_sequence",
            "upload_videos"
        ],
        order_by="order_sequence asc"
    )

    return {
        "data": videos
    }