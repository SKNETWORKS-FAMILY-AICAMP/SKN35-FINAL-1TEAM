import enum


class YN(str, enum.Enum):
    Y = "Y"
    N = "N"


class VerificationPurpose(str, enum.Enum):
    COMPANY_REGISTER = "COMPANY_REGISTER"
    EMPLOYEE_SIGNUP = "EMPLOYEE_SIGNUP"
