import enum


class YN(str, enum.Enum):
    Y = "Y"
    N = "N"

class UserLevel(str, enum.Enum):
    LIMITED = "LIMITED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

class ApprovalStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"

class ProjectMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    LEADER = "LEADER"
    MEMBER = "MEMBER"

class DocumentGrade(str, enum.Enum):
    COMPANY_PUBLIC = "COMPANY_PUBLIC"
    PROJECT_PRIVATE = "PROJECT_PRIVATE"
    TEAM_PRIVATE = "TEAM_PRIVATE"
    EXTERNAL_SHARED = "EXTERNAL_SHARED"

class VerificationPurpose(str, enum.Enum):
    COMPANY_REGISTER = "COMPANY_REGISTER"
    EMPLOYEE_SIGNUP = "EMPLOYEE_SIGNUP"
