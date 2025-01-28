from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count
from .models import Room, Booking, Review, PromoCode
from .serializers import (
    RoomSerializer, BookingSerializer, ReviewSerializer, PromoCodeSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class RoomViewSet(viewsets.ModelViewSet):
    """
    Otel odalarını yönetmek için API uç noktası.
    """
    queryset = Room.objects.annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review')
    )
    serializer_class = RoomSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'room_type']
    ordering_fields = ['price', 'avg_rating', 'review_count']
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'check_in', openapi.IN_QUERY,
                description="Giriş tarihi (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE
            ),
            openapi.Parameter(
                'check_out', openapi.IN_QUERY,
                description="Çıkış tarihi (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE
            ),
        ],
        responses={
            200: openapi.Response(
                description="Oda müsaitlik durumu",
                examples={
                    "application/json": {
                        "available": True
                    }
                }
            ),
            400: "Hatalı İstek - Geçersiz tarihler"
        }
    )
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """
        Belirtilen tarihler için oda müsaitliğini kontrol et.
        """
        room = self.get_object()
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        
        if not (check_in and check_out):
            return Response(
                {'error': 'Lütfen giriş ve çıkış tarihlerini belirtin'},
                status=400
            )
            
        is_available = room.is_available(check_in, check_out)
        return Response({'available': is_available})

class BookingViewSet(viewsets.ModelViewSet):
    """
    Rezervasyonları yönetmek için API uç noktası.
    """
    serializer_class = BookingSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['check_in', 'check_out', 'created_at']
    
    def get_queryset(self):
        """
        Personel kullanıcıları için tüm rezervasyonları, normal kullanıcılar için sadece kendi rezervasyonlarını döndür.
        """
        queryset = Booking.objects.select_related('user', 'room')
        if self.request.user.is_staff:
            return queryset.all()
        return queryset.filter(user=self.request.user)
    
    @swagger_auto_schema(
        request_body=BookingSerializer,
        responses={
            201: BookingSerializer,
            400: "Hatalı İstek - Geçersiz veri"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Yeni bir rezervasyon oluştur.
        """
        return super().create(request, *args, **kwargs)

class ReviewViewSet(viewsets.ModelViewSet):
    """
    Değerlendirmeleri yönetmek için API uç noktası.
    """
    serializer_class = ReviewSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['rating', 'created_at']
    
    def get_queryset(self):
        queryset = Review.objects.select_related('user', 'room')
        if self.request.user.is_staff:
            return queryset.all()
        return queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PromoCodeViewSet(viewsets.ModelViewSet):
    """
    Promosyon kodlarını yönetmek için API uç noktası.
    """
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAdminUser] 