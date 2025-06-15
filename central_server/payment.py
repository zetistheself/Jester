import yookassa
import uuid
import dotenv


dotenv.load_dotenv()

yookassa.Configuration.account_id = "1096375"
yookassa.Configuration.secret_key = "test_ZDbReX2Bky2d3Nsz4A4dX9F4umnlYb4yV05VfZhxDAA"

payment_tariff = {
    "50 мбит/сек": 49.00,
    "100 мбит/сек": 89.00,
    "300 мбит/сек": 249.00,
}


def get_payment(value: float, description: str):
    return yookassa.Payment.create({
        "amount": {
            "value": str(value),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/jestervpnbot",
        },
        "capture": True,
        "description": description,
    }, uuid.uuid4())


def check_payment(payment_id: str):
    try:
        payment = yookassa.Payment.find_one(payment_id)
        if payment.status == "succeeded":
            return True, payment
        else:
            return False, payment
    except Exception as e:
        print(f"Error checking payment: {e}")
        return False, None
