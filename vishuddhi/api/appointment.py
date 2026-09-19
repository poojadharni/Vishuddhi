import frappe
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