from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "password_confirm", "first_name", "last_name", "phone")

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "loyalty_points_balance", "date_joined")
        read_only_fields = ("id", "loyalty_points_balance", "date_joined")
