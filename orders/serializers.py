from rest_framework import serializers
from .models import Order
from tracking.models import Entregador


class OrderSerializer(serializers.ModelSerializer):

    restaurante_nome = serializers.CharField(
        source='restaurante.nome_fantasia',
        read_only=True
    )
    restaurante_latitude = serializers.CharField(
        source='restaurante.latitude',
        read_only=True
    )
    restaurante_longitude = serializers.CharField(
        source='restaurante.longitude',
        read_only=True
    )
    entregador_nome = serializers.CharField(
        source='entregador.usuario.user.first_name',
        read_only=True
    )
    entregador_latitude = serializers.CharField(
        source='entregador.localizacao.latitude',
        read_only=True
    )

    entregador_longitude = serializers.CharField(
        source='entregador.localizacao.longitude',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    class Meta:
        model = Order

        fields = [
            'id',
            'address',
            'delivery_fee',
            'delivery_distance_km',
            'payment_state',

            'customer_name',
            'customer_phone',

            'latitude',
            'longitude',

            'status',
            'status_display',

            'restaurante',
            'restaurante_nome',
            'restaurante_latitude',
            'restaurante_longitude',

            'entregador',
            'entregador_nome',
            'entregador_latitude',
            'entregador_longitude',

            'cliente',

            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'restaurante', 'delivery_fee', 'delivery_distance_km', 'payment_state',
            'status',
            'entregador',
            'created_at',
            'updated_at',
        ]


class AssignOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    entregador_id = serializers.IntegerField()