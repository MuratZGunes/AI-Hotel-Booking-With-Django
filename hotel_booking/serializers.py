from rest_framework import serializers
from .models import Room, Booking, Review, PromoCode

class RoomSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Room
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'user', 'user_name', 'room', 'room_name', 'check_in', 
                 'check_out', 'status', 'total_cost', 'created_at']
        read_only_fields = ['total_cost', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'room', 'room_name', 'rating', 
                 'comment', 'created_at']
        read_only_fields = ['created_at']

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['code', 'discount_percentage', 'valid_from', 'valid_until', 
                 'max_uses', 'current_uses']
        read_only_fields = ['current_uses'] 