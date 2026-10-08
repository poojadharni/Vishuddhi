
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

    if hasattr(value, "total_seconds"):

        return int(
            value.total_seconds()
        )

    return _time_to_seconds(value)


# ============================================================
# HELPER: GET APPOINTMENT BOOKING SETTINGS
#
# SOURCE:
# Appointment Booking Settings
#
# This is the ONLY source for:
#
# - Appointment Duration
# - Availability Of Slots
# - Number Of Concurrent Appointments
# - Holiday List
# - Advance Booking
# ============================================================

def _get_booking_settings():

    settings = frappe.get_single(
        "Appointment Booking Settings"
    )

    if not settings:

        frappe.throw(
            "Appointment Booking Settings could not be found."
        )

    # --------------------------------------------------------
    # Check scheduling enabled
    # --------------------------------------------------------

    if not settings.enable_scheduling:

        frappe.throw(
            "Appointment scheduling is currently disabled."
        )

    # --------------------------------------------------------
    # Appointment Duration
    # --------------------------------------------------------

    try:

        appointment_duration = int(
            settings.appointment_duration or 0
        )

    except (TypeError, ValueError):

        appointment_duration = 0

    if appointment_duration <= 0:

        frappe.throw(
            "Please configure a valid Appointment Duration "
            "(In Minutes) in Appointment Booking Settings."
        )

    return (
        settings,
        appointment_duration
    )


# ============================================================
# HELPER: GET CONFIGURED AVAILABILITY GROUPS
#
# Example:
#
# Tuesday
#   Group 1 = 10:00 - 13:00
#   Group 2 = 15:00 - 19:00
#
# Every row in Availability Of Slots is treated as ONE
# independent booking group.
# ============================================================

def _get_configured_groups(day):

    settings, appointment_duration = (
        _get_booking_settings()
    )

    groups = []

    availability_rows = (
        settings.get("availability_of_slots") or []
    )

    for index, row in enumerate(
        availability_rows,
        start=1
    ):

        row_day = (
            row.get("day_of_week")
            if hasattr(row, "get")
            else getattr(
                row,
                "day_of_week",
                None
            )
        )

        if not row_day:
            continue

        row_day = str(
            row_day
        ).strip().capitalize()

        if row_day != day:
            continue

        from_time = (
            row.get("from_time")
            if hasattr(row, "get")
            else getattr(
                row,
                "from_time",
                None
            )
        )

        to_time = (
            row.get("to_time")
            if hasattr(row, "get")
            else getattr(
                row,
                "to_time",
                None
            )
        )

        if from_time is None:
            continue

        if to_time is None:
            continue

        start_seconds = _get_time_seconds(
            from_time
        )

        end_seconds = _get_time_seconds(
            to_time
        )

        if start_seconds is None:
            continue

        if end_seconds is None:
            continue

        if end_seconds <= start_seconds:
            continue

        groups.append(
            {
                "group": len(groups) + 1,
                "day": row_day,
                "from_time": str(from_time),
                "to_time": str(to_time),
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
            }
        )

    groups.sort(
        key=lambda row: row[
            "start_seconds"
        ]
    )

    # Re-number after sorting

    for index, group in enumerate(
        groups,
        start=1
    ):

        group["group"] = index

    return (
        settings,
        appointment_duration,
        groups
    )


# ============================================================
# HELPER: GET DATETIME RANGE FOR A GROUP
# ============================================================

def _get_group_datetime_range(
    selected_date,
    group
):

    start_seconds = group[
        "start_seconds"
    ]

    end_seconds = group[
        "end_seconds"
    ]

    start_datetime = (
        datetime.combine(
            selected_date,
            datetime.min.time()
        )
        + timedelta(
            seconds=start_seconds
        )
    )

    end_datetime = (
        datetime.combine(
            selected_date,
            datetime.min.time()
        )
        + timedelta(
            seconds=end_seconds
        )
    )

    return (
        start_datetime,
        end_datetime
    )


# ============================================================
# HELPER: CHECK WHETHER A GROUP IS ALREADY BOOKED
#
# If ANY appointment exists inside the group:
#
# 10:00 - 13:00
#
# the whole group becomes unavailable.
#
# Group 2:
#
# 15:00 - 19:00
#
# remains available.
# ============================================================

def _is_group_booked(
    selected_date,
    group
):

    start_datetime, end_datetime = (
        _get_group_datetime_range(
            selected_date,
            group
        )
    )

    appointments = frappe.get_all(
        "Appointment",
        filters={
            "scheduled_time": [
                "between",
                [
                    start_datetime,
                    end_datetime
                ]
            ],
            "status": [
                "in",
                [
                    "Open",
                    "Unverified"
                ]
            ]
        },
        fields=[
            "name",
            "scheduled_time",
            "status"
        ],
        limit=1
    )

    return bool(
        appointments
    )


# ============================================================
# HELPER: FIND GROUP FOR SELECTED TIME
# ============================================================

def _find_group_for_time(
    selected_seconds,
    groups,
    appointment_duration
):

    duration_seconds = (
        appointment_duration * 60
    )

    for group in groups:

        start_seconds = group[
            "start_seconds"
        ]

        end_seconds = group[
            "end_seconds"
        ]

        # ----------------------------------------------------
        # Selected time must be inside group
        # and have enough duration remaining.
        # ----------------------------------------------------

        if (
            selected_seconds >= start_seconds
            and
            selected_seconds + duration_seconds
            <= end_seconds
        ):

            # ------------------------------------------------
            # Must align exactly with appointment duration.
            # ------------------------------------------------

            if (
                (
                    selected_seconds
                    - start_seconds
                )
                % duration_seconds
                == 0
            ):

                return group

    return None


# ============================================================
# HELPER: CHECK HOLIDAY
# ============================================================

def _is_holiday(
    settings,
    selected_date
):

    holiday_list = settings.get(
        "holiday_list"
    )

    if not holiday_list:
        return False

    try:

        holiday_exists = frappe.db.exists(
            "Holiday",
            {
                "parent": holiday_list,
                "parenttype": "Holiday List",
                "holiday_date": selected_date
            }
        )

        return bool(
            holiday_exists
        )

    except Exception:

        return False


# ============================================================
# HELPER: CHECK ADVANCE BOOKING LIMIT
# ============================================================

def _check_advance_booking_limit(
    settings,
    selected_date
):

    advance_booking_days = settings.get(
        "advance_booking_days"
    )

    try:

        advance_booking_days = int(
            advance_booking_days or 0
        )

    except (TypeError, ValueError):

        advance_booking_days = 0

    if advance_booking_days <= 0:
        return

    today = frappe.utils.getdate(
        frappe.utils.nowdate()
    )

    selected_date = frappe.utils.getdate(
        selected_date
    )

    max_date = (
        today
        + timedelta(
            days=advance_booking_days
        )
    )

    if selected_date > max_date:

        frappe.throw(
            "Appointments can only be booked "
            f"up to {advance_booking_days} days in advance."
        )


# ============================================================
# GET AVAILABLE APPOINTMENT SLOTS
#
# PRIMARY FRONTEND API:
#
# ?date=2026-10-09
#
# The API automatically converts:
#
# 2026-10-09
#       ↓
# Friday
#
# Then it loads Friday's availability.
#
# BACKWARD COMPATIBILITY:
#
# ?day=Tuesday
#
# Also supported.
#
# OPTIONAL:
#
# ?day=Tuesday&date=2026-10-06
#
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_available_slots(
    day=None,
    date=None
):

    # ========================================================
    # 1. DATE IS THE PRIMARY INPUT
    # ========================================================

    selected_date = None

    if date:

        try:

            selected_date = frappe.utils.getdate(
                date
            )

        except Exception:

            frappe.throw(
                "Invalid date. Expected YYYY-MM-DD."
            )

        # ----------------------------------------------------
        # Automatically determine weekday
        # ----------------------------------------------------

        actual_day = selected_date.strftime(
            "%A"
        )

        # ----------------------------------------------------
        # DATE ALWAYS TAKES PRIORITY
        #
        # Example:
        #
        # date=2026-10-09
        #
        # automatically becomes:
        #
        # Friday
        # ----------------------------------------------------

        day = actual_day

    # ========================================================
    # 2. BACKWARD COMPATIBILITY
    #
    # If no date is supplied but day is supplied:
    #
    # ?day=Tuesday
    #
    # this still works.
    # ========================================================

    if not day:

        frappe.throw(
            "Date is required."
        )

    day = str(
        day
    ).strip().capitalize()

    # ========================================================
    # 3. VALIDATE DAY
    # ========================================================

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
            "Invalid day. Expected Monday, Tuesday, "
            "Wednesday, Thursday, Friday, Saturday "
            "or Sunday."
        )

    # ========================================================
    # 4. IF DATE EXISTS, VERIFY THE DAY
    #
    # This is mostly useful when somebody manually sends:
    #
    # ?date=2026-10-09&day=Tuesday
    #
    # Since date takes priority, we already converted it.
    # ========================================================

    if selected_date:

        actual_day = selected_date.strftime(
            "%A"
        )

        day = actual_day

    # ========================================================
    # 5. GET CONFIGURED GROUPS
    # ========================================================

    (
        settings,
        appointment_duration,
        groups
    ) = _get_configured_groups(
        day
    )

    # ========================================================
    # 6. NO AVAILABILITY
    # ========================================================

    if not groups:

        return []

    # ========================================================
    # 7. CHECK HOLIDAY
    # ========================================================

    if (
        selected_date
        and
        _is_holiday(
            settings,
            selected_date
        )
    ):

        return []

    # ========================================================
    # 8. CHECK ADVANCE BOOKING
    # ========================================================

    if selected_date:

        _check_advance_booking_limit(
            settings,
            selected_date
        )

    # ========================================================
    # 9. GENERATE SLOTS
    # ========================================================

    slots = []

    # ========================================================
    # PROCESS EACH GROUP SEPARATELY
    #
    # Example:
    #
    # Group 1:
    # 10:00 - 13:00
    #
    # Group 2:
    # 15:00 - 19:00
    #
    # If Group 1 is booked:
    #
    # Group 1 -> hidden
    # Group 2 -> available
    #
    # ========================================================

    for group in groups:

        group_booked = False

        if selected_date:

            group_booked = (
                _is_group_booked(
                    selected_date,
                    group
                )
            )

        # ----------------------------------------------------
        # Entire group is unavailable
        # ----------------------------------------------------

        if group_booked:
            continue

        start_seconds = group[
            "start_seconds"
        ]

        end_seconds = group[
            "end_seconds"
        ]

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
        # Generate slots
        # ----------------------------------------------------

        while current < end_dt:

            slot_end = (
                current
                + timedelta(
                    minutes=appointment_duration
                )
            )

            # ------------------------------------------------
            # Only return complete slots
            # ------------------------------------------------

            if slot_end <= end_dt:

                slots.append(
                    {
                        "day": day,

                        "date": (
                            str(selected_date)
                            if selected_date
                            else None
                        ),

                        "group": group[
                            "group"
                        ],

                        "group_from": (
                            datetime.min
                            + timedelta(
                                seconds=group[
                                    "start_seconds"
                                ]
                            )
                        ).strftime(
                            "%H:%M:%S"
                        ),

                        "group_to": end_dt.strftime(
                            "%H:%M:%S"
                        ),

                        "time": current.strftime(
                            "%H:%M:%S"
                        ),

                        "label": current.strftime(
                            "%I:%M %p"
                        ),

                        "end_time": slot_end.strftime(
                            "%H:%M:%S"
                        ),

                        "duration": (
                            appointment_duration
                        ),

                        "available": True
                    }
                )

            current = slot_end

    # ========================================================
    # RETURN SLOTS
    # ========================================================

    return slots


# ============================================================
# BOOK APPOINTMENT
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

    date = str(
        date
    ).strip()

    time = str(
        time
    ).strip()

    name = str(
        name
    ).strip()

    email = str(
        email
    ).strip()

    phone = str(
        phone
    ).strip()

    if subject:

        subject = str(
            subject
        ).strip()

    if message:

        message = str(
            message
        ).strip()

    # --------------------------------------------------------
    # Parse date/time
    # --------------------------------------------------------

    try:

        scheduled_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        try:

            scheduled_datetime = datetime.strptime(
                f"{date} {time}",
                "%Y-%m-%d %H:%M"
            )

        except ValueError:

            frappe.throw(
                "Invalid date or time format. "
                "Expected date YYYY-MM-DD and "
                "time HH:MM or HH:MM:SS."
            )

    # --------------------------------------------------------
    # Current datetime
    # --------------------------------------------------------

    current_datetime = (
        frappe.utils.get_datetime(
            frappe.utils.now_datetime()
        )
    )

    if scheduled_datetime <= current_datetime:

        frappe.throw(
            "Please select a future date and time."
        )

    # --------------------------------------------------------
    # Selected date
    # --------------------------------------------------------

    selected_date = (
        frappe.utils.getdate(
            date
        )
    )

    # --------------------------------------------------------
    # Determine weekday automatically
    # --------------------------------------------------------

    selected_day = (
        scheduled_datetime.strftime(
            "%A"
        )
    )

    # --------------------------------------------------------
    # Get Appointment Booking Settings
    # --------------------------------------------------------

    (
        settings,
        appointment_duration,
        groups
    ) = _get_configured_groups(
        selected_day
    )

    if not groups:

        frappe.throw(
            f"Appointments are not available on "
            f"{selected_day}."
        )

    # --------------------------------------------------------
    # Check Holiday
    # --------------------------------------------------------

    if _is_holiday(
        settings,
        selected_date
    ):

        frappe.throw(
            "Appointments are not available "
            "on this holiday."
        )

    # --------------------------------------------------------
    # Check advance booking
    # --------------------------------------------------------

    _check_advance_booking_limit(
        settings,
        selected_date
    )

    # --------------------------------------------------------
    # Convert selected time to seconds
    # --------------------------------------------------------

    selected_seconds = (
        scheduled_datetime.hour * 3600
        + scheduled_datetime.minute * 60
        + scheduled_datetime.second
    )

    # --------------------------------------------------------
    # Find selected GROUP
    # --------------------------------------------------------

    selected_group = (
        _find_group_for_time(
            selected_seconds,
            groups,
            appointment_duration
        )
    )

    # --------------------------------------------------------
    # Invalid slot
    # --------------------------------------------------------

    if not selected_group:

        frappe.throw(
            "The selected time is not an available "
            "appointment slot."
        )

    # --------------------------------------------------------
    # Check whole group
    # --------------------------------------------------------

    if _is_group_booked(
        selected_date,
        selected_group
    ):

        frappe.throw(
            "This appointment time group has already "
            "been booked. Please select another "
            "available time group."
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
    # Create ERPNext Appointment
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
    # Disable automatic Appointment after_insert
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
    # Commit
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

        "date": date,

        "day": selected_day,

        "group": selected_group[
            "group"
        ],

        "group_from": selected_group[
            "from_time"
        ],

        "group_to": selected_group[
            "to_time"
        ],

        "duration": appointment_duration,

        "message": (
            "Appointment booked successfully."
        )
    }


# ============================================================
# CONTACT US
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

    name = (
        name or ""
    ).strip()

    email = (
        email or ""
    ).strip()

    phone = (
        phone or ""
    ).strip()

    source = (
        source or "Website Contact Form"
    ).strip()

    message = (
        message or ""
    ).strip()

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
    # --------------------------------------------------------

    import html

    safe_name = html.escape(
        name
    )

    safe_email = html.escape(
        email
    )

    safe_phone = html.escape(
        phone or "Not provided"
    )

    safe_source = html.escape(
        source
    )

    safe_message = html.escape(
        message
    )

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
    # --------------------------------------------------------

    frappe.sendmail(
        recipients=[
            "vishuddhihomegardens@gmail.com"
        ],
        subject=email_subject,
        message=email_message
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

