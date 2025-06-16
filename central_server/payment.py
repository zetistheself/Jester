import yookassa
import uuid
import dotenv
import os
import datetime

dotenv.load_dotenv()

shop_id = str(os.getenv("SHOP_ID"))
yookassa_key = os.getenv("YOOKASSA_KEY")
yookassa.Configuration.account_id = shop_id
yookassa.Configuration.secret_key = yookassa_key

payment_tariff = {
    "50 мбит/сек": 49.00,
    "100 мбит/сек": 89.00,
    "300 мбит/сек": 249.00,
}


def get_payment(value: float, description: str, email: str):
    expire_at = (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat() + "Z"
    idempotence_key = str(uuid.uuid4())
    return yookassa.Payment.create({
        "amount": {
            "value": str(f'{value:.2f}'),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/jestervpnbot",
        },
        "capture": True,
        "description": description,
        "expires_at": expire_at,
        "receipt": {
            "customer": {
                "email": email
            },
            "items": [
                {
                    "description": description,
                    "quantity": 1.0,
                    "amount": {
                        "value": f"{value:.2f}",
                        "currency": "RUB"
                    },
                    "vat_code": 4,
                    "payment_mode": "full_payment",
                    "payment_subject": "service"
                }
            ]
        }
    }, idempotence_key)


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
