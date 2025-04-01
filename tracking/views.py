# views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models import Trip, Stop, GPSLog, ELDLog
from .serializers import TripSerializer, StopSerializer, GPSLogSerializer, ELDLogSerializer

class TripCreateView(generics.CreateAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Save trip with the currently authenticated driver
        serializer.save(driver=self.request.user)

class TripListView(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter trips by status if provided in query params
        status_filter = self.request.query_params.get('status', None)
        queryset = Trip.objects.filter(driver=self.request.user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset

class TripDetailView(generics.RetrieveAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

class TripUpdateView(generics.UpdateAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        trip = serializer.instance
        status = serializer.validated_data.get('status', trip.status)
        
        # If trip is marked as completed, set actual end date
        if status == 'completed' and trip.status != 'completed':
            serializer.save(actual_end_date=timezone.now())
        else:
            serializer.save()

class StartTripView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            trip = Trip.objects.get(pk=pk, driver=request.user)
            
            if trip.status != 'planned':
                return Response({"error": "Only planned trips can be started"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Update trip status to in_progress
            trip.status = 'in_progress'
            trip.startDate = timezone.now()
            trip.save()
            
            # Create first ELD log entry - On Duty for pickup
            ELDLog.objects.create(
                trip=trip,
                event_type='on_duty',
                location=trip.pickup_location,
                coordinates=trip.pickup_coordinates,
                duration=1.0,  # 1 hour for pickup
                start_time=timezone.now()
            )
            
            return Response(TripSerializer(trip).data)
            
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

class LogELDEventView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            trip = Trip.objects.get(pk=pk, driver=request.user)
            
            if trip.status != 'in_progress':
                return Response({"error": "Trip must be in progress to log ELD events"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ELDLogSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(trip=trip)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

class LogGPSView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            trip = Trip.objects.get(pk=pk, driver=request.user)
            
            if trip.status != 'in_progress':
                return Response({"error": "Trip must be in progress to log GPS data"}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            serializer = GPSLogSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(trip=trip)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

class CompleteStopView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk, stop_id):
        try:
            trip = Trip.objects.get(pk=pk, driver=request.user)
            stop = Stop.objects.get(pk=stop_id, trip=trip)
            
            stop.completed = True
            stop.actual_arrival_time = timezone.now()
            stop.save()
            
            return Response(StopSerializer(stop).data)
            
        except Trip.DoesNotExist:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)
        except Stop.DoesNotExist:
            return Response({"error": "Stop not found"}, status=status.HTTP_404_NOT_FOUND)