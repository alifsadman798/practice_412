from datetime import timedelta, timezone

APP_VERSION = "1.0.0"
BANGLADESH_TIME = timezone(timedelta(hours=6))

# 64 Official Districts of Bangladesh (from 64_districts.csv)
BANGLADESH_64_DISTRICTS = [
    "Bagerhat", "Bandarban", "Barguna", "Barishal", "Bhola", "Bogura",
    "Brahmanbaria", "Chandpur", "Chapainawabganj", "Chattogram", "Chuadanga",
    "Cox's Bazar", "Cumilla", "Dhaka", "Dinajpur", "Faridpur", "Feni",
    "Gaibandha", "Gazipur", "Gopalganj", "Habiganj", "Jamalpur", "Jashore",
    "Jhalokati", "Jhenaidah", "Joypurhat", "Khagrachhari", "Khulna",
    "Kishoreganj", "Kurigram", "Kushtia", "Lakshmipur", "Lalmonirhat",
    "Madaripur", "Magura", "Manikganj", "Meherpur", "Moulvibazar",
    "Munshiganj", "Mymensingh", "Naogaon", "Narail", "Narayanganj",
    "Narsingdi", "Natore", "Netrokona", "Nilphamari", "Noakhali", "Pabna",
    "Panchagarh", "Patuakhali", "Pirojpur", "Rajbari", "Rajshahi",
    "Rangamati", "Rangpur", "Satkhira", "Shariatpur", "Sherpur",
    "Sirajganj", "Sunamganj", "Sylhet", "Tangail", "Thakurgaon"
]

# Core cities influence bus fare calculation (Section 7.1)
CORE_CITIES = frozenset({"Dhaka", "Chattogram", "Khulna", "Rajshahi"})

# Major cities influence estimated road travel time (Section 7.2)
MAJOR_CITIES = frozenset({"Dhaka", "Chattogram", "Khulna", "Rajshahi", "Sylhet"})

# Manual traffic factors by departure time window (Section 9.2)
TRAFFIC_FACTORS = {
    "06:00-08:00": 1.0,
    "08:00-10:00": 0.7,
    "10:00-17:00": 1.0,
    "17:00-20:00": 0.7,
    "20:00-22:00": 1.0,
    "22:00-06:00": 1.2,
}

# Base speeds (Section 9.1)
BUS_BASE_SPEED_KMH = 45
LOCAL_SPEED_KMH = 30
LOCAL_FARE_BDT = 50

# Transfer buffers (Section 11.4)
BUS_TRANSFER_BUFFER_MINUTES = 30
TRAIN_TRANSFER_BUFFER_MINUTES = 30
LOCAL_TRANSFER_BUFFER_MINUTES = 15
