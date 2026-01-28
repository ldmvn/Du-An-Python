📱 Phone Store – Django Web Application
1. Giới thiệu dự án

Dự án Phone Store là website bán điện thoại di động được xây dựng bằng Python Django.
Hệ thống hỗ trợ hiển thị danh sách sản phẩm, quản lý sản phẩm qua trang quản trị, đăng nhập – đăng ký người dùng và sử dụng layout giao diện chung cho toàn bộ website.

Dự án được thực hiện nhằm đáp ứng yêu cầu học phần về xây dựng ứng dụng web với Python.

2. Mục tiêu

Xây dựng ứng dụng web hoàn chỉnh bằng Django

Thiết kế cơ sở dữ liệu với các bảng dữ liệu chính

Hiển thị dữ liệu động từ database

Áp dụng template inheritance (layout chung)

Triển khai chức năng đăng nhập – đăng ký người dùng

3. Công nghệ sử dụng

  Ngôn ngữ: Python 3

  Framework: Django

  Cơ sở dữ liệu: SQLite

  Frontend: HTML, CSS, Bootstrap

  Quản lý dữ liệu: Django Admin

4. Các chức năng chính

  Hiển thị danh sách sản phẩm điện thoại

  Thêm, sửa, xoá sản phẩm (Admin)

  Đăng ký tài khoản người dùng

  Đăng nhập / đăng xuất

  Phân quyền người dùng (User / Admin)

  Sử dụng template inheritance với base.html

  Menu điều hướng, header thống nhất trên toàn website

5. Cấu trúc dữ liệu

User (sử dụng hệ thống xác thực mặc định của Django)

Product

  name

  price

  image

  description

  created_at

6. Tiến độ thực hiện

✔ Tạo project và app Django

✔ Thiết kế model và database

✔ Thêm dữ liệu mẫu (seed data)

✔ Hiển thị dữ liệu trên trang web

✔ Cài đặt đăng nhập – đăng ký

✔ Template inheritance (layout chung)

✔ Hoàn thiện giao diện cơ bản

7. Hướng dẫn cài đặt và chạy thử
Bước 1: Clone project
  git clone <link-github>
  cd Du-An-Python

Bước 2: Tạo môi trường ảo
  python -m venv venv
  venv\Scripts\activate

Bước 3: Cài đặt thư viện
  pip install -r requirements.txt

Bước 4: Khởi tạo database
  python manage.py migrate
  python manage.py createsuperuser

Bước 5: Chạy server
  python manage.py runserver


Truy cập website tại:
👉 http://127.0.0.1:8000/

8. Tài khoản mẫu

  Admin: tạo bằng createsuperuser

  User: đăng ký trực tiếp trên website

9. Hướng phát triển

  hêm chức năng đặt hàng

  Thêm thống kê – báo cáo

  Cải thiện giao diện người dùng

  Tích hợp thanh toán online