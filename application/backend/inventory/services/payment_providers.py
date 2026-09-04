from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

@dataclass(frozen=True)
class PaymentProviderResult:
    success: bool
    provider_reference: str | None

class MockPaymentProvider:
    name = "mock"

    def charge(self, *, order_id: int, amount: Decimal):
        return PaymentProviderResult(
            success=True,
            provider_reference=f"mock_{uuid4().hex}",
        )
    
mock_payment_provider = MockPaymentProvider()