""" MoMo Payment Gateway Utilities """
import hmac
import hashlib
import uuid
import json
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class MoMoUtil:
    """MoMo payment utility class"""

    def __init__(self):
        self.partner_code = getattr(settings, 'MOMO_PARTNER_CODE', 'MOMO')
        self.access_key = getattr(settings, 'MOMO_ACCESS_KEY', 'F8BBA842ECF85')
        self.secret_key = getattr(settings, 'MOMO_SECRET_KEY', 'K951B6PE1waDMi640xX08PD3vg6EkVlz')
        self.endpoint = getattr(settings, 'MOMO_ENDPOINT', 'https://test-payment.momo.vn/v2/gateway/api/create')
        self.redirect_url = getattr(settings, 'MOMO_RETURN_URL', 'http://localhost:8000/momo/return/')
        self.ipn_url = getattr(settings, 'MOMO_IPN_URL', 'http://localhost:8000/momo/ipn/')

    def create_payment(self, amount, order_id, order_info, extra_data=''):
        """Create MoMo payment request"""
        request_id = str(uuid.uuid4())

        raw_signature = (
            f"accessKey={self.access_key}&amount={amount}&extraData={extra_data}&ipnUrl={self.ipn_url}"
            f"&orderId={order_id}&orderInfo={order_info}&partnerCode={self.partner_code}"
            f"&redirectUrl={self.redirect_url}&requestId={request_id}&requestType=payWithMethod"
        )

        logger.info(f"[MoMo] raw_signature: {raw_signature}")

        signature = hmac.new(
            bytes(self.secret_key, 'ascii'),
            bytes(raw_signature, 'ascii'),
            hashlib.sha256
        ).hexdigest()

        logger.info(f"[MoMo] signature: {signature}")

        data = {
            'partnerCode': self.partner_code,
            'partnerName': 'Test',
            'storeId': 'MomoTestStore',
            'requestId': request_id,
            'amount': str(amount),
            'orderId': order_id,
            'orderInfo': order_info,
            'redirectUrl': self.redirect_url,
            'ipnUrl': self.ipn_url,
            'lang': 'vi',
            'extraData': extra_data,
            'requestType': 'payWithMethod',
            'orderGroupId': '',
            'autoCapture': True,
            'signature': signature
        }

        logger.info(f"[MoMo] request body: {json.dumps(data)}")

        try:
            response = requests.post(
                self.endpoint,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            result = response.json()
            logger.info(f"[MoMo] Response: {result}")
            return result
        except Exception as e:
            logger.error(f"[MoMo] Error: {e}")
            return {'error': True, 'message': str(e)}

    def verify_signature(self, data):
        """Verify MoMo callback signature"""
        raw_signature = (
            f"accessKey={self.access_key}&amount={data.get('amount')}"
            f"&extraData={data.get('extraData', '')}&orderId={data.get('orderId')}"
            f"&orderInfo={data.get('orderInfo', '')}&partnerCode={data.get('partnerCode')}"
            f"&requestId={data.get('requestId')}"
        )

        expected_signature = hmac.new(
            bytes(self.secret_key, 'ascii'),
            bytes(raw_signature, 'ascii'),
            hashlib.sha256
        ).hexdigest()

        return data.get('signature') == expected_signature

    @staticmethod
    def build_payment_url(amount, order_id, order_info):
        """Static method for easy call"""
        momo = MoMoUtil()
        return momo.create_payment(amount, order_id, order_info)
