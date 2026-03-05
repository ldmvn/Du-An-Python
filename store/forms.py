from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import Product, ProductSpecification, UserProfile, Category


class CategoryForm(forms.ModelForm):
    """Form for managing product categories/brands"""
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên nhà sản xuất (vd: Apple, Samsung, Xiaomi)',
                'required': True
            })
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise forms.ValidationError('Tên nhà sản xuất không được để trống')
        return name.strip()


class UserManagementForm(forms.ModelForm):
    """Form for admin to manage user accounts"""
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mật khẩu (để trống nếu không muốn đổi)'
        }),
        help_text='Để trống để giữ mật khẩu hiện tại'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên đăng nhập'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tên'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Họ'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'ram', 'rom', 'discount', 'description', 'image']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Giá phải lớn hơn 0')
        return price
    
    def clean_discount(self):
        discount = self.cleaned_data.get('discount')
        if discount is not None and (discount < 0 or discount > 100):
            raise forms.ValidationError('Giảm giá phải từ 0 đến 100%')
        return discount


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
