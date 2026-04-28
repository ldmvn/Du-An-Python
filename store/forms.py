from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.models import User
from .models import Product, ProductSpecification, UserProfile, Category, Banner
import re


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


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
        fields = [
            'category',
            'name',
            'price',
            'stock',
            'ram',
            'rom',
            'discount',
            'description',
            'image',
        ]
    
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
    
    def clean_image(self):
        """Kiểm tra định dạng và kích thước file ảnh"""
        image = self.cleaned_data.get('image')
        
        if image:
            # Kiểm tra định dạng file
            allowed_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            file_extension = image.name.split('.')[-1].lower()
            
            if file_extension not in allowed_formats:
                raise forms.ValidationError(
                    f'❌ Định dạng file không hợp lệ! Chỉ chấp nhận: {", ".join(allowed_formats).upper()}'
                )
            
            # Kiểm tra kích thước file (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if image.size > max_size:
                raise forms.ValidationError(
                    f'❌ Kích thước file quá lớn! Tối đa 5MB, file của bạn {image.size / (1024*1024):.2f}MB'
                )
        
        return image

    def clean_feature_image(self):
        feature_image = self.cleaned_data.get('feature_image')
        if not feature_image:
            return feature_image

        allowed_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        file_extension = feature_image.name.split('.')[-1].lower()
        if file_extension not in allowed_formats:
            raise forms.ValidationError('Ảnh tính năng chỉ nhận JPG, JPEG, PNG, GIF, WEBP.')

        if feature_image.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Ảnh tính năng tối đa 10MB.')

        return feature_image


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
    
    def clean_phone(self):
        """Validate phone number format - only digits and spaces/dashes, 10-15 characters"""
        phone = self.cleaned_data.get('phone', '').strip()
        
        if not phone:
            raise forms.ValidationError('❌ Số điện thoại không được để trống')
        
        # Remove spaces and dashes for validation
        phone_digits = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Check if contains only digits and optional + at start
        if not re.match(r'^\+?[0-9]{10,15}$', phone_digits):
            raise forms.ValidationError('❌ Số điện thoại không hợp lệ! Chỉ nhập số (10-15 chữ số)')
        
        # If starts with +84, check it's valid Vietnamese number
        if phone_digits.startswith('+84') and len(phone_digits) != 13:
            raise forms.ValidationError('❌ Số điện thoại Việt Nam định dạng +84 phải có 13 chữ số')
        
        # If starts with 0, check it's valid Vietnamese number (0 + 9 digits)
        if phone_digits.startswith('0') and len(phone_digits) != 10:
            raise forms.ValidationError('❌ Số điện thoại Việt Nam phải có 10 chữ số (0X XXXX XXXX)')
        
        return phone


class CheckoutForm(forms.Form):
    """Form for checkout with phone validation"""
    fullname = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập họ tên'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập email'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập số điện thoại',
            'type': 'tel'
        })
    )
    address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập địa chỉ chi tiết',
            'rows': 3
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập thành phố/tỉnh'
        })
    )
    district = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập quận/huyện'
        })
    )
    ward = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập phường/xã'
        })
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('cash', 'Thanh toán khi nhận hàng'),
            ('bank', 'Chuyển khoản ngân hàng'),
            ('vnpay', 'VNPAY')
        ],
        required=True,
        widget=forms.RadioSelect()
    )
    
    def clean_fullname(self):
        fullname = self.cleaned_data.get('fullname', '').strip()
        if not fullname:
            raise forms.ValidationError('❌ Họ tên không được để trống')
        if len(fullname) < 2:
            raise forms.ValidationError('❌ Họ tên phải có ít nhất 2 ký tự')
        return fullname
    
    def clean_phone(self):
        """Validate phone number format - only digits and spaces/dashes, 10-15 characters"""
        phone = self.cleaned_data.get('phone', '').strip()
        
        if not phone:
            raise forms.ValidationError('❌ Số điện thoại không được để trống')
        
        # Remove spaces and dashes for validation
        phone_digits = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Check if contains only digits and optional + at start
        if not re.match(r'^\+?[0-9]{10,15}$', phone_digits):
            raise forms.ValidationError('❌ Số điện thoại chỉ được chứa chữ số (0-9)! Chỉ nhập số điện thoại (10-15 chữ số)')
        
        # If starts with +84, check it's valid Vietnamese number
        if phone_digits.startswith('+84') and len(phone_digits) != 13:
            raise forms.ValidationError('❌ Số điện thoại Việt Nam định dạng +84 phải có 13 chữ số')
        
        # If starts with 0, check it's valid Vietnamese number (0 + 9 digits)
        if phone_digits.startswith('0') and len(phone_digits) != 10:
            raise forms.ValidationError('❌ Số điện thoại Việt Nam phải có 10 chữ số (0X XXXX XXXX)')
        
        return phone
    
    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if not address or len(address) < 5:
            raise forms.ValidationError('❌ Địa chỉ phải có ít nhất 5 ký tự')
        return address
    
    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city or len(city) < 2:
            raise forms.ValidationError('❌ Thành phố/Tỉnh phải có ít nhất 2 ký tự')
        return city


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


class BannerForm(forms.ModelForm):
    """Form for managing banner images"""
    class Meta:
        model = Banner
        fields = ['banner_id', 'image', 'is_active']
        widgets = {
            'banner_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vị trí banner (1, 2, 3, ...)'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,video/*'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_banner_id(self):
        banner_id = self.cleaned_data.get('banner_id')
        if banner_id is None or banner_id <= 0:
            raise forms.ValidationError('Vị trí banner phải lớn hơn 0')
        return banner_id
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            allowed_image_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            allowed_video_formats = ['mp4', 'webm', 'ogg', 'mov', 'm4v']
            file_extension = image.name.split('.')[-1].lower()
            
            if file_extension not in allowed_image_formats and file_extension not in allowed_video_formats:
                raise forms.ValidationError('❌ Định dạng không hợp lệ! Chỉ nhận ảnh JPG, PNG, GIF, WEBP hoặc video MP4, WEBM, OGG, MOV')
            
            max_size = 10 * 1024 * 1024 if file_extension in allowed_image_formats else 50 * 1024 * 1024
            if image.size > max_size:
                if file_extension in allowed_image_formats:
                    raise forms.ValidationError('❌ Kích thước ảnh quá lớn! Tối đa 10MB')
                raise forms.ValidationError('❌ Kích thước video quá lớn! Tối đa 50MB')
        
        return image

