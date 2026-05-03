---
name: vnpay-audit
description: "Use when: vnpay, VNPay, thanh toan VNPAY, checksum, ipn, vnpay return, loi giao dich VNPAY. Huong dan phan tich tich hop VNPAY va debug giao dich that bai."
---

# VNPAY Audit Skill

## Muc tieu
- Tom tat luong tich hop VNPAY trong he thong.
- Ra soat logic checksum (vnp_SecureHash).
- Kiem tra luong IPN va return.
- Dua ra checklist debug khi giao dich that bai.

## Cach su dung
Khi duoc goi, thuc hien nhanh cac buoc sau:

1) Xac dinh file trong codebase
- Tim cac file chinh lien quan VNPAY.
- Uu tien: utils, views, models, settings, frontend checkout.

2) Kiem tra cau hinh
- Doc VNPAY_CONFIG: TMN code, hash secret, URL, return/ipn URL.
- Dam bao URL return/ipn phu hop moi truong (local/sandbox/prod).

3) Kiem tra checksum
- Xem ham tinh checksum (HMAC SHA512).
- Dam bao cac tham so duoc sort theo key.
- Dam bao khong kem vnp_SecureHash vao chuoi tinh.
- Dam bao encoding dung (quote_plus).

4) Kiem tra vnpay_create
- Validate amount > 0.
- Tao order_code duy nhat.
- Tao VNPayPayment status pending.
- Build payment_url va tra ve frontend.

5) Kiem tra vnpay_return
- Chi lay param bat dau bang vnp_.
- Verify checksum + response_code.
- Neu OK: cap nhat payment, tao Order, tao OrderItem, xoa cart.
- Neu fail: cap nhat payment failed va thong bao.

6) Kiem tra vnpay_ipn
- Verify checksum.
- Cap nhat payment paid/failed.
- Tra RspCode theo spec VNPAY.

7) Checklist debug nhanh
- Hash secret dung chua?
- Return URL va IPN URL co hop le, truy cap duoc?
- response_code != 00 thi message gi?
- session mat items_param hay order_code?
- vnp_Amount co nhan 100 chua?

## Output mong muon
- Danh sach file lien quan VNPAY (link file).
- Nhan xet nhanh ve checksum, return, ipn.
- Danh sach buoc debug uu tien (1-5 buoc).
