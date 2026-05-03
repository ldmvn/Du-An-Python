# Website Bán Điện Thoại Di Động (Python – Django)

## 1. Giới thiệu đề tài
Dự án **Website bán điện thoại di động** được xây dựng bằng ngôn ngữ lập trình **Python** sử dụng framework **Django**.  
Hệ thống mô phỏng quy trình kinh doanh điện thoại trực tuyến từ quản lý sản phẩm, người dùng đến đặt hàng và thống kê, đáp ứng yêu cầu của một ứng dụng web hoàn chỉnh có thể triển khai thực tế.

---

## 2. Mục tiêu & phạm vi

### 🎯 Mục tiêu
- Xây dựng ứng dụng web hoàn chỉnh cho một bài toán nghiệp vụ cụ thể
- Có cơ sở dữ liệu, giao diện người dùng, xử lý nghiệp vụ
- Có thể chạy và demo thực tế

### 📌 Phạm vi
- Quản lý tối thiểu **5 thực thể dữ liệu có quan hệ**, ví dụ:
  - Người dùng (User)
  - Sản phẩm (Product)
  - Danh mục (Category)
  - Đơn hàng (Order)
  - Chi tiết đơn hàng / Bình luận (OrderItem / Review)

### ✅ Kết quả mong đợi
- Hệ thống hoạt động ổn định
- Có dữ liệu mẫu (seed data)
- Minh họa được quy trình nghiệp vụ đầu – cuối
- Có tài liệu và mã nguồn rõ ràng

---

## 3. Vai trò người dùng

### 👤 Khách (Guest)
- Đăng ký tài khoản
- Đăng nhập
- Xem danh sách sản phẩm
- Tìm kiếm sản phẩm

### 👥 Người dùng đã đăng nhập
- Cập nhật thông tin cá nhân
- Thực hiện các nghiệp vụ được phân quyền (đặt hàng, bình luận, quản lý dữ liệu của mình)

### 🛠 Quản trị viên (Admin)
- Quản lý người dùng
- Quản lý sản phẩm, danh mục
- Phân quyền hệ thống
- Xem thống kê, báo cáo

---

## 4. Yêu cầu chức năng

### a) Xác thực & phân quyền
- Đăng ký
- Đăng nhập / đăng xuất
- Quên mật khẩu (cơ bản)
- Kiểm soát truy cập theo vai trò

### b) CRUD dữ liệu
- Thêm – Xem – Sửa – Xóa (CRUD) cho:
  - Người dùng
  - Sản phẩm
- Hỗ trợ:
  - Tìm kiếm
  - Lọc
  - Sắp xếp dữ liệu

### c) Nghiệp vụ đặc thù
- Đặt hàng sản phẩm
- Quản lý trạng thái đơn hàng:
  - `Pending`
  - `Approved`
  - `Rejected`

### d) Thống kê – báo cáo
- Thống kê số lượng sản phẩm
- Thống kê đơn hàng theo thời gian (ngày/tháng)
- Hiển thị bằng bảng hoặc biểu đồ

### e) Upload tệp / ảnh
- Upload ảnh sản phẩm
- Giới hạn định dạng và kích thước tệp
- Lưu trữ an toàn trong hệ thống

---

## 5. Kiến trúc & công nghệ

- **Ngôn ngữ**: Python 3
- **Framework**: Django
- **Cơ sở dữ liệu**: SQLite (có thể mở rộng MySQL / PostgreSQL)
- **Frontend**:
  - HTML, CSS, Bootstrap
  - Django Template Engine
- **Mô hình kiến trúc**: MVT (Model – View – Template)

---

## 6. Tiến độ thực hiện hiện tại

✔️ Dự án được tạo thành công bằng Django, cấu trúc thư mục đúng chuẩn  
✔️ Thiết kế giao diện chính (Home, Login, Dashboard, CRUD)  
✔️ Giao diện bố cục hợp lý, responsive, dễ sử dụng  
✔️ Kết nối thành công với cơ sở dữ liệu  
✔️ Tạo ít nhất 2 bảng dữ liệu chính với model đầy đủ  
✔️ Hiển thị dữ liệu mẫu (seed data) trên website  
✔️ Chức năng đăng nhập – đăng ký hoạt động  
✔️ Có menu điều hướng, header, footer thống nhất  
✔️ Áp dụng template inheritance (layout chung)  
✔️ Cập nhật README.md mô tả tiến độ và hướng dẫn chạy thử  

---

## 7. Cấu trúc thư mục (rút gọn)
```
Du-An-Python/
│── config/
│── store/
│── templates/
│── static/
│── media/
│── venv/
│── db.sqlite3
│── manage.py
│── README.md
```

---

## 8. Hướng dẫn chạy dự án

### 🚀 Quick Start (Khuyến nghị)

#### Cho Windows:
1. **Chạy file setup tự động**:
   ```cmd
   # Double-click setup.bat hoặc chạy trong Command Prompt
   setup.bat
   ```
   Chọn `1` cho local development hoặc `2` cho production.

#### Cho Linux/Mac:
1. **Chạy script setup tự động**:
   ```bash
   python setup.py
   ```
   Chọn `local` cho development hoặc `production` cho deployment.

#### Tất cả nền tảng:
2. **Chạy server**:
   ```bash
   python run.py
   ```

3. **Truy cập ứng dụng**:
   - Local: http://127.0.0.1:8000
   - Production: https://idvn.io.vn

### 🔧 Setup thủ công (Manual Setup)

1. **Clone project**
   ```bash
   git clone <repository-url>
   cd shop-dien-thoai
   ```

2. **Cài đặt thư viện**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình environment**
   ```bash
   cp .env.example .env.local  # Cho local development
   # Hoặc
   cp .env.example .env.production  # Cho production
   ```

4. **Cập nhật environment variables**
   Chỉnh sửa file `.env` với thông tin thực tế.

5. **Chạy database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Tạo tài khoản admin**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files (chỉ production)**
   ```bash
   python manage.py collectstatic
   ```

### 🌐 Production Deployment

1. **Upload code lên server production**
2. **Chạy script deployment**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

### 📋 Thông tin tài khoản mặc định
- **Username**: admin
- **Password**: admin123
- **Email**: admin@example.com

⚠️ **Quan trọng**: Hãy đổi mật khẩu admin mặc định sau lần đầu đăng nhập!
python manage.py runserver

Bước 7: Truy cập hệ thống

Trang chủ: http://127.0.0.1:8000/

Trang quản trị: http://127.0.0.1:8000/admin/