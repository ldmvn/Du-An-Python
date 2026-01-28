from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductSpecification

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'description', 'image']


ProductSpecFormSet = inlineformset_factory(
    Product,
    ProductSpecification,
    fields=('key', 'value'),
    extra=1,
    can_delete=True
)
