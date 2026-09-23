import frappe
from frappe import _
from datetime import datetime, timedelta


# ============================================================
# HELPER: CONVERT TIME TO SECONDS
# ============================================================

def _time_to_seconds(value):

    value = str(value)

    try:
        parts = value.split(":")

        hours = int(parts[0])
        minutes = int(parts[1])

        seconds = 0

        if len(parts) > 2:
            seconds = int(float(parts[2]))

        return (
            hours * 3600
            + minutes * 60
            + seconds
        )

    except Exception:

        frappe.throw(
            f"Invalid time value: {value}"
        )


# ============================================================
# HELPER: GET TIME IN SECONDS
# ============================================================

def _get_time_seconds(value):

    if value is None:
        return None

    if hasattr(
        value,
        "total_seconds"
    ):

        return int(
            value.total_seconds()
        )

    return _time_to_seconds(value)


# ============================================================
# GET AVAILABLE APPOINTMENT SLOTS
#
# Frontend sends:
#
# ?day=Monday
# ?day=Tuesday
#
# Availability is recurring weekly.
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_available_slots(day=None):

    # --------------------------------------------------------
    # Validate day
    # --------------------------------------------------------

    if not day:

        frappe.throw(
            "Day is required"
        )

    day = str(
        day
    ).strip().capitalize()

    valid_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    if day not in valid_days:

        frappe.throw(
            "Invalid day. Expected Monday, Tuesday, Wednesday, "
            "Thursday, Friday, Saturday or Sunday."
        )

    # --------------------------------------------------------
    # Get recurring availability
    # --------------------------------------------------------

    availability = frappe.db.get_value(
        "User Appointment Availability",
        "Administrator",
        [
            "name",
            "enable_scheduling",
            "slug"
        ],
        as_dict=True
    )

    if not availability:

        return []

    # --------------------------------------------------------
    # Check scheduling enabled
    # --------------------------------------------------------

    if not availability.enable_scheduling:

        return []

    # --------------------------------------------------------
    # Get configured time ranges
    # --------------------------------------------------------

    time_slots = frappe.get_all(
        "Appointment Time Slot",
        filters={
            "parent": availability.name,
            "parenttype": "User Appointment Availability",
            "day": day
        },
        fields=[
            "day",
            "start_time",
            "end_time"
        ],
        order_by="start_time asc"
    )

    if not time_slots:

        return []

    slots = []

    # --------------------------------------------------------
    # Generate 30-minute slots
    # --------------------------------------------------------

    for row in time_slots:

        if row.start_time is None:
            continue

        if row.end_time is None:
            continue

        start_seconds = _get_time_seconds(
            row.start_time
        )

        end_seconds = _get_time_seconds(
            row.end_time
        )

        if start_seconds is None:
            continue

        if end_seconds is None:
            continue

        if end_seconds <= start_seconds:
            continue

        # ----------------------------------------------------
        # Convert seconds to datetime
        # ----------------------------------------------------

        current = (
            datetime.min
            + timedelta(
                seconds=start_seconds
            )
        )

        end_dt = (
            datetime.min
            + timedelta(
                seconds=end_seconds
            )
        )

        # ----------------------------------------------------
        # Generate 30-minute intervals
        # ----------------------------------------------------

        while current < end_dt:

            slot_end = (
                current
                + timedelta(
                    minutes=30
                )
            )

            # Only complete 30-minute slots
            if slot_end <= end_dt:

                slots.append(
                    {
                        "day": day,

                        "time": current.strftime(
                            "%H:%M:%S"
                        ),

                        "label": current.strftime(
                            "%I:%M %p"
                        )
                    }
                )

            current = slot_end

    return slots


# ============================================================
# BOOK APPOINTMENT
#
# Creates ERPNext Appointment.
#
# NO EMAIL IS SENT.
#
# Actual Appointment fields:
#
# scheduled_time
# status
# created_through_portal
# customer_name
# customer_phone_number
# customer_email
# customer_details
# ============================================================

@frappe.whitelist(allow_guest=True)
def book_appointment(
    date=None,
    time=None,
    name=None,
    email=None,
    phone=None,
    subject=None,
    message=None
):

    # --------------------------------------------------------
    # Validate required fields
    # --------------------------------------------------------

    if not date:

        frappe.throw(
            "Date is required"
        )

    if not time:

        frappe.throw(
            "Time is required"
        )

    if not name:

        frappe.throw(
            "Name is required"
        )

    if not email:

        frappe.throw(
            "Email is required"
        )

    if not phone:

        frappe.throw(
            "Phone is required"
        )

    # --------------------------------------------------------
    # Clean values
    # --------------------------------------------------------

    date = str(date).strip()
    time = str(time).strip()
    name = str(name).strip()
    email = str(email).strip()
    phone = str(phone).strip()

    if subject:

        subject = str(
            subject
        ).strip()

    if message:

        message = str(
            message
        ).strip()

    # --------------------------------------------------------
    # Validate date/time format
    # --------------------------------------------------------

    try:

        scheduled_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        frappe.throw(
            "Invalid date or time format. "
            "Expected date YYYY-MM-DD and time HH:MM:SS."
        )

    # --------------------------------------------------------
    # Prevent booking in the past
    # --------------------------------------------------------

    if scheduled_datetime <= datetime.now():

        frappe.throw(
            "Please select a future date and time."
        )

    # --------------------------------------------------------
    # Determine weekday
    # --------------------------------------------------------

    selected_day = (
        scheduled_datetime.strftime(
            "%A"
        )
    )

    # --------------------------------------------------------
    # Get appointment availability
    # --------------------------------------------------------

    availability = frappe.db.get_value(
        "User Appointment Availability",
        "Administrator",
        [
            "name",
            "enable_scheduling",
            "slug"
        ],
        as_dict=True
    )

    if not availability:

        frappe.throw(
            "Appointment scheduling is not configured."
        )

    # --------------------------------------------------------
    # Check scheduling enabled
    # --------------------------------------------------------

    if not availability.enable_scheduling:

        frappe.throw(
            "Appointment scheduling is currently disabled."
        )

    # --------------------------------------------------------
    # Get configured availability for weekday
    # --------------------------------------------------------

    configured_slots = frappe.get_all(
        "Appointment Time Slot",
        filters={
            "parent": availability.name,
            "parenttype": "User Appointment Availability",
            "day": selected_day
        },
        fields=[
            "start_time",
            "end_time"
        ],
        order_by="start_time asc"
    )

    if not configured_slots:

        frappe.throw(
            f"Appointments are not available on {selected_day}."
        )

    # --------------------------------------------------------
    # Convert requested time to seconds
    # --------------------------------------------------------

    selected_seconds = (
        scheduled_datetime.hour * 3600
        + scheduled_datetime.minute * 60
        + scheduled_datetime.second
    )

    # --------------------------------------------------------
    # Validate selected 30-minute slot
    # --------------------------------------------------------

    selected_slot_is_valid = False

    for row in configured_slots:

        if row.start_time is None:
            continue

        if row.end_time is None:
            continue

        start_seconds = _get_time_seconds(
            row.start_time
        )

        end_seconds = _get_time_seconds(
            row.end_time
        )

        if start_seconds is None:
            continue

        if end_seconds is None:
            continue

        # ----------------------------------------------------
        # Selected slot must:
        #
        # 1. Start inside configured range
        # 2. Have full 30 minutes available
        # 3. Start exactly on 30-minute boundary
        # ----------------------------------------------------

        if (
            selected_seconds >= start_seconds
            and
            selected_seconds + 1800 <= end_seconds
            and
            selected_seconds % 1800 == 0
        ):

            selected_slot_is_valid = True

            break

    if not selected_slot_is_valid:

        frappe.throw(
            "The selected time is not an available appointment slot."
        )

    # --------------------------------------------------------
    # Prevent duplicate booking
    # --------------------------------------------------------

    existing_appointment = frappe.db.exists(
        "Appointment",
        {
            "scheduled_time": scheduled_datetime,

            "status": [
                "in",
                [
                    "Open",
                    "Unverified"
                ]
            ]
        }
    )

    if existing_appointment:

        frappe.throw(
            "This appointment slot has already been booked. "
            "Please select another time."
        )

    # --------------------------------------------------------
    # Prepare customer details
    # --------------------------------------------------------

    customer_details = (
        "Appointment booked through website."
    )

    if subject:

        customer_details = (
            f"Subject: {subject}"
        )

    if message:

        if subject:

            customer_details += (
                f"\n\nMessage: {message}"
            )

        else:

            customer_details = (
                f"Message: {message}"
            )

    # --------------------------------------------------------
    # Create Appointment document
    # --------------------------------------------------------

    appointment = frappe.new_doc(
        "Appointment"
    )

    appointment.scheduled_time = (
        scheduled_datetime
    )

    appointment.status = "Open"

    appointment.created_through_portal = 1

    appointment.customer_name = name

    appointment.customer_phone_number = phone

    appointment.customer_email = email

    appointment.customer_details = (
        customer_details
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # ERPNext Appointment.after_insert()
    # automatically calls send_confirmation_email().
    #
    # We do NOT want that for this website booking.
    # --------------------------------------------------------

    original_after_insert = getattr(
        appointment,
        "after_insert",
        None
    )

    try:

        appointment.after_insert = (
            lambda: None
        )

        appointment.insert(
            ignore_permissions=True
        )

    finally:

        if original_after_insert:

            appointment.after_insert = (
                original_after_insert
            )

    # --------------------------------------------------------
    # Commit database transaction
    # --------------------------------------------------------

    frappe.db.commit()

    # --------------------------------------------------------
    # Return success
    # --------------------------------------------------------

    return {
        "success": True,

        "name": appointment.name,

        "scheduled_time": (
            scheduled_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ),

        "message": (
            "Appointment booked successfully."
        )
    }


# ============================================================
# CONTACT US
#
# Sends Contact Us form directly to:
#
# vishuddhihomegardens@gmail.com
#
# NO DocType is created.
# ============================================================

@frappe.whitelist(allow_guest=True)
def send_contact_message(
    name=None,
    email=None,
    phone=None,
    source=None,
    message=None
):

    # --------------------------------------------------------
    # Clean input
    # --------------------------------------------------------

    name = (name or "").strip()
    email = (email or "").strip()
    phone = (phone or "").strip()
    source = (
        source or "Website Contact Form"
    ).strip()
    message = (message or "").strip()

    # --------------------------------------------------------
    # Validate name
    # --------------------------------------------------------

    if not name:

        frappe.throw(
            _("Please enter your name.")
        )

    if len(name) < 2:

        frappe.throw(
            _("Name must contain at least 2 characters.")
        )

    # --------------------------------------------------------
    # Validate email
    # --------------------------------------------------------

    if not email:

        frappe.throw(
            _("Please enter your email address.")
        )

    if not frappe.utils.validate_email_address(
        email
    ):

        frappe.throw(
            _("Please enter a valid email address.")
        )

    # --------------------------------------------------------
    # Validate message
    # --------------------------------------------------------

    if not message:

        frappe.throw(
            _("Please enter your message.")
        )

    if len(message) < 5:

        frappe.throw(
            _("Please enter at least 5 characters.")
        )

    # --------------------------------------------------------
    # Validate phone
    #
    # Phone is optional.
    # If entered, it must be a valid
    # 10-digit Indian mobile number.
    # --------------------------------------------------------

    if phone:

        phone = "".join(
            character
            for character in phone
            if character.isdigit()
        )

        if (
            len(phone) != 10
            or phone[0] not in "6789"
        ):

            frappe.throw(
                _(
                    "Please enter a valid "
                    "10-digit Indian mobile number."
                )
            )

    # --------------------------------------------------------
    # Email subject
    # --------------------------------------------------------

    email_subject = (
        f"New Contact Us Message - {name}"
    )

    # --------------------------------------------------------
    # Safely escape user input
    #
    # Prevents HTML entered by the visitor
    # from being interpreted as email HTML.
    # --------------------------------------------------------

    import html

    safe_name = html.escape(name)
    safe_email = html.escape(email)
    safe_phone = html.escape(
        phone or "Not provided"
    )
    safe_source = html.escape(source)
    safe_message = html.escape(message)

    # --------------------------------------------------------
    # Email HTML
    # --------------------------------------------------------

    email_message = f"""
    <div style="
        font-family: Arial, sans-serif;
        max-width: 700px;
        margin: 0 auto;
        color: #183126;
    ">

        <div style="
            background: #203b27;
            color: #ffffff;
            padding: 22px 25px;
            border-radius: 10px 10px 0 0;
        ">

            <h2 style="margin:0;">
                New Contact Us Message
            </h2>

            <p style="
                margin:8px 0 0;
                color:#dcebdd;
            ">
                Vishuddhi Plants Website
            </p>

        </div>

        <div style="
            padding: 25px;
            border: 1px solid #dfe9e1;
            border-top: 0;
            border-radius: 0 0 10px 10px;
        ">

            <table style="
                width:100%;
                border-collapse:collapse;
            ">

                <tr>
                    <td style="
                        padding:10px 0;
                        font-weight:bold;
                        width:140px;
                    ">
                        Name
                    </td>

                    <td style="padding:10px 0;">
                        {safe_name}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:10px 0;
                        font-weight:bold;
                    ">
                        Email
                    </td>

                    <td style="padding:10px 0;">
                        <a href="mailto:{safe_email}">
                            {safe_email}
                        </a>
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:10px 0;
                        font-weight:bold;
                    ">
                        Phone
                    </td>

                    <td style="padding:10px 0;">
                        {safe_phone}
                    </td>
                </tr>

                <tr>
                    <td style="
                        padding:10px 0;
                        font-weight:bold;
                    ">
                        Source
                    </td>

                    <td style="padding:10px 0;">
                        {safe_source}
                    </td>
                </tr>

            </table>

            <hr style="
                border:0;
                border-top:1px solid #dfe9e1;
                margin:20px 0;
            ">

            <h3 style="
                color:#203b27;
                margin-bottom:10px;
            ">
                Message
            </h3>

            <div style="
                background:#f5faf5;
                border:1px solid #dfe9e1;
                border-radius:8px;
                padding:15px;
                white-space:pre-wrap;
                line-height:1.6;
            ">
                {safe_message}
            </div>

        </div>

    </div>
    """

    # --------------------------------------------------------
    # SEND EMAIL
    #
    # This sends directly to the Vishuddhi Gmail address.
    # No Contact document is created.
    # --------------------------------------------------------

    frappe.sendmail(
        recipients=[
            "poojarajuhe@gmail.com"
        ],
        subject=email_subject,
        message=email_message,
        # now=True
    )

    # --------------------------------------------------------
    # Return success
    # --------------------------------------------------------

    return {
        "success": True,
        "message": (
            "Your message has been sent successfully."
        )
    }