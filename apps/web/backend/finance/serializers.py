from rest_framework import serializers

from .models import ITRData, TaxProfile, Transaction, UserProfile, WealthItem

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        # Using camelCase to match your React state
        fields = ['monthlyIncome', 'monthlyBudget', 'dailyBudget', 'is_business']


class UserProfileUpdateSerializer(serializers.Serializer):
    monthlyIncome = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, min_value=0)
    monthlyBudget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, min_value=0)
    dailyBudget = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, min_value=0)
    is_business = serializers.BooleanField(required=False)
    email = serializers.EmailField(required=False, allow_blank=True)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        # Added 'is_recurring' so your frontend knows which are subscriptions
        fields = ['id', 'title', 'amount', 'type', 'category', 'date', 'is_recurring']


class TransactionWriteSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255, write_only=True)

    class Meta:
        model = Transaction
        fields = ['title', 'description', 'amount', 'type', 'category', 'date', 'is_recurring']
        extra_kwargs = {
            "amount": {"required": False, "min_value": 0.01},
            "type": {"required": False},
            "category": {"required": False},
            "date": {"required": False},
            "is_recurring": {"required": False},
        }

    def validate_type(self, value):
        normalized = str(value).strip().lower()
        if normalized not in {"income", "expense"}:
            raise serializers.ValidationError("Transaction type must be 'income' or 'expense'")
        return normalized

    def validate_category(self, value):
        return str(value).strip().lower()

    def validate(self, attrs):
        if not attrs.get("title") and attrs.get("description"):
            attrs["title"] = attrs["description"]
        if "title" in attrs:
            attrs["title"] = attrs["title"].strip() or "Untitled Transaction"
        return attrs
        
class WealthItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WealthItem
        # Changed 'name' to 'title' and 'institution' to 'category' 
        # to match your models.py
        fields = ['id', 'title', 'amount', 'type', 'category']


class WealthItemWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=100)

    class Meta:
        model = WealthItem
        fields = ['title', 'name', 'amount', 'type', 'category']
        extra_kwargs = {
            "title": {"required": False, "allow_blank": True},
            "amount": {"required": False, "min_value": 0.01},
            "type": {"required": False},
            "category": {"required": False},
        }

    def validate_type(self, value):
        normalized = str(value).strip().lower()
        if normalized not in {"asset", "liability"}:
            raise serializers.ValidationError("Wealth type must be 'asset' or 'liability'")
        return normalized

    def validate(self, attrs):
        if not attrs.get("title") and attrs.get("name"):
            attrs["title"] = attrs["name"]
        if "title" in attrs:
            attrs["title"] = attrs["title"].strip() or "Untitled"
        if "category" in attrs:
            attrs["category"] = str(attrs["category"]).strip() or "General"
        return attrs
        
class TaxProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxProfile
        # Keep snake_case here; the methods below handle the conversion
        fields = [
            'is_business', 'annual_rent', 'annual_epf', 
            'nps_contribution', 'health_insurance_self', 
            'health_insurance_parents', 'home_loan_interest', 
            'education_loan_interest'
        ]

    def to_representation(self, instance):
        """Converts database snake_case to React camelCase"""
        return {
            "isBusiness": instance.is_business,
            "annualRent": float(instance.annual_rent),
            "annualEPF": float(instance.annual_epf),
            "npsContribution": float(instance.nps_contribution),
            "healthInsuranceSelf": float(instance.health_insurance_self),
            "healthInsuranceParents": float(instance.health_insurance_parents),
            "homeLoanInterest": float(instance.home_loan_interest),
            "educationLoanInterest": float(instance.education_loan_interest),
        }

    def to_internal_value(self, data):
        """Converts React camelCase back to database snake_case"""
        # Define the mapping
        map_fields = {
            "isBusiness": "is_business",
            "annualRent": "annual_rent",
            "annualEPF": "annual_epf",
            "npsContribution": "nps_contribution",
            "healthInsuranceSelf": "health_insurance_self",
            "healthInsuranceParents": "health_insurance_parents",
            "homeLoanInterest": "home_loan_interest",
            "educationLoanInterest": "education_loan_interest",
        }
        
        internal_data = {}
        for json_key, db_key in map_fields.items():
            if json_key in data:
                internal_data[db_key] = data.get(json_key)
        
        return super().to_internal_value(internal_data)


class ITRDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ITRData
        fields = ["income_data", "deductions_data", "filing_details", "tax_regime"]

    def validate_tax_regime(self, value):
        normalized = str(value).strip().lower()
        if normalized not in {"new", "old"}:
            raise serializers.ValidationError("tax_regime must be 'new' or 'old'")
        return normalized
