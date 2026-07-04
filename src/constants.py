from enum import Enum

class Environment(str, Enum):
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"

class Business(str, Enum):
    HOTEL = "HOTEL"
    HOSPITAL = "HOSPITAL"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"