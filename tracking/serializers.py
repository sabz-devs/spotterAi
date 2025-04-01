# serializers.py
from rest_framework import serializers
from .models import Trip, Stop, GPSLog, ELDLog

class GPSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPSLog
        fields = '__all__'

class ELDLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ELDLog
        fields = '__all__'

class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    eld_logs = ELDLogSerializer(many=True, read_only=True)
    has_route = serializers.SerializerMethodField()
    
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['driver', 'created_at', 'updated_at']
    
    def get_has_route(self, obj):
        """Return whether the trip has an associated route."""
        return hasattr(obj, 'route')