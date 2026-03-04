from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import Product, ProductSpecification, UserProfile


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'description', 'image']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Giá phải lớn hơn 0')
        return price


ProductSpecFormSet = inlineformset_factory(
    Product,
    ProductSpecification,
    fields=('key', 'value'),
    extra=1,
    can_delete=True
)


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'profile-form-input',
                'placeholder': 'Tên đăng nhập',
                'readonly': True  # Không cho phép sửa username
            }),
            'email': forms.EmailInput(attrs={
                'class': 'profile-form-input',
                'placeholder': 'Email'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'profile-form-input',
                'placeholder': 'Tên'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'profile-form-input',
                'placeholder': 'Họ'
            }),
        }


class UserExtendedProfileForm(forms.ModelForm):
    """Form for editing extended user profile (phone, address)"""
    class Meta:
        model = UserProfile
        fields = ['phone', 'address']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'profile-form-input',
                'placeholder': 'Số điện thoại',
                'type': 'tel'
            }),
            'address': forms.Textarea(attrs={
                'class': 'profile-form-textarea',
                'placeholder': 'Địa chỉ giao hàng',
                'rows': 3
            }),
        }


class ChangePasswordForm(forms.Form):
    """Form for changing password"""
    old_password = forms.CharField(
        label='Mật khẩu hiện tại',
        widget=forms.PasswordInput(attrs={
            'class': 'profile-form-input',
            'placeholder': 'Nhập mật khẩu hiện tại'
        })
    )
    new_password1 = forms.CharField(
        label='Mật khẩu mới',
        widget=forms.PasswordInput(attrs={
            'class': 'profile-form-input',
            'placeholder': 'Nhập mật khẩu mới'
        })
    )
    new_password2 = forms.CharField(
        label='Xác nhận mật khẩu',
        widget=forms.PasswordInput(attrs={
            'class': 'profile-form-input',
            'placeholder': 'Xác nhận mật khẩu mới'
        })
    )
