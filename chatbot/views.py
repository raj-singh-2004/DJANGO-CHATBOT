# chatbot/views.py
import uuid
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from menu.models import MenuItem  # 👈 add this

from restaurants.models import Restaurant
from .serializers import ChatRequestSerializer
from .engine import parse_message
from .services import apply_intent
from orders.models import Order   # ✅ add this


from django.utils import timezone
from datetime import timedelta



class ChatbotWidgetDemoView(TemplateView):
    template_name = "chatbot_widget_demo.html"


@method_decorator(csrf_exempt, name="dispatch")
class SimpleChatbotView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant_id = serializer.validated_data["restaurant_id"]
        session_id = serializer.validated_data.get("session_id") or ""
        message = serializer.validated_data["message"]

        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:16]}"

        # 1️⃣ Parse message → intent
        result = parse_message(message)

        # 2️⃣ Handle CONFIRM_ORDER intent separately (payment trigger)
        if result.intent == "CONFIRM_ORDER":
            order = Order.objects.filter(
                restaurant=restaurant,
                session_id=session_id,
                status=Order.OrderStatus.PENDING,
            ).first()

            if not order:
                return Response(
                    {"reply": "No open order found to confirm.", "session_id": session_id},
                    status=status.HTTP_200_OK,
                )

            payments_api = request.build_absolute_uri("/api/payments/create/")
            try:
                r = requests.post(payments_api, json={"order_id": order.id})
                if r.status_code != 200:
                    # Razorpay create failed → reply politely instead of KeyError
                    msg = r.json().get("detail", "Unable to create payment.")
                    return Response(
                        {
                            "reply": f"⚠️ Cannot process payment — there should be atleast one order.",
                            "session_id": session_id,
                        },
                        status=status.HTTP_200_OK,
                    )

                data = r.json()

                return Response(
                    {
                        "reply": "Please complete your payment to confirm the order.",
                        "session_id": session_id,
                        "payment": {
                            "key": data["key"],
                            "order_id": data["razorpay_order_id"],
                            "amount": data["amount"],
                            "currency": data["currency"],
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                print("Payment creation error:", e)
                return Response(
                    {"reply": "Something went wrong creating the payment."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


        # 3️⃣ For all other intents → process normally
                # 3️⃣ For all other intents → process normally
        reply_text, order, extra = apply_intent(restaurant, session_id, result)

        # 4️⃣ Prepare order snapshot
        items_data = [
            {
                "id": item.menu_item.id,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }
            for item in order.items.select_related("menu_item").all()
        ]

        order_data = {
            "id": order.id,
            "status": order.status,
            "subtotal": str(order.subtotal),
            "tax": str(order.tax),
            "total": str(order.total),
            "items": items_data,
        }

        # 5️⃣ Return chat response (+ any extra UI payload like menu_items)
        payload = {
            "reply": reply_text,
            "session_id": session_id,
            "order": order_data,
        }
        if extra:
            payload.update(extra)

        return Response(payload, status=status.HTTP_200_OK)


class PopularItemsView(APIView):
    """
    Returns a list of most-ordered menu items for a restaurant.

    GET /api/chatbot/popular-items/?restaurant_id=1

    Response:
    {
        "items": [
            {"id": 12, "name": "Masala Dosa"},
            {"id": 5, "name": "Paneer Butter Masala"},
            ...
        ]
    }
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response(
                {"detail": "restaurant_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        # Aggregate by MenuItem, ordered by total quantity ordered (most popular first)
        qs = (
            OrderItem.objects
            .filter(order__restaurant=restaurant)
            .values("menu_item_id", "menu_item__name")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")[:6]   # top 6
        )

        items = [
            {
                "id": row["menu_item_id"],
                "name": row["menu_item__name"],
            }
            for row in qs
            if row["menu_item_id"] is not None
        ]

        return Response({"items": items}, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    """
    Return distinct menu categories for a restaurant.

    GET /api/chatbot/categories/?restaurant_id=1
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response(
                {"detail": "restaurant_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Make sure restaurant exists (optional but nice)
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        cutoff = timezone.now() - timedelta(seconds= 5)

        qs = (
            MenuItem.objects.filter(
                restaurant=restaurant,
                available=True,
                created_at__lte=cutoff,
            )
            .exclude(category__isnull=True)
            .exclude(category__exact="")
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )

        return Response({"categories": list(qs)}, status=status.HTTP_200_OK)


