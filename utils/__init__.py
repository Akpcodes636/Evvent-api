from email_validator import EmailNotValidError, validate_email

def validate_nigeria_phone_number(phone_number: str | int) -> str | None:
    phone_number = str(phone_number)
    if not phone_number.isdigit():
        return "Phone number must be numeric"
    if not phone_number.startswith(("080", "081", "090", "091", "070", "071", "01")):
        return "Phone number must start with 080, 081, 090, 091, 070, 071 or 01"
    if phone_number.startswith("01"):
        if len(phone_number) != 11:
            return "Phone number must be 11 digits"
    if len(phone_number) != 11:
        return "Phone number must be 11 digits"

    return None

def validate_email_address(email: str) -> tuple[bool, str]:
    try:
        validated_email = validate_email(email, check_deliverability=False)
        normalized_email = validated_email.normalized
        return True, normalized_email
    except EmailNotValidError as e:
        return False, str(e)
