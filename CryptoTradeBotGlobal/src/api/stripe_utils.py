import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_123")

# Funções utilitárias para criar checkout, etc.
def criar_checkout_session(preco_id, success_url, cancel_url, cliente_email=None):
    return stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": preco_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=cliente_email,
    )
